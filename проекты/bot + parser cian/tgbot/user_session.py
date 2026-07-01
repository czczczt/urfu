import db

# Состояния бота
class BotState:
    WAITING_REQUEST = "waiting_request"  # Состояние 1: Ожидание запроса (начальное)
    CHOOSING_DEAL_TYPE = "choosing_deal_type"  # Состояние: Выбор типа сделки (аренда/продажа)
    WAITING_PROMPT = "waiting_prompt"    # Состояние: Ожидание промпта от пользователя
    COLLECTING_CITY = "collecting_city"  # Состояние 2: Сбор параметров (устаревшее, но оставим)
    COLLECTING_AREA = "collecting_area"
    COLLECTING_BUDGET = "collecting_budget"
    PROCESSING = "processing"  # Состояние 3: Обработка и ответ


# Хранилище данных пользователей
user_sessions = {}


def get_user_session(user_id: int) -> dict:
    """Получает или создает сессию пользователя"""
    if user_id not in user_sessions:
        # Загружаем данные из БД
        favorites = db.get_favorites(user_id)
        dislikes_list = db.get_dislikes(user_id)
        
        # Преобразуем дизлайки в формат сессии
        dislikes_dict = {}
        for item in dislikes_list:
            listing = item['listing']
            listing_id = listing.get('id')
            dislikes_dict[listing_id] = {
                "reason": item['reason'],
                "listing": listing
            }
            
        # Получаем ID лайков
        likes_ids = [l.get('id') for l in favorites]
        
        # Получаем ID исключенных (дизлайки)
        excluded_ids = [l.get('id') for l in [d['listing'] for d in dislikes_list]]

        user_sessions[user_id] = {
            "state": BotState.WAITING_REQUEST,
            "criteria": {
                "city": None,
                "district": None,
                "area_min": None,
                "area_max": None,
                "budget": None,
                "floor": None,
                "deal_type": None
            },
            "likes": likes_ids,
            "dislikes": dislikes_dict,
            "current_listings": [],
            "all_listings": favorites if favorites else [],
            "original_listings": favorites if favorites else [],
            "current_page": 0,
            "listings_per_page": 3,
            "dislike_message_id": None,
            "previous_state": None,
            "excluded_listing_ids": excluded_ids,
            "is_refining": False,
            "old_criteria": {},
            "favorite_index": 0,
            "sort_by": None,
            "sort_order": 'asc',
            # Spam protection
            "last_message_time": 0,
            "message_count": 0,
            "is_spamming": False
        }
        
    return user_sessions[user_id]


def reset_user_session(user_id: int):
    """Сбрасывает сессию пользователя (но сохраняет избранное из БД)"""
    # Загружаем данные из БД
    favorites = db.get_favorites(user_id)
    dislikes_list = db.get_dislikes(user_id)
    
    dislikes_dict = {}
    for item in dislikes_list:
        listing = item['listing']
        listing_id = listing.get('id')
        dislikes_dict[listing_id] = {
            "reason": item['reason'],
            "listing": listing
        }
        
    likes_ids = [l.get('id') for l in favorites]
    excluded_ids = [l.get('id') for l in [d['listing'] for d in dislikes_list]]

    user_sessions[user_id] = {
        "state": BotState.WAITING_REQUEST,
        "criteria": {
            "city": None,
            "district": None,
            "area_min": None,
            "area_max": None,
            "budget": None,
            "floor": None,
            "deal_type": None
        },
        "likes": likes_ids,
        "dislikes": dislikes_dict,
        "current_listings": [],
        "all_listings": [],
        "original_listings": [],
        "current_page": 0,
        "listings_per_page": 3,
        "dislike_message_id": None,
        "previous_state": None,
        "excluded_listing_ids": excluded_ids,
        "is_refining": False,
        "old_criteria": {},
        "favorite_index": 0,
        "sort_by": None,
        "sort_order": 'asc'
    }

def full_reset_user_session(user_id: int):
    """Полный сброс данных пользователя, включая БД"""
    db.reset_user_data(user_id)
    # После очистки БД, обычный сброс создаст пустую сессию
    reset_user_session(user_id)
