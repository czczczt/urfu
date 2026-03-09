import os
import json
from gigachat import GigaChat
from gigachat.models import Chat, Messages, MessagesRole

TOKEN_PATH = os.getenv("GIGACHAT_TOKEN_PATH", "authGigaChat.txt")
DEFAULT_MODEL = os.getenv("GIGACHAT_MODEL", "GigaChat-2")
PROMPT_PATH = os.getenv("SYSTEM_PROMPT_PATH", "prompt.json.txt")


def _load_token() -> str:
    with open(TOKEN_PATH, "r", encoding="utf-8") as f:
        return f.read().strip()


def load_system_prompt(path: str = PROMPT_PATH) -> str:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    sp = data["system_prompt"]
    instructions = data["processing_instructions"]
    fallback = data["fallback_behavior"]

    parts: list[str] = []

    # Роль и экспертиза
    parts.append(sp["role"])
    parts.append("Твоя экспертиза:")
    for item in sp["expertise"]:
        parts.append(f"- {item}")
    parts.append(f"Главная цель: {sp['primary_goal']}")
    parts.append(f"Язык ответа: {sp['output_language']}.")

    # Что приходит на вход
    parts.append(
        "На вход ты получаешь параметры поиска и список объявлений "
        "в структурированном виде. Не придумывай данные, которых нет во входе."
    )

    # Шаги анализа
    parts.append("Следуй этим шагам анализа (адаптируй по ситуации):")
    for step in instructions["analysis_steps"]:
        parts.append(str(step))

    # Fallback‑поведение
    parts.append("Правила на случай малого числа подходящих объявлений:")
    parts.append(f"Если менее 3 объявлений: {fallback['if_less_than_3']}")
    parts.append(f"Если нет совпадений: {fallback['if_no_matches']}")

    # Формат ответа
    parts.append(
        "Структурируй ответ по секциям: summary, top_3_recommendations, "
        "risk_warnings, draft_email_to_landlord. Пиши по‑русски, "
        "используй подзаголовки и точные цифры из входных данных."
    )

    return "\n".join(parts)


SYSTEM_PROMPT = load_system_prompt()


def ask_gigachat_simple(message: str) -> str:
    """
    Простой один вопрос – один ответ, без ролей и истории.
    """
    token = _load_token()
    with GigaChat(
        credentials=token,
        verify_ssl_certs=False,
        model=DEFAULT_MODEL,
    ) as giga:
        response = giga.chat(message)
        return response.choices[0].message.content


def ask_gigachat_chat(
    user_message: str,
    temperature: float = 0.7,
    max_tokens: int = 300,
) -> str:
    """
    Основной вызов: SYSTEM = SYSTEM_PROMPT, USER = твой текст.
    """
    token = _load_token()

    messages = [
        Messages(
            role=MessagesRole.SYSTEM,
            content=SYSTEM_PROMPT,
        ),
        Messages(
            role=MessagesRole.USER,
            content=user_message,
        ),
    ]

    payload = Chat(
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    with GigaChat(
        credentials=token,
        verify_ssl_certs=False,
        model=DEFAULT_MODEL,
    ) as giga:
        response = giga.chat(payload)
        return response.choices[0].message.content
