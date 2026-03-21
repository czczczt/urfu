"""Тесты для модуля language_detector."""

import pytest
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.language_detector import LanguageDetector


class TestLanguageDetector:
    """Тесты для класса LanguageDetector."""

    def test_detect_english(self):
        """Тест определения английского языка."""
        text = "This is an English text about machine learning."
        lang = LanguageDetector.detect_language(text)
        assert lang == "english"

    def test_detect_russian(self):
        """Тест определения русского языка."""
        text = "Это русский текст о машинном обучении."
        lang = LanguageDetector.detect_language(text)
        assert lang == "russian"

    def test_detect_german(self):
        """Тест определения немецкого языка."""
        text = "Dies ist ein deutscher Text über maschinelles Lernen."
        lang = LanguageDetector.detect_language(text)
        assert lang == "german"

    def test_detect_empty_text(self):
        """Тест определения языка пустого текста."""
        lang = LanguageDetector.detect_language("")
        assert lang == "english"

    def test_detect_whitespace_only(self):
        """Тест определения языка текста только с пробелами."""
        lang = LanguageDetector.detect_language("   \n\t  ")
        assert lang == "english"

    def test_is_supported_english(self):
        """Тест проверки поддержки английского языка."""
        assert LanguageDetector.is_supported("english") is True
        assert LanguageDetector.is_supported("English") is True
        assert LanguageDetector.is_supported("ENGLISH") is True

    def test_is_supported_russian(self):
        """Тест проверки поддержки русского языка."""
        assert LanguageDetector.is_supported("russian") is True
        assert LanguageDetector.is_supported("Russian") is True

    def test_is_supported_german(self):
        """Тест проверки поддержки немецкого языка."""
        assert LanguageDetector.is_supported("german") is True
        assert LanguageDetector.is_supported("German") is True

    def test_is_supported_unsupported(self):
        """Тест проверки неподдерживаемого языка."""
        assert LanguageDetector.is_supported("french") is False
        assert LanguageDetector.is_supported("spanish") is False
        assert LanguageDetector.is_supported("chinese") is False

    def test_supported_languages_constant(self):
        """Тест наличия константы поддерживаемых языков."""
        assert hasattr(LanguageDetector, "SUPPORTED_LANGUAGES")
        assert isinstance(LanguageDetector.SUPPORTED_LANGUAGES, set)
        assert len(LanguageDetector.SUPPORTED_LANGUAGES) == 3

    def test_language_map_constant(self):
        """Тест наличия константы карты языков."""
        assert hasattr(LanguageDetector, "LANGUAGE_MAP")
        assert isinstance(LanguageDetector.LANGUAGE_MAP, dict)
        assert "en" in LanguageDetector.LANGUAGE_MAP
        assert "ru" in LanguageDetector.LANGUAGE_MAP
        assert "de" in LanguageDetector.LANGUAGE_MAP


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

