"""Multilingual Learning Material Summarizer package."""

from src.summarizer import TextSummarizer
from src.language_detector import LanguageDetector
from src.utils import preprocess_text, normalize_compression_ratio

__all__ = [
    "TextSummarizer",
    "LanguageDetector",
    "preprocess_text",
    "normalize_compression_ratio",
]

