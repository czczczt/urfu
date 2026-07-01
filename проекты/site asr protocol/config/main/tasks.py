from celery import shared_task
import logging
import threading
from time import perf_counter

from django.db import transaction
from django.utils import timezone
from gigachat.exceptions import ResponseError

from main.transcribe_worker import (
    TranscribeWorker,
    ProtocolWorker,
    CONFIG,
    GigachatLockBusy,
)

_tls = threading.local()
logger = logging.getLogger(__name__)


def _get_transcribe_worker() -> TranscribeWorker:
    """Отдельный WhisperX-воркер на поток/процесс Celery (модели не thread-safe)."""
    worker = getattr(_tls, "transcribe_worker", None)
    if worker is None:
        worker = TranscribeWorker(config=CONFIG)
        _tls.transcribe_worker = worker
    return worker


def _get_protocol_worker() -> ProtocolWorker:
    worker = getattr(_tls, "protocol_worker", None)
    if worker is None:
        worker = ProtocolWorker()
        _tls.protocol_worker = worker
    return worker


def _is_final_retry(task) -> bool:
    return task.request.retries >= task.max_retries


def _split_segment(seg: dict) -> list[dict]:
    words = seg.get("words", [])
    seg_speaker = seg.get("speaker", "Unknown")

    if not words or not any(w.get("speaker") for w in words):
        return [{
            "speaker": seg_speaker,
            "text": seg.get("text", "").strip(),
            "start": seg.get("start", 0.0),
            "end": seg.get("end", 0.0),
        }]

    chunks = []
    current_speaker = words[0].get("speaker") or seg_speaker
    current_words = [words[0]]

    for w in words[1:]:
        sp = w.get("speaker") or current_speaker
        if sp != current_speaker:
            chunks.append({
                "speaker": current_speaker,
                "text": " ".join(x["word"] for x in current_words).strip(),
                "start": current_words[0].get("start", 0.0),
                "end": current_words[-1].get("end", 0.0),
            })
            current_speaker = sp
            current_words = [w]
        else:
            current_words.append(w)

    chunks.append({
        "speaker": current_speaker,
        "text": " ".join(x["word"] for x in current_words).strip(),
        "start": current_words[0].get("start", 0.0),
        "end": current_words[-1].get("end", 0.0),
    })
    return chunks


def _resolve_file_path(raw_path: str) -> str:
    from django.conf import settings as django_settings
    import os

    path = str(raw_path or "").strip()
    if not path:
        return path
    if os.path.exists(path):
        return path

    normalized = path.replace("\\", "/")
    marker = "/media/"
    if marker in normalized:
        rel_path = normalized.split(marker, 1)[1].lstrip("/")
        candidate = os.path.join(str(django_settings.MEDIA_ROOT), rel_path)
        if os.path.exists(candidate):
            return candidate

    return path


def _extract_response_status_code(exc: ResponseError):
    status_code = getattr(exc, "status_code", None)
    if isinstance(status_code, int):
        return status_code
    if len(getattr(exc, "args", ())) > 1 and isinstance(exc.args[1], int):
        return exc.args[1]
    return None


def _claim_transcription(task, transcription_id: int):
    """Блокировка строки: защита от дублей задач и очистка частичных результатов."""
    from .models import Result, Transcription

    with transaction.atomic():
        try:
            transcription = (
                Transcription.objects.select_for_update()
                .select_related("file")
                .get(id=transcription_id)
            )
        except Transcription.DoesNotExist:
            return None

        if transcription.status == Transcription.Status.COMPLETED:
            return None

        if (
            transcription.status == Transcription.Status.PROCESSING
            and task.request.retries == 0
        ):
            logger.info(
                "Skip duplicate transcription task transcription_id=%s",
                transcription_id,
            )
            return None

        transcription.status = Transcription.Status.PROCESSING
        transcription.save(update_fields=["status"])
        Result.objects.filter(transcription_id=transcription_id).delete()
        return transcription


