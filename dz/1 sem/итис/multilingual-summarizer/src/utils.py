"""Вспомогательные функции для обработки текста."""

import re
from typing import List


def preprocess_text(text: str) -> List[str]:
    """
    Предварительная обработка текста: разбиение на предложения.

    Args:
        text: Исходный текст

    Returns:
        Список предложений
    """
    if not text:
        return []

    # Удаляем лишние пробелы и переносы строк
    text = re.sub(r"\s+", " ", text).strip()

    # Разбиваем на предложения
    sentences = re.split(r"[.!?]+", text)

    # Очищаем пустые предложения
    return [s.strip() for s in sentences if s.strip()]


def normalize_compression_ratio(ratio: float) -> float:
    """
    Нормализует коэффициент сжатия к допустимому диапазону.

    Args:
        ratio: Исходный коэффициент сжатия

    Returns:
        Нормализованный коэффициент (0.1 - 0.9) или 0.3 по умолчанию
    """
    if ratio <= 0 or ratio >= 1:
        return 0.3
    if ratio < 0.1:
        return 0.1
    if ratio > 0.9:
        return 0.9
    return ratio

