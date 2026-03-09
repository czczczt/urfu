# 🔗 Пример интеграции улучшений в bot.py

## Изменения в обработчике поиска

```python
from ai_integration import ai_service

# ... существующий код ...

@router.message(StateFilter(SearchState.waiting_for_parameters))
async def process_search_input(message: Message, state: FSMContext):
    """Обработка ввода параметров поиска с валидацией"""
    
    user_input = message.text
    
    # 1. Извлекаем параметры (теперь с расширенными полями)
    params = await ai_service.extract_search_parameters(user_input)
    
    if not params:
        await message.answer("❌ Не удалось распознать параметры поиска. Попробуйте ещё раз.")
        return
    
    # 2. НОВОЕ: Валидация критериев
    validation = await ai_service.validate_search_criteria(params)
    
    # 3. Показываем предупреждения, если есть
    if not validation["is_realistic"] or not validation["is_valid"]:
        for warning in validation["warnings"]:
            await message.answer(f"⚠️ {warning}")
        
        if validation["suggestions"]:
            await message.answer("\n💡 ".join(["Рекомендации:"] + validation["suggestions"]))
        
        # Если критично нереалистично - спрашиваем подтверждение
        if not validation["is_realistic"]:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Продолжить поиск", callback_data="continue_search"),
                    InlineKeyboardButton(text="✏️ Изменить критерии", callback_data="change_criteria")
                ]
            ])
            await message.answer(
                "Продолжить поиск с такими критериями или изменить?",
                reply_markup=keyboard
            )
            await state.update_data(pending_params=params)
            return
    
    # 4. Логируем критичные параметры (для отладки)
    if params.get("is_strict"):
        print(f"🔒 СТРОГИЕ ТРЕБОВАНИЯ для пользователя {message.from_user.id}")
    if params.get("excluded_districts"):
        print(f"🚫 Исключены районы: {params['excluded_districts']}")
    
    # 5. Сохраняем параметры в state
    await state.update_data(search_params=params)
    
    # 6. Запускаем поиск
    await perform_search(message, state, params)


@router.callback_query(F.data == "continue_search")
async def continue_search_anyway(callback: CallbackQuery, state: FSMContext):
    """Продолжить поиск несмотря на предупреждения"""
    data = await state.get_data()
    params = data.get("pending_params")
    
    await callback.message.edit_text("⏳ Продолжаю поиск...")
    await perform_search(callback.message, state, params)


async def perform_search(message: Message, state: FSMContext, params: dict):
    """Выполнение поиска с учётом всех критериев"""
    
    # Получаем объявления от парсера
    listings = await parser.get_listings(params)
    
    if not listings:
        await message.answer("😔 Ничего не найдено по вашим критериям.")
        
        # Предлагаем смягчить критерии
        if params.get("is_strict"):
            await message.answer(
                "💡 Попробуйте ослабить требования:\n"
                "• Расширить диапазон цены\n"
                "• Рассмотреть соседние районы\n"
                "• Увеличить диапазон площади"
            )
        return
    
    # НОВОЕ: Ранжируем с учётом приоритетов и дизлайков
    data = await state.get_data()
    last_dislike = data.get("last_dislike_reason")
    
    ranked_listings = await ai_service.analyze_listings(
        criteria=params,
        listings=listings,
        dislike_reason=last_dislike,
        budget_exceeded=any(l["price"] > params.get("budget", float('inf')) for l in listings),
        area_exceeded=True  # определить логику
    )
    
    # Сохраняем в state
    await state.update_data(
        current_listings=ranked_listings,
        current_index=0
    )
    
    # Показываем первое объявление
    await show_listing(message, state, 0)


async def show_listing(message: Message, state: FSMContext, index: int):
    """Показ объявления с AI-объяснением"""
    
    data = await state.get_data()
    listings = data.get("current_listings", [])
    
    if index >= len(listings):
        await message.answer("Это все объявления!")
        return
    
    listing = listings[index]
    
    # Формируем сообщение
    text = f"""
🏢 <b>Объявление #{index + 1} из {len(listings)}</b>

📍 <b>Адрес:</b> {listing['address']}
📏 <b>Площадь:</b> {listing['area']} м²
💰 <b>Цена:</b> {listing['price']:,} руб/мес
🏢 <b>Этаж:</b> {listing['floor']}
"""
    
    # НОВОЕ: Добавляем AI-объяснение
    if listing.get("ai_reason"):
        text += f"\n🤖 <b>Почему этот вариант:</b>\n{listing['ai_reason']}\n"
    
    # НОВОЕ: Добавляем ранг
    if listing.get("ai_rank"):
        rank_emoji = "🥇" if listing["ai_rank"] == 1 else "🥈" if listing["ai_rank"] == 2 else "🥉" if listing["ai_rank"] == 3 else "📍"
        text += f"\n{rank_emoji} <b>Позиция в рейтинге:</b> #{listing['ai_rank']}\n"
    
    # Показываем превышения бюджета явно
    params = data.get("search_params", {})
    if params.get("budget") and listing["price"] > params["budget"]:
        overpay = listing["price"] - params["budget"]
        percent = (overpay / params["budget"]) * 100
        text += f"\n⚠️ Превышение бюджета: +{overpay:,} руб ({percent:.1f}%)\n"
    
    text += f"\n🔗 <a href='{listing['url']}'>Смотреть на сайте</a>"
    
    # Кнопки
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👍 Понравилось", callback_data=f"like_{index}"),
            InlineKeyboardButton(text="👎 Не подходит", callback_data=f"dislike_{index}")
        ],
        [
            InlineKeyboardButton(text="➡️ Следующее", callback_data=f"next_{index}"),
            InlineKeyboardButton(text="⏹ Завершить", callback_data="finish_search")
        ]
    ])
    
    await message.answer(text, parse_mode="HTML", reply_markup=keyboard)


@router.callback_query(F.data.startswith("dislike_"))
async def handle_dislike(callback: CallbackQuery, state: FSMContext):
    """Обработка дизлайка с запросом причины"""
    
    index = int(callback.data.split("_")[1])
    
    # Спрашиваем причину
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💸 Дорого", callback_data=f"reason_expensive_{index}")],
        [InlineKeyboardButton(text="📏 Маленькая площадь", callback_data=f"reason_small_{index}")],
        [InlineKeyboardButton(text="🚇 Далеко от метро", callback_data=f"reason_metro_{index}")],
        [InlineKeyboardButton(text="🏢 Не подходит этаж", callback_data=f"reason_floor_{index}")],
        [InlineKeyboardButton(text="📍 Не тот район", callback_data=f"reason_district_{index}")],
        [InlineKeyboardButton(text="✍️ Своя причина", callback_data=f"reason_custom_{index}")]
    ])
    
    await callback.message.edit_text(
        "Почему это объявление не подходит?",
        reply_markup=keyboard
    )


@router.callback_query(F.data.startswith("reason_"))
async def handle_dislike_reason(callback: CallbackQuery, state: FSMContext):
    """Сохранение причины дизлайка для учёта в следующих поисках"""
    
    parts = callback.data.split("_")
    reason_type = parts[1]
    index = int(parts[2])
    
    # Сохраняем причину
    reasons_map = {
        "expensive": "Дорого",
        "small": "Маленькая площадь",
        "metro": "Далеко от метро",
        "floor": "Не подходит этаж",
        "district": "Не тот район"
    }
    
    reason = reasons_map.get(reason_type, "Не подходит")
    
    # КРИТИЧНО: Сохраняем для учёта в analyze_listings
    await state.update_data(last_dislike_reason=reason)
    
    data = await state.get_data()
    listings = data.get("current_listings", [])
    disliked_listing = listings[index]
    
    # Логируем для анализа
    print(f"👎 Дизлайк: {disliked_listing['address']} - Причина: {reason}")
    
    await callback.message.edit_text(f"✅ Учту: '{reason}'. Следующие объявления будут лучше!")
    
    # Показываем следующее
    await show_listing(callback.message, state, index + 1)


# ... остальной код ...
```

