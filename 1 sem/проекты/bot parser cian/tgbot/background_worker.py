import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import db
from parser import parse_listings
from user_session import user_sessions, get_user_session

logger = logging.getLogger(__name__)

async def check_new_listings(context):
    """Проверка новых объявлений (запускается через JobQueue)"""
    logger.info("Запуск фоновой проверки объявлений...")
    
    # Получаем активных пользователей (за последние 48 часов)
    active_users = db.get_active_users(hours=48)
    
    for user_id in active_users:
        # Получаем подписки пользователя
        subscriptions = db.get_subscriptions(user_id)
        
        for sub in subscriptions:
            criteria = sub['criteria']
            
            # Парсим объявления
            listings = parse_listings(
                city=criteria.get("city"),
                district=criteria.get("district"),
                min_area=criteria.get("area_min"),
                max_area=criteria.get("area_max"),
                max_price=criteria.get("budget"),
                floor=criteria.get("floor"),
                deal_type=criteria.get("deal_type")
            )
            
            # Получаем уже просмотренные
            viewed_ids = db.get_viewed_ids(user_id)
            
            new_listings = []
            for listing in listings:
                listing_id = str(listing['id'])
                if listing_id not in viewed_ids:
                    new_listings.append(listing)
                    # Добавляем в просмотренные
                    db.add_viewed(user_id, listing_id)
            
            if new_listings:
                # Обновляем сессию пользователя, чтобы кнопки работали
                # Получаем или создаем сессию
                session = get_user_session(user_id)
                
                # Добавляем новые объявления в all_listings, если их там нет
                current_all = session.get("all_listings", [])
                existing_ids = {str(l.get('id')) for l in current_all}
                
                for l in new_listings:
                    if str(l.get('id')) not in existing_ids:
                        current_all.insert(0, l) # Добавляем в начало
                
                session["all_listings"] = current_all
                
                # Формируем описание критериев
                criteria_desc = []
                if criteria.get('city'):
                    criteria_desc.append(f"📍 Город: {criteria['city']}")
                
                deal_type = criteria.get('deal_type')
                if deal_type:
                    deal_text = "Аренда" if deal_type == 'rent' else "Продажа"
                    criteria_desc.append(f"💼 Тип: {deal_text}")
                
                if criteria.get('area_min') or criteria.get('area_max'):
                    area_parts = []
                    if criteria.get('area_min'):
                        area_parts.append(f"от {criteria['area_min']}")
                    if criteria.get('area_max'):
                        area_parts.append(f"до {criteria['area_max']}")
                    criteria_desc.append(f"📐 Площадь: {' '.join(area_parts)} м²")
                
                if criteria.get('budget'):
                    currency = "руб/мес" if deal_type == 'rent' else "руб"
                    criteria_desc.append(f"💰 Бюджет: до {criteria['budget']} {currency}")

                criteria_text = "\n".join(criteria_desc)

                # Генерируем уведомление
                count = len(new_listings)
                text = f"🔔 **Новые предложения!**\n\nНайдено {count} новых предложений по вашим критериям:\n\n{criteria_text}"
                
                keyboard = [[InlineKeyboardButton("👁 Посмотреть", callback_data="view_new_listings")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                try:
                    await context.bot.send_message(chat_id=user_id, text=text, parse_mode='Markdown', reply_markup=reply_markup)
                    logger.info(f"Уведомление отправлено пользователю {user_id}")
                except Exception as e:
                    logger.error(f"Ошибка отправки уведомления пользователю {user_id}: {e}")
