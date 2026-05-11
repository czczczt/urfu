from service import (
    init_app,
    handle_new_request,
    process_request_with_listings,
    build_report_for_request,
)


# временный фейковый парсер (потом заменишь на реальный)
def fake_scrape_listings(city: str, district: str):
    return [
        {
            "external_id": "cian-123",
            "url": "https://example.com/cian-123",
            "address": "ул. Пушкина, д. 10",
            "city": city,
            "district": district,
            "total_area": 150.0,
            "price_total": 750000.0,
            "price_per_sqm": 5000.0,
            "floor": 1,
            "building_type": "отдельное здание",
            "year_built": 2005,
            "status": "active",
        },
        {
            "external_id": "avito-456",
            "url": "https://example.com/avito-456",
            "address": "пр. Ленина, д. 5",
            "city": city,
            "district": district,
            "total_area": 110.0,
            "price_total": 517000.0,
            "price_per_sqm": 4700.0,
            "floor": 1,
            "building_type": "БЦ",
            "year_built": 2012,
            "status": "active",
        },
    ]


def main():
    # 1. инициализация БД и приложения
    init_app()

    # 2. ввод параметров (для CLI MVP)
    print("=== Подбор помещения для банка ===")
    city = input("Город: ")
    district = input("Район: ")
    min_area = float(input("Мин. площадь (м²): "))
    max_area = float(input("Макс. площадь (м²): "))
    min_rate = float(input("Мин. ставка (₽/м²): "))
    max_rate = float(input("Макс. ставка (₽/м²): "))

    # 3. создаём заявку
    request_id = handle_new_request(
        city=city,
        district=district,
        min_area=min_area,
        max_area=max_area,
        min_rate=min_rate,
        max_rate=max_rate,
    )
    print(f"\nСоздана заявка #{request_id}")

    # 4. получаем (пока фейковые) объявления
    scraped_listings = fake_scrape_listings(city, district)

    # 5. сохраняем объявления и связи в БД
    process_request_with_listings(request_id, scraped_listings)

    # 6. строим отчёт через GigaChat
    report_md = build_report_for_request(request_id)

    print("\n=== Отчёт по заявке ===\n")
    print(report_md)


if __name__ == "__main__":
    main()
