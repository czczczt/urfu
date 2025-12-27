from typing import List, Dict, Any

from db import (
    init_db,
    create_request,
    save_listings_for_request,
    get_listings_for_request,
)
from llm_client import ask_gigachat_chat


def init_app() -> None:
    """
    Вызывается один раз при старте приложения.
    """
    init_db()


def handle_new_request(
    city: str,
    district: str,
    min_area: float,
    max_area: float,
    min_rate: float,
    max_rate: float,
) -> int:
    """
    Создаёт заявку в БД и возвращает её id.
    """
    request_id = create_request(
        city=city,
        district=district,
        min_area=min_area,
        max_area=max_area,
        min_rate=min_rate,
        max_rate=max_rate,
    )
    return request_id


def process_request_with_listings(
    request_id: int,
    scraped_listings: List[Dict[str, Any]],
) -> None:
    """
    Принимает спарсенные объявления и сохраняет их в БД
    вместе со связями request_listings и скорингом.
    """
    save_listings_for_request(request_id, scraped_listings)


def build_report_for_request(request_id: int) -> str:
    """
    Достаёт из БД подходящие объекты и просит GigaChat
    оформить их в отчёт. Возвращает markdown‑строку.
    """
    listings = get_listings_for_request(request_id)

    if not listings:
        return "Подходящих вариантов не найдено."

    # Текст для LLM из объявлений
    lines: list[str] = []
    for i, l in enumerate(listings, start=1):
        line = (
            f"{i}. ad_id: {l.get('external_id', 'N/A')}; "
            f"источник: {l.get('source_name', 'N/A')}; "
            f"адрес: {l['address']}; "
            f"район: {l.get('district', 'не указан')}; "
            f"площадь: {l.get('total_area', 'N/A')} м²; "
            f"ставка: {l.get('price_per_sqm', 'N/A')} ₽/м²; "
            f"этаж: {l.get('floor', 'N/A')}; "
            f"тип здания: {l.get('building_type', 'N/A')}; "
            f"статус: {l.get('status', 'неизвестен')}."
        )
        lines.append(line)

    listings_text = "\n".join(lines)

    user_message = (
        "Вот параметры одной заявки банка и список найденных объявлений.\n\n"
        f"Заявка #{request_id}.\n\n"
        "Список объявлений:\n"
        f"{listings_text}\n\n"
        "На основе этих данных выполни анализ в соответствии с системными инструкциями: "
        "выбери до трёх лучших вариантов, посчитай и опиши ключевые метрики, "
        "выдели риски и подготовь шаблон письма арендодателю по лучшему варианту."
    )

    answer = ask_gigachat_chat(
        user_message=user_message,
        temperature=0.3,
        max_tokens=800,
    )
    return answer
