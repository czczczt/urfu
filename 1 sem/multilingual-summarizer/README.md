# Multilingual Learning Material Summarizer

Инструмент для автоматического резюмирования учебных материалов с поддержкой нескольких языков (English, Russian, German).

## Описание

Система разработана для автоматизации процесса создания кратких резюме из учебных материалов на различных языках. Особенно полезна для:

- Быстрого усвоения больших объемов информации
- Создания справочников и шпаргалок
- Преподавателей, готовящих материалы для студентов
- Исследователей, работающих с многоязычными данными

**Область применения:** AI в образовании, обработка текста (NLP)

## Особенности

- ✓ Поддержка 3 языков: English, Russian, German
- ✓ Выбор уровня сжатия: 20%, 30%, 50%
- ✓ Выделение ключевых моментов
- ✓ Сохранение результатов в файлы
- ✓ Автоматическое определение языка текста

## Установка

### Требования
- Python 3.8+
- pip или conda

### Быстрый старт

```bash
git clone https://github.com/[username]/multilingual-summarizer.git
cd multilingual-summarizer

python -m venv venv
source venv/bin/activate  # На Windows: venv\Scripts\activate

pip install -r requirements.txt
```

## Использование

### Базовый пример

```python
from src.summarizer import TextSummarizer

summarizer = TextSummarizer()

text = """Machine learning is a subset of artificial intelligence that focuses on 
the development of computer programs that can learn and adapt from experience. 
The key advantage of machine learning is that it can automatically learn from 
data without being explicitly programmed. Machine learning algorithms can be 
broadly categorized into three types: supervised learning, unsupervised learning, 
and reinforcement learning. Each type has its own applications and advantages."""

summary = summarizer.summarize(text, compression_ratio=0.3)
print(summary)
```

**Ожидаемый вывод:**
```
Machine learning algorithms can be broadly categorized into three types: supervised learning, unsupervised learning, and reinforcement learning. Each type has its own applications and advantages.
```

### Пример с русским текстом

```python
from src.summarizer import TextSummarizer

summarizer = TextSummarizer()

russian_text = """Машинное обучение — это подмножество искусственного интеллекта, 
которое фокусируется на разработке компьютерных программ, способных учиться и 
адаптироваться на основе опыта. Ключевое преимущество машинного обучения заключается 
в том, что оно может автоматически обучаться на данных без явного программирования. 
Алгоритмы машинного обучения можно широко классифицировать на три типа: обучение 
с учителем, обучение без учителя и обучение с подкреплением. Каждый тип имеет свои 
собственные приложения и преимущества."""

summary = summarizer.summarize(russian_text, compression_ratio=0.3)
print("Резюме:")
print(summary)

# Извлечение ключевых слов
keywords = summarizer.get_key_words(russian_text, n_words=5)
print("\nКлючевые слова:", ", ".join(keywords))
```

**Ожидаемый вывод:**
```
Резюме:
Алгоритмы машинного обучения можно широко классифицировать на три типа: обучение с учителем, обучение без учителя и обучение с подкреплением.

Ключевые слова: машинного, обучения, интеллекта, алгоритмы, обучение
```

### Пример с разными уровнями сжатия

```python
from src.summarizer import TextSummarizer

summarizer = TextSummarizer()

text = """Artificial intelligence represents one of the most transformative 
technologies of our time. It encompasses machine learning, natural language 
processing, computer vision, and robotics. Each subfield contributes to creating 
systems that can perform tasks typically requiring human intelligence. The 
applications are vast, from healthcare diagnostics to autonomous vehicles."""

# 20% сжатие
summary_20 = summarizer.summarize(text, compression_ratio=0.2)
print("20% сжатие:")
print(summary_20)

# 50% сжатие
summary_50 = summarizer.summarize(text, compression_ratio=0.5)
print("\n50% сжатие:")
print(summary_50)
```

### Определение языка

```python
from src.language_detector import LanguageDetector

detector = LanguageDetector()

text_en = "This is an English text about machine learning."
text_ru = "Это русский текст о машинном обучении."
text_de = "Dies ist ein deutscher Text über maschinelles Lernen."

print(f"English text detected: {detector.detect_language(text_en)}")
print(f"Russian text detected: {detector.detect_language(text_ru)}")
print(f"German text detected: {detector.detect_language(text_de)}")
```

**Ожидаемый вывод:**
```
English text detected: english
Russian text detected: russian
German text detected: german
```

### Запуск приложения

```bash
# Запуск из корня проекта (рекомендуется)
python -m src.main

# Или запуск напрямую
python src/main.py
```

## Структура проекта

```
multilingual-summarizer/
├── src/
│   ├── __init__.py
│   ├── main.py              # Главный модуль для запуска
│   ├── summarizer.py        # Основной класс TextSummarizer
│   ├── language_detector.py # Модуль определения языка
│   └── utils.py             # Вспомогательные функции
├── tests/
│   ├── __init__.py
│   ├── test_summarizer.py   # Тесты для суммаризатора
│   ├── test_main.py         # Тесты для main модуля
│   └── test_language.py     # Тесты для определения языка
├── data/
│   ├── sample.txt           # Пример текста для тестирования
│   └── sample.csv           # Пример текстов на разных языках
├── docs/                    # Документация
├── .github/
│   └── workflows/
│       ├── tests.yml        # Workflow для тестирования и проверки кода
│       └── scheduled-analysis.yml  # Scheduled workflow для анализа
├── .gitignore
├── requirements.txt
└── README.md
```

## Требования (Dependencies)

- **numpy** >= 1.20.0 — численные вычисления
- **pandas** >= 1.3.0 — работа с данными
- **scikit-learn** >= 1.0.0 — TF-IDF векторизация и анализ
- **langdetect** >= 1.0.9 — автоматическое определение языка
- **pytest** >= 7.0.0 — фреймворк для тестирования
- **pytest-cov** >= 3.0.0 — покрытие кода тестами
- **flake8** >= 4.0.0 — проверка стиля кода (PEP 8)
- **black** >= 22.0.0 — форматирование кода
- **matplotlib** >= 3.4.0 — визуализация (опционально)

## Тестирование

```bash
# Запуск всех тестов
pytest

# Тесты с подробным выводом
pytest -v

# Тесты с покрытием кода
pytest --cov=src tests/

# Проверка стиля кода (PEP 8)
flake8 src tests

# Форматирование кода
black src tests
```

## CI/CD

Проект использует GitHub Actions для автоматизации:

### Основной workflow (`tests.yml`)
- ✅ Автоматическое тестирование на каждый push и pull request
- ✅ Проверка кода на соответствие PEP 8 (flake8)
- ✅ Форматирование кода (black)
- ✅ Запуск unit тестов с покрытием кода
- ✅ Поддержка Python 3.8, 3.9, 3.10
- ✅ Загрузка покрытия кода на Codecov

### Scheduled workflow (`scheduled-analysis.yml`)
- ✅ Автоматический запуск каждую неделю (понедельник, 10:00 UTC)
- ✅ Ручной запуск через `workflow_dispatch` с параметрами (compression_ratio)
- ✅ Генерация отчетов анализа с использованием sample данных
- ✅ Автоматическое сохранение результатов в artifacts (retention 30 дней)
- ✅ Автоматический коммит результатов в репозиторий
- ✅ Уведомление о завершении работы

Это демонстрирует продвинутое использование CI/CD не только для проверки кода, но и для автоматизации регулярных задач анализа данных.

