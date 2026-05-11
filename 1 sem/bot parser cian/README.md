# Телеграм бот "Поиск Недвижимости"

Проект для подбора коммерческих помещений под банковские отделения.

Репозиторий содержит:
- **Telegram-бота** для интерактивного сбора критериев и выдачи результатов.
- **ИИ-слой (GigaChat)** для извлечения параметров из свободного текста и ранжирования объявлений.
- **Парсер CIAN (Selenium)** для получения объявлений.

## Возможности

- Сбор критериев поиска (город, площадь, бюджет и др.) в диалоге.
- ИИ-интерпретация запросов: строгие требования, исключения, приоритеты, срочность.
- Ранжирование вариантов и объяснение выбора.
- Лайки/дизлайки, избранное и «скрытые» объявления.
- Фоновая проверка новых объявлений (в `tgbot/background_worker.py`).

## Структура репозитория

```
.
├── aigent/                # CLI/MVP: заявки, SQLite, отчёт через GigaChat
├── parser/                # Парсер объявлений (CIAN, Selenium)
└── tgbot/                 # Telegram-бот + интеграция ИИ
```

## Быстрый старт (Windows)

### 1) Подготовка окружения

Создайте виртуальное окружение и установите зависимости бота:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r tgbot/requirements.txt
```

> Примечание: `tgbot/requirements.txt` включает `selenium` и `pandas`. Для реального парсинга понадобится установленный браузер и соответствующий WebDriver (Firefox/GeckoDriver или Chrome/ChromeDriver).

### 2) Настройка переменных окружения

Бот читает настройки из файла `tgbot/apis.env`.

Пример содержимого:

```
TELEGRAM_BOT_TOKEN=ваш_токен_бота
GIGACHAT_CREDENTIALS=ваши_учётные_данные_gigachat
GIGACHAT_SCOPE=GIGACHAT_API_PERS
GIGACHAT_MODEL=GigaChat-Pro
SPEECH_TO_TEXT_API_KEY=ваш_ключ_если_нужен
```

Важно:
- **Не коммитьте** секреты (токены/ключи) в репозиторий.
- Если секреты уже попали в git — их нужно **срочно отозвать/перевыпустить**.

## Запуск

### Telegram-бот

Из корня репозитория:

```bash
python tgbot/bot.py
```

### Парсер CIAN

Файл: `parser/cian.py`.

Внутри задаются параметры (например `CITY_NAME`, `SALE`, `MODE`, `PAGES_LIMIT`). Запуск:

```bash
python parser/cian.py
```

Результат сохраняется в CSV рядом с парсером (например `parser/chelyabinsk_cian_rent.csv`).

### CLI/MVP агент (aigent)

Папка `aigent` — минимальный CLI сценарий:
- создаёт заявку
- сохраняет объявления в SQLite (`aigent/test/testdb.sqlite3`)
- формирует Markdown-отчёт через GigaChat

Запуск:

```bash
python aigent/main.py
```

Настройки GigaChat для `aigent/llm_client.py`:
- `GIGACHAT_TOKEN_PATH` — путь до файла с токеном (по умолчанию `authGigaChat.txt`)
- `SYSTEM_PROMPT_PATH` — путь до системного промпта (по умолчанию `prompt.json.txt`)

## Где что лежит

- `tgbot/bot.py` — основная логика Telegram-бота.
- `tgbot/ai_integration.py` — извлечение параметров/ранжирование через GigaChat.
- `tgbot/config.py` — загрузка переменных окружения из `tgbot/apis.env`.
- `parser/cian.py` — Selenium-парсер объявлений CIAN.
- `aigent/service.py` — сценарий обработки заявки и построения отчёта.
- `aigent/db.py` — SQLite-схема и операции с заявками/объявлениями.

