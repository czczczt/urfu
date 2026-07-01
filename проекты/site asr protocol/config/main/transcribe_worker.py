import json
import logging
import os
import re
import ast
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

import redis
from django.conf import settings
import whisperx
from whisperx.diarize import DiarizationPipeline
from dotenv import load_dotenv
from gigachat import GigaChat

_DOTENV_PATH = Path(__file__).resolve().parent.parent / ".env"
if _DOTENV_PATH.exists():
    load_dotenv(dotenv_path=_DOTENV_PATH)
else:
    load_dotenv()


@dataclass
class TranscribeConfig:
    model_size: str = "large-v2"
    language: str = "ru"
    device: str = "cpu"
    batch_size: int = 4
    compute_type: str = "int8"
    diarize: bool = True
    skip_align: bool = False


CONFIG = TranscribeConfig()
logger = logging.getLogger(__name__)


class TranscribeWorker:

    def __init__(self, config: TranscribeConfig = CONFIG):
        self.cfg = config
        self.hf_token = os.getenv("HF_KEY")
        self._model = None
        self._align_model = None
        self._align_metadata = None
        self._diarize_model = None

    def _get_model(self):
        if self._model is None:
            self._model = whisperx.load_model(
                self.cfg.model_size,
                self.cfg.device,
                compute_type=self.cfg.compute_type,
                language=self.cfg.language,
            )
        return self._model

    def _get_align_model(self, language_code: str):
        if self._align_model is None:
            self._align_model, self._align_metadata = whisperx.load_align_model(
                language_code=language_code, device=self.cfg.device
            )
        return self._align_model, self._align_metadata

    def _get_diarize_model(self):
        if self._diarize_model is None:
            self._diarize_model = DiarizationPipeline(
                token=self.hf_token, device=self.cfg.device
            )
        return self._diarize_model

    def transcribe_and_diarize(self, audio_path: str) -> list:
        audio = whisperx.load_audio(audio_path)
        result = self._get_model().transcribe(audio, batch_size=self.cfg.batch_size)

        if not self.cfg.skip_align:
            model_a, metadata = self._get_align_model(result["language"])
            result = whisperx.align(
                result["segments"], model_a, metadata, audio,
                self.cfg.device, return_char_alignments=False,
            )

        if self.cfg.diarize:
            diarize_segments = self._get_diarize_model()(audio)
            result = whisperx.assign_word_speakers(diarize_segments, result)

        return result["segments"]


@dataclass(frozen=True)
class ProtocolResult:
    brief_summary: str
    meeting_recap: str
    timeline_recap: str


_GIGACHAT_LOCK_KEY = "protoconv:gigachat:lock"
_REDIS: redis.Redis | None = None


class GigachatLockBusy(Exception):
    """Не удалось занять слот GigaChat за отведённое время ожидания."""


def _gigachat_redis() -> redis.Redis:
    global _REDIS
    if _REDIS is None:
        _REDIS = redis.from_url(settings.CELERY_BROKER_URL)
    return _REDIS


@contextmanager
def gigachat_slot() -> Iterator[None]:
    """Один активный запрос GigaChat на весь кластер воркеров."""
    wait_seconds = int(getattr(settings, "GIGACHAT_LOCK_WAIT_SECONDS", 7200))
    hold_seconds = int(getattr(settings, "GIGACHAT_LOCK_HOLD_SECONDS", 3600))
    poll_seconds = float(getattr(settings, "GIGACHAT_LOCK_POLL_SECONDS", 2.0))

    client = _gigachat_redis()
    token = uuid.uuid4().hex
    deadline = time.monotonic() + wait_seconds

    while True:
        if client.set(_GIGACHAT_LOCK_KEY, token, nx=True, ex=hold_seconds):
            try:
                yield
            finally:
                current = client.get(_GIGACHAT_LOCK_KEY)
                if current is not None and current.decode() == token:
                    client.delete(_GIGACHAT_LOCK_KEY)
            return

        if time.monotonic() >= deadline:
            raise GigachatLockBusy(
                f"GigaChat lock not available within {wait_seconds}s"
            )

        time.sleep(poll_seconds)


class ProtocolWorker:
    def __init__(self):
        token = os.getenv("GIGA_KEY") or os.getenv("GIGACHAT_CREDENTIALS")
        if not token:
            raise RuntimeError(
                'Missing "GIGA_KEY" (or "GIGACHAT_CREDENTIALS") in config/.env'
            )
        client_kwargs = {
            "verify_ssl_certs": False,
            "scope": "GIGACHAT_API_PERS",
            "model": "GigaChat-Lite",
            "proxies": {}
        }
        try:
            self._client = GigaChat(credentials=token, **client_kwargs)
        except TypeError:
            self._client = GigaChat(api_key=token, **client_kwargs)
        logger.info("GigaChat client initialized")

    def summarize(self, segments: list[dict[str, Any]]) -> ProtocolResult:
        with gigachat_slot():
            return self._summarize_impl(segments)

    def _summarize_impl(self, segments: list[dict[str, Any]]) -> ProtocolResult:
        giga_in = [[seg.get("text", ""), seg.get("speaker", "")] for seg in segments]
        text_chars = sum(len(str(seg.get("text", ""))) for seg in segments)
        logger.info(
            "Sending transcript to GigaChat: segments=%s, chars=%s",
            len(segments),
            text_chars,
        )
        prompt = f'''
# РОЛЬ
Ты — профессиональный бизнес-аналитик и экспертный резюмировщик протоколов деловых встреч. Твоя задача — анализировать только предоставленный текст и формировать структурированное резюме.

# ЗАДАЧА
1. Проанализируй входной протокол встречи (текст разбит на сегменты с указанием говорящего).
2. Верни ТРИ текстовых блока в JSON-объекте:
   - brief_summary: краткая выжимка 2-4 предложения (для поля "описание"), без списков.
   - meeting_recap: пересказ встречи с абзацами и подзаголовками: "Коротко о встрече", "Обсуждаемые темы", "Итоги".
   - timeline_recap: пересказ по временным блокам (например, 00:00-05:00, 05:00-10:00 и т.д.).
3. Не дублируй brief_summary внутри meeting_recap и timeline_recap.
4. Верни результат ТОЛЬКО в валидном JSON-объекте, без дополнительного текста.

# СТРОГИЕ ЗАПРЕТЫ
- Не добавляй информацию, которой нет во входных данных.
- Не делай предположений, не интерпретируй намерения, не домысливай детали.
- Не используй оценочные суждения, эмоции или субъективные формулировки.
- Не включай приветствия, подписи или служебные фразы.
- Не используй списки, если не указано иное.

# ТРЕБОВАНИЯ К КОНТЕНТУ
- Для meeting_recap: связный деловой текст, несколько абзацев, с подзаголовками как в задании.
- Для timeline_recap: блоки в порядке времени, каждый блок начинается с диапазона времени.
- Атрибуция: по возможности не отмечай ключевых спикеров в значимых тезисах.
- Язык: русский, деловой и нейтральный стиль.
- Временные метки в протоколе — единственный источник истины для timeline_recap. Определяй границы блоков строго по меткам из входных данных, не округляй и не усредняй произвольно.
- Для meeting_recap и timeline_recap используй Markdown-оформление для читаемости: подзаголовки (##), маркированные списки (-) и акценты (**...**) там, где уместно.
- Объём meeting_recap:
  - если встреча длинная: ориентир 260–340 слов;
  - если встреча короткая: сокращай пропорционально, без искусственного раздувания.

# ТЕХНИЧЕСКИЕ ПРАВИЛА ВЫВОДА
- Ответ должен содержать ТОЛЬКО валидный JSON-объект.
- Запрещён любой пояснительный текст, теги, markdown-обёртки (```json) или пустые строки до/после JSON.
- Внутри строковых значений JSON строго экранируй кавычки (\") и переносы строк (\\n).
- Строго следуй схеме:
{{
  "brief_summary": "краткая выжимка",
  "meeting_recap": "пересказ встречи с абзацами",
  "timeline_recap": "пересказ по временным блокам"
}}

# ВХОДНЫЕ ДАННЫЕ
{giga_in}
        '''

        resp = self._client.chat(prompt)
        logger.info("GigaChat response received for %s segments", len(segments))
        try:
            # SDK object response
            content = resp.choices[0].message.content
        except (AttributeError, TypeError, KeyError, IndexError):
            # Dict-like response (older integrations)
            content = resp["choices"][0]["message"]["content"]
        if not isinstance(content, str):
            raise ValueError("GigaChat returned non-text content")

        def _parse_json_payload(raw: str) -> dict[str, Any]:
            def _extract_quoted_value(payload: str, key: str) -> str:
                marker = f'"{key}"'
                i = payload.find(marker)
                if i == -1:
                    return ""
                colon = payload.find(":", i + len(marker))
                if colon == -1:
                    return ""
                q1 = payload.find('"', colon + 1)
                if q1 == -1:
                    return ""

                out_chars: list[str] = []
                escaped = False
                j = q1 + 1
                while j < len(payload):
                    ch = payload[j]
                    if escaped:
                        out_chars.append(ch)
                        escaped = False
                    elif ch == "\\":
                        escaped = True
                    elif ch == '"':
                        return "".join(out_chars).strip()
                    else:
                        out_chars.append(ch)
                    j += 1
                return ""

            text = raw.strip()
            if not text:
                return {}
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass
            # Accept Python-dict-like payloads with single quotes.
            try:
                parsed = ast.literal_eval(text)
                if isinstance(parsed, dict):
                    return parsed
            except (ValueError, SyntaxError):
                pass

            fenced = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text, flags=re.IGNORECASE)
            if fenced:
                try:
                    return json.loads(fenced.group(1))
                except json.JSONDecodeError:
                    try:
                        parsed = ast.literal_eval(fenced.group(1))
                        if isinstance(parsed, dict):
                            return parsed
                    except (ValueError, SyntaxError):
                        pass

            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                candidate = text[start : end + 1]
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    try:
                        parsed = ast.literal_eval(candidate)
                        if isinstance(parsed, dict):
                            return parsed
                    except (ValueError, SyntaxError):
                        pass

            # Last-resort recovery for malformed JSON where quoted fields still exist.
            recovered = {
                "brief_summary": _extract_quoted_value(text, "brief_summary"),
                "meeting_recap": _extract_quoted_value(text, "meeting_recap"),
                "timeline_recap": _extract_quoted_value(text, "timeline_recap"),
            }
            if any(recovered.values()):
                return recovered

            logger.warning("GigaChat returned non-JSON content; using text fallback")
            return {"meeting_recap": text}

        data = _parse_json_payload(content)

        def _to_text(value: Any) -> str:
            if value is None:
                return ""
            if isinstance(value, str):
                return value.strip()
            if isinstance(value, (dict, list)):
                # Keep model payload as-is, only serialize to valid text for DB/UI.
                return json.dumps(value, ensure_ascii=False)
            return str(value).strip()

        def _pick_text(*keys: str) -> str:
            for key in keys:
                text = _to_text(data.get(key))
                if text:
                    return text
            return ""

        # Support common variants from different prompts/SDK wrappers.
        brief_summary = _pick_text(
            "brief_summary",
            "brief",
            "summary",
            "short_summary",
            "краткая_выжимка",
            "краткий_пересказ",
        )
        meeting_recap = _pick_text(
            "meeting_recap",
            "protocol_text",
            "recap",
            "giga_protocol",
            "пересказ_встречи",
            "пересказ",
        )
        timeline_recap = _pick_text(
            "timeline_recap",
            "compressed_text",
            "timeline",
            "giga_compressed_text",
            "пересказ_по_абзацам",
            "пересказ_по_блокам",
            "таймлайн",
        )

        nested = data.get("result")
        if isinstance(nested, dict):
            if not brief_summary:
                brief_summary = _to_text(nested.get("brief_summary"))
            if not meeting_recap:
                meeting_recap = _to_text(nested.get("meeting_recap"))
            if not timeline_recap:
                timeline_recap = _to_text(nested.get("timeline_recap"))

        if not timeline_recap and isinstance(data, dict):
            known_keys = {
                "brief_summary", "brief", "summary", "short_summary", "краткая_выжимка", "краткий_пересказ",
                "meeting_recap", "protocol_text", "recap", "giga_protocol", "пересказ_встречи", "пересказ",
                "timeline_recap", "compressed_text", "timeline", "giga_compressed_text", "пересказ_по_абзацам",
                "пересказ_по_блокам", "таймлайн", "result", "raw_text", "text", "content",
            }
            if data and all(str(k) not in known_keys for k in data.keys()):
                # Response can be a plain timeline mapping: {"00:00-05:00": "...", ...}
                timeline_recap = _to_text(data)
        if not meeting_recap:
            meeting_recap = _pick_text("raw_text", "text", "content")
        if not brief_summary:
            brief_summary = meeting_recap.split("\n", 1)[0].strip()[:600]

        return ProtocolResult(
            brief_summary=brief_summary,
            meeting_recap=meeting_recap,
            timeline_recap=timeline_recap,
        )