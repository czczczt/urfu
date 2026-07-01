import io
import json
import os
import platform
import re
import subprocess
from html import escape
from urllib.parse import quote

import markdown
try:
    import psutil
except ImportError:
    psutil = None

from django.conf import settings as django_settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import FileResponse, Http404, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.safestring import mark_safe
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import File, Transcription, Result, FileAccess, MeetingProtocol
from login.models import User


def _has_edit_permission(transcription, user):
    if transcription.initializer == user:
        return True
    access = FileAccess.objects.filter(file=transcription.file, user=user).first()
    return access and access.permission == "edit"
from .tasks import run_transcription
from .tasks import enqueue_protocol_generation

ALLOWED_EXTENSIONS = {"mp4", "mkv", "avi", "mov", "webm", "mp3", "wav"}

CONTENT_TYPES = {
    "mp4": "video/mp4",
    "mkv": "video/x-matroska",
    "avi": "video/x-msvideo",
    "mov": "video/quicktime",
    "webm": "video/webm",
    "mp3": "audio/mpeg",
    "wav": "audio/wav",
}


def _save_upload(file_obj, user_id: int) -> str:
    upload_dir = os.path.join(django_settings.MEDIA_ROOT, str(user_id))
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, file_obj.name)
    if os.path.exists(file_path):
        base, ext = os.path.splitext(file_obj.name)
        i = 1
        while os.path.exists(os.path.join(upload_dir, f"{base}_{i}{ext}")):
            i += 1
        file_path = os.path.join(upload_dir, f"{base}_{i}{ext}")
    with open(file_path, "wb") as f:
        for chunk in file_obj.chunks():
            f.write(chunk)
    return file_path


def _get_media_duration_seconds(file_path: str):
    try:
        probe = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "json",
                file_path,
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        data = json.loads(probe.stdout or "{}")
        duration = float(data.get("format", {}).get("duration", 0.0))
        return duration if duration > 0 else None
    except Exception:
        return None


def _resolve_file_path(raw_path: str) -> str:
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


def _render_markdown(md_text: str):
    text = str(md_text or "").strip()
    if not text:
        return mark_safe("")

    # Escape raw HTML first, then apply markdown formatting.
    # This preserves markdown syntax while avoiding HTML/script injection.
    safe_source = escape(text)
    rendered = markdown.markdown(
        safe_source,
        extensions=["extra", "nl2br", "sane_lists"],
    )
    return mark_safe(rendered)


def _is_service_admin(user):
    return bool(
        user.is_authenticated
        and (
            user.role in (User.Role.ADMIN, User.Role.USER_AND_ADMIN)
            or user.is_staff
            or user.is_superuser
        )
    )


def _format_bytes(bytes_value: int | None) -> str:
    if not bytes_value:
        return "—"
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if bytes_value < 1024:
            return f"{bytes_value:.1f} {unit}"
        bytes_value /= 1024
    return f"{bytes_value:.1f} PB"


def _format_seconds(seconds: int | None) -> str:
    if seconds is None:
        return "—"
    minutes, sec = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    parts = []
    if days:
        parts.append(f"{days} дн")
    if hours:
        parts.append(f"{hours} ч")
    if minutes:
        parts.append(f"{minutes} мин")
    if sec or not parts:
        parts.append(f"{sec} сек")
    return " ".join(parts)


