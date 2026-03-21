"""Тесты для модуля summarizer."""

import pytest
import sys
import os
import tempfile

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.summarizer import TextSummarizer


class TestTextSummarizer:
    """Тесты для класса TextSummarizer."""

    @pytest.fixture
    def summarizer(self):
        """Фикстура для создания объекта суммаризатора."""
        return TextSummarizer()

    @pytest.fixture
    def sample_text(self):
        """Образец текста для тестирования."""
        return """Machine learning is a subset of artificial intelligence. 
        It focuses on developing programs that can learn from experience. 
        Machine learning algorithms are very powerful. 
        They work best with large datasets."""

    def test_initialization(self, summarizer):
        """Тест инициализации суммаризатора."""
        assert summarizer is not None
        assert summarizer.language == "english"

    def test_preprocess_text_through_summarize(self, summarizer, sample_text):
        """Тест предварительной обработки текста через summarize."""
        summary = summarizer.summarize(sample_text, compression_ratio=0.5)
        assert isinstance(summary, str)
        assert len(summary) > 0

    def test_summarize_basic(self, summarizer, sample_text):
        """Тест базового резюмирования."""
        summary = summarizer.summarize(sample_text, compression_ratio=0.5)
        assert isinstance(summary, str)
        assert len(summary) > 0
        assert len(summary) <= len(sample_text)

    def test_summarize_with_ratio(self, summarizer, sample_text):
        """Тест резюмирования с разными коэффициентами."""
        summary_30 = summarizer.summarize(sample_text, compression_ratio=0.3)
        summary_50 = summarizer.summarize(sample_text, compression_ratio=0.5)

        assert len(summary_30) <= len(summary_50)

    def test_summarize_with_language_specification(self, summarizer):
        """Тест резюмирования с явным указанием языка."""
        text = "This is an English text for testing."
        summary = summarizer.summarize(text, language="english", compression_ratio=0.5)
        assert isinstance(summary, str)
        assert len(summary) > 0

    def test_get_key_words(self, summarizer, sample_text):
        """Тест извлечения ключевых слов."""
        keywords = summarizer.get_key_words(sample_text, n_words=3)
        assert isinstance(keywords, list)
        assert len(keywords) > 0

    def test_get_key_words_custom_count(self, summarizer, sample_text):
        """Тест извлечения заданного количества ключевых слов."""
        keywords = summarizer.get_key_words(sample_text, n_words=5)
        assert isinstance(keywords, list)
        assert len(keywords) <= 5

    def test_get_key_words_empty_text(self, summarizer):
        """Тест извлечения ключевых слов из пустого текста."""
        keywords = summarizer.get_key_words("")
        assert isinstance(keywords, list)
        assert len(keywords) == 0

    def test_invalid_compression_ratio(self, summarizer, sample_text):
        """Тест обработки некорректных коэффициентов."""
        # Должен использовать нормализованное значение
        summary = summarizer.summarize(sample_text, compression_ratio=1.5)
        assert isinstance(summary, str)

    def test_empty_text(self, summarizer):
        """Тест на пустой текст."""
        summary = summarizer.summarize("")
        assert summary == ""

    def test_single_sentence(self, summarizer):
        """Тест на текст с одним предложением."""
        text = "This is a single sentence."
        summary = summarizer.summarize(text)
        # Для одного предложения резюме должно быть тем же текстом
        assert summary == text

    def test_calculate_sentence_scores(self, summarizer, sample_text):
        """Тест вычисления важности предложений."""
        from src.utils import preprocess_text
        sentences = preprocess_text(sample_text)
        scores = summarizer.calculate_sentence_scores(sentences)
        assert isinstance(scores, type(__import__('numpy').array([])))
        assert len(scores) == len(sentences)
        assert all(score >= 0 for score in scores)

    def test_summarize_very_small_ratio(self, summarizer, sample_text):
        """Тест резюмирования с очень малым коэффициентом."""
        summary = summarizer.summarize(sample_text, compression_ratio=0.1)
        assert isinstance(summary, str)
        assert len(summary) > 0

    def test_summarize_large_ratio(self, summarizer, sample_text):
        """Тест резюмирования с большим коэффициентом."""
        summary = summarizer.summarize(sample_text, compression_ratio=0.9)
        assert isinstance(summary, str)
        assert len(summary) <= len(sample_text)

    def test_russian_text_summarization(self, summarizer):
        """Тест резюмирования русского текста."""
        russian_text = """Машинное обучение — это подмножество искусственного интеллекта. 
        Оно фокусируется на разработке программ, которые могут учиться. 
        Алгоритмы машинного обучения очень мощные."""
        summary = summarizer.summarize(russian_text, compression_ratio=0.3)
        assert isinstance(summary, str)
        assert len(summary) > 0
        assert len(summary) <= len(russian_text)

    def test_german_text_summarization(self, summarizer):
        """Тест резюмирования немецкого текста."""
        german_text = """Maschinelles Lernen ist eine Teilmenge der künstlichen Intelligenz. 
        Es konzentriert sich auf die Entwicklung von Programmen, die lernen können. 
        Algorithmen für maschinelles Lernen sind sehr mächtig."""
        summary = summarizer.summarize(german_text, compression_ratio=0.3)
        assert isinstance(summary, str)
        assert len(summary) > 0
        assert len(summary) <= len(german_text)

    def test_summarize_and_save(self, summarizer, tmp_path):
        """Тест сохранения резюме в файл."""
        # Создаем временный входной файл
        input_file = tmp_path / "input.txt"
        output_file = tmp_path / "output.txt"

        input_file.write_text(
            "This is a test text. It has multiple sentences. Each sentence is important.",
            encoding="utf-8",
        )

        summarizer.summarize_and_save(
            str(input_file), str(output_file), compression_ratio=0.5
        )

        assert output_file.exists()
        content = output_file.read_text(encoding="utf-8")
        assert len(content) > 0

    def test_supported_languages_constant(self, summarizer):
        """Тест наличия константы поддерживаемых языков."""
        assert hasattr(TextSummarizer, "SUPPORTED_LANGUAGES")
        assert isinstance(TextSummarizer.SUPPORTED_LANGUAGES, set)
        assert "english" in TextSummarizer.SUPPORTED_LANGUAGES
        assert "russian" in TextSummarizer.SUPPORTED_LANGUAGES
        assert "german" in TextSummarizer.SUPPORTED_LANGUAGES


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