@shared_task(bind=True, max_retries=3)
def run_transcription(self, transcription_id: int):
    from .models import Result, Transcription

    transcription = _claim_transcription(self, transcription_id)
    if transcription is None:
        return

    try:
        transcribe_started = perf_counter()
        resolved_path = _resolve_file_path(transcription.file.path_to_file)
        if resolved_path != transcription.file.path_to_file:
            transcription.file.path_to_file = resolved_path
            transcription.file.save(update_fields=["path_to_file"])
        segments = _get_transcribe_worker().transcribe_and_diarize(resolved_path)
        transcribe_elapsed = perf_counter() - transcribe_started
        logger.info(
            "Transcription stage finished for transcription_id=%s in %.2fs",
            transcription_id,
            transcribe_elapsed,
        )
        if not Transcription.objects.filter(id=transcription_id).exists():
            return

        chunks = [
            chunk
            for seg in segments
            for chunk in _split_segment(seg)
        ]

        with transaction.atomic():
            if not Transcription.objects.filter(id=transcription_id).exists():
                return

            Result.objects.filter(transcription_id=transcription_id).delete()
            Result.objects.bulk_create([
                Result(
                    transcription_id=transcription_id,
                    speaker=chunk["speaker"],
                    text=chunk["text"],
                    phrase_start_time=chunk["start"],
                    phrase_end_time=chunk["end"],
                )
                for chunk in chunks
            ])

            Transcription.objects.filter(id=transcription_id).update(
                status=Transcription.Status.COMPLETED,
                protocol_status=Transcription.ProtocolStatus.NOT_STARTED,
                execution_datetime=timezone.now(),
            )

        logger.info(
            "Transcription completed transcription_id=%s, enqueueing GigaChat protocol (%s chunks)",
            transcription_id,
            len(chunks),
        )
        enqueue_protocol_generation(transcription_id)

    except Exception as exc:
        if _is_final_retry(self):
            Transcription.objects.filter(id=transcription_id).update(
                status=Transcription.Status.FAILED,
            )
            logger.exception(
                "Transcription failed permanently transcription_id=%s",
                transcription_id,
            )
            return

        logger.warning(
            "Transcription retry %s/%s transcription_id=%s: %s",
            self.request.retries + 1,
            self.max_retries,
            transcription_id,
            exc,
        )
        Transcription.objects.filter(id=transcription_id).update(
            status=Transcription.Status.PROCESSING,
        )
        raise self.retry(exc=exc, countdown=60)


def enqueue_protocol_generation(transcription_id: int) -> bool:
    from .models import Transcription

    with transaction.atomic():
        try:
            transcription = (
                Transcription.objects.select_for_update()
                .get(id=transcription_id)
            )
        except Transcription.DoesNotExist:
            return False

        if transcription.effective_status != Transcription.Status.COMPLETED:
            return False
        if transcription.protocol_status == Transcription.ProtocolStatus.PROCESSING:
            return False
        if transcription.protocol_status not in (
            Transcription.ProtocolStatus.NOT_STARTED,
            Transcription.ProtocolStatus.FAILED,
            Transcription.ProtocolStatus.COMPLETED,
        ):
            return False
        from .models import Result

        if not Result.objects.filter(transcription_id=transcription_id).exists():
            return False

        transcription.protocol_status = Transcription.ProtocolStatus.PROCESSING
        transcription.save(update_fields=["protocol_status"])

    logger.info("Protocol task queued for transcription_id=%s (GigaChat)", transcription_id)
    run_protocol_generation.delay(transcription_id)
    return True


def _claim_protocol(task, transcription_id: int):
    from .models import Transcription

    with transaction.atomic():
        try:
            transcription = (
                Transcription.objects.select_for_update().get(id=transcription_id)
            )
        except Transcription.DoesNotExist:
            return None

        if transcription.effective_status != Transcription.Status.COMPLETED:
            return None

        if transcription.protocol_status == Transcription.ProtocolStatus.PROCESSING:
            return transcription

        transcription.protocol_status = Transcription.ProtocolStatus.PROCESSING
        transcription.save(update_fields=["protocol_status"])
        return transcription


@shared_task(bind=True, max_retries=48)
def run_protocol_generation(self, transcription_id: int):
    from .models import MeetingProtocol, Result, Transcription

    transcription = _claim_protocol(self, transcription_id)
    if transcription is None:
        return

    try:
        chunks = list(
            Result.objects.filter(transcription_id=transcription_id)
            .order_by("phrase_start_time")
            .values("speaker", "text")
        )

        if not chunks:
            transcription.protocol_status = Transcription.ProtocolStatus.FAILED
            transcription.save(update_fields=["protocol_status"])
            return

        segment_payload = [
            {"speaker": c.get("speaker"), "text": c.get("text")}
            for c in chunks
            if (c.get("text") or "").strip()
        ]
        started = perf_counter()
        try:
            logger.info(
                "GigaChat request started transcription_id=%s",
                transcription_id,
            )
            proto = _get_protocol_worker().summarize(segment_payload)
        except GigachatLockBusy as exc:
            logger.info(
                "GigaChat queue busy, requeue transcription_id=%s: %s",
                transcription_id,
                exc,
            )
            raise self.retry(exc=exc, countdown=10)
        elapsed = perf_counter() - started
        logger.info(
            "Protocol stage finished for transcription_id=%s in %.2fs",
            transcription_id,
            elapsed,
        )

        MeetingProtocol.objects.update_or_create(
            transcription_id=transcription_id,
            defaults={
                "brief_text": proto.brief_summary or "",
                "protocol_text": proto.meeting_recap or "",
                "compressed_text": proto.timeline_recap or "",
            },
        )

        update_fields = ["protocol_status", "edit_datetime"]
        transcription.edit_datetime = timezone.now()
        if proto.brief_summary:
            transcription.description = proto.brief_summary
            update_fields.append("description")

        transcription.protocol_status = Transcription.ProtocolStatus.COMPLETED
        transcription.save(update_fields=update_fields)

    except ResponseError as exc:
        status_code = _extract_response_status_code(exc)
        if status_code in {401, 402, 403}:
            if Transcription.objects.filter(id=transcription_id).exists():
                Transcription.objects.filter(id=transcription_id).update(
                    protocol_status=Transcription.ProtocolStatus.FAILED,
                )
            return

        if _is_final_retry(self):
            if Transcription.objects.filter(id=transcription_id).exists():
                Transcription.objects.filter(id=transcription_id).update(
                    protocol_status=Transcription.ProtocolStatus.FAILED,
                )
            logger.exception(
                "Protocol failed permanently transcription_id=%s",
                transcription_id,
            )
            return

        logger.warning(
            "Protocol retry %s/%s transcription_id=%s: %s",
            self.request.retries + 1,
            self.max_retries,
            transcription_id,
            exc,
        )
        Transcription.objects.filter(id=transcription_id).update(
            protocol_status=Transcription.ProtocolStatus.PROCESSING,
        )
        raise self.retry(exc=exc, countdown=30)

    except Exception as exc:
        if _is_final_retry(self):
            if Transcription.objects.filter(id=transcription_id).exists():
                Transcription.objects.filter(id=transcription_id).update(
                    protocol_status=Transcription.ProtocolStatus.FAILED,
                )
            logger.exception(
                "Protocol failed permanently transcription_id=%s",
                transcription_id,
            )
            return

        logger.warning(
            "Protocol retry %s/%s transcription_id=%s: %s",
            self.request.retries + 1,
            self.max_retries,
            transcription_id,
            exc,
        )
        Transcription.objects.filter(id=transcription_id).update(
            protocol_status=Transcription.ProtocolStatus.PROCESSING,
        )
        raise self.retry(exc=exc, countdown=30)


@shared_task(name="main.protocol_tasks.run_protocol_generation")
def run_protocol_generation_legacy(transcription_id: int):
    return run_protocol_generation.delay(transcription_id)
