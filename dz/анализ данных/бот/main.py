import telebot
from gigachat import GigaChat
from gigachat.models import Chat, Messages, MessagesRole
import PyPDF2
from dotenv import load_dotenv
import os


def load_pdf(filename):
    text = ""
    with open(filename, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            text += page.extract_text()
    return text
KNOWLEDGE_BASE = load_pdf('base.pdf')
load_dotenv('api.env')

token = os.getenv("TELEGRAM")
giga_token = os.getenv("LLM")

PROMPT = f"""Ты - преподаватель ВУЗА по специальности "Анализ данных и искусственный интеллект".

**Область компетенции:**
Отвечай ТОЛЬКО на вопросы по следующим темам:

*Лекционные темы:*
* Введение в искусственный интеллект. Жизненный цикл ИИ
* Элементы машинного обучения
* Элементы машинного обучения. Модели, жизненный цикл
* Технологии искусственного интеллекта
* Большие языковые модели
* Агентные и многоагентные системы
* Этика искусственного интеллекта
* Форсайт ИИ

**Контекст курса(ИСПОЛЬЗУЙ СНАЧАЛО ЭТОТ ФАЙЛ ДЛЯ ОВТЕТА, ПОТОМ ИЩИ В ИНТЕРНЕТЕ):**
{KNOWLEDGE_BASE}

*Практические темы:*
* Работа с NumPy
* Работа с Pandas
* Работа с Pandas. Сводный анализ и визуализация данных
* Модели машинного обучения в scikit-learn, уровень fit-predict
* Пайплайны решения задач на HuggingFace
* Промпт инжиниринг с GigaChat API
* Салют бот
* Whisper/Spaces/Gradio

**На другие запросы:**
Отвечай только на вопросы, касающиеся перечисленных выше тем. На любые другие вопросы отвечай: "Извините, я цифровой ассистент преподавателя курса по анализу данных и искусственному интеллекту. Я отвечаю только на вопросы, касающиеся курса."

**Формат ответа:**
* Научный стиль на русском языке
* Markdown форматирование
* Максимум 50 слов
* Ссылки на источники, если релевантно
* Примеры кода на Python, если нужно
"""

bot = telebot.TeleBot(token)

giga = GigaChat(credentials=giga_token, verify_ssl_certs=False)

@bot.message_handler(commands=['start'])
def start_message(message):
    bot.send_message(message.chat.id,
                     "Привет! Я цифровой ассистент курса по анализу данных и ИИ.\nЗадавайте вопросы по темам машинного обучения, ИИ и анализа данных.")


@bot.message_handler(func=lambda message: True)
def echo_all(message):
    payload = Chat(
        messages=[
            Messages(role=MessagesRole.SYSTEM, content=PROMPT),
            Messages(role=MessagesRole.USER, content=message.text)
        ]
    )
    response = giga.chat(payload)

    bot.reply_to(message, response.choices[0].message.content, parse_mode='Markdown')


if __name__ == '__main__':
    print("СТАРТУЕМ")
    bot.infinity_polling()