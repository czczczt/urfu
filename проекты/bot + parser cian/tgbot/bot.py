"""
Telegram бот для подбора помещений
"""
import logging
import asyncio
import time
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from config import TELEGRAM_BOT_TOKEN
from ai_integration import ai_service
from speech_service import speech_service
from parser import parse_listings
import db  # Import the new database module
from background_worker import check_new_listings
from user_session import BotState, user_sessions, get_user_session, reset_user_session, full_reset_user_session as session_full_reset

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


HELP_TEXT = """📚 Справка по использованию бота:

Бот поможет подобрать помещение на основе ваших критериев:
• Город расположения
• Площадь помещения
• Бюджет на аренду

💡 Важно: Любой критерий можно пропустить, написав "не важно" или просто пропустив его. Поиск будет произведен по указанным критериям.

После ввода параметров бот:
1. Найдет подходящие объявления
2. Проанализирует их с помощью ИИ
3. Покажет найденные варианты с объяснением выбора

Вы можете оценить каждое объявление:
👍 Лайк - помещение понравилось, предпочтение сохранено
👎 Дизлайк - помещение не подходит, убирается из списка (можно вернуть во вкладке "непонравившиеся")

Команды:
/start - Начать поиск заново (полный сброс данных)
/help - Показать эту справку

Кнопки:
🆕 Новый чат - полностью очистить все данные сессии и начать заново
🔍 Уточнить критерии - изменить параметры поиска (предпочтения сохраняются)
⏭ Пропустить - пропустить указание критерия (поиск по остальным параметрам)"""


# Состояния бота (импортированы из user_session)


# Хранилище данных пользователей (импортировано из user_session)





def get_main_page_buttons(session: dict, user_id: int = None) -> list:
    """
    Возвращает список кнопок главной страницы в зависимости от состояния сессии
    
    Args:
        session: Сессия пользователя
        user_id: ID пользователя для проверки избранного в БД
    
    Returns:
        Список списков кнопок для InlineKeyboardMarkup
    """
    keyboard = []
    
    # Проверяем, есть ли активная сессия (критерии заданы или есть объявления)
    criteria = session.get("criteria", {})
    all_listings = session.get("all_listings", [])
    has_active_session = (
        criteria.get("city") is not None or
        criteria.get("area_min") is not None or
        criteria.get("area_max") is not None or
        criteria.get("budget_min") is not None or
        criteria.get("budget_max") is not None or
        len(all_listings) > 0
    )
    
    # Проверяем наличие избранного и скрытых в БД
    has_favorites = False
    has_dislikes = False
    if user_id:
        has_favorites = len(db.get_favorite_ids(user_id)) > 0
        has_dislikes = len(db.get_disliked_ids(user_id)) > 0
    
    if not has_active_session:
        # Начальный экран: кнопки выбора типа сделки
        keyboard.append([InlineKeyboardButton("💼 Арендовать помещение", callback_data="deal_type_rent")])
        keyboard.append([InlineKeyboardButton("🏢 Купить помещение", callback_data="deal_type_sale")])
        
        # Добавляем кнопки избранного и скрытых, если они есть
        row_fav = []
        if has_favorites:
            row_fav.append(InlineKeyboardButton("❤️ Понравившиеся", callback_data="favorites"))
        
        if has_dislikes:
            row_fav.append(InlineKeyboardButton("💔 Скрытые", callback_data="dislikes"))
            
        if row_fav:
            keyboard.append(row_fav)
        
        # Добавляем кнопку настроек
        keyboard.append([InlineKeyboardButton("⚙️ Настройки", callback_data="settings")])
        
    else:
        # Активная сессия: показываем все кнопки кроме "Начать поиск"
        # Первая строка: Понравившиеся и Уточнить критерии
        row1 = []
        if has_favorites:
            row1.append(InlineKeyboardButton("❤️ Понравившиеся", callback_data="favorites"))
        
        # Добавляем кнопку для скрытых (дизлайкнутых) объявлений
        if has_dislikes:
            row1.append(InlineKeyboardButton("💔 Скрытые", callback_data="dislikes"))
            
        row1.append(InlineKeyboardButton("🔍 Уточнить критерии", callback_data="refine"))
        keyboard.append(row1)
        
        # Вторая строка: Новый поиск и Настройки
        row2 = [
            InlineKeyboardButton("🆕 Новый поиск", callback_data="new_chat"),
            InlineKeyboardButton("⚙️ Настройки", callback_data="settings")
        ]
        keyboard.append(row2)
        
        # Если есть объявления, добавляем кнопку "Показать результаты"
        if all_listings:
            keyboard.append([InlineKeyboardButton("📋 Показать результаты", callback_data="show_results")])
            
        # Если есть сравнение (больше 1 элемента), добавляем кнопку
        comparison_list = session.get("comparison_list", [])
        if len(comparison_list) > 1:
            keyboard.append([InlineKeyboardButton(f"⚖️ Сравнить ({len(comparison_list)})", callback_data="show_comparison")])
    
    return keyboard


def get_to_main_button() -> list:
    """
    Возвращает кнопку "На главную" для добавления на другие страницы
    
    Returns:
        Список с одной кнопкой
    """
    return [[InlineKeyboardButton("🏠 На главную", callback_data="to_main")]]


def create_temp_update_from_query(query):
    """Создает временный объект Update из callback query"""
    class TempUpdate:
        def __init__(self, callback_query):
            self.callback_query = callback_query
            self.effective_user = callback_query.from_user
    
    return TempUpdate(query)


async def show_main_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает главную страницу с кнопками навигации в зависимости от состояния сессии"""
    user_id = update.effective_user.id
    session = get_user_session(user_id)
    
    all_listings = session.get("all_listings", [])
    criteria = session.get("criteria", {})
    
    # Проверяем, есть ли активная сессия
    has_active_session = (
        criteria.get("city") is not None or
        criteria.get("area_min") is not None or
        criteria.get("area_max") is not None or
        criteria.get("budget_min") is not None or
        criteria.get("budget_max") is not None or
        len(all_listings) > 0
    )
    
    if not has_active_session:
        # Начальный экран
        main_text = """🏦 **Главная страница**

Добро пожаловать! Я помогу подобрать помещение.

Что вы хотите сделать?"""
    else:
        # Активная сессия
        main_text = """🏦 **Главная страница** """
        
        if all_listings:
            main_text += f"\n\n✅ Найдено помещений: **{len(all_listings)}**\nНажмите кнопку ниже, чтобы посмотреть результаты."
        
        main_text += "\n\nВыберите действие:"
    
    keyboard = get_main_page_buttons(session, user_id)
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if hasattr(update, 'message') and update.message:
        await update.message.reply_text(main_text, parse_mode='Markdown', reply_markup=reply_markup)
    elif hasattr(update, 'callback_query') and update.callback_query:
        query = update.callback_query
        await query.edit_message_text(main_text, parse_mode='Markdown', reply_markup=reply_markup)
        await query.answer()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    user_id = user.id
    
    # Обновляем данные пользователя в БД
    db.update_user(user_id, user.username, user.first_name)
    
    # Проверяем, есть ли история поиска
    last_search = db.get_last_search(user_id)
    
    if last_search:
        # Существующий пользователь
        reset_user_session(user_id) # Сбрасываем сессию, но не БД
        
        # Формируем текст критериев
        criteria_text = []
        if last_search.get('city'): criteria_text.append(f"Город: {last_search['city']}")
        
        if last_search.get('budget_min') and last_search.get('budget_max'):
            criteria_text.append(f"Бюджет: {last_search['budget_min']}-{last_search['budget_max']}")
        elif last_search.get('budget_min'):
            criteria_text.append(f"Бюджет от: {last_search['budget_min']}")
        elif last_search.get('budget_max'):
            criteria_text.append(f"Бюджет до: {last_search['budget_max']}")
            
        if last_search.get('area_min'): criteria_text.append(f"Площадь от: {last_search['area_min']}")
        
        criteria_str = ", ".join(criteria_text) if criteria_text else "без конкретных параметров"
        
        text = f"С возвращением, {user.first_name}! 👋\n\nВ прошлый раз вы искали: {criteria_str}.\n\nХотите продолжить поиск с этими параметрами или начать заново?"
        
        keyboard = [
            [InlineKeyboardButton("✅ Продолжить поиск", callback_data="restore_search")],
            [InlineKeyboardButton("🔄 Начать заново", callback_data="new_chat")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup)
    else:
        # Новый пользователь
        reset_user_session(user_id)
        await show_main_page(update, context)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    user_id = update.effective_user.id
    session = get_user_session(user_id)
    
    # Сохраняем текущее состояние как предыдущее для кнопки "Назад"
    session["previous_state"] = session["state"]
    
    # Создаем кнопку "На главную"
    keyboard = get_to_main_button()
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(HELP_TEXT, reply_markup=reply_markup)


async def process_user_text(user_id: int, user_message: str, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает текстовый ввод пользователя (из сообщения или голоса)"""
    # user_id уже передан
    # user_message уже передан
    session = get_user_session(user_id)
    state = session["state"]
    
    # Проверяем доступность ИИ
    if not ai_service.is_available() and state != BotState.COLLECTING_CITY:
        await update.message.reply_text(
            "❌ ИИ модель не настроена.\n\n"
            "Для работы бота необходимо:\n"
            "1. Создать .env файл\n"
            "2. Добавить GIGACHAT_CREDENTIALS=ваш_ключ\n"
            "3. Перезапустить бота\n\n"
            "Получить ключ можно на https://developers.sber.ru/studio"
        )
        return
    
    # Обработка в зависимости от состояния
    if state == BotState.WAITING_PROMPT:
        if not user_message:
            await update.message.reply_text("Пожалуйста, введите запрос текстом.")
            return

        await update.message.reply_text("⏳ Анализирую ваш запрос...")
        
        # Получаем текущий город из сессии (если есть)
        current_city = session["criteria"].get("city")
        
        # Извлекаем параметры через ИИ
        params = await ai_service.extract_search_parameters(user_message, current_city=current_city)
        
        if not params:
            await update.message.reply_text("❌ Не удалось распознать параметры. Попробуйте переформулировать запрос.")
            return
            
        # Обновляем критерии
        keys_to_update = [
            "city", "district", "area_min", "area_max", "budget_min", "budget_max", "floor",
            "excluded_districts", "excluded_floors", "priority", "urgency", 
            "accessibility", "is_strict", "deal_type", "renovation_status", 
            "parking", "entrance_type"
        ]

        if session.get("is_refining"):
            # При уточнении: обновляем только те параметры, которые явно указаны в новом запросе
            # Остальные сохраняем из старых критериев
            old_criteria = session.get("old_criteria", {})
            
            # Получаем тип операции для районов
            district_op = params.get("district_operation", "replace")
            
            # Определяем, обновляются ли группы параметров (бюджет и площадь)
            # Если хотя бы один параметр из группы указан, считаем, что группа переопределяется полностью
            budget_updated = (params.get("budget_min") is not None or params.get("budget_max") is not None or 
                              params.get("budget_min") == "RESET" or params.get("budget_max") == "RESET")
            
            area_updated = (params.get("area_min") is not None or params.get("area_max") is not None or
                            params.get("area_min") == "RESET" or params.get("area_max") == "RESET")
            
            for key in keys_to_update:
                val = params.get(key)
                
                # Определяем, нужно ли пропускать восстановление старого значения
                skip_restore = False
                if key in ["budget_min", "budget_max"] and budget_updated:
                    skip_restore = True
                if key in ["area_min", "area_max"] and area_updated:
                    skip_restore = True
                
                if val == "RESET":
                    session["criteria"][key] = None
                elif val is not None:
                    # Для районов - специальная обработка списков
                    if key == "district":
                        if district_op == "add":
                            existing = session["criteria"].get("district")
                            # Преобразуем существующее значение в список
                            if existing is None:
                                existing = []
                            elif isinstance(existing, str):
                                existing = [existing]
                            # Преобразуем новое значение в список
                            new_districts = [val] if isinstance(val, str) else (val if isinstance(val, list) else [])
                            # Объединяем и убираем дубликаты
                            combined = list(set(existing + new_districts))
                            # Сохраняем как список если больше одного, иначе как строку
                            session["criteria"][key] = combined if len(combined) > 1 else (combined[0] if combined else None)
                        else:
                            # Если replace или не указано - просто заменяем
                            session["criteria"][key] = val
                    else:
                        session["criteria"][key] = val
                else:
                    # Если параметр не указан в новом запросе
                    if skip_restore:
                        # Если группа обновляется, но конкретное значение не указано - сбрасываем его
                        session["criteria"][key] = None
                    elif old_criteria.get(key) is not None:
                        # Иначе сохраняем старое значение
                        session["criteria"][key] = old_criteria[key]
            
            session["is_refining"] = False
        else:
            # При первом запросе просто записываем все параметры
            for key in keys_to_update:
                val = params.get(key)
                if val == "RESET":
                    session["criteria"][key] = None
                elif val is not None:
                    # Для районов - специальная обработка списков
                    if key == "district":
                        # При первом запросе сохраняем район как есть (строка или список)
                        session["criteria"][key] = val
                    else:
                        session["criteria"][key] = val
        
        # Формируем сводку
        summary = "**Распознанные критерии:**\n"
        summary += f"📍 Город: {session['criteria']['city'] or 'не указан'}\n"
        if session['criteria']['district']:
            # Обрабатываем список районов или одиночный район
            districts = session['criteria']['district']
            if isinstance(districts, list):
                summary += f"🏙 Район: {', '.join(districts)}\n"
            else:
                summary += f"🏙 Район: {districts}\n"
        
        if session['criteria']['area_min'] and session['criteria']['area_max']:
            summary += f"📐 Площадь: {session['criteria']['area_min']}-{session['criteria']['area_max']} м²\n"
        elif session['criteria']['area_min']:
            summary += f"📐 Площадь: от {session['criteria']['area_min']} м²\n"
        elif session['criteria']['area_max']:
            summary += f"📐 Площадь: до {session['criteria']['area_max']} м²\n"
        
        if session['criteria'].get('budget_min') and session['criteria'].get('budget_max'):
            price_suffix = "руб/мес" if session['criteria'].get('deal_type') == 'rent' else "руб"
            summary += f"💰 Бюджет: {session['criteria']['budget_min']:,}-{session['criteria']['budget_max']:,} {price_suffix}\n"
        elif session['criteria'].get('budget_min'):
            price_suffix = "руб/мес" if session['criteria'].get('deal_type') == 'rent' else "руб"
            summary += f"💰 Бюджет: от {session['criteria']['budget_min']:,} {price_suffix}\n"
        elif session['criteria'].get('budget_max'):
            price_suffix = "руб/мес" if session['criteria'].get('deal_type') == 'rent' else "руб"
            summary += f"💰 Бюджет: до {session['criteria']['budget_max']:,} {price_suffix}\n"
            
        if session['criteria']['floor']:
            summary += f"🏢 Этаж: {session['criteria']['floor']}\n"

        await update.message.reply_text(
            f"{summary}\n"
            "🔍 Ищу подходящие помещения...",
            parse_mode='Markdown'
        )
        
        session["state"] = BotState.PROCESSING
        await process_search(update, context)
        return

    if state == BotState.COLLECTING_CITY:
        # Проверяем пустой ввод или "не важно"
        if not user_message or user_message.lower() in ["не важно", "неважно", "не важно", "пропустить", "skip"]:
            session["criteria"]["city"] = None
            city_status = "не указан"
        else:
            session["criteria"]["city"] = user_message
            city_status = user_message
        
        # Сохраняем предыдущее состояние
        session["previous_state"] = BotState.COLLECTING_CITY
        session["state"] = BotState.COLLECTING_AREA
        
        # Получаем старое значение площади для подсказки
        old_criteria = session.get("old_criteria", {})
        area_hint = ""
        if old_criteria.get("area_min") and old_criteria.get("area_max"):
            area_hint = f"\n💭 Предыдущее значение: {old_criteria['area_min']}-{old_criteria['area_max']} м²"
        
        # Создаем кнопки для выбора "не важно"
        keyboard = [
            [InlineKeyboardButton("⏭ Пропустить (не важно)", callback_data="skip_area")],
            [InlineKeyboardButton("🏠 На главную", callback_data="to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"✅ Город: {city_status}\n\n"
            "Теперь укажите площадь помещения.\n"
            "Можно указать диапазон, например: **50-100** м²\n"
            "Или одно значение: **80** м²\n"
            "Или нажмите кнопку, чтобы пропустить этот параметр"
            + area_hint + "\n\n"
            "💡 **Оставьте строку пустой, если параметр не важен**",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    elif state == BotState.COLLECTING_AREA:
        # Проверяем пустой ввод или "не важно"
        if not user_message or user_message.lower() in ["не важно", "неважно", "не важно", "пропустить", "skip"]:
            session["criteria"]["area_min"] = None
            session["criteria"]["area_max"] = None
            area_status = "не указана"
        else:
            # Парсим площадь
            try:
                if '-' in user_message:
                    # Диапазон
                    parts = user_message.replace('м²', '').replace('м2', '').replace(' ', '').split('-')
                    session["criteria"]["area_min"] = int(parts[0])
                    session["criteria"]["area_max"] = int(parts[1])
                else:
                    # Одно значение
                    area = int(user_message.replace('м²', '').replace('м2', '').replace(' ', ''))
                    session["criteria"]["area_min"] = area - 20  # Диапазон ±20
                    session["criteria"]["area_max"] = area + 20
                
                area_status = f"{session['criteria']['area_min']}-{session['criteria']['area_max']} м²"
            except ValueError:
                await update.message.reply_text(
                    "❌ Не удалось распознать площадь. Пожалуйста, укажите число, диапазон, оставьте пустым или напишите 'не важно'.\n"
                    "Например: **50-100**, **80**, оставьте пустым или **не важно**\n\n"
                    "💡 **Оставьте строку пустой, если параметр не важен**",
                    parse_mode='Markdown'
                )
                return
        
        # Сохраняем предыдущее состояние
        session["previous_state"] = BotState.COLLECTING_AREA
        session["state"] = BotState.COLLECTING_BUDGET
        
        # Получаем старое значение бюджета для подсказки
        old_criteria = session.get("old_criteria", {})
        price_suffix = "руб/мес" if session['criteria'].get('deal_type') == 'rent' else "руб"
        budget_hint = ""
        if old_criteria.get("budget_min") and old_criteria.get("budget_max"):
            budget_hint = f"\n💭 Предыдущее значение: {old_criteria['budget_min']:,}-{old_criteria['budget_max']:,} {price_suffix}"
        elif old_criteria.get("budget_max"):
            budget_hint = f"\n💭 Предыдущее значение: до {old_criteria['budget_max']:,} {price_suffix}"
        
        # Создаем кнопки для выбора "не важно"
        keyboard = [
            [InlineKeyboardButton("⏭ Пропустить (не важно)", callback_data="skip_budget")],
            [InlineKeyboardButton("🏠 На главную", callback_data="to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        deal_text = "аренду в месяц" if session['criteria'].get('deal_type') == 'rent' else "покупку"
        
        await update.message.reply_text(
            f"✅ Площадь: {area_status}\n\n"
            f"Теперь укажите бюджет на {deal_text}.\n"
            f"Можно указать диапазон, например: **100-200 тыс**\n"
            f"Или одно значение (максимум): **200000**\n"
            "Или нажмите кнопку, чтобы пропустить этот параметр"
            + budget_hint + "\n\n"
            "💡 **Оставьте строку пустой, если параметр не важен**",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    elif state == BotState.COLLECTING_BUDGET:
        # Проверяем пустой ввод или "не важно"
        if not user_message or user_message.lower() in ["не важно", "неважно", "не важно", "пропустить", "skip"]:
            session["criteria"]["budget_min"] = None
            session["criteria"]["budget_max"] = None
            budget_status = "не указан"
        else:
            # Парсим бюджет
            try:
                # Нормализация строки
                text = user_message.lower().replace('руб', '').replace('рублей', '').replace('руб/мес', '')
                text = text.replace('кк', '000000').replace('kk', '000000')
                text = text.replace('млн', '000000').replace('mln', '000000')
                text = text.replace('тыс', '000').replace('тысяч', '000')   
                text = text.replace('к', '000').replace('k', '000')
                text = text.replace(' ', '') # Убираем пробелы
                
                budget_min = None
                budget_max = None
                
                import re
                
                if '-' in text:
                    parts = text.split('-')
                    if len(parts) == 2 and parts[0] and parts[1]:
                        budget_min = int(parts[0])
                        budget_max = int(parts[1])
                elif 'от' in text and 'до' in text:
                     nums = re.findall(r'\d+', text)
                     if len(nums) >= 2:
                         budget_min = int(nums[0])
                         budget_max = int(nums[1])
                elif 'от' in text:
                    nums = re.findall(r'\d+', text)
                    if nums:
                        budget_min = int(nums[0])
                elif 'до' in text:
                    nums = re.findall(r'\d+', text)
                    if nums:
                        budget_max = int(nums[0])
                else:
                    # Одно число - считаем как максимум
                    val = int(text)
                    budget_max = val
                
                session["criteria"]["budget_min"] = budget_min
                session["criteria"]["budget_max"] = budget_max
                
                price_suffix = "руб/мес" if session['criteria'].get('deal_type') == 'rent' else "руб"
                if budget_min and budget_max:
                    budget_status = f"{budget_min:,}-{budget_max:,} {price_suffix}"
                elif budget_min:
                    budget_status = f"от {budget_min:,} {price_suffix}"
                elif budget_max:
                    budget_status = f"до {budget_max:,} {price_suffix}"
                else:
                    budget_status = "не указан"

            except ValueError:
                await update.message.reply_text(
                    "❌ Не удалось распознать бюджет. Пожалуйста, укажите число или диапазон.\n"
                    "Например: **100-200 тыс**, **до 200000**, **от 100к**\n\n"
                    "💡 **Оставьте строку пустой, если параметр не важен**",
                    parse_mode='Markdown'
                )
                return
        
        # Сбрасываем флаг уточнения после завершения сбора параметров
        if session.get("is_refining"):
            session["is_refining"] = False
            session["old_criteria"] = {}
        
        session["state"] = BotState.PROCESSING
        
        # Формируем сводку критериев
        summary = "**Сводка критериев:**\n"
        summary += f"📍 Город: {session['criteria']['city'] or 'не указан'}\n"
        
        if session['criteria']['area_min'] and session['criteria']['area_max']:
            summary += f"📐 Площадь: {session['criteria']['area_min']}-{session['criteria']['area_max']} м²\n"
        else:
            summary += f"📐 Площадь: не указана\n"
        
        if session['criteria'].get('budget_min') and session['criteria'].get('budget_max'):
            price_suffix = "руб/мес" if session['criteria'].get('deal_type') == 'rent' else "руб"
            summary += f"💰 Бюджет: {session['criteria']['budget_min']:,}-{session['criteria']['budget_max']:,} {price_suffix}\n"
        elif session['criteria'].get('budget_min'):
            price_suffix = "руб/мес" if session['criteria'].get('deal_type') == 'rent' else "руб"
            summary += f"💰 Бюджет: от {session['criteria']['budget_min']:,} {price_suffix}\n"
        elif session['criteria'].get('budget_max'):
            price_suffix = "руб/мес" if session['criteria'].get('deal_type') == 'rent' else "руб"
            summary += f"💰 Бюджет: до {session['criteria']['budget_max']:,} {price_suffix}\n"
        else:
            summary += f"💰 Бюджет: не указан\n"
        
        await update.message.reply_text(
            f"✅ {budget_status}\n\n{summary}\n"
            "🔍 Ищу подходящие помещения и анализирую их с помощью ИИ...",
            parse_mode='Markdown'
        )
        
        # Запускаем обработку
        await process_search(update, context)
    
    elif state == BotState.PROCESSING:
        # Игнорируем сообщения во время обработки
        await update.message.reply_text("⏳ Пожалуйста, подождите, идет обработка предыдущего запроса...")
    
    elif state == BotState.WAITING_REQUEST:
        # Если пользователь в состоянии ожидания, предлагаем начать новый поиск
        await update.message.reply_text(
            "Используйте /start для начала нового поиска помещений или /help для справки."
        )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    user_id = update.effective_user.id
    raw_message = update.message.text or ""
    user_message = raw_message.strip()

    # --- Spam Protection ---
    session = get_user_session(user_id)
    current_time = time.time()
    last_time = session.get("last_message_time", 0)
    
    # Если прошло меньше 2 секунд с последнего сообщения
    if current_time - last_time < 2.0:
        session["message_count"] = session.get("message_count", 0) + 1
    else:
        # Сбрасываем счетчик, если прошло достаточно времени
        session["message_count"] = 1
        session["is_spamming"] = False
        
    session["last_message_time"] = current_time
    
    if session.get("message_count", 0) > 2:
        if not session.get("is_spamming"):
            session["is_spamming"] = True
            await update.message.reply_text("⚠️ Пожалуйста, не спамьте. Отправляйте сообщения медленнее.")
        return
    # -----------------------

    await process_user_text(user_id, user_message, update, context)


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик голосовых сообщений"""
    user_id = update.effective_user.id
    
    # --- Spam Protection ---
    session = get_user_session(user_id)
    current_time = time.time()
    last_time = session.get("last_message_time", 0)
    
    # Если прошло меньше 2 секунд с последнего сообщения
    if current_time - last_time < 2.0:
        session["message_count"] = session.get("message_count", 0) + 1
    else:
        # Сбрасываем счетчик, если прошло достаточно времени
        session["message_count"] = 1
        session["is_spamming"] = False
        
    session["last_message_time"] = current_time
    
    if session.get("message_count", 0) > 2:
        if not session.get("is_spamming"):
            session["is_spamming"] = True
            await update.message.reply_text("⚠️ Пожалуйста, не спамьте. Отправляйте сообщения медленнее.")
        return
    # -----------------------
    
    if not speech_service.is_available():
        await update.message.reply_text("❌ Распознавание речи не настроено.")
        return
        
    await update.message.reply_text("🎤 Слушаю...")
    
    try:
        # Получаем файл
        voice_file = await context.bot.get_file(update.message.voice.file_id)
        
        # Скачиваем файл в память
        voice_byte_array = await voice_file.download_as_bytearray()
        
        # Распознаем
        text = await speech_service.recognize(voice_byte_array)
        
        if text:
            await update.message.reply_text(f"🗣 Распознано: \"{text}\"")
            # Обрабатываем как текст
            await process_user_text(user_id, text, update, context)
        else:
            await update.message.reply_text("❌ Не удалось распознать речь.")
            
    except Exception as e:
        logger.error(f"Ошибка обработки голосового сообщения: {e}")
        await update.message.reply_text("❌ Произошла ошибка при обработке голосового сообщения.")


async def show_listings_page(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = None):
    """Показывает страницу с объявлениями"""
    user_id = update.effective_user.id
    session = get_user_session(user_id)
    
    all_listings = session.get("all_listings", [])
    if not all_listings:
        return
    
    # Применяем сортировку
    sort_by = session.get("sort_by")
    sort_order = session.get("sort_order", "asc")
    
    # Если есть исходный список, используем его как базу, но фильтруем исключенные
    if session.get("original_listings"):
        excluded_ids = session.get("excluded_listing_ids", [])
        # Берем исходные, но убираем те, что в исключенных
        all_listings = [l for l in session["original_listings"] if l.get('id') not in excluded_ids]
        session["all_listings"] = all_listings
    
    if sort_by:
        reverse = (sort_order == 'desc')
        if sort_by == 'price':
            all_listings.sort(key=lambda x: x.get('price', 0), reverse=reverse)
        elif sort_by == 'area':
            all_listings.sort(key=lambda x: x.get('area', 0), reverse=reverse)
        elif sort_by == 'price_per_sqm':
            all_listings.sort(key=lambda x: (x.get('price', 0) / x.get('area', 1)) if x.get('area', 0) > 0 else 0, reverse=reverse)

    listings_per_page = session.get("listings_per_page", 3)
    
    if page is None:
        page = session.get("current_page", 0)
    
    total_pages = (len(all_listings) + listings_per_page - 1) // listings_per_page
    
    if page < 0:
        page = 0
    if page >= total_pages:
        page = total_pages - 1
    
    session["current_page"] = page
    
    # Получаем объявления для текущей страницы
    start_idx = page * listings_per_page
    end_idx = start_idx + listings_per_page
    current_listings = all_listings[start_idx:end_idx]
    
    # Сохраняем текущие объявления для показа деталей
    session["current_listings"] = current_listings
    
    # Формируем текст со списком объявлений
    total_count = len(all_listings)
    listings_text = f"🏆 **Найдено {total_count} помещений:**\n"
    listings_text += f"📄 Страница {page + 1} из {total_pages}\n\n"
    
    # Проверяем, соответствуют ли объявления критериям
    criteria = session.get("criteria", {})
    budget_min = criteria.get("budget_min")
    budget_max = criteria.get("budget_max")
    area_min = criteria.get("area_min")
    area_max = criteria.get("area_max")
    budget_exceeded = session.get("budget_exceeded", False)
    area_exceeded = session.get("area_exceeded", False)
    floor_mismatch = session.get("floor_mismatch", False)
    criteria_exceeded = session.get("criteria_exceeded", False)
    
    if criteria_exceeded:
        warnings = []
        if budget_exceeded:
            price_suffix = "руб/мес" if criteria.get('deal_type') == 'rent' else "руб"
            if budget_min and budget_max:
                warnings.append(f"бюджету ({budget_min:,}-{budget_max:,} {price_suffix})")
            elif budget_min:
                warnings.append(f"бюджету (от {budget_min:,} {price_suffix})")
            elif budget_max:
                warnings.append(f"бюджету (до {budget_max:,} {price_suffix})")
        if area_exceeded:
            if area_min and area_max:
                warnings.append(f"площади ({area_min}-{area_max} м²)")
            elif area_min:
                warnings.append(f"площади (от {area_min} м²)")
            elif area_max:
                warnings.append(f"площади (до {area_max} м²)")
        if floor_mismatch and criteria.get("floor"):
            warnings.append(f"этажу ({criteria['floor']})")
        
        if warnings:
            warnings_text = " и ".join(warnings)
            listings_text += f"⚠️ **Внимание:** В указанном диапазоне ({warnings_text}) не найдено подходящих помещений.\n"
            listings_text += f"Показаны объявления, максимально близкие к вашим критериям:\n\n"
    
    for i, listing in enumerate(current_listings, 1):
        global_index = start_idx + i
        price_suffix = "руб/мес" if listing.get('deal_type') == 'rent' else "руб"
        price_per_sqm = round(listing['price'] / listing['area']) if listing['area'] > 0 else 0
        price_text = f"💰Цена: {listing['price']:,} {price_suffix} ({price_per_sqm:,} руб/м²)"
        if budget_exceeded:
            if budget_max and listing['price'] > budget_max:
                price_text += f" ⚠️ (превышает бюджет на {listing['price'] - budget_max:,} {price_suffix})"
            elif budget_min and listing['price'] < budget_min:
                price_text += f" ⚠️ (ниже бюджета на {budget_min - listing['price']:,} {price_suffix})"
        
        # Проверяем соответствие площади
        area_text = f"📐Площадь помещения: {listing['area']} м²"
        if area_exceeded:
            if area_min and listing['area'] < area_min:
                area_text += f" ⚠️ (меньше минимума на {area_min - listing['area']} м²)"
            elif area_max and listing['area'] > area_max:
                area_text += f" ⚠️ (больше максимума на {listing['area'] - area_max} м²)"
        
        # Проверяем соответствие этажа
        floor_text = f"📍 {listing['floor']} этаж"
        if floor_mismatch and criteria.get("floor"):
            try:
                if int(listing.get("floor", 0)) != criteria["floor"]:
                    floor_text += f" ⚠️ (искали {criteria['floor']})"
            except:
                pass

        # Проверяем, в избранном ли объявление
        is_liked = listing.get('id') in session.get("likes", [])
        like_mark = "❤️" if is_liked else ""

        listings_text += f"**{global_index}. {like_mark} {listing['address']}**\n"
        listings_text += f"{area_text} \n{price_text} \n{floor_text}\n"
        # Показываем объяснение ИИ только если оно есть
        ai_reason = listing.get('ai_reason', '').strip()
        if ai_reason:
            listings_text += f"💡 {ai_reason[:80]}...\n"
        
        # Всегда показываем ссылку, если она есть
        link = listing.get('link', '')
        if link:
            listings_text += f"🔗 {link}\n"
        else:
            listings_text += f"🔗 Ссылка недоступна\n"  

        listings_text += "\n"
    
    # Создаем кнопки с номерами объявлений для выбора
    id_buttons = []
    for i, listing in enumerate(current_listings, 1):
        global_index = start_idx + i
        listing_id = listing.get('id', 0)
        id_buttons.append(InlineKeyboardButton(str(global_index), callback_data=f"show_listing_id_{listing_id}"))
    
    # Создаем кнопки навигации
    nav_buttons = []
    
    # Кнопка "В начало" (показывается если не на первой странице)
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⏮ В начало", callback_data="page_0"))
    
    # Кнопки пагинации
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("← Предыдущая", callback_data=f"page_{page - 1}"))
    
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("Следующая →", callback_data=f"page_{page + 1}"))
    
    # Формируем клавиатуру
    keyboard = [id_buttons]
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    # Добавляем кнопку сортировки
    sort_icon = "🔽"
    if sort_by == 'price':
        sort_icon = "💰" + ("⬆️" if sort_order == 'asc' else "⬇️")
    elif sort_by == 'area':
        sort_icon = "📐" + ("⬆️" if sort_order == 'asc' else "⬇️")
        
    keyboard.append([InlineKeyboardButton(f"{sort_icon} Сортировка", callback_data="sort_menu")])
    
    # Добавляем кнопку подписки
    criteria = session.get("criteria", {})
    sub_id = db.check_subscription(user_id, criteria)
    
    if sub_id:
        keyboard.append([InlineKeyboardButton("🔕 Отписаться от обновлений", callback_data=f"unsub_curr_{sub_id}")])
    else:
        keyboard.append([InlineKeyboardButton("🔔 Подписаться на обновления", callback_data="subscribe")])

    # Добавляем кнопку "На главную"
    keyboard.extend(get_to_main_button())
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправляем или редактируем сообщение
    if hasattr(update, 'message') and update.message:
        await update.message.reply_text(
            listings_text + "Нажмите на ID объявления, чтобы увидеть полное описание.",
            parse_mode='Markdown',
            reply_markup=reply_markup,
            disable_web_page_preview=True
        )
    elif hasattr(update, 'callback_query') and update.callback_query:
        query = update.callback_query
        await query.edit_message_text(
            listings_text + "Нажмите на ID объявления, чтобы увидеть полное описание.",
            parse_mode='Markdown',
            reply_markup=reply_markup,
            disable_web_page_preview=True
        )
        await query.answer()
    else:
        # Если update не имеет ни message, ни callback_query, пробуем через context
        # Это для случаев, когда вызываем из другого места
        if hasattr(update, 'effective_user'):
            # Создаем временное сообщение через бота
            chat_id = update.effective_user.id
            await context.bot.send_message(
                chat_id=chat_id,
                text=listings_text + "Нажмите на номер объявления, чтобы увидеть полное описание.",
                parse_mode='Markdown',
                reply_markup=reply_markup,
                disable_web_page_preview=True
            )
    
    session["state"] = BotState.WAITING_REQUEST


async def show_favorites(update: Update, context: ContextTypes.DEFAULT_TYPE, index: int = None):
    """Показывает одно избранное объявление с навигацией"""
    user_id = update.effective_user.id
    session = get_user_session(user_id)
    
    # Получаем список избранного из БД
    favorite_listings_from_db = db.get_favorites(user_id)
    
    if not favorite_listings_from_db:
        # Если список пуст, показываем сообщение
        keyboard = get_to_main_button()
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if hasattr(update, 'message') and update.message:
            await update.message.reply_text(
                "❤️ **Понравившиеся**\n\n"
                "Вы пока не добавили ни одного объявления в избранное.\n\n"
                "Чтобы добавить объявление в избранное, нажмите кнопку 👍 Лайк под его описанием.",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        elif hasattr(update, 'callback_query') and update.callback_query:
            query = update.callback_query
            await query.edit_message_text(
                "❤️ **Понравившиеся**\n\n"
                "Вы пока не добавили ни одного объявления в избранное.\n\n"
                "Чтобы добавить объявление в избранное, нажмите кнопку 👍 Лайк под его описанием.",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            await query.answer()
        return
    
    # Определяем текущий индекс
    if index is None:
        index = session.get("favorite_index", 0)
    else:
        session["favorite_index"] = index
    
    # Проверяем границы
    if index < 0:
        index = 0
    if index >= len(favorite_listings_from_db):
        index = len(favorite_listings_from_db) - 1
    
    session["favorite_index"] = index
    
    # Получаем текущее объявление из БД
    listing = favorite_listings_from_db[index]
    listing_id = str(listing.get('id'))
    
    # Проверяем актуальность объявления через парсер
    from parser import get_listing_by_id
    actual_listing = get_listing_by_id(
        int(listing_id),
        city=listing.get('city'),
        deal_type=listing.get('deal_type')
    )
    
    # Если объявление больше не существует, удаляем его из избранного
    if actual_listing is None:
        db.remove_favorite(user_id, listing_id)
        
        # Также удаляем из сессии, если есть
        likes = session.get("likes", [])
        if listing_id in likes:
            likes.remove(listing_id)
            session["likes"] = likes
        
        # Обновляем список избранного после удаления
        favorite_listings_from_db = db.get_favorites(user_id)
        
        # Если после удаления список пуст
        if not favorite_listings_from_db:
            keyboard = get_to_main_button()
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            text = (
                "❤️ **Понравившиеся**\n\n"
                "Объявление больше не доступно и было удалено из избранного.\n\n"
                "Список избранного теперь пуст."
            )
            
            if hasattr(update, 'callback_query') and update.callback_query:
                query = update.callback_query
                await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)
                await query.answer("Объявление удалено")
            else:
                await update.message.reply_text(text, parse_mode='Markdown', reply_markup=reply_markup)
            return
        
        # Если есть ещё объявления, корректируем индекс и показываем следующее
        if index >= len(favorite_listings_from_db):
            index = len(favorite_listings_from_db) - 1
        session["favorite_index"] = index
        
        # Рекурсивно вызываем show_favorites для показа следующего объявления
        await show_favorites(update, context, index)
        return
    
    # Используем актуальные данные из парсера
    listing = actual_listing
    
    # Обновляем данные в БД на случай, если что-то изменилось
    db.add_favorite(user_id, listing)
    
    # Формируем полное описание
    full_text = f"❤️ **Понравившиеся** ({index + 1} из {len(favorite_listings_from_db)})\n\n"
    full_text += f"**{listing['address']}**\n\n"
    full_text += f"📐 **Площадь:** {listing['area']} м²\n"
    price_suffix = "руб/мес" if listing.get('deal_type') == 'rent' else "руб"
    price_per_sqm = round(listing['price'] / listing['area']) if listing['area'] > 0 else 0
    full_text += f"💰 **Цена:** {listing['price']:,} {price_suffix} ({price_per_sqm:,} руб/м²)\n"
    full_text += f"📍 **Этаж:** {listing['floor']}\n"
    full_text += f"🚶 **Трафик:** {listing.get('traffic', 'не указан')}\n"
    full_text += f"🚇 **Доступность:** {listing.get('accessibility', 'не указана')}\n\n"
    full_text += f"📝 **Описание:**\n{listing.get('description', 'Нет описания')}\n\n"
    
    # Контакты
    full_text += f"📞 **Телефон:** {listing.get('phone', 'Не указан')}\n\n"

    # Показываем объяснение ИИ только если оно есть
    ai_reason = listing.get('ai_reason', '').strip()
    if ai_reason:
        full_text += f"💡 **Почему подходит:**\n{ai_reason}\n\n"
    
    # Всегда показываем ссылку
    link = listing.get('link', '')
    if link:
        full_text += f"🔗 **Ссылка:** {link}"
    else:
        full_text += f"🔗 **Ссылка:** недоступна"
    
    # Создаем кнопки навигации
    keyboard = []
    
    # Кнопки навигации (Назад/Вперёд)
    nav_buttons = []
    if index > 0:
        nav_buttons.append(InlineKeyboardButton("← Назад", callback_data="favorite_prev"))
    if index < len(favorite_listings_from_db) - 1:
        nav_buttons.append(InlineKeyboardButton("Вперёд →", callback_data="favorite_next"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    # Кнопка удаления из избранного
    keyboard.append([InlineKeyboardButton("❌ Убрать из понравившихся", callback_data=f"remove_favorite_{listing['id']}")])
    
    # Кнопка "На главную"
    keyboard.extend(get_to_main_button())
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправляем или редактируем сообщение
    if hasattr(update, 'message') and update.message:
        await update.message.reply_text(
            full_text,
            parse_mode='Markdown',
            reply_markup=reply_markup,
            disable_web_page_preview=True
        )
    elif hasattr(update, 'callback_query') and update.callback_query:
        query = update.callback_query
        await query.edit_message_text(
            full_text,
            parse_mode='Markdown',
            reply_markup=reply_markup,
            disable_web_page_preview=True
        )
        await query.answer()


async def show_dislikes(update: Update, context: ContextTypes.DEFAULT_TYPE, index: int = None):
    """Показывает одно скрытое (дизлайкнутое) объявление с навигацией"""
    user_id = update.effective_user.id
    session = get_user_session(user_id)
    
    dislikes = session.get("dislikes", {})
    
    if not dislikes:
        # Если список пуст, показываем сообщение
        keyboard = get_to_main_button()
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = "💔 **Скрытые объявления**\n\nСписок скрытых объявлений пуст."
        
        if hasattr(update, 'message') and update.message:
            await update.message.reply_text(text, parse_mode='Markdown', reply_markup=reply_markup)
        elif hasattr(update, 'callback_query') and update.callback_query:
            query = update.callback_query
            await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)
            await query.answer()
        return
    
    # Формируем список объявлений из dislikes
    disliked_listings = []
    for listing_id, data in dislikes.items():
        if isinstance(data, dict) and data.get("listing"):
            disliked_listings.append(data["listing"])
        else:
            # Fallback для старых записей или если объект не сохранился
            disliked_listings.append({
                'id': listing_id,
                'address': f"Объявление #{listing_id}",
                'area': 0,
                'price': 0,
                'floor': 1,
                'description': "Информация об этом объявлении недоступна",
                'traffic': "не указан",
                'accessibility': "не указана",
                'ai_reason': "Это объявление было скрыто ранее."
            })
    
    # Определяем текущий индекс
    if index is None:
        index = session.get("dislike_index", 0)
    else:
        session["dislike_index"] = index
    
    # Проверяем границы
    if index < 0:
        index = 0
    if index >= len(disliked_listings):
        index = len(disliked_listings) - 1
    
    session["dislike_index"] = index
    
    # Получаем текущее объявление
    listing = disliked_listings[index]
    
    # Формируем полное описание
    full_text = f"💔 **Скрытые** ({index + 1} из {len(disliked_listings)})\n\n"
    full_text += f"**{listing['address']}**\n\n"
    full_text += f"📐 **Площадь:** {listing['area']} м²\n"
    price_suffix = "руб/мес" if listing.get('deal_type') == 'rent' else "руб"
    price_per_sqm = round(listing['price'] / listing['area']) if listing['area'] > 0 else 0
    full_text += f"💰 **Цена:** {listing['price']:,} {price_suffix} ({price_per_sqm:,} руб/м²)\n"
    full_text += f"📍 **Этаж:** {listing['floor']}\n"
    full_text += f"🚶 **Трафик:** {listing.get('traffic', 'не указан')}\n"
    full_text += f"🚇 **Доступность:** {listing.get('accessibility', 'не указана')}\n\n"
    full_text += f"📝 **Описание:**\n{listing.get('description', 'Нет описания')}\n\n"
    
    # Контакты
    full_text += f"📞 **Телефон:** {listing.get('phone', 'Не указан')}\n\n"

    # Всегда показываем ссылку
    link = listing.get('link', '')
    if link:
        full_text += f"🔗 **Ссылка:** {link}"
    else:
        full_text += f"🔗 **Ссылка:** недоступна"
    
    # Создаем кнопки навигации
    keyboard = []
    
    # Кнопки навигации (Назад/Вперёд)
    nav_buttons = []
    if index > 0:
        nav_buttons.append(InlineKeyboardButton("← Назад", callback_data="dislike_prev"))
    if index < len(disliked_listings) - 1:
        nav_buttons.append(InlineKeyboardButton("Вперёд →", callback_data="dislike_next"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    # Кнопка восстановления
    keyboard.append([InlineKeyboardButton("♻️ Вернуть в поиск", callback_data=f"restore_dislike_{listing['id']}")])
    
    # Кнопка "На главную"
    keyboard.extend(get_to_main_button())
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправляем или редактируем сообщение
    if hasattr(update, 'message') and update.message:
        await update.message.reply_text(
            full_text,
            parse_mode='Markdown',
            reply_markup=reply_markup,
            disable_web_page_preview=True
        )
    elif hasattr(update, 'callback_query') and update.callback_query:
        query = update.callback_query
        await query.edit_message_text(
            full_text,
            parse_mode='Markdown',
            reply_markup=reply_markup,
            disable_web_page_preview=True
        )
        await query.answer()


async def show_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает историю поиска"""
    user_id = update.effective_user.id
    history = db.get_search_history(user_id, limit=5)
    
    if not history:
        text = "📜 **История поиска**\n\nИстория пуста."
        keyboard = get_to_main_button()
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if hasattr(update, 'message') and update.message:
            await update.message.reply_text(text, parse_mode='Markdown', reply_markup=reply_markup)
        elif hasattr(update, 'callback_query') and update.callback_query:
            query = update.callback_query
            await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)
            await query.answer()
        return

    text = "📜 **История поиска**\nВыберите запрос, чтобы повторить поиск:\n\n"
    keyboard = []
    
    for item in history:
        criteria = item['criteria']
        date_str = item['created_at']
        try:
            # Попробуем распарсить дату, если она в стандартном формате
            dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
            date_fmt = dt.strftime("%d.%m %H:%M")
        except:
            date_fmt = date_str

        # Формируем описание
        desc = f"{criteria.get('city') or '?'}"
        if criteria.get('area_min') or criteria.get('area_max'):
            desc += f", {criteria.get('area_min') or 0}-{criteria.get('area_max') or '∞'}м²"
        if criteria.get('budget_min') or criteria.get('budget_max'):
            budget = ""
            if criteria.get('budget_min') and criteria.get('budget_max'):
                budget = f"{criteria['budget_min']}-{criteria['budget_max']}"
            elif criteria.get('budget_min'):
                budget = f"от {criteria['budget_min']}"
            elif criteria.get('budget_max'):
                budget = f"до {criteria['budget_max']}"
            desc += f", {budget}р"
            
        btn_text = f"{date_fmt}: {desc}"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"history_select_{item['id']}")])
    
    keyboard.extend(get_to_main_button())
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if hasattr(update, 'message') and update.message:
        await update.message.reply_text(text, parse_mode='Markdown', reply_markup=reply_markup)
    elif hasattr(update, 'callback_query') and update.callback_query:
        query = update.callback_query
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)
        await query.answer()


async def process_search_from_query(query, context: ContextTypes.DEFAULT_TYPE):
    """Вспомогательная функция для запуска поиска из callback query"""
    # Создаем объект, похожий на Update, для вызова process_search
    class QueryUpdate:
        def __init__(self, callback_query):
            self.effective_user = callback_query.from_user
            self.message = callback_query.message
    
    temp_update = QueryUpdate(query)
    await process_search(temp_update, context)


async def process_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает поиск и анализ помещений"""
    user_id = update.effective_user.id
    session = get_user_session(user_id)
    criteria = session["criteria"]
    
    # Сохраняем историю поиска
    db.add_search_history(user_id, criteria)
    
    try:
        # Получаем объявления от парсера
        excluded_ids = session.get("excluded_listing_ids", [])
        listings = parse_listings(
            city=criteria["city"],
            district=criteria.get("district"),
            min_area=criteria["area_min"],
            max_area=criteria["area_max"],
            min_price=criteria.get("budget_min"),
            max_price=criteria.get("budget_max"),
            floor=criteria.get("floor"),
            excluded_ids=excluded_ids,
            deal_type=criteria.get("deal_type")
        )
        
        if not listings:
            session["state"] = BotState.WAITING_REQUEST
            
            # Анализируем причины отсутствия результатов
            analysis_text = ""
            try:
                # Загружаем все объявления в городе без фильтров (кроме типа сделки)
                all_city_listings = parse_listings(
                    city=criteria["city"],
                    deal_type=criteria.get("deal_type"),
                    excluded_ids=excluded_ids
                )
                
                if all_city_listings:
                    reasons = []
                    
                    # Если выбран район, сужаем круг поиска до района
                    candidates = all_city_listings
                    if criteria.get("district"):
                        # Используем parse_listings для фильтрации по району, так как там сложная логика
                        candidates = parse_listings(
                            city=criteria["city"],
                            district=criteria["district"],
                            deal_type=criteria.get("deal_type"),
                            excluded_ids=excluded_ids
                        )
                        if not candidates:
                            reasons.append(f"• Район: в районе '{criteria['district']}' нет предложений.")
                            reasons.append(f"• В других районах города найдено {len(all_city_listings)} объявлений.")
                    
                    if candidates:
                        # Проверяем бюджет на кандидатах (в районе или в городе)
                        if criteria.get("budget_max"):
                            cheapest = min(l["price"] for l in candidates)
                            in_budget = [l for l in candidates if l["price"] <= criteria["budget_max"]]
                            if not in_budget:
                                reasons.append(f"• Бюджет: в выбранной локации все варианты дороже {criteria['budget_max']}. Минимальная цена: {cheapest}")
                        
                        if criteria.get("budget_min"):
                            most_expensive = max(l["price"] for l in candidates)
                            in_budget = [l for l in candidates if l["price"] >= criteria["budget_min"]]
                            if not in_budget:
                                reasons.append(f"• Бюджет: в выбранной локации все варианты дешевле {criteria['budget_min']}. Максимальная цена: {most_expensive}")
                        
                        # Проверяем площадь
                        if criteria.get("area_min"):
                            largest = max(l["area"] for l in candidates)
                            in_area = [l for l in candidates if l["area"] >= criteria["area_min"]]
                            if not in_area:
                                reasons.append(f"• Площадь: в выбранной локации нет помещений больше {criteria['area_min']} м². Максимум: {largest} м²")
                                
                        if criteria.get("area_max"):
                            smallest = min(l["area"] for l in candidates)
                            in_area = [l for l in candidates if l["area"] <= criteria["area_max"]]
                            if not in_area:
                                reasons.append(f"• Площадь: в выбранной локации нет помещений меньше {criteria['area_max']} м². Минимум: {smallest} м²")
                        
                        # Проверяем этаж
                        if criteria.get("floor") is not None:
                             in_floor = [l for l in candidates if l.get("floor") == criteria["floor"]]
                             if not in_floor:
                                 reasons.append(f"• Этаж: в выбранной локации нет помещений на {criteria['floor']} этаже.")

                    if reasons:
                        analysis_text = "Причины отсутствия результатов:\n" + "\n".join(reasons)
                    else:
                        # Если причины не очевидны (например, комбинация факторов)
                        analysis_text = f"В выбранной локации найдено {len(candidates)} объявлений, но ни одно не подходит под все критерии одновременно."
                else:
                    analysis_text = f"В городе {criteria['city']} вообще не найдено объявлений."
            except Exception as e:
                logger.error(f"Error analyzing empty search: {e}")

            # Генерируем альтернативы
            alternatives = await ai_service.generate_search_alternatives(criteria, analysis_text)
            
            msg_text = f"❌ К сожалению, не найдено подходящих помещений по вашим критериям.\n\n"
            if analysis_text:
                msg_text += f"📊 **Анализ:**\n{analysis_text}\n\n"
            
            msg_text += f"💡 **Предложения ИИ:**\n{alternatives}\n\n"
            msg_text += "Используйте кнопку 'Уточнить критерии' или /start для нового поиска."

            await update.message.reply_text(
                msg_text,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔍 Уточнить критерии", callback_data="refine")],
                    [InlineKeyboardButton("🏠 На главную", callback_data="to_main")]
                ])
            )   
            return
        
        # Проверяем, соответствуют ли объявления всем критериям
        budget_exceeded = False
        area_exceeded = False
        
        # Проверяем соответствие по бюджету
        session["budget_exceeded"] = False
        if criteria.get("budget_max"):
            all_in_budget = all(l["price"] <= criteria["budget_max"] for l in listings)
            if not all_in_budget:
                budget_exceeded = True
                session["budget_exceeded"] = True
        
        if criteria.get("budget_min"):
            all_in_budget = all(l["price"] >= criteria["budget_min"] for l in listings)
            if not all_in_budget:
                budget_exceeded = True
                session["budget_exceeded"] = True
        
        # Проверяем соответствие по площади
        if criteria.get("area_min") or criteria.get("area_max"):
            all_match_area = all(
                (not criteria.get("area_min") or l["area"] >= criteria["area_min"]) and
                (not criteria.get("area_max") or l["area"] <= criteria["area_max"])
                for l in listings
            )
            if not all_match_area:
                area_exceeded = True
                session["area_exceeded"] = True
            else:
                session["area_exceeded"] = False
        else:
            session["area_exceeded"] = False
            
        # Проверяем соответствие по этажу
        floor_mismatch = False
        if criteria.get("floor") is not None:
            all_match_floor = True
            for l in listings:
                try:
                    if int(l.get("floor", 0)) != criteria["floor"]:
                        all_match_floor = False
                        break
                except:
                    pass
            
            if not all_match_floor:
                floor_mismatch = True
                session["floor_mismatch"] = True
            else:
                session["floor_mismatch"] = False
        else:
            session["floor_mismatch"] = False
        
        # Сохраняем общий флаг несоответствия критериям
        session["criteria_exceeded"] = budget_exceeded or area_exceeded or floor_mismatch
        
        # Если ИИ доступен, анализируем объявления (ранжируем все)
        # Передаем причину дизлайка, если есть
        dislike_reason = session.get("last_dislike_reason")
        if ai_service.is_available() and len(listings) > 0:
            all_listings = await ai_service.analyze_listings(criteria, listings, dislike_reason=dislike_reason, budget_exceeded=budget_exceeded, area_exceeded=area_exceeded)
            # Очищаем причину дизлайка после использования
            if dislike_reason:
                session["last_dislike_reason"] = None
        else:
            # Без ИИ просто берем все объявления
            all_listings = listings
            for listing in all_listings:
                listing['ai_reason'] = ""  # ИИ анализ недоступен
        
        # Формируем ответ с рекомендациями
        if not all_listings:
            session["state"] = BotState.WAITING_REQUEST
            await update.message.reply_text(
                "❌ Не удалось проанализировать объявления.\n"
                "Попробуйте еще раз с /start"
            )
            return
        
        # Сохраняем все объявления и сбрасываем страницу
        session["all_listings"] = all_listings
        session["original_listings"] = list(all_listings)
        session["current_page"] = 0
        
        # Показываем главную страницу с кнопкой "Показать результаты"
        await show_main_page(update, context)
        
    except Exception as e:
        logger.error(f"Ошибка при обработке поиска: {e}")
        session["state"] = BotState.WAITING_REQUEST
        await update.message.reply_text(
            f"❌ Произошла ошибка при обработке запроса: {str(e)}\n\n"
            "Попробуйте еще раз с /start"
        )


async def send_like_to_backend(user_id: int, listing_id: int):
    """Отправляет лайк на бэкенд"""
    # TODO: Реализовать отправку на реальный бэкенд
    logger.info(f"User {user_id} liked listing {listing_id}")
    # Пример: requests.post('https://api.example.com/likes', json={
    #     'user_id': user_id,
    #     'listing_id': listing_id,
    #     'liked': True
    # })


async def send_dislike_to_backend(user_id: int, listing_id: int, reason: str):
    """Отправляет дизлайк с причиной на бэкенд"""
    # TODO: Реализовать отправку на реальный бэкенд
    logger.info(f"User {user_id} disliked listing {listing_id}. Reason: {reason}")
    # Пример: requests.post('https://api.example.com/dislikes', json={
    #     'user_id': user_id,
    #     'listing_id': listing_id,
    #     'reason': reason
    # })


async def apply_dislike(user_id: int, listing_id: int, query, context: ContextTypes.DEFAULT_TYPE, session: dict):
    """Применяет дизлайк: удаляет из избранного, возвращает к списку (редактируя сообщение)"""
    # Находим объект объявления перед удалением
    all_listings = session.get("all_listings", [])
    listing = next((l for l in all_listings if l.get('id') == listing_id), None)
    
    # Если не нашли в текущих, ищем в исходных (на случай если уже удалено)
    if not listing:
        original = session.get("original_listings", [])
        listing = next((l for l in original if l.get('id') == listing_id), None)
    
    # Сохраняем дизлайк вместе с объектом объявления
    if listing:
        session["dislikes"][listing_id] = {"reason": "disliked", "listing": listing}
        # Сохраняем в БД
        db.add_dislike(user_id, listing, "disliked")
    else:
        # Fallback если объявление не найдено (маловероятно)
        session["dislikes"][listing_id] = "disliked"
    
    # Если объявление было в избранном - удаляем его
    if listing_id in session.get("likes", []):
        session["likes"].remove(listing_id)
        # Удаляем из БД
        db.remove_favorite(user_id, listing_id)
        logger.info(f"Объявление {listing_id} удалено из списка")
    
    # Отправляем на бэкенд (пустая причина)
    await send_dislike_to_backend(user_id, listing_id, "")
    
    # Исключаем текущее объявление из будущих результатов
    excluded_ids = session.get("excluded_listing_ids", [])
    if listing_id not in excluded_ids:
        excluded_ids.append(listing_id)
    session["excluded_listing_ids"] = excluded_ids
    
    # Удаляем объявление из текущего списка (all_listings), если оно там есть
    all_listings = session.get("all_listings", [])
    session["all_listings"] = [l for l in all_listings if l.get('id') != listing_id]
    logger.info(f"Объявление {listing_id} удалено из текущего списка")
    
    # Сбрасываем состояние
    session["state"] = BotState.WAITING_REQUEST
    session["dislike_message_id"] = None
    
    # Возвращаемся к списку объявлений (редактируя текущее сообщение)
    class TempUpdate:
        def __init__(self, callback_query):
            self.effective_user = callback_query.from_user
            self.callback_query = callback_query
            self.message = None
    
    temp_update = TempUpdate(query)
    await show_listings_page(temp_update, context, session.get("current_page", 0))
    
    await query.answer("Объявление скрыто")


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик callback-запросов от кнопок"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    session = get_user_session(user_id)
    
    if query.data.startswith("deal_type_"):
        # Обработка выбора типа сделки
        deal_type = query.data.split("_")[2]  # "rent" или "sale"
        session["criteria"]["deal_type"] = deal_type        
        
        # Переходим к выбору города
        session["state"] = BotState.COLLECTING_CITY
        
        deal_text = "аренду" if deal_type == "rent" else "покупку"
        
        keyboard = [
            [InlineKeyboardButton("Екатеринбург", callback_data="city_Екатеринбург")],
            [InlineKeyboardButton("Челябинск", callback_data="city_Челябинск")],
            [InlineKeyboardButton("🏠 На главную", callback_data="to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"🏙 **Выберите город**\n\n"
            f"Ищем помещение на {deal_text}.\n"
            f"В каком городе будем искать?",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        await query.answer()
    
    elif query.data == "help":
        # Открываем страницу помощи
        keyboard = get_to_main_button()
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(HELP_TEXT, reply_markup=reply_markup)
        await query.answer()
    
    elif query.data == "refine":
        # Начинаем заново сбор критериев (но сохраняем предпочтения и предыдущие значения как defaults)
        # Сохраняем текущие критерии как значения по умолчанию
        old_criteria = session["criteria"].copy()
        
        session["state"] = BotState.WAITING_PROMPT
        # Сохраняем старые критерии для отображения как подсказок и для сохранения при пропуске
        session["old_criteria"] = old_criteria
        session["is_refining"] = True  # Флаг, что мы в режиме уточнения
        session["current_listings"] = []
        
        keyboard = [
            [InlineKeyboardButton("🏠 На главную", callback_data="to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🔍 **Уточнить критерии**\n\n"
            "Напишите, что вы хотите изменить. Например:\n"
            "\"Ищем в центре\"\n"
            "\"Бюджет до 300000\"\n"
            "\"Площадь от 100 кв.м\"\n\n"
            "Я обновлю только указанные параметры.",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        await query.answer()
    
    elif query.data == "skip_city":
        # Если мы в режиме уточнения, сохраняем старое значение, иначе ставим None
        if session.get("is_refining") and session.get("old_criteria", {}).get("city"):
            session["criteria"]["city"] = session["old_criteria"]["city"]
            city_status = session["old_criteria"]["city"]
        else:
            session["criteria"]["city"] = None
            city_status = "не указан"
        
        session["state"] = BotState.COLLECTING_AREA
        
        # Получаем старое значение площади для подсказки
        old_criteria = session.get("old_criteria", {})
        area_hint = ""
        if old_criteria.get("area_min") and old_criteria.get("area_max"):
            area_hint = f"\n💭 Предыдущее значение: {old_criteria['area_min']}-{old_criteria['area_max']} м²"
        
        keyboard = [
            [InlineKeyboardButton("⏭ Пропустить (не важно)", callback_data="skip_area")],
            [InlineKeyboardButton("🏠 На главную", callback_data="to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"✅ Город: {city_status}\n\n"
            "Теперь укажите площадь помещения.\n"
            "Можно указать диапазон, например: **50-100** м²\n"
            "Или одно значение: **80** м²\n"
            "Или нажмите кнопку, чтобы пропустить этот параметр"
            + area_hint + "\n\n"
            "💡 **Оставьте строку пустой, если параметр не важен**",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        await query.answer()
    
    elif query.data == "skip_area":
        # Если мы в режиме уточнения, сохраняем старое значение, иначе ставим None
        if session.get("is_refining") and session.get("old_criteria", {}).get("area_min") and session.get("old_criteria", {}).get("area_max"):
            session["criteria"]["area_min"] = session["old_criteria"]["area_min"]
            session["criteria"]["area_max"] = session["old_criteria"]["area_max"]
            area_status = f"{session['old_criteria']['area_min']}-{session['old_criteria']['area_max']} м²"
        else:
            session["criteria"]["area_min"] = None
            session["criteria"]["area_max"] = None
            area_status = "не указана"
        
        session["state"] = BotState.COLLECTING_BUDGET
        
        # Получаем старое значение бюджета для подсказки
        old_criteria = session.get("old_criteria", {})
        price_suffix = "руб/мес" if session['criteria'].get('deal_type') == 'rent' else "руб"
        budget_hint = ""
        if old_criteria.get("budget_min") and old_criteria.get("budget_max"):
            budget_hint = f"\n💭 Предыдущее значение: {old_criteria['budget_min']:,}-{old_criteria['budget_max']:,} {price_suffix}"
        elif old_criteria.get("budget_max"):
            budget_hint = f"\n💭 Предыдущее значение: до {old_criteria['budget_max']:,} {price_suffix}"
        
        keyboard = [
            [InlineKeyboardButton("⏭ Пропустить (не важно)", callback_data="skip_budget")],
            [InlineKeyboardButton("🏠 На главную", callback_data="to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        deal_text = "аренду в месяц" if session['criteria'].get('deal_type') == 'rent' else "покупку"
        
        await query.edit_message_text(
            f"✅ Площадь: {area_status}\n\n"
            f"Теперь укажите бюджет на {deal_text}.\n"
            f"Можно указать диапазон, например: **100-200 тыс**\n"
            f"Или одно значение (максимум): **200000**\n"
            "Или нажмите кнопку, чтобы пропустить этот параметр"
            + budget_hint + "\n\n"
            "💡 **Оставьте строку пустой, если параметр не важен**",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        await query.answer()
    
    elif query.data == "skip_budget":
        # Если мы в режиме уточнения, сохраняем старое значение, иначе ставим None
        price_suffix = "руб/мес" if session['criteria'].get('deal_type') == 'rent' else "руб"
        
        if session.get("is_refining") and (session.get("old_criteria", {}).get("budget_min") or session.get("old_criteria", {}).get("budget_max")):
            session["criteria"]["budget_min"] = session["old_criteria"].get("budget_min")
            session["criteria"]["budget_max"] = session["old_criteria"].get("budget_max")
            
            if session["criteria"]["budget_min"] and session["criteria"]["budget_max"]:
                budget_status = f"{session['criteria']['budget_min']:,}-{session['criteria']['budget_max']:,} {price_suffix}"
            elif session["criteria"]["budget_min"]:
                budget_status = f"от {session['criteria']['budget_min']:,} {price_suffix}"
            else:
                budget_status = f"до {session['criteria']['budget_max']:,} {price_suffix}"
        else:
            session["criteria"]["budget_min"] = None
            session["criteria"]["budget_max"] = None
            budget_status = "не указан"
        
        # Сбрасываем флаг уточнения
        session["is_refining"] = False
        session["old_criteria"] = {}
        
        session["state"] = BotState.PROCESSING
        
        # Формируем сводку критериев
        summary = "**Сводка критериев:**\n"
        summary += f"📍 Город: {session['criteria']['city'] or 'не указан'}\n"
        
        if session['criteria']['area_min'] and session['criteria']['area_max']:
            summary += f"📐 Площадь: {session['criteria']['area_min']}-{session['criteria']['area_max']} м²\n"
        else:
            summary += f"📐 Площадь: не указана\n"
        
        if session['criteria']['budget']:
            price_suffix = "руб/мес" if session['criteria'].get('deal_type') == 'rent' else "руб"
            summary += f"💰 Бюджет: {session['criteria']['budget']:,} {price_suffix}\n"
        else:
            summary += f"💰 Бюджет: не указан\n"
        
        await query.edit_message_text(
            f"✅ Бюджет: {budget_status}\n\n{summary}\n"
            "🔍 Ищу подходящие помещения и анализирую их с помощью ИИ...",
            parse_mode='Markdown'
        )
        
        # Создаем update из query для вызова process_search
        # Используем query.message как основу для создания update
        await process_search_from_query(query, context)
        await query.answer()
    
    elif query.data == "restore_search":
        # Восстанавливаем последний поиск
        last_search = db.get_last_search(user_id)
        if last_search:
            session["criteria"] = last_search
            session["state"] = BotState.PROCESSING
            await query.edit_message_text("🔄 Восстанавливаю параметры поиска...")
            
            # Создаем update из query для вызова process_search
            await process_search_from_query(query, context)
        else:
            await query.answer("❌ История поиска не найдена", show_alert=True)
            await show_main_page(create_temp_update_from_query(query), context)

    elif query.data == "settings":
        # Меню настроек
        keyboard = [
            [InlineKeyboardButton("🔔 Уведомления", callback_data="subscriptions")],
            [InlineKeyboardButton("📜 История поиска", callback_data="history")],
            [InlineKeyboardButton("📚 Инструкция", callback_data="help")],
            [InlineKeyboardButton("🗑 Очистить историю поиска", callback_data="reset_history")],
            [InlineKeyboardButton("🗑 Очистить избранное", callback_data="reset_favorites")],
            [InlineKeyboardButton("🗑 Очистить скрытые", callback_data="reset_dislikes")],
            [InlineKeyboardButton("⚠️ Полный сброс данных", callback_data="full_reset_confirm")],
            [InlineKeyboardButton("🏠 На главную", callback_data="to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "⚙️ **Настройки**\n\nВыберите действие:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        await query.answer()

    elif query.data == "reset_history":
        db.clear_user_history(user_id)
        await query.answer("✅ История поиска очищена", show_alert=True)
        # Возвращаемся в настройки
        keyboard = [
            [InlineKeyboardButton("🔔 Уведомления", callback_data="subscriptions")],
            [InlineKeyboardButton("📜 История поиска", callback_data="history")],
            [InlineKeyboardButton("📚 Инструкция", callback_data="help")],
            [InlineKeyboardButton("🗑 Очистить историю поиска", callback_data="reset_history")],
            [InlineKeyboardButton("🗑 Очистить избранное", callback_data="reset_favorites")],
            [InlineKeyboardButton("🗑 Очистить скрытые", callback_data="reset_dislikes")],
            [InlineKeyboardButton("⚠️ Полный сброс данных", callback_data="full_reset_confirm")],
            [InlineKeyboardButton("🏠 На главную", callback_data="to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "⚙️ **Настройки**\n\n✅ История поиска очищена.\nВыберите действие:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    elif query.data == "reset_favorites":
        db.clear_user_favorites(user_id)
        session["likes"] = []
        session["all_listings"] = [] # Если мы показывали избранное
        await query.answer("✅ Избранное очищено", show_alert=True)
        # Возвращаемся в настройки
        keyboard = [
            [InlineKeyboardButton("🔔 Уведомления", callback_data="subscriptions")],
            [InlineKeyboardButton("📜 История поиска", callback_data="history")],
            [InlineKeyboardButton("📚 Инструкция", callback_data="help")],
            [InlineKeyboardButton("🗑 Очистить историю поиска", callback_data="reset_history")],
            [InlineKeyboardButton("🗑 Очистить избранное", callback_data="reset_favorites")],
            [InlineKeyboardButton("🗑 Очистить скрытые", callback_data="reset_dislikes")],
            [InlineKeyboardButton("⚠️ Полный сброс данных", callback_data="full_reset_confirm")],
            [InlineKeyboardButton("🏠 На главную", callback_data="to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "⚙️ **Настройки**\n\n✅ Избранное очищено.\nВыберите действие:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    elif query.data == "reset_dislikes":
        db.clear_user_dislikes(user_id)
        session["dislikes"] = {}
        session["excluded_listing_ids"] = []
        await query.answer("✅ Скрытые объявления очищены", show_alert=True)
        # Возвращаемся в настройки
        keyboard = [
            [InlineKeyboardButton("🔔 Уведомления", callback_data="subscriptions")],
            [InlineKeyboardButton("📜 История поиска", callback_data="history")],
            [InlineKeyboardButton("📚 Инструкция", callback_data="help")],
            [InlineKeyboardButton("🗑 Очистить историю поиска", callback_data="reset_history")],
            [InlineKeyboardButton("🗑 Очистить избранное", callback_data="reset_favorites")],
            [InlineKeyboardButton("🗑 Очистить скрытые", callback_data="reset_dislikes")],
            [InlineKeyboardButton("⚠️ Полный сброс данных", callback_data="full_reset_confirm")],
            [InlineKeyboardButton("🏠 На главную", callback_data="to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "⚙️ **Настройки**\n\n✅ Скрытые объявления очищены.\nВыберите действие:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    elif query.data == "full_reset_confirm":
        # Подтверждение полного сброса
        keyboard = [
            [InlineKeyboardButton("✅ Да, сбросить всё", callback_data="full_reset")],
            [InlineKeyboardButton("❌ Отмена", callback_data="settings")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "⚠️ **Вы уверены?**\n\nЭто действие удалит всю вашу историю, избранное и настройки. Отменить это действие нельзя.",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        await query.answer()

    elif query.data == "new_chat":
        # Полный сброс всех данных сессии и возврат на главную
        reset_user_session(user_id)
        session = get_user_session(user_id)
        
        class QueryUpdate:
            def __init__(self, callback_query):
                self.effective_user = callback_query.from_user
                self.callback_query = callback_query
        
        temp_update = QueryUpdate(query)
        await show_main_page(temp_update, context)
        await query.answer("🆕 Новый чат начат! Все данные очищены.")
    
    elif query.data == "subscribe":
        # Подписка на обновления
        criteria = session.get("criteria", {})
        if criteria:
            db.add_subscription(user_id, criteria)
            
            # Помечаем текущие объявления как просмотренные, чтобы не получать уведомления о них
            try:
                current_listings = parse_listings(
                    city=criteria.get("city"),
                    district=criteria.get("district"),
                    min_area=criteria.get("area_min"),
                    max_area=criteria.get("area_max"),
                    max_price=criteria.get("budget"),
                    floor=criteria.get("floor"),
                    deal_type=criteria.get("deal_type")
                )
                for listing in current_listings:
                    db.add_viewed(user_id, str(listing['id']))
            except Exception as e:
                logger.error(f"Error marking initial listings as viewed: {e}")

            await query.answer("✅ Вы подписались на обновления!", show_alert=True)
            
            # Обновляем страницу, чтобы кнопка изменилась
            temp_update = create_temp_update_from_query(query)
            await show_listings_page(temp_update, context, session.get("current_page", 0))
        else:
            await query.answer("❌ Нет активных критериев для подписки", show_alert=True)

    elif query.data.startswith("unsub_curr_"):
        sub_id = int(query.data.split("_")[2])
        db.remove_subscription(sub_id)
        await query.answer("✅ Вы отписались от обновлений!", show_alert=True)
        
        # Обновляем страницу, чтобы кнопка изменилась
        temp_update = create_temp_update_from_query(query)
        await show_listings_page(temp_update, context, session.get("current_page", 0))

    elif query.data.startswith("compare_add_"):
        listing_id = int(query.data.split("_")[2])
        comparison_list = session.get("comparison_list", [])
        
        # Проверяем лимит
        if len(comparison_list) >= 5:
            await query.answer("❌ Можно сравнить максимум 5 объявлений", show_alert=True)
            return

        # Добавляем ID
        if listing_id not in comparison_list:
            comparison_list.append(listing_id)
            session["comparison_list"] = comparison_list
            await query.answer(f"✅ Добавлено к сравнению ({len(comparison_list)}/5)")
        else:
            await query.answer("⚠️ Уже в списке сравнения")

    elif query.data == "show_comparison":
        comparison_list = session.get("comparison_list", [])
        if len(comparison_list) < 2:
            await query.answer("⚠️ Для сравнения нужно минимум 2 объявления", show_alert=True)
            return
            
        await query.edit_message_text("⏳ Генерирую сравнение с помощью ИИ...")
        
        # Получаем данные объявлений
        all_listings = session.get("all_listings", [])
        listings_to_compare = [l for l in all_listings if l.get('id') in comparison_list]
        
        # Если каких-то нет в памяти (странно, но возможно), пробуем восстановить из favorites/dislikes или просто пропускаем
        # Для простоты берем только те, что нашли
        
        if len(listings_to_compare) < 2:
             await query.edit_message_text("❌ Не удалось найти данные объявлений для сравнения.")
             return

        comparison_text = await ai_service.compare_listings(listings_to_compare)
        
        keyboard = [
            [InlineKeyboardButton("🗑 Очистить сравнение", callback_data="clear_comparison")],
            [InlineKeyboardButton("🏠 На главную", callback_data="to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"⚖️ **Сравнение вариантов**\n\n{comparison_text}",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    elif query.data == "clear_comparison":
        session["comparison_list"] = []
        await query.answer("✅ Список сравнения очищен")
        await show_main_page(create_temp_update_from_query(query), context)

    elif query.data.startswith("like_"):
        # Обработка лайка
        listing_id = int(query.data.split("_")[1])
        
        # Получаем объявление
        all_listings = session.get("all_listings", [])
        listing = next((l for l in all_listings if l.get('id') == listing_id), None)
        
        # Сохраняем в сессии
        if listing_id not in session.get("likes", []):
            session["likes"].append(listing_id)
        
        # Сохраняем в БД
        if listing:
            db.add_favorite(user_id, listing)
            # Если был в дизлайках в БД, удаляем
            db.remove_dislike(user_id, listing_id)
        
        # Удаляем из дизлайков, если был там
        if listing_id in session.get("dislikes", {}):
            del session["dislikes"][listing_id]
        
        # Отправляем на бэкенд
        await send_like_to_backend(user_id, listing_id)
        
        # После лайка убираем кнопку дизлайк, добавляем кнопки "Понравившиеся" и "К списку"
        keyboard = [
            [InlineKeyboardButton("❤️ Понравившиеся", callback_data="favorites")],
            [InlineKeyboardButton("← К списку", callback_data="back_to_list")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # (listing уже найден выше)
        
        if listing:
            # Формируем полное описание с контактами
            full_text = f"**{listing['address']}**\n\n"
            full_text += f"📐 **Площадь:** {listing['area']} м²\n"
            price_suffix = "руб/мес" if listing.get('deal_type') == 'rent' else "руб"
            price_per_sqm = round(listing['price'] / listing['area']) if listing['area'] > 0 else 0
            full_text += f"💰 **Цена:** {listing['price']:,} {price_suffix} ({price_per_sqm:,} руб/м²)\n"
            full_text += f"📍 **Этаж:** {listing['floor']}\n"
            full_text += f"🚶 **Трафик:** {listing.get('traffic', 'не указан')}\n"
            full_text += f"🚇 **Доступность:** {listing.get('accessibility', 'не указана')}\n\n"
            full_text += f"📝 **Описание:**\n{listing.get('description', 'Нет описания')}\n\n"
            
            # Добавляем контакты (так как теперь лайкнуто)
            full_text += f"📞 **Телефон:** {listing.get('phone', 'Не указан')}\n\n"
            
            ai_reason = listing.get('ai_reason', '').strip()
            if ai_reason:
                full_text += f"💡 **Почему подходит:**\n{ai_reason}\n\n"
            
            if listing.get('link'):
                full_text += f"🔗 Ссылка: {listing['link']}"
            
            try:
                await query.edit_message_text(full_text, parse_mode='Markdown', reply_markup=reply_markup, disable_web_page_preview=True)
            except Exception as e:
                logger.error(f"Ошибка при обновлении сообщения: {e}")
        else:
            # Если объявление не найдено (странно), обновляем только кнопки
            try:
                await query.edit_message_reply_markup(reply_markup=reply_markup)
            except Exception as e:
                logger.error(f"Ошибка при обновлении кнопок: {e}")
        
        await query.answer("👍 Спасибо! Объявление добавлено в избранное.")
    
    elif query.data.startswith("show_listing_id_"):
        # Показываем полное описание объявления по ID
        listing_id_str = query.data.split("_")[3]
        current_listings = session.get("current_listings", [])
        
        # Ищем объявление по ID в текущих объявлениях (сравниваем как строки)
        listing = next((l for l in current_listings if str(l.get('id')) == listing_id_str), None)
        
        if not listing:
            # Если не найдено в текущих, ищем во всех объявлениях
            all_listings = session.get("all_listings", [])
            listing = next((l for l in all_listings if str(l.get('id')) == listing_id_str), None)
        
        if not listing:
            await query.answer("Объявление не найдено", show_alert=True)
            return
        
        # Сохраняем ID объявления для возврата к списку
        session["viewing_listing_id"] = listing['id']
        
        # Проверяем, был ли уже лайк или дизлайк
        listing_id = listing['id']
        is_liked = listing_id in session.get("likes", [])
        is_disliked = listing_id in session.get("dislikes", {})
        
        # Формируем полное описание
        full_text = f"**{listing['address']}**\n\n"
        full_text += f"📐 **Площадь:** {listing['area']} м²\n"
        price_suffix = "руб/мес" if listing.get('deal_type') == 'rent' else "руб"
        price_per_sqm = round(listing['price'] / listing['area']) if listing['area'] > 0 else 0
        full_text += f"💰 **Цена:** {listing['price']:,} {price_suffix} ({price_per_sqm:,} руб/м²)\n"
        full_text += f"📍 **Этаж:** {listing['floor']}\n"
        full_text += f"🚶 **Трафик:** {listing.get('traffic', 'не указан')}\n"
        full_text += f"🚇 **Доступность:** {listing.get('accessibility', 'не указана')}\n\n"
        full_text += f"📝 **Описание:**\n{listing.get('description', 'Нет описания')}\n\n"
        
        # Если лайкнуто, показываем контакты
        if is_liked:
            full_text += f"📞 **Телефон:** {listing.get('phone', 'Не указан')}\n\n"
            
        # Показываем объяснение ИИ только если оно есть
        ai_reason = listing.get('ai_reason', '').strip()
        if ai_reason:
            full_text += f"💡 **Почему подходит:**\n{ai_reason}\n\n"
        
        # Всегда показываем ссылку
        link = listing.get('link', '')
        if link:
            full_text += f"🔗 **Ссылка:** {link}"
        else:
            full_text += f"🔗 **Ссылка:** недоступна"
        
        # Создаем кнопки Лайк/Дизлайк
        like_text = "✅ Лайк" if is_liked else "👍 Лайк"
        dislike_text = "❌ Дизлайк" if is_disliked else "👎 Дизлайк"
        
        keyboard = [
            [
                InlineKeyboardButton(like_text, callback_data=f"like_{listing_id}"),
                InlineKeyboardButton(dislike_text, callback_data=f"dislike_{listing_id}")
            ],
            [InlineKeyboardButton("← К списку", callback_data="back_to_list")]
        ]
        
        # Сохраняем предыдущее состояние для кнопки "Назад"
        session["previous_state"] = BotState.WAITING_REQUEST
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Редактируем сообщение, показывая полное описание
        await query.edit_message_text(
            full_text,
            parse_mode='Markdown',
            reply_markup=reply_markup,
            disable_web_page_preview=True
        )
        
        await query.answer()
    
    elif query.data == "sort_menu":
        # Меню сортировки
        sort_by = session.get("sort_by")
        sort_order = session.get("sort_order", "asc")
        
        price_text = "По цене"
        if sort_by == 'price':
            price_text += " " + ("⬆️" if sort_order == 'asc' else "⬇️")
            
        area_text = "По площади"
        if sort_by == 'area':
            area_text += " " + ("⬆️" if sort_order == 'asc' else "⬇️")
            
        price_per_sqm_text = "По цене за м²"
        if sort_by == 'price_per_sqm':
            price_per_sqm_text += " " + ("⬆️" if sort_order == 'asc' else "⬇️")
            
        keyboard = [
            [InlineKeyboardButton(price_text, callback_data="sort_price")],
            [InlineKeyboardButton(area_text, callback_data="sort_area")],
            [InlineKeyboardButton(price_per_sqm_text, callback_data="sort_price_per_sqm")],
            [InlineKeyboardButton("Сбросить", callback_data="sort_reset")],
            [InlineKeyboardButton("← Назад", callback_data="back_to_list")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Выберите тип сортировки:", reply_markup=reply_markup)
        await query.answer()

    elif query.data == "sort_price":
        # Сортировка по цене
        if session.get("sort_by") == 'price':
            # Переключаем порядок
            session["sort_order"] = 'desc' if session.get("sort_order") == 'asc' else 'asc'
        else:
            session["sort_by"] = 'price'
            session["sort_order"] = 'asc'
            
        # Возвращаемся к списку
        class QueryUpdate:
            def __init__(self, callback_query):
                self.effective_user = callback_query.from_user
                self.callback_query = callback_query
        
        temp_update = QueryUpdate(query)
        await show_listings_page(temp_update, context, 0)
        await query.answer("Сортировка по цене применена")

    elif query.data == "sort_area":
        # Сортировка по площади
        if session.get("sort_by") == 'area':
            # Переключаем порядок
            session["sort_order"] = 'desc' if session.get("sort_order") == 'asc' else 'asc'
        else:
            session["sort_by"] = 'area'
            session["sort_order"] = 'asc'
            
        # Возвращаемся к списку
        class QueryUpdate:
            def __init__(self, callback_query):
                self.effective_user = callback_query.from_user
                self.callback_query = callback_query
        
        temp_update = QueryUpdate(query)
        await show_listings_page(temp_update, context, 0)
        await query.answer("Сортировка по площади применена")

    elif query.data == "sort_price_per_sqm":
        # Сортировка по цене за квадратный метр
        if session.get("sort_by") == 'price_per_sqm':
            # Переключаем порядок
            session["sort_order"] = 'desc' if session.get("sort_order") == 'asc' else 'asc'
        else:
            session["sort_by"] = 'price_per_sqm'
            session["sort_order"] = 'asc'
            
        # Возвращаемся к списку
        class QueryUpdate:
            def __init__(self, callback_query):
                self.effective_user = callback_query.from_user
                self.callback_query = callback_query
        
        temp_update = QueryUpdate(query)
        await show_listings_page(temp_update, context, 0)
        await query.answer("Сортировка по цене за м² применена")

    elif query.data == "sort_reset":
        # Сброс сортировки
        session["sort_by"] = None
        session["sort_order"] = 'asc'
        
        # Возвращаемся к списку
        class QueryUpdate:
            def __init__(self, callback_query):
                self.effective_user = callback_query.from_user
                self.callback_query = callback_query
        
        temp_update = QueryUpdate(query)
        await show_listings_page(temp_update, context, 0)
        await query.answer("Сортировка сброшена")

    elif query.data == "to_main":
        # Возвращаемся на главную страницу с 5 кнопками
        class QueryUpdate:
            def __init__(self, callback_query):
                self.effective_user = callback_query.from_user
                self.callback_query = callback_query
        
        temp_update = QueryUpdate(query)
        await show_main_page(temp_update, context)
    
    elif query.data == "back_to_list":
        # Возвращаемся к списку объявлений
        all_listings = session.get("all_listings", [])
        
        if all_listings:
            current_page = session.get("current_page", 0)
            
            class QueryUpdate:
                def __init__(self, callback_query):
                    self.effective_user = callback_query.from_user
                    self.callback_query = callback_query
            
            temp_update = QueryUpdate(query)
            await show_listings_page(temp_update, context, current_page)
        else:
            await query.answer("Список объявлений пуст. Начните новый поиск.", show_alert=True)
    
    elif query.data == "start_search":
        # Сбрасываем критерии перед новым поиском
        session["criteria"] = {
            "city": None,
            "district": None,
            "area_min": None,
            "area_max": None,
            "budget": None,
            "floor": None,
            "deal_type": None
        }
        # Начинаем сбор параметров с выбора города
        session["state"] = BotState.COLLECTING_CITY
        
        keyboard = [
            [InlineKeyboardButton("Екатеринбург", callback_data="city_Екатеринбург")],
            [InlineKeyboardButton("Челябинск", callback_data="city_Челябинск")],
            [InlineKeyboardButton("🏠 На главную", callback_data="to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🏙 **Выберите город**\n\n"
            "В каком городе будем искать помещение?",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        await query.answer()

    elif query.data.startswith("city_"):
        city = query.data.split("_")[1]
        session["criteria"]["city"] = city
        session["state"] = BotState.WAITING_PROMPT
        
        keyboard = [
            [InlineKeyboardButton("🏠 На главную", callback_data="to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"✅ Выбран город: **{city}**\n\n"
            "Теперь опишите, какое помещение вы ищете. Например:\n"
            "\"В центре, от 50 до 100 кв.м, до 200000 рублей\"\n\n"
            "Я постараюсь понять ваш запрос и найти подходящие варианты.",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        await query.answer()
    
    elif query.data == "show_results":
        # Показываем результаты поиска (список объявлений)
        all_listings = session.get("all_listings", [])
        
        if all_listings:
            current_page = session.get("current_page", 0)
            
            class QueryUpdate:
                def __init__(self, callback_query):
                    self.effective_user = callback_query.from_user
                    self.callback_query = callback_query
            
            temp_update = QueryUpdate(query)
            await show_listings_page(temp_update, context, current_page)
        else:
            await query.answer("Результаты поиска не найдены. Начните новый поиск.", show_alert=True)
    
    elif query.data.startswith("page_"):
        # Переход на другую страницу
        page = int(query.data.split("_")[1])
        
        class QueryUpdate:
            def __init__(self, callback_query):
                self.effective_user = callback_query.from_user
                self.callback_query = callback_query
        
        temp_update = QueryUpdate(query)
        await show_listings_page(temp_update, context, page)
    
    elif query.data == "favorites":
        # Показываем первое избранное объявление
        session["favorite_index"] = 0
        class QueryUpdate:
            def __init__(self, callback_query):
                self.effective_user = callback_query.from_user
                self.callback_query = callback_query
        
        temp_update = QueryUpdate(query)
        await show_favorites(temp_update, context, index=0)
    
    elif query.data == "favorite_prev":
        # Переход к предыдущему избранному объявлению
        session = get_user_session(user_id)
        current_index = session.get("favorite_index", 0)
        new_index = max(0, current_index - 1)
        
        class QueryUpdate:
            def __init__(self, callback_query):
                self.effective_user = callback_query.from_user
                self.callback_query = callback_query
        
        temp_update = QueryUpdate(query)
        await show_favorites(temp_update, context, index=new_index)
    
    elif query.data == "favorite_next":
        # Переход к следующему избранному объявлению
        session = get_user_session(user_id)
        likes = session.get("likes", [])
        all_listings = session.get("all_listings", [])
        favorite_listings = [listing for listing in all_listings if listing.get('id') in likes]
        
        current_index = session.get("favorite_index", 0)
        new_index = min(len(favorite_listings) - 1, current_index + 1)
        
        class QueryUpdate:
            def __init__(self, callback_query):
                self.effective_user = callback_query.from_user
                self.callback_query = callback_query
        
        temp_update = QueryUpdate(query)
        await show_favorites(temp_update, context, index=new_index)
    
    elif query.data.startswith("remove_favorite_"):
        # Убираем объявление из избранного
        listing_id = int(query.data.split("_")[2])
        session = get_user_session(user_id)
        
        # Получаем текущий индекс
        current_index = session.get("favorite_index", 0)
        
        # Получаем список избранного из БД до удаления
        favorite_listings_from_db = db.get_favorites(user_id)
        
        # Находим индекс удаляемого объявления
        remove_index = next((i for i, l in enumerate(favorite_listings_from_db) if l.get('id') == listing_id), -1)
        
        # Удаляем из БД
        db.remove_favorite(user_id, listing_id)
        
        # Также удаляем из сессии, если есть
        likes = session.get("likes", [])
        if listing_id in likes:
            session["likes"].remove(listing_id)
        
        await query.answer("✅ Объявление убрано из избранного")
        
        # Проверяем, есть ли еще избранные
        favorite_listings_from_db = db.get_favorites(user_id)
        if not favorite_listings_from_db:
            # Если список пуст, показываем сообщение
            keyboard = get_to_main_button()
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "❤️ **Понравившиеся**\n\n"
                "Вы пока не добавили ни одного объявления в избранное.\n\n"
                "Чтобы добавить объявление в избранное, нажмите кнопку 👍 Лайк под его описанием.",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            session["favorite_index"] = 0
        else:
            # Определяем новый индекс для перехода
            # После удаления список стал короче на 1 элемент
            new_length = len(favorite_listings_from_db)
            
            if remove_index == current_index:
                # Удалили текущее объявление
                if current_index >= new_length:
                    # Удалили последнее - переходим к новому последнему
                    new_index = max(0, new_length - 1)
                else:
                    # Удалили не последнее - остаемся на том же индексе (следующее займет место)
                    new_index = current_index
                    if new_index >= new_length:
                        new_index = max(0, new_length - 1)
            elif remove_index < current_index:
                # Удалили объявление до текущего - уменьшаем индекс
                new_index = max(0, current_index - 1)
            else:
                # Удалили объявление после текущего - индекс не меняется
                new_index = current_index
            
            # Обновляем страницу избранного с новым индексом
            class QueryUpdate:
                def __init__(self, callback_query):
                    self.effective_user = callback_query.from_user
                    self.callback_query = callback_query
            
            temp_update = QueryUpdate(query)
            await show_favorites(temp_update, context, index=new_index)
    
    elif query.data == "view_new_listings":
        # Сбрасываем страницу на начало
        session["current_page"] = 0
        # Показываем список объявлений (новые уже добавлены в начало списка в background_worker)
        await show_listings_page(update, context, page=0)
    
    elif query.data.startswith("dislike_") and not query.data.startswith("dislike_prev") and not query.data.startswith("dislike_next"):
        # Обработка дизлайка
        listing_id = int(query.data.split("_")[1])
        
        # Если уже есть дизлайк, просто показываем сообщение
        if listing_id in session.get("dislikes", {}):
            await query.answer("Вы уже скрыли это объявление.", show_alert=True)
            return
        
        # Применяем дизлайк сразу
        await apply_dislike(user_id, listing_id, query, context, session)
    
    elif query.data == "dislikes":
        # Показываем первое скрытое объявление
        session["dislike_index"] = 0
        class QueryUpdate:
            def __init__(self, callback_query):
                self.effective_user = callback_query.from_user
                self.callback_query = callback_query
        
        temp_update = QueryUpdate(query)
        await show_dislikes(temp_update, context, index=0)
    
    elif query.data == "dislike_prev":
        # Переход к предыдущему скрытому объявлению
        session = get_user_session(user_id)
        current_index = session.get("dislike_index", 0)
        new_index = max(0, current_index - 1)
        
        class QueryUpdate:
            def __init__(self, callback_query):
                self.effective_user = callback_query.from_user
                self.callback_query = callback_query
        
        temp_update = QueryUpdate(query)
        await show_dislikes(temp_update, context, index=new_index)
    
    elif query.data == "dislike_next":
        # Переход к следующему скрытому объявлению
        session = get_user_session(user_id)
        dislikes = session.get("dislikes", {})
        
        current_index = session.get("dislike_index", 0)
        new_index = min(len(dislikes) - 1, current_index + 1)
        
        class QueryUpdate:
            def __init__(self, callback_query):
                self.effective_user = callback_query.from_user
                self.callback_query = callback_query
        
        temp_update = QueryUpdate(query)
        await show_dislikes(temp_update, context, index=new_index)
    
    elif query.data.startswith("restore_dislike_"):
        # Восстановление скрытого объявления
        listing_id = int(query.data.split("_")[2])
        session = get_user_session(user_id)
        
        dislikes = session.get("dislikes", {})
        
        if listing_id in dislikes:
            # Получаем данные объявления
            data = dislikes[listing_id]
            listing = None
            if isinstance(data, dict) and data.get("listing"):
                listing = data["listing"]
            
            # Удаляем из дизлайков
            del dislikes[listing_id]
            # Удаляем из БД
            db.remove_dislike(user_id, listing_id)
            
            # Удаляем из исключенных
            excluded_ids = session.get("excluded_listing_ids", [])
            if listing_id in excluded_ids:
                excluded_ids.remove(listing_id)
                session["excluded_listing_ids"] = excluded_ids
            
            # Если есть объект объявления, возвращаем его в списки
            if listing:
                # Добавляем в all_listings если его там нет
                all_listings = session.get("all_listings", [])
                if not any(l.get('id') == listing_id for l in all_listings):
                    all_listings.append(listing)
                    # Сортируем по ID, чтобы сохранить порядок (или можно просто добавить в конец)
                    # all_listings.sort(key=lambda x: x.get('id', 0))
                    session["all_listings"] = all_listings
                
                # Добавляем в original_listings если его там нет
                original_listings = session.get("original_listings", [])
                if not any(l.get('id') == listing_id for l in original_listings):
                    original_listings.append(listing)
                    session["original_listings"] = original_listings
            
            await query.answer("✅ Объявление возвращено в поиск")
            
            # Обновляем просмотр скрытых
            if not dislikes:
                # Если больше нет скрытых, возвращаемся на главную
                class QueryUpdate:
                    def __init__(self, callback_query):
                        self.effective_user = callback_query.from_user
                        self.callback_query = callback_query
                
                temp_update = QueryUpdate(query)
                await show_main_page(temp_update, context)
            else:
                # Показываем следующее или предыдущее
                current_index = session.get("dislike_index", 0)
                new_index = max(0, min(current_index, len(dislikes) - 1))
                
                class QueryUpdate:
                    def __init__(self, callback_query):
                        self.effective_user = callback_query.from_user
                        self.callback_query = callback_query
                
                temp_update = QueryUpdate(query)
                await show_dislikes(temp_update, context, index=new_index)
        else:
            await query.answer("Объявление не найдено в скрытых", show_alert=True)

    elif query.data == "history":
        class QueryUpdate:
            def __init__(self, callback_query):
                self.effective_user = callback_query.from_user
                self.callback_query = callback_query
        
        temp_update = QueryUpdate(query)
        await show_history(temp_update, context)

    elif query.data.startswith("history_select_"):
        history_id = int(query.data.split("_")[2])
        history = db.get_search_history(user_id, limit=20)
        item = next((h for h in history if h['id'] == history_id), None)
        
        if item:
            criteria = item['criteria']
            session["criteria"] = criteria
            session["state"] = BotState.PROCESSING
            
            await query.edit_message_text(
                f"🔄 Повторяю поиск...\n"
                f"📍 Город: {criteria.get('city')}\n"
                f"🔍 Ищу подходящие помещения...",
                parse_mode='Markdown'
            )
            
            # Запускаем поиск
            await process_search_from_query(query, context)
        else:
            await query.answer("Запись истории не найдена", show_alert=True)

    elif query.data == "subscriptions":
        subs = db.get_subscriptions(user_id)
        
        if not subs:
            keyboard = [[InlineKeyboardButton("🔙 Назад в настройки", callback_data="settings")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("🔔 **Ваши подписки на уведомления:**\n\nУ вас нет активных подписок.", parse_mode='Markdown', reply_markup=reply_markup)
            await query.answer()
            return

        text = "🔔 **Ваши подписки на уведомления:**\n\n"
        keyboard = []
        
        for i, sub in enumerate(subs, 1):
            criteria = sub['criteria']
            
            # Формируем описание
            desc_parts = []
            if criteria.get('city'):
                desc_parts.append(f"📍 {criteria['city']}")
            
            if criteria.get('deal_type'):
                deal = "Аренда" if criteria['deal_type'] == 'rent' else "Продажа"
                desc_parts.append(f"💼 {deal}")
                
            if criteria.get('area_min') or criteria.get('area_max'):
                area = ""
                if criteria.get('area_min') and criteria.get('area_max'):
                    area = f"{criteria['area_min']}-{criteria['area_max']}"
                elif criteria.get('area_min'):
                    area = f"от {criteria['area_min']}"
                elif criteria.get('area_max'):
                    area = f"до {criteria['area_max']}"
                desc_parts.append(f"📐 {area} м²")
                
            if criteria.get('budget_min') or criteria.get('budget_max'):
                budget = ""
                if criteria.get('budget_min') and criteria.get('budget_max'):
                    budget = f"{criteria['budget_min']}-{criteria['budget_max']}"
                elif criteria.get('budget_min'):
                    budget = f"от {criteria['budget_min']}"
                elif criteria.get('budget_max'):
                    budget = f"до {criteria['budget_max']}"
                desc_parts.append(f"💰 {budget}")
            
            desc = ", ".join(desc_parts)
            text += f"**{i}.** {desc}\n"
            
            keyboard.append([InlineKeyboardButton(f"❌ Отписаться от №{i}", callback_data=f"unsubscribe_{sub['id']}")])
        
        keyboard.append([InlineKeyboardButton("🔙 Назад в настройки", callback_data="settings")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)
        await query.answer()

    elif query.data.startswith("unsubscribe_"):
        sub_id = int(query.data.split("_")[1])
        db.remove_subscription(sub_id)
        await query.answer("✅ Подписка удалена")
        
        # Обновляем список
        subs = db.get_subscriptions(user_id)
        if not subs:
             keyboard = [[InlineKeyboardButton("🔙 Назад в настройки", callback_data="settings")]]
             reply_markup = InlineKeyboardMarkup(keyboard)
             await query.edit_message_text("🔔 **Ваши подписки на уведомления:**\n\nСписок пуст.", parse_mode='Markdown', reply_markup=reply_markup)
        else:
            text = "🔔 **Ваши подписки на уведомления:**\n\n"
            keyboard = []
            for i, sub in enumerate(subs, 1):
                criteria = sub['criteria']
                desc_parts = []
                if criteria.get('city'): desc_parts.append(f"📍 {criteria['city']}")
                if criteria.get('deal_type'): desc_parts.append("Аренда" if criteria['deal_type'] == 'rent' else "Продажа")
                if criteria.get('area_min') or criteria.get('area_max'):
                    area = ""
                    if criteria.get('area_min') and criteria.get('area_max'): area = f"{criteria['area_min']}-{criteria['area_max']}"
                    elif criteria.get('area_min'): area = f"от {criteria['area_min']}"
                    elif criteria.get('area_max'): area = f"до {criteria['area_max']}"
                    desc_parts.append(f"📐 {area} м²")
                if criteria.get('budget_min') or criteria.get('budget_max'):
                    budget = ""
                    if criteria.get('budget_min') and criteria.get('budget_max'): budget = f"{criteria['budget_min']}-{criteria['budget_max']}"
                    elif criteria.get('budget_min'): budget = f"от {criteria['budget_min']}"
                    elif criteria.get('budget_max'): budget = f"до {criteria['budget_max']}"
                    desc_parts.append(f"💰 {budget}")
                
                desc = ", ".join(desc_parts)
                text += f"**{i}.** {desc}\n"
                keyboard.append([InlineKeyboardButton(f"❌ Отписаться от №{i}", callback_data=f"unsubscribe_{sub['id']}")])
            
            keyboard.append([InlineKeyboardButton("🔙 Назад в настройки", callback_data="settings")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)

    elif query.data == "full_reset":
        # Спрашиваем подтверждение
        keyboard = [
            [InlineKeyboardButton("✅ Да, удалить всё", callback_data="confirm_full_reset")],
            [InlineKeyboardButton("❌ Отмена", callback_data="to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "⚠️ **Вы уверены?**\n\n"
            "Это действие удалит:\n"
            "• Историю поиска\n"
            "• Все понравившиеся объявления\n"
            "• Список скрытых объявлений\n\n"
            "Это действие нельзя отменить.",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        await query.answer()

    elif query.data == "confirm_full_reset":
        session_full_reset(user_id)
        
        class QueryUpdate:
            def __init__(self, callback_query):
                self.effective_user = callback_query.from_user
                self.callback_query = callback_query
        
        temp_update = QueryUpdate(query)
        await show_main_page(temp_update, context)
        await query.answer("🗑 Все данные удалены")
    

def main():
    """Запуск бота"""
    # Инициализация базы данных
    db.init_db()

    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN не установлен!")
        return
    
    # Создаем приложение
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Запускаем фоновую задачу (раз в 3 часа = 10800 секунд)
    if application.job_queue:
        application.job_queue.run_repeating(check_new_listings, interval=10800, first=10)
    
    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    
    # Регистрируем обработчик callback-запросов
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    # Регистрируем обработчик текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Регистрируем обработчик голосовых сообщений
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))
    
    # Запускаем бота
    logger.info("Бот запущен...")

    async def _runner() -> None:
        await application.initialize()
        try:
            await application.start()

            if application.updater is None:
                raise RuntimeError(
                    "Updater is not available. Install python-telegram-bot with polling extras. "
                    "For example: python-telegram-bot[job-queue]"
                )

            await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
            # В PTB 22.x у Updater больше нет метода idle().
            # Просто ждем отмены (Ctrl+C) и корректно останавливаемся в finally.
            await asyncio.Event().wait()
        finally:
            if application.updater is not None and application.updater.running:
                await application.updater.stop()
            if application.running:
                await application.stop()
            await application.shutdown()

    asyncio.run(_runner())


if __name__ == '__main__':
    main()