def _get_service_metrics() -> dict:
    metrics = {
        "cpu_percent": None,
        "memory_total": None,
        "memory_used": None,
        "memory_percent": None,
        "disk_total": None,
        "disk_used": None,
        "disk_percent": None,
        "uptime_seconds": None,
        "celery_workers": 0,
        "process_count": None,
        "platform": platform.platform(),
        "memory_total_human": "—",
        "memory_used_human": "—",
        "disk_total_human": "—",
        "disk_used_human": "—",
        "uptime_human": "—",
        "redis_connected": None,
    }
    try:
        import redis

        client = redis.from_url(django_settings.CELERY_BROKER_URL)
        metrics["redis_connected"] = client.ping()
    except Exception:
        metrics["redis_connected"] = False

    if psutil is None:
        return metrics

    try:
        metrics["cpu_percent"] = psutil.cpu_percent(interval=0.3)
        vm = psutil.virtual_memory()
        metrics["memory_total"] = vm.total
        metrics["memory_used"] = vm.used
        metrics["memory_percent"] = vm.percent
        disk = psutil.disk_usage(str(django_settings.BASE_DIR))
        metrics["disk_total"] = disk.total
        metrics["disk_used"] = disk.used
        metrics["disk_percent"] = disk.percent
        metrics["uptime_seconds"] = int(timezone.now().timestamp() - psutil.boot_time())
        metrics["memory_total_human"] = _format_bytes(vm.total)
        metrics["memory_used_human"] = _format_bytes(vm.used)
        metrics["disk_total_human"] = _format_bytes(disk.total)
        metrics["disk_used_human"] = _format_bytes(disk.used)
        metrics["uptime_human"] = _format_seconds(metrics["uptime_seconds"])
        processes = list(psutil.process_iter(["name", "cmdline"]))
        metrics["process_count"] = len(processes)
        celery_workers = 0
        for proc in processes:
            cmdline = " ".join(proc.info.get("cmdline") or []) if proc.info.get("cmdline") else ""
            name = (proc.info.get("name") or "").lower()
            if "celery" in cmdline.lower() or "celery" in name:
                celery_workers += 1
        metrics["celery_workers"] = celery_workers
    except Exception:
        pass

    return metrics


def _check_service_admin(request):
    if not _is_service_admin(request.user):
        return HttpResponseForbidden("Требуются права администратора.")
    return None


def main_page(request):
    if not request.user.is_authenticated:
        return redirect("auth")
    return render(
        request,
        "main.html",
        {"is_service_admin": _is_service_admin(request.user)},
    )


@login_required
def admin_panel(request):
    admin_check = _check_service_admin(request)
    if admin_check:
        return admin_check

    if request.method == "POST" and request.POST.get("action") == "create_user":
        login_value = request.POST.get("login", "").strip()
        password_value = request.POST.get("password", "")
        role_value = request.POST.get("role", User.Role.USER)
        is_active = True
        is_staff = False

        if not login_value or not password_value:
            messages.error(request, "Логин и пароль обязательны для создания пользователя.")
        elif User.objects.filter(login=login_value).exists():
            messages.error(request, "Пользователь с таким логином уже существует.")
        else:
            User.objects.create_user(
                login=login_value,
                password=password_value,
                role=role_value,
                is_active=is_active,
                is_staff=is_staff,
            )
            messages.success(request, "Пользователь успешно создан.")
            return redirect("admin_panel")

    users = User.objects.order_by("login").all()
    metrics = _get_service_metrics()
    stats = {
        "total_users": users.count(),
        "active_users": users.filter(is_active=True).count(),
        "admin_users": users.filter(role__in=(User.Role.ADMIN, User.Role.USER_AND_ADMIN)).count(),
        "total_files": File.objects.count(),
        "total_transcriptions": Transcription.objects.count(),
        "processing_transcriptions": Transcription.objects.filter(status=Transcription.Status.PROCESSING).count(),
        "pending_transcriptions": Transcription.objects.filter(status=Transcription.Status.PENDING).count(),
        "failed_transcriptions": Transcription.objects.filter(status=Transcription.Status.FAILED).count(),
        "protocol_processing": Transcription.objects.filter(protocol_status=Transcription.ProtocolStatus.PROCESSING).count(),
    }
    return render(request, "admin_panel.html", {
        "users": users,
        "metrics": metrics,
        "stats": stats,
    })


@login_required
def admin_user_edit(request, user_id):
    admin_check = _check_service_admin(request)
    if admin_check:
        return admin_check

    user_obj = get_object_or_404(User, id=user_id)
    if request.method == "POST":
        role_value = request.POST.get("role", user_obj.role)
        is_superuser = request.POST.get("is_superuser") == "1"
        password_value = request.POST.get("password", "")

        user_obj.role = role_value
        user_obj.is_superuser = is_superuser
        if password_value:
            user_obj.set_password(password_value)
        user_obj.save()
        messages.success(request, "Пользователь сохранён.")
        return redirect("admin_panel")

    return render(request, "admin_user_edit.html", {"user_obj": user_obj})


@login_required
@require_POST
def admin_user_delete(request, user_id):
    admin_check = _check_service_admin(request)
    if admin_check:
        return admin_check

    user_obj = get_object_or_404(User, id=user_id)
    if user_obj.id == request.user.id:
        messages.error(request, "Нельзя отключить собственную учётную запись.")
        return redirect("admin_panel")

    user_obj.is_active = False
    user_obj.save(update_fields=["is_active"])
    messages.success(request, "Пользователь отключён.")
    return redirect("admin_panel")


