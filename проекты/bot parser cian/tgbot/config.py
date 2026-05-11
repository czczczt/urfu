"""
Конфигурация бота
"""
import os
from dotenv import load_dotenv

# Получаем директорию, где находится этот файл
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.path.join(BASE_DIR, 'apis.env')

# Загружаем переменные окружения из apis.env файла
load_dotenv(ENV_FILE)

# Токен Telegram бота
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')

# Настройки GigaChat
GIGACHAT_CREDENTIALS = os.getenv('GIGACHAT_CREDENTIALS', '')
GIGACHAT_SCOPE = os.getenv('GIGACHAT_SCOPE', 'GIGACHAT_API_PERS')
GIGACHAT_MODEL = os.getenv('GIGACHAT_MODEL', 'GigaChat-Pro')

# Настройки SaluteSpeech
SPEECH_TO_TEXT_API_KEY = os.getenv('SPEECH_TO_TEXT_API_KEY', '')

# Лимиты токенов для GigaChat
GIGACHAT_MAX_TOKENS_SEARCH = 500      # Для извлечения параметров
GIGACHAT_MAX_TOKENS_RESPONSE = 1000    # Для обычных ответов
GIGACHAT_MAX_TOKENS_ANALYSIS = 5000   # Для анализа объявлений