---

## Пример использования валидации

```python
# В начале поиска
params = await ai_service.extract_search_parameters("Только центр за 50 тысяч")

validation = await ai_service.validate_search_criteria(params)

if validation["warnings"]:
    # warnings: ["⚠️ В центре помещения обычно от 150 000 руб/мес..."]
    for warning in validation["warnings"]:
        await message.answer(warning)

if validation["suggestions"]:
    # suggestions: ["💡 Предложите увеличить бюджет..."]
    await message.answer("\n".join(validation["suggestions"]))

if not validation["is_realistic"]:
    # Спросить подтверждение перед поиском
    pass
```

---

## Проверка работы логирования

После запуска бота в консоли должны появляться:

```
🔒 СТРОГИЕ ТРЕБОВАНИЯ для пользователя 123456789
🚫 Исключены районы: ['Зеленоград', 'Митино', 'Солнцево']
⚡ СРОЧНЫЙ ЗАПРОС: urgency=9
📍 Расширение 'центр' → Центральный
🏆 #1: ул. Тверская 10 - Идеально: центр + в бюджете, 3 мин до метро
🏆 #2: пр-т Ленинский 5 - ⚠️ Превышает бюджет на 25к, но отличное расположение
👎 Дизлайк: ул. Окружная 15 - Причина: Далеко от метро
```

---

## Дополнительно: Расширение DISTRICT_MAPPING

```python
# Добавить в ai_integration.py

DISTRICT_MAPPING = {
    "москва": {
        "центр": ["Центральный", "Тверской", "Пресненский", "Арбат", "Хамовники"],
        "деловой_центр": ["Москва-Сити", "Пресненский", "Центральный"],
        "окраины": ["Зеленоград", "Новокосино", "Митино", "Солнцево", "Южное Бутово"],
        
        # Синонимы для районов
        "сити": ["Пресненский"],  # Москва-Сити
        "арбат": ["Арбат", "Хамовники"],
        "тверская": ["Тверской"],
        # ... добавить больше
    },
    
    # Добавить больше городов
    "новосибирск": {
        "центр": ["Центральный"],
        "окраины": ["Кировский", "Дзержинский"],
    },
    
    "казань": {
        "центр": ["Вахитовский"],
        "окраины": ["Советский", "Приволжский"],
    },
    
    # ... и т.д.
}
```

---

**Готово к интеграции!** 🚀