@login_required
def history_page(request):
    qs = (
        Transcription.objects.filter(
            Q(initializer=request.user) | Q(file__accesses__user=request.user)
        ).distinct()
        .select_related("file")
        .prefetch_related("results")
        .only(
            "id",
            "status",
            "protocol_status",
            "execution_datetime",
            "file__name",
            "file__extension",
        )
    )

    name = request.GET.get("name", "").strip()
    status = request.GET.get("status", "").strip()
    date_start = request.GET.get("date_start", "").strip()
    date_end = request.GET.get("date_end", "").strip()
    page = max(int(request.GET.get("page", 1)), 1)

    if name:
        qs = qs.filter(file__name__icontains=name)
    if status:
        qs = qs.filter(status=status)
    if date_start:
        qs = qs.filter(execution_datetime__date__gte=date_start)
    if date_end:
        qs = qs.filter(execution_datetime__date__lte=date_end)

    per_page = 20
    total = qs.count()
    total_pages = max((total + per_page - 1) // per_page, 1)
    offset = (page - 1) * per_page

    return render(request, "history.html", {
        "transcriptions": qs[offset: offset + per_page],
        "page": page,
        "total_pages": total_pages,
        "page_range": range(1, total_pages + 1),
        "filters": {"name": name, "status": status, "date_start": date_start, "date_end": date_end},
    })


@login_required
def transcription_page(request, transcription_id):
    transcription = get_object_or_404(
        Transcription.objects.select_related("file").filter(
            Q(initializer=request.user) | Q(file__accesses__user=request.user)
        ),
        id=transcription_id,
    )
    can_edit = _has_edit_permission(transcription, request.user)

    if request.method == "POST":
        if not can_edit:
            return JsonResponse({"error": "Недостаточно прав для редактирования."}, status=403)
        results = list(Result.objects.filter(transcription=transcription))

        def _to_float(val):
            try:
                return float(str(val).strip().replace(",", "."))
            except (ValueError, TypeError):
                return 0.0

        # Speaker renames: optional "all segments that had this old label" vs per-row only
        # (controlled by checkbox `speaker_rename_all` in transcription edit form).
        rename_all_same = request.POST.get("speaker_rename_all") == "1"
        if rename_all_same:
            rename_map = {}
            for result in results:
                new_speaker = request.POST.get(f"speaker_{result.id}", result.speaker).strip()
                if new_speaker and new_speaker != result.speaker:
                    rename_map[result.speaker] = new_speaker
            for old, new in rename_map.items():
                Result.objects.filter(transcription=transcription, speaker=old).update(speaker=new)
            for result in results:
                result.text = request.POST.get(f"text_{result.id}", result.text)
                result.phrase_start_time = _to_float(request.POST.get(f"start_{result.id}", result.phrase_start_time))
                result.phrase_end_time = _to_float(request.POST.get(f"end_{result.id}", result.phrase_end_time))
            Result.objects.bulk_update(results, ["text", "phrase_start_time", "phrase_end_time"])
        else:
            for result in results:
                new_speaker = request.POST.get(f"speaker_{result.id}", result.speaker).strip()
                if new_speaker:
                    result.speaker = new_speaker
                result.text = request.POST.get(f"text_{result.id}", result.text)
                result.phrase_start_time = _to_float(request.POST.get(f"start_{result.id}", result.phrase_start_time))
                result.phrase_end_time = _to_float(request.POST.get(f"end_{result.id}", result.phrase_end_time))
            Result.objects.bulk_update(results, ["speaker", "text", "phrase_start_time", "phrase_end_time"])
        transcription.edit_datetime = timezone.now()
        transcription.save(update_fields=["edit_datetime"])
        return redirect("transcription", transcription_id=transcription_id)

    results = list(Result.objects.filter(transcription=transcription).order_by("phrase_start_time"))
    protocol = MeetingProtocol.objects.filter(transcription=transcription).first()
    has_protocol = bool(
        protocol
        and (
            str(getattr(protocol, "brief_text", "")).strip()
            or str(getattr(protocol, "protocol_text", "")).strip()
            or str(getattr(protocol, "compressed_text", "")).strip()
        )
    )
    timeline_recap_md = ""
    protocol_html = mark_safe("")
    timeline_html = mark_safe("")
    if protocol and str(getattr(protocol, "compressed_text", "")).strip():
        # Keep markdown formatting, but escape speaker ids like SPEAKER_00
        # to avoid accidental emphasis rendering.
        timeline_recap_md = re.sub(
            r"\b(SPEAKER)_(\d+)\b",
            r"\1\\_\2",
            str(protocol.compressed_text),
        )
        timeline_html = _render_markdown(timeline_recap_md)
    if protocol and str(getattr(protocol, "protocol_text", "")).strip():
        protocol_html = _render_markdown(str(protocol.protocol_text))
    can_start_transcription = can_edit and (
        transcription.status == Transcription.Status.PENDING
        or (
            transcription.status == Transcription.Status.FAILED
            and not results
        )
    )
    has_transcript = bool(results)
    can_show_protocol_button = can_edit and has_transcript
    can_start_protocol = (
        can_show_protocol_button
        and transcription.protocol_status != Transcription.ProtocolStatus.PROCESSING
    )
    speakers = sorted({r.speaker.strip() for r in results})
    for i, r in enumerate(results):
        r.show_speaker = (i == 0 or results[i - 1].speaker != r.speaker)

    # Access lists for UI (include owner/uploader as implicit viewer/editor).
    owner_login = str(getattr(transcription.file.owner, "login", "") or "").strip()
    access_logins = list(
        FileAccess.objects.filter(file=transcription.file)
        .select_related("user")
        .values_list("user__login", flat=True)
    )
    view_set = {l for l in ([owner_login] + access_logins) if str(l or "").strip()}
    edit_set = {owner_login} if owner_login else set()
    edit_set.update(
        FileAccess.objects.filter(file=transcription.file, permission="edit")
        .select_related("user")
        .values_list("user__login", flat=True)
    )

    view_logins = sorted(view_set, key=lambda x: str(x).lower())
    edit_logins = sorted({l for l in edit_set if str(l or "").strip()}, key=lambda x: str(x).lower())

    # Owner is displayed separately in UI.
    view_others = [l for l in view_logins if l != owner_login]
    edit_others = [l for l in edit_logins if l != owner_login]

    return render(request, "transcription.html", {
        "transcription": transcription,
        "protocol": protocol,
        "has_protocol": has_protocol,
        "timeline_recap_md": timeline_recap_md,
        "protocol_html": protocol_html,
        "timeline_html": timeline_html,
        "can_start_transcription": can_start_transcription,
        "can_show_protocol_button": can_show_protocol_button,
        "can_start_protocol": can_start_protocol,
        "results": results,
        "speakers": speakers,
        "can_edit": can_edit,
        "owner_login": owner_login,
        "view_logins": view_logins,
        "edit_logins": edit_logins,
        "view_others": view_others,
        "edit_others": edit_others,
    })


@login_required
@require_POST
def load_page(request):
    videos = request.FILES.getlist("video")
    if not videos:
        return render(request, "main.html", {"error": "Файл не выбран."})

    invalid_files = []
    for v in videos:
        parts = v.name.rsplit(".", 1)
        ext = parts[-1].lower() if len(parts) > 1 else ""
        if ext not in ALLOWED_EXTENSIONS:
            invalid_files.append(v.name)
    if invalid_files:
        return render(
            request,
            "main.html",
            {"error": f"Недопустимый формат файла: {', '.join(invalid_files)}"},
        )

    queued = []
    for video in videos:
        ext = video.name.rsplit(".", 1)[-1].lower()
        file_path = _save_upload(video, request.user.id)
        file_obj = File.objects.create(
            name=video.name.rsplit(".", 1)[0],
            extension=ext,
            owner=request.user,
            load_datetime=timezone.now(),
            path_to_file=file_path,
        )
        transcription = Transcription.objects.create(
            file=file_obj,
            name=file_obj.name,
            initializer=request.user,
            status=Transcription.Status.PENDING,
        )
        duration = _get_media_duration_seconds(file_path)
        queued.append(
            {
                "transcription_id": transcription.id,
                "duration": duration if duration is not None else float("inf"),
            }
        )

    for item in sorted(queued, key=lambda x: x["duration"]):
        run_transcription.delay(item["transcription_id"])

    return redirect("history")


@login_required
def video_page(request, id_video):
    file_obj = get_object_or_404(File, id=id_video)
    has_any_access = (file_obj.owner_id == request.user.id) or FileAccess.objects.filter(
        file=file_obj,
        user=request.user,
    ).exists()
    if not has_any_access:
        raise Http404

    if request.method == "GET":
        resolved_path = _resolve_file_path(file_obj.path_to_file)
        if not os.path.exists(resolved_path):
            raise Http404
        if resolved_path != file_obj.path_to_file:
            file_obj.path_to_file = resolved_path
            file_obj.save(update_fields=["path_to_file"])
        content_type = CONTENT_TYPES.get(file_obj.extension, "application/octet-stream")
        response = FileResponse(
            open(resolved_path, "rb"),
            content_type=content_type,
            as_attachment=False,
        )
        response["Accept-Ranges"] = "bytes"
        return response

    # Upload/replace video: only owner or edit access
    has_edit_access = (file_obj.owner_id == request.user.id) or FileAccess.objects.filter(
        file=file_obj,
        user=request.user,
        permission="edit",
    ).exists()
    if not has_edit_access:
        return JsonResponse({"error": "Недостаточно прав для редактирования."}, status=403)

    video = request.FILES.get("video")
    if not video:
        return JsonResponse({"error": "Файл не передан."}, status=400)

    file_path = _save_upload(video, request.user.id)
    file_obj.path_to_file = file_path
    file_obj.save(update_fields=["path_to_file"])
    return JsonResponse({"ok": True})


@login_required
@require_POST
def phrase_page(request):
    try:
        body = json.loads(request.body)
        transcription_id = body["id"]
        last_time = float(body.get("last_time", 0.0))
    except (ValueError, KeyError, TypeError):
        return JsonResponse({"error": "Неверный формат запроса."}, status=400)

    transcription = get_object_or_404(Transcription, id=transcription_id, initializer=request.user)
    results = (
        Result.objects.filter(transcription=transcription, phrase_start_time__gt=last_time)
        .order_by("phrase_start_time")
        .values("id", "speaker", "text", "phrase_start_time", "phrase_end_time")
    )
    return JsonResponse({"results": list(results)})


@login_required
@require_POST
def delete_transcription(request, transcription_id):
    transcription = get_object_or_404(
        Transcription.objects.filter(
            Q(initializer=request.user) | Q(file__accesses__user=request.user)
        ),
        id=transcription_id,
    )
    if not _has_edit_permission(transcription, request.user):
        return HttpResponseForbidden("Недостаточно прав.")
    if transcription.status not in (
        Transcription.Status.PENDING,
        Transcription.Status.PROCESSING,
        Transcription.Status.COMPLETED,
        Transcription.Status.FAILED,
    ):
        return HttpResponseForbidden("Удаление в этом статусе недоступно.")

    file_obj = transcription.file
    file_path = _resolve_file_path(file_obj.path_to_file)
    # DB cleanup:
    # - deleting File cascades to Transcription(s), Result, MeetingProtocol and FileAccess
    # - if multiple transcriptions share one file, delete only requested transcription
    with transaction.atomic():
        if file_obj.transcriptions.exclude(id=transcription.id).exists():
            transcription.delete()
        else:
            file_obj.delete()
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except OSError:
            # File can be locked by an active worker; DB objects are already removed.
            pass
    return redirect("history")


@login_required
@require_POST
def rename_speaker(request, transcription_id):
    transcription = get_object_or_404(
        Transcription.objects.filter(
            Q(initializer=request.user) | Q(file__accesses__user=request.user)
        ),
        id=transcription_id,
    )
    if not _has_edit_permission(transcription, request.user):
        return JsonResponse({"error": "Недостаточно прав для редактирования."}, status=403)
    old_name = request.POST.get("old_name", "").strip()
    new_name = request.POST.get("new_name", "").strip()
    if old_name and new_name:
        Result.objects.filter(transcription=transcription, speaker=old_name).update(speaker=new_name)
        transcription.edit_datetime = timezone.now()
        transcription.save(update_fields=["edit_datetime"])
    return redirect("transcription", transcription_id=transcription_id)


@login_required
def export_transcription(request, transcription_id):
    transcription = get_object_or_404(Transcription, id=transcription_id)
    # Check access
    if transcription.initializer != request.user and not FileAccess.objects.filter(file=transcription.file, user=request.user).exists():
        raise Http404
    output = transcription.get_formatted_output()
    meeting_name = (transcription.file.name or "meeting").strip()
    safe_name = re.sub(r"[\\/:*?\"<>|]+", "_", meeting_name).strip(" .") or "meeting"
    utf8_name = quote(f"{safe_name}.md")
    payload = io.BytesIO(output.encode("utf-8"))
    response = FileResponse(
        payload,
        content_type="text/markdown; charset=utf-8",
        as_attachment=True,
        filename=f"{safe_name}.md",
    )
    response["Content-Disposition"] = f"attachment; filename=\"meeting.md\"; filename*=UTF-8''{utf8_name}"
    return response


@login_required
@require_POST
def share_transcription(request, transcription_id):
    transcription = get_object_or_404(Transcription, id=transcription_id, initializer=request.user)
    login = request.POST.get("login", "").strip()
    permission = request.POST.get("permission", "view")
    if permission not in ["view", "edit"]:
        return JsonResponse({"error": "Отсутсвуют права доступа."}, status=400)
    if not login:
        return JsonResponse({"error": "Логин не указан."}, status=400)
    try:
        user = User.objects.get(login=login)
    except User.DoesNotExist:
        return JsonResponse({"error": "Пользователь не найден."}, status=400)

    # Prevent pointless sharing to yourself and avoid confusing UI states.
    if user.id == request.user.id:
        return JsonResponse({"error": "Нельзя выдать доступ самому себе."}, status=400)

    # Update permissions if record already exists (supports both upgrade and downgrade).
    access, created = FileAccess.objects.get_or_create(
        file=transcription.file,
        user=user,
        defaults={"permission": permission},
    )
    if not created:
        current = access.permission
        if current != permission:
            access.permission = permission
            access.save(update_fields=["permission"])
    return JsonResponse({"ok": True})


@login_required
@require_POST
def edit_transcription_name(request, transcription_id):
    transcription = get_object_or_404(
        Transcription.objects.filter(
            Q(initializer=request.user) | Q(file__accesses__user=request.user)
        ),
        id=transcription_id,
    )
    if not _has_edit_permission(transcription, request.user):
        return JsonResponse({"error": "Недостаточно прав для редактирования."}, status=403)
    name = request.POST.get("name", "").strip()
    description = request.POST.get("description", "").strip()
    if not name:
        return JsonResponse({"error": "Название не может быть пустым."}, status=400)
    transcription.file.name = name
    transcription.file.save(update_fields=["name"])
    transcription.name = name
    transcription.description = description
    transcription.edit_datetime = timezone.now()
    transcription.save()
    return JsonResponse({"ok": True})


@login_required
@require_POST
def start_transcription(request, transcription_id):
    transcription = get_object_or_404(
        Transcription.objects.filter(
            Q(initializer=request.user) | Q(file__accesses__user=request.user)
        ),
        id=transcription_id,
    )
    if not _has_edit_permission(transcription, request.user):
        return JsonResponse({"error": "Недостаточно прав для запуска."}, status=403)
    if transcription.status == Transcription.Status.PROCESSING:
        return JsonResponse({"error": "Транскрибация уже выполняется."}, status=400)
    if (
        transcription.status == Transcription.Status.COMPLETED
        and Result.objects.filter(transcription=transcription).exists()
    ):
        return JsonResponse({"error": "Транскрибация уже завершена."}, status=400)

    transcription.status = Transcription.Status.PENDING
    transcription.protocol_status = Transcription.ProtocolStatus.NOT_STARTED
    transcription.save(update_fields=["status", "protocol_status"])
    run_transcription.delay(transcription.id)
    return JsonResponse({"ok": True})


@login_required
@require_POST
def start_protocol(request, transcription_id):
    transcription = get_object_or_404(
        Transcription.objects.filter(
            Q(initializer=request.user) | Q(file__accesses__user=request.user)
        ),
        id=transcription_id,
    )
    if not _has_edit_permission(transcription, request.user):
        return JsonResponse({"error": "Недостаточно прав для запуска."}, status=403)
    if not Result.objects.filter(transcription=transcription).exists():
        return JsonResponse(
            {"error": "Нет текста транскрибации для отправки в GigaChat."},
            status=400,
        )
    if transcription.effective_status != Transcription.Status.COMPLETED:
        return JsonResponse({"error": "Протоколирование доступно после транскрибации."}, status=400)
    if transcription.protocol_status == Transcription.ProtocolStatus.PROCESSING:
        return JsonResponse({"error": "Протоколирование уже выполняется."}, status=400)

    ok = enqueue_protocol_generation(transcription.id)
    if not ok:
        return JsonResponse({"error": "Не удалось запустить протоколирование."}, status=400)
    return JsonResponse({"ok": True})