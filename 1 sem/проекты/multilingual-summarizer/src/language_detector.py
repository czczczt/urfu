"""Модуль для определения языка текста."""

from langdetect import detect, LangDetectException


class LanguageDetector:
    """Класс для определения языка текста."""

    SUPPORTED_LANGUAGES = {"english", "russian", "german"}
    LANGUAGE_MAP = {"en": "english", "ru": "russian", "de": "german"}

    @staticmethod
    def detect_language(text: str) -> str:
        """
        Определяет язык текста.

        Args:
            text: Текст для определения языка

        Returns:
            Название языка (english, russian, german) или 'english' по умолчанию
        """
        if not text or not text.strip():
            return "english"

        try:
            lang_code = detect(text)
            return LanguageDetector.LANGUAGE_MAP.get(lang_code, "english")
        except LangDetectException:
            return "english"

    @staticmethod
    def is_supported(language: str) -> bool:
        """
        Проверяет, поддерживается ли язык.

        Args:
            language: Название языка

        Returns:
            True если язык поддерживается, False иначе
        """
        return language.lower() in LanguageDetector.SUPPORTED_LANGUAGES

