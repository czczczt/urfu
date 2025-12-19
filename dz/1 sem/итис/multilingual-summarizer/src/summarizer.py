"""Модуль для резюмирования текстов."""

from typing import List
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from src.language_detector import LanguageDetector
from src.utils import preprocess_text, normalize_compression_ratio


class TextSummarizer:
    """Основной класс для резюмирования текстов на разных языках."""

    SUPPORTED_LANGUAGES = LanguageDetector.SUPPORTED_LANGUAGES

    def __init__(self):
        """Инициализация суммаризатора."""
        self.vectorizer = TfidfVectorizer(max_features=100, stop_words="english")
        self.language = "english"

    def calculate_sentence_scores(self, sentences: List[str]) -> np.ndarray:
        """
        Вычисляет важность предложений на основе TF-IDF и косинусного сходства.

        Args:
            sentences: Список предложений

        Returns:
            Массив оценок важности для каждого предложения
        """
        if len(sentences) < 2:
            return np.ones(len(sentences))

        try:
            # TF-IDF матрица
            tfidf_matrix = self.vectorizer.fit_transform(sentences)
            # Косинусное сходство
            similarity_matrix = cosine_similarity(tfidf_matrix)
            # Важность каждого предложения = среднее сходство с другими
            scores = similarity_matrix.mean(axis=1)
            return scores
        except Exception:
            return np.ones(len(sentences))

    def summarize(
        self, text: str, compression_ratio: float = 0.3, language: str = None
    ) -> str:
        """
        Резюмирует текст.

        Args:
            text: Текст для резюмирования
            compression_ratio: Доля текста в резюме (0-1)
            language: Язык текста (автоматически если None)

        Returns:
            Резюмированный текст
        """
        if not text or not text.strip():
            return ""

        # Определяем язык
        if language is None:
            self.language = LanguageDetector.detect_language(text)
        else:
            self.language = language.lower() if LanguageDetector.is_supported(language) else "english"

        # Нормализуем коэффициент сжатия
        compression_ratio = normalize_compression_ratio(compression_ratio)

        # Разбиваем текст на предложения
        sentences = preprocess_text(text)
        if len(sentences) < 2:
            return text

        # Вычисляем важность
        scores = self.calculate_sentence_scores(sentences)

        # Выбираем топ-предложения
        num_sentences = max(1, int(len(sentences) * compression_ratio))
        top_indices = np.argsort(scores)[-num_sentences:]
        top_indices = sorted(top_indices)

        # Восстанавливаем текст в исходном порядке
        summary_sentences = [sentences[i] for i in top_indices]
        summary = ". ".join(summary_sentences) + "."

        return summary

    def summarize_and_save(
        self, input_file: str, output_file: str, compression_ratio: float = 0.3
    ) -> None:
        """
        Резюмирует текст из файла и сохраняет результат.

        Args:
            input_file: Путь к входному файлу
            output_file: Путь к выходному файлу
            compression_ratio: Коэффициент сжатия
        """
        with open(input_file, "r", encoding="utf-8") as f:
            text = f.read()

        summary = self.summarize(text, compression_ratio)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(summary)

    def get_key_words(self, text: str, n_words: int = 5) -> List[str]:
        """
        Извлекает ключевые слова из текста на основе TF-IDF.

        Args:
            text: Текст для анализа
            n_words: Количество ключевых слов

        Returns:
            Список ключевых слов
        """
        if not text or not text.strip():
            return []

        try:
            tfidf_matrix = self.vectorizer.fit_transform([text])
            feature_names = self.vectorizer.get_feature_names_out()
            scores = tfidf_matrix.toarray()[0]
            top_indices = np.argsort(scores)[-n_words:]
            return [feature_names[i] for i in reversed(top_indices)]
        except Exception:
            return []

