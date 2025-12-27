"""
Модуль для парсинга объявлений о помещениях
(Заглушка с мок-данными для демонстрации)
"""
from typing import List, Dict
import random
import os
import csv
import re
import hashlib


def parse_listings(city: str = None, district: str = None, min_area: int = None, max_area: int = None, min_price: int = None, max_price: int = None, floor: int = None, excluded_ids: List[int] = None, deal_type: str = None) -> List[Dict]:
    """
    Парсит объявления о помещениях по заданным критериям
    
    Args:
        city: Город
        district: Район
        min_area: Минимальная площадь в м²
        max_area: Максимальная площадь в м²
        min_price: Минимальная цена в руб/мес
        max_price: Максимальная цена в руб/мес
        floor: Этаж
        excluded_ids: Список ID объявлений для исключения
        deal_type: Тип сделки ('rent' - аренда, 'sale' - продажа)
    
    Returns:
        Список словарей с данными об объявлениях
    """
    # Мок-данные для демонстрации
    # В реальном проекте здесь будет парсинг с сайтов объявлений
    
    # Определяем город для адресов
    city_name = city if city else "Екатеринбург"  # По умолчанию Екатеринбург, если город не указан
    
    listings = []
    
    # Попытка загрузить из CSV (если есть)
    # Ищем CSV в папке parser на уровень выше
    
    # Маппинг городов для поиска CSV файлов
    city_mapping = {
        "москва": "moscow",
        "санкт-петербург": "spb",
        "екатеринбург": "ekaterinburg",
        "челябинск": "chelyabinsk"
    }
    
    csv_path = None
    if city:
        english_name = city_mapping.get(city.lower())
        if english_name:
            # Формируем имя файла в зависимости от типа сделки
            deal_suffix = "_rent" if deal_type == "rent" else "_sale" if deal_type == "sale" else ""
            csv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "parser", f"{english_name}_cian{deal_suffix}.csv")
    else:
        # Если город не указан, пробуем загрузить Екатеринбург как дефолтный
        deal_suffix = "_rent" if deal_type == "rent" else "_sale" if deal_type == "sale" else "_rent"
        csv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "parser", f"ekaterinburg_cian{deal_suffix}.csv")
    
    if csv_path and os.path.exists(csv_path):
        try:
            with open(csv_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for i, row in enumerate(reader):
                    try:
                        # Парсим цену
                        price_str = row.get("Цена", "").replace(" ", "").replace("₽/мес.", "").replace("\xa0", "")
                        price = int(price_str) if price_str.isdigit() else 0
                        
                        # Парсим площадь
                        area_str = row.get("Площадь", "").replace(" м²", "").replace(",", ".").replace("\xa0", "")
                        area = float(area_str) if area_str.replace(".", "").isdigit() else 0.0
                        
                        # Парсим этаж (извлекаем только число)
                        floor_str = row.get("Этаж", "1")
                        try:
                            # Извлекаем первое число из строки
                            floor_num = int(''.join(filter(str.isdigit, str(floor_str))) or "1")
                        except (ValueError, TypeError):
                            floor_num = 1
                        
                        # Генерируем стабильный ID
                        link = row.get("Ссылка", "")
                        listing_id = None
                        
                        # Пытаемся извлечь ID из ссылки CIAN
                        if link and "cian.ru" in link:
                            match = re.search(r'/(\d+)/', link)
                            if match:
                                listing_id = int(match.group(1))
                        
                        # Если не удалось, используем хеш от ссылки или адреса
                        if not listing_id:
                            unique_str = link if link else f"{row.get('Адрес')}{price}{area}"
                            listing_id = int(str(int(hashlib.md5(unique_str.encode('utf-8')).hexdigest(), 16))[:10])

                        listing = {
                            "id": listing_id,
                            "address": row.get("Адрес", ""),
                            "area": area,
                            "price": price,
                            "floor": floor_num,
                            "deal_type": deal_type if deal_type else "rent",  # Используем переданный тип сделки
                            "description": f"{row.get('Тип помещения', '')}. {row.get('Этажей в доме', '')} этажей.",
                            "traffic": "неизвестно",
                            "accessibility": "неизвестно",
                            "link": row.get("Ссылка", ""),
                            "phone": row.get("Телефон", "Не указан")
                        }
                        listings.append(listing)
                    except Exception as e:
                        continue
        except Exception as e:
            print(f"Ошибка чтения CSV: {e}")

    # Если CSV пуст или не найден, используем мок-данные
    if not listings:
        mock_listings = [
        {
            "id": 1,
            "address": f"{city_name}, ул. Центральная, д. 15",
            "area": 80,
            "price": 180000,
            "floor": 1,
            "deal_type": "rent",
            "description": "Помещение на первом этаже с хорошей проходимостью",
            "traffic": "высокий",
            "accessibility": "отличная",
            "link": "https://example.com/listings/1",
            "phone": "Не указан"
        },
        {
            "id": 2,
            "address": f"{city_name}, пр. Ленина, д. 42",
            "area": 120,
            "price": 250000,
            "floor": 1,
            "deal_type": "rent",
            "description": "Просторное помещение в центре города",
            "traffic": "очень высокий",
            "accessibility": "отличная",
            "link": "https://example.com/listings/2",
            "phone": "Не указан"
        },
        {
            "id": 3,
            "address": f"{city_name}, ул. Мира, д. 7",
            "area": 60,
            "price": 150000,
            "floor": 1,
            "deal_type": "rent",
            "description": "Компактное помещение рядом с метро",
            "traffic": "высокий",
            "accessibility": "хорошая",
            "link": "https://example.com/listings/3",
            "phone": "Не указан"
        },
        {
            "id": 4,
            "address": f"{city_name}, ул. Победы, д. 33",
            "area": 95,
            "price": 200000,
            "floor": 1,
            "deal_type": "rent",
            "description": "Помещение в торговом центре",
            "traffic": "очень высокий",
            "accessibility": "отличная",
            "link": "https://example.com/listings/4",
            "phone": "Не указан"
        },
        {
            "id": 5,
            "address": f"{city_name}, ул. Садовая, д. 12",
            "area": 70,
            "price": 170000,
            "floor": 1,
            "deal_type": "rent",
            "description": "Помещение с отдельным входом",
            "traffic": "средний",
            "accessibility": "хорошая",
            "link": "https://example.com/listings/5",
            "phone": "Не указан"
        },
        {
            "id": 6,
            "address": f"{city_name}, пр. Свободы, д. 88",
            "area": 110,
            "price": 280000,
            "floor": 1,
            "deal_type": "rent",
            "description": "Просторное помещение на проспекте",
            "traffic": "высокий",
            "accessibility": "отличная",
            "link": "https://example.com/listings/6",
            "phone": "Не указан"
        },
        {
            "id": 7,
            "address": f"{city_name}, ул. Рабочая, д. 5",
            "area": 55,
            "price": 140000,
            "floor": 1,
            "deal_type": "rent",
            "description": "Небольшое помещение в спальном районе",
            "traffic": "средний",
            "accessibility": "удовлетворительная",
            "link": "https://example.com/listings/7",
            "phone": "Не указан"
        },
        {
            "id": 8,
            "address": f"{city_name}, бул. Комсомольский, д. 20",
            "area": 85,
            "price": 190000,
            "floor": 1,
            "deal_type": "rent",
            "description": "Помещение с большими витринами",
            "traffic": "высокий",
            "accessibility": "хорошая",
            "link": "https://example.com/listings/8",
            "phone": "Не указан"
        },
        {
            "id": 9,
            "address": f"{city_name}, ул. Торговая, д. 25",
            "area": 100,
            "price": 220000,
            "floor": 1,
            "deal_type": "rent",
            "description": "Помещение в торговом квартале",
            "traffic": "очень высокий",
            "accessibility": "отличная",
            "link": "https://example.com/listings/9",
            "phone": "Не указан"
        },
        {
            "id": 10,
            "address": f"{city_name}, пр. Парковый, д. 14",
            "area": 65,
            "price": 160000,
            "floor": 1,
            "deal_type": "rent",
            "description": "Помещение рядом с парком",
            "traffic": "средний",
            "accessibility": "хорошая",
            "link": "https://example.com/listings/10",
            "phone": "Не указан"
        },
        {
            "id": 11,
            "address": f"{city_name}, ул. Деловая, д. 50",
            "area": 130,
            "price": 300000,
            "floor": 1,
            "deal_type": "rent",
            "description": "Просторное помещение в деловом центре",
            "traffic": "очень высокий",
            "accessibility": "отличная",
            "link": "https://example.com/listings/11",
            "phone": "Не указан"
        },
        {
            "id": 12,
            "address": f"{city_name}, ул. Студенческая, д. 8",
            "area": 75,
            "price": 175000,
            "floor": 1,
            "deal_type": "rent",
            "description": "Помещение в студенческом районе",
            "traffic": "высокий",
            "accessibility": "хорошая",
            "link": "https://example.com/listings/12",
            "phone": "Не указан"
        },
        {
            "id": 13,
            "address": f"{city_name}, пр. Октябрьский, д. 66",
            "area": 90,
            "price": 195000,
            "floor": 1,
            "deal_type": "rent",
            "description": "Помещение на оживленном проспекте",
            "traffic": "высокий",
            "accessibility": "отличная",
            "link": "https://example.com/listings/13",
            "phone": "Не указан"
        },
        {
            "id": 14,
            "address": f"{city_name}, ул. Спортивная, д. 19",
            "area": 58,
            "price": 145000,
            "floor": 1,
            "deal_type": "rent",
            "description": "Компактное помещение в спортивном районе",
            "traffic": "средний",
            "accessibility": "удовлетворительная",
            "link": "https://example.com/listings/14",
            "phone": "Не указан"
        },
        {
            "id": 15,
            "address": f"{city_name}, бул. Набережный, д. 30",
            "area": 105,
            "price": 240000,
            "floor": 1,
            "deal_type": "rent",
            "description": "Помещение с видом на набережную",
            "traffic": "высокий",
            "accessibility": "хорошая",
            "link": "https://example.com/listings/15",
            "phone": "Не указан"
        },
        {
            "id": 16,
            "address": f"{city_name}, ул. Новая, д. 11",
            "area": 50,
            "price": 85000,
            "floor": 1,
            "deal_type": "rent",
            "description": "Компактное помещение в новом районе",
            "traffic": "средний",
            "accessibility": "хорошая",
            "link": "https://example.com/listings/16",
            "phone": "Не указан"
        },
        {
            "id": 17,
            "address": f"{city_name}, ул. Заводская, д. 22",
            "area": 65,
            "price": 95000,
            "floor": 1,
            "deal_type": "rent",
            "description": "Помещение в промышленном районе",
            "traffic": "средний",
            "accessibility": "удовлетворительная",
            "link": "https://example.com/listings/17",
            "phone": "Не указан"
        },
        {
            "id": 18,
            "address": f"{city_name}, ул. Школьная, д. 9",
            "area": 55,
            "price": 90000,
            "floor": 1,
            "deal_type": "rent",
            "description": "Помещение рядом со школой",
            "traffic": "высокий",
            "accessibility": "хорошая",
            "link": "https://example.com/listings/18",
            "phone": "Не указан"
        },
        {
            "id": 19,
            "address": f"{city_name}, пр. Мира, д. 45",
            "area": 70,
            "price": 98000,
            "floor": 1,
            "deal_type": "rent",
            "description": "Помещение на проспекте",
            "traffic": "высокий",
            "accessibility": "отличная",
            "link": "https://example.com/listings/19",
            "phone": "Не указан"
        },
        {
            "id": 20,
            "address": f"{city_name}, ул. Парковая, д. 18",
            "area": 60,
            "price": 92000,
            "floor": 1,
            "deal_type": "rent",
            "description": "Помещение в парковой зоне",
            "traffic": "средний",
            "accessibility": "хорошая",
            "link": "https://example.com/listings/20",
            "phone": "Не указан"
        },
        {
            "id": 21,
            "address": f"{city_name}, ул. Центральная, д. 33",
            "area": 75,
            "price": 99000,
            "floor": 1,
            "deal_type": "rent",
            "description": "Помещение в центре города",
            "traffic": "очень высокий",
            "accessibility": "отличная",
            "link": "https://example.com/listings/21",
            "phone": "Не указан"
        },
        {
            "id": 22,
            "address": f"{city_name}, ул. Торговая, д. 7",
            "area": 58,
            "price": 88000,
            "floor": 1,
            "deal_type": "rent",
            "description": "Помещение в торговой зоне",
            "traffic": "высокий",
            "accessibility": "хорошая",
            "link": "https://example.com/listings/22",
            "phone": "Не указан"
        },
        {
            "id": 23,
            "address": f"{city_name}, пр. Ленина, д. 55",
            "area": 68,
            "price": 96000,
            "floor": 1,
            "deal_type": "rent",
            "description": "Помещение на главном проспекте",
            "traffic": "очень высокий",
            "accessibility": "отличная",
            "link": "https://example.com/listings/23",
            "phone": "Не указан"
        },
        {
            "id": 24,
            "address": f"{city_name}, ул. Мира, д. 12",
            "area": 52,
            "price": 87000,
            "floor": 1,
            "deal_type": "rent",
            "description": "Небольшое помещение в центре",
            "traffic": "высокий",
            "accessibility": "хорошая",
            "link": "https://example.com/listings/24",
            "phone": "Не указан"
        },
        {
            "id": 25,
            "address": f"{city_name}, ул. Садовая, д. 28",
            "area": 62,
            "price": 93000,
            "floor": 1,
            "deal_type": "rent",
            "description": "Помещение в спальном районе",
            "traffic": "средний",
            "accessibility": "удовлетворительная",
            "link": "https://example.com/listings/25",
            "phone": "Не указан"
        },
        {
            "id": 26,
            "address": f"{city_name}, ул. Бизнес-центр, д. 10",
            "area": 140,
            "price": 320000,
            "floor": 2,
            "deal_type": "rent",
            "description": "Просторное офисное помещение на втором этаже бизнес-центра",
            "traffic": "высокий",
            "accessibility": "отличная",
            "link": "https://example.com/listings/26",
            "phone": "Не указан"
        },
        {
            "id": 27,
            "address": f"{city_name}, пр. Деловой, д. 25",
            "area": 88,
            "price": 210000,
            "floor": 2,
            "deal_type": "rent",
            "description": "Офисное помещение на втором этаже с панорамными окнами",
            "traffic": "высокий",
            "accessibility": "отличная",
            "link": "https://example.com/listings/27",
            "phone": "Не указан"
        },
        {
            "id": 28,
            "address": f"{city_name}, ул. Офисная, д. 8",
            "area": 72,
            "price": 165000,
            "floor": 2,
            "deal_type": "rent",
            "description": "Комфортное помещение на втором этаже",
            "traffic": "средний",
            "accessibility": "хорошая",
            "link": "https://example.com/listings/28",
            "phone": "Не указан"
        },
        {
            "id": 29,
            "address": f"{city_name}, пр. Центральный, д. 50",
            "area": 115,
            "price": 270000,
            "floor": 3,
            "deal_type": "rent",
            "description": "Просторное помещение на третьем этаже в центре города",
            "traffic": "очень высокий",
            "accessibility": "отличная",
            "link": "https://example.com/listings/29",
            "phone": "Не указан"
        },
        {
            "id": 30,
            "address": f"{city_name}, ул. Торговая, д. 40",
            "area": 95,
            "price": 230000,
            "floor": 3,
            "deal_type": "rent",
            "description": "Помещение на третьем этаже торгового центра",
            "traffic": "очень высокий",
            "accessibility": "отличная",
            "link": "https://example.com/listings/30",
            "phone": "Не указан"
        },
        {
            "id": 31,
            "address": f"{city_name}, ул. Деловая, д. 15",
            "area": 78,
            "price": 185000,
            "floor": 3,
            "deal_type": "rent",
            "description": "Офисное помещение на третьем этаже",
            "traffic": "высокий",
            "accessibility": "хорошая",
            "link": "https://example.com/listings/31",
            "phone": "Не указан"
        },
        {
            "id": 32,
            "address": f"{city_name}, пр. Ленина, д. 30",
            "area": 105,
            "price": 245000,
            "floor": 4,
            "deal_type": "rent",
            "description": "Помещение на четвертом этаже с хорошим видом",
            "traffic": "высокий",
            "accessibility": "отличная",
            "link": "https://example.com/listings/32",
            "phone": "Не указан"
        },
        {
            "id": 33,
            "address": f"{city_name}, ул. Бизнес-парк, д. 5",
            "area": 125,
            "price": 290000,
            "floor": 4,
            "deal_type": "rent",
            "description": "Просторное помещение на четвертом этаже бизнес-парка",
            "traffic": "высокий",
            "accessibility": "отличная",
            "link": "https://example.com/listings/33",
            "phone": "Не указан"
        },
        {
            "id": 34,
            "address": f"{city_name}, ул. Офисная, д. 22",
            "area": 82,
            "price": 195000,
            "floor": 4,
            "deal_type": "rent",
            "description": "Офисное помещение на четвертом этаже",
            "traffic": "средний",
            "accessibility": "хорошая",
            "link": "https://example.com/listings/34",
            "phone": "Не указан"
        },
        {
            "id": 35,
            "address": f"{city_name}, пр. Деловой, д. 60",
            "area": 150,
            "price": 350000,
            "floor": 5,
            "deal_type": "rent",
            "description": "Большое помещение на пятом этаже с панорамными окнами",
            "traffic": "очень высокий",
            "accessibility": "отличная",
            "link": "https://example.com/listings/35",
            "phone": "Не указан"
        },
        {
            "id": 36,
            "address": f"{city_name}, ул. Центральная, д. 45",
            "area": 98,
            "price": 225000,
            "floor": 5,
            "deal_type": "rent",
            "description": "Помещение на пятом этаже в центре",
            "traffic": "высокий",
            "accessibility": "отличная",
            "link": "https://example.com/listings/36",
            "phone": "Не указан"
        },
        {
            "id": 37,
            "address": f"{city_name}, ул. Бизнес-центр, д. 12",
            "area": 110,
            "price": 260000,
            "floor": 5,
            "deal_type": "rent",
            "description": "Офисное помещение на пятом этаже бизнес-центра",
            "traffic": "высокий",
            "accessibility": "отличная",
            "link": "https://example.com/listings/37",
            "phone": "Не указан"
        }
    ]
    
    # Если listings пуст (не загрузился CSV), используем mock_listings
    if not listings:
        listings = mock_listings

    # Применяем бизнес-правила фильтрации (Business Rules)
    filtered_listings = []
    for l in listings:
        # 1. Цена должна быть адекватной (>= 1000)
        if l.get("price", 0) < 1000:
            continue
        
        # 2. Описание должно быть информативным (>= 10 символов)
        if len(l.get("description", "")) < 10:
            continue
            
        # 3. Площадь должна быть положительной
        if l.get("area", 0) <= 0:
            continue
            
        filtered_listings.append(l)
    
    listings = filtered_listings

    # Фильтруем по критериям
    if excluded_ids is None:
        excluded_ids = []
    
    # Исключаем объявления по ID
    available_listings = [l for l in listings if l["id"] not in excluded_ids]
    
    # Строгая фильтрация по району (если указан)
    if district:
        filtered_by_district = []
        for listing in available_listings:
            is_match = False
            if isinstance(district, list):
                for d in district:
                    clean_d = d.lower().replace("район", "").replace("р-н", "").replace("ский", "").replace("ый", "").strip()
                    # Для "Центральный" ищем "центр", для "Ленинский" - "ленин"
                    if clean_d and clean_d in listing["address"].lower():
                        is_match = True
                        break
            else:
                clean_district = district.lower().replace("район", "").replace("р-н", "").replace("ский", "").replace("ый", "").strip()
                # Для "Центральный" ищем "центр", для "Ленинский" - "ленин"
                if clean_district and clean_district in listing["address"].lower():
                    is_match = True
            
            if is_match:
                filtered_by_district.append(listing)
        
        available_listings = filtered_by_district

    if not available_listings:
        return []
    
    # Функция для проверки, соответствует ли объявление всем критериям
    def matches_all_criteria(listing):
        # Проверка города (если указан)
        if city and city.lower() not in listing["address"].lower():
            return False

        # Проверка района
        if district:
            if isinstance(district, list):
                # Если список районов, проверяем, есть ли хотя бы один из них в адресе
                found = False
                for d in district:
                    clean_d = d.lower().replace("район", "").replace("р-н", "").replace("ский", "").replace("ый", "").strip()
                    # Для "Центральный" ищем "центр", для "Ленинский" - "ленин"
                    if clean_d and clean_d in listing["address"].lower():
                        found = True
                        break
                if not found:
                    return False
            else:
                # Нормализуем название района для поиска
                clean_district = district.lower().replace("район", "").replace("р-н", "").replace("ский", "").replace("ый", "").strip()
                # Для "Центральный" ищем "центр", для "Ленинский" - "ленин"
                if clean_district and clean_district not in listing["address"].lower():
                    return False

        # Проверка площади
        if min_area and listing["area"] < min_area:
            return False
        if max_area and listing["area"] > max_area:
            return False
        # Проверка бюджета
        if min_price and listing["price"] < min_price:
            return False
        if max_price and listing["price"] > max_price:
            return False
            
        # Проверка этажа
        if floor is not None:
            try:
                listing_floor = int(listing.get("floor", 0))
                if listing_floor != floor:
                    return False
            except (ValueError, TypeError):
                pass
                
        return True
    
    # Функция для вычисления "расстояния" от объявления до критериев (чем меньше, тем ближе)
    def calculate_distance(listing):
        distance = 0
        
        # Штраф за несовпадение района (очень большой)
        if district:
            is_match = False
            if isinstance(district, list):
                for d in district:
                    clean_d = d.lower().replace("район", "").replace("р-н", "").replace("ский", "").replace("ый", "").strip()
                    # Для "Центральный" ищем "центр", для "Ленинский" - "ленин"
                    if clean_d and clean_d in listing["address"].lower():
                        is_match = True
                        break
            else:
                clean_district = district.lower().replace("район", "").replace("р-н", "").replace("ский", "").replace("ый", "").strip()
                # Для "Центральный" ищем "центр", для "Ленинский" - "ленин"
                if clean_district and clean_district in listing["address"].lower():
                    is_match = True
            
            if not is_match:
                distance += 10000000  # Огромный штраф, чтобы такие объявления были в конце

        # Штраф за несовпадение этажа
        if floor is not None:
            try:
                listing_floor = int(listing.get("floor", 0))
                if listing_floor != floor:
                    distance += 5000000  # Большой штраф
            except (ValueError, TypeError):
                pass

        # Расстояние по площади
        if min_area and listing["area"] < min_area:
            # Если площадь меньше минимальной, штрафуем пропорционально разнице
            distance += (min_area - listing["area"]) * 1000
        elif max_area and listing["area"] > max_area:
            # Если площадь больше максимальной, штрафуем пропорционально разнице
            distance += (listing["area"] - max_area) * 1000
        # Расстояние по бюджету
        if min_price and listing["price"] < min_price:
            distance += (min_price - listing["price"]) * 2
        elif max_price and listing["price"] > max_price:
            distance += (listing["price"] - max_price) * 2
        elif max_price:
            # Если цена в пределах бюджета, но далеко от него - небольшой штраф
            # Предпочитаем объявления ближе к бюджету
            distance += abs(listing["price"] - max_price) * 0.1
        
        return distance
    
    # Сначала ищем объявления, полностью соответствующие всем критериям
    perfect_matches = [l for l in available_listings if matches_all_criteria(l)]
    
    return perfect_matches
    
    # Если идеальных совпадений нет - ищем максимально близкие по всем критериям
    # Вычисляем расстояние для каждого объявления
    # listings_with_distance = [(l, calculate_distance(l)) for l in available_listings]
    
    # Сортируем по расстоянию (от ближайших к дальним)
    # closest_listings = sorted(listings_with_distance, key=lambda x: x[1])
    
    # Возвращаем ближайшие (до 15 самых близких)
    # return [l[0] for l in closest_listings[:15]]


def get_listing_by_id(listing_id: int, city: str = None, deal_type: str = None) -> Dict:
    """
    Получает объявление по ID
    
    Args:
        listing_id: ID объявления
        city: Город (для поиска в нужном CSV файле)
        deal_type: Тип сделки ('rent' - аренда, 'sale' - продажа)
    
    Returns:
        Словарь с данными объявления или None если не найдено
    """
    # Маппинг городов для поиска CSV файлов
    city_mapping = {
        "москва": "moscow",
        "санкт-петербург": "spb",
        "екатеринбург": "ekaterinburg",
        "челябинск": "chelyabinsk"
    }
    
    # Список путей к CSV файлам для проверки
    csv_paths = []
    
    if city:
        english_name = city_mapping.get(city.lower())
        if english_name:
            if deal_type:
                deal_suffix = "_rent" if deal_type == "rent" else "_sale"
                csv_paths.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), "parser", f"{english_name}_cian{deal_suffix}.csv"))
            else:
                # Проверяем оба типа
                csv_paths.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), "parser", f"{english_name}_cian_rent.csv"))
                csv_paths.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), "parser", f"{english_name}_cian_sale.csv"))
    else:
        # Проверяем все доступные CSV файлы
        parser_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "parser")
        if os.path.exists(parser_dir):
            for filename in os.listdir(parser_dir):
                if filename.endswith(".csv"):
                    csv_paths.append(os.path.join(parser_dir, filename))
    
    # Ищем объявление во всех CSV файлах
    for csv_path in csv_paths:
        if not os.path.exists(csv_path):
            continue
            
        try:
            with open(csv_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        # Парсим данные аналогично parse_listings
                        link = row.get("Ссылка", "")
                        current_id = None
                        
                        # Пытаемся извлечь ID из ссылки CIAN
                        if link and "cian.ru" in link:
                            match = re.search(r'/(\d+)/', link)
                            if match:
                                current_id = int(match.group(1))
                        
                        # Если не удалось, используем хеш
                        if not current_id:
                            unique_str = link if link else f"{row.get('Адрес')}{row.get('Цена')}{row.get('Площадь')}"
                            current_id = int(str(int(hashlib.md5(unique_str.encode('utf-8')).hexdigest(), 16))[:10])
                        
                        # Если нашли нужное объявление
                        if current_id == listing_id:
                            # Парсим цену
                            price_str = row.get("Цена", "").replace(" ", "").replace("₽/мес.", "").replace("\xa0", "")
                            price = int(price_str) if price_str.isdigit() else 0
                            
                            # Парсим площадь
                            area_str = row.get("Площадь", "").replace(" м²", "").replace(",", ".").replace("\xa0", "")
                            area = float(area_str) if area_str.replace(".", "").isdigit() else 0.0
                            
                            # Парсим этаж
                            floor_str = row.get("Этаж", "1")
                            try:
                                floor_num = int(''.join(filter(str.isdigit, str(floor_str))) or "1")
                            except (ValueError, TypeError):
                                floor_num = 1
                            
                            # Определяем тип сделки из имени файла
                            detected_deal_type = "rent" if "_rent" in csv_path else "sale" if "_sale" in csv_path else "rent"
                            
                            return {
                                "id": current_id,
                                "address": row.get("Адрес", ""),
                                "area": area,
                                "price": price,
                                "floor": floor_num,
                                "deal_type": detected_deal_type,
                                "description": f"{row.get('Тип помещения', '')}. {row.get('Этажей в доме', '')} этажей.",
                                "traffic": "неизвестно",
                                "accessibility": "неизвестно",
                                "link": row.get("Ссылка", ""),
                                "phone": row.get("Телефон", "Не указан")
                            }
                    except Exception as e:
                        continue
        except Exception as e:
            continue
    
    return None

