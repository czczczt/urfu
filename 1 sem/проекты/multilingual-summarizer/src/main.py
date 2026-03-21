"""Главный модуль для запуска приложения."""

import sys
import os

# Добавляем корневую папку проекта в sys.path для корректных импортов
# Это позволяет запускать скрипт как из корня проекта, так и напрямую
_current_file = os.path.abspath(__file__)
_current_dir = os.path.dirname(_current_file)
project_root = os.path.dirname(_current_dir)

# Добавляем корень проекта в начало sys.path
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Теперь можем импортировать модули из src
from src.summarizer import TextSummarizer


def main():
    """Основная функция для демонстрации работы суммаризатора."""
    # Пример использования
    sample_text = """
    Machine learning is a subset of artificial intelligence that focuses on 
    the development of computer programs that can learn and adapt from experience. 
    The key advantage of machine learning is that it can automatically learn from 
    data without being explicitly programmed. Machine learning algorithms can be 
    broadly categorized into three types: supervised learning, unsupervised learning, 
    and reinforcement learning. Each type has its own applications and advantages.
    """

    summarizer = TextSummarizer()

    print("Оригинальный текст:")
    print(sample_text)
    print("\n" + "=" * 50)
    print("\nРезюме (30%):")
    summary = summarizer.summarize(sample_text, compression_ratio=0.3)
    print(summary)

    print("\n" + "=" * 50)
    print("\nКлючевые слова:")
    keywords = summarizer.get_key_words(sample_text)
    print(", ".join(keywords))


if __name__ == "__main__":
    main()
