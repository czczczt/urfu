import requests
import uuid
import json

def send_question(question: str = None) -> str:
    """Отправить вопрос, получить ответ"""
    url = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"

    actok = ""
    try:
        with open("access_token.txt") as f:
            actok = f.readline().replace("\n", "")
    except:
        print("Ошибка чтения токена доступа")
        return

    headers = {
        "Authorization": f"Bearer {actok}",
        "Content-Type": "application/json",
        'Accept': 'application/json',
    }
    if question is None:
        print("Вопрос должен существовать")
        return
    
    data = {
        "model": "GigaChat",
        "messages": [
        {
            "role": "user",
            "content": question
        }
        ],
        "stream": False,
        "repetition_penalty": 1
    }

    response = requests.request("POST", url, headers=headers, json=data, verify=False, timeout=60)
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        print(f"Ошибка: {response.status_code}")
        print(response.text)
        return response.text


def get_access_token(client_id: str = None, client_secret: str = None, base64_credentials: str = None) -> str:
    scope = 'GIGACHAT_API_PERS'
    
    if base64_credentials is None:
        try:
            with open("authorization_key.txt", "r+") as f:
                client_id = f.readline().replace("\n", "")
                client_secret = f.readline().replace("\n", "")
                base64_credentials = f.readline().replace("\n", "")
        except:
            print("Не удалось прочитать данные")
            return
    
    # Генерация RqUID
    rquid = str(uuid.uuid4())

    headers = {
        'Authorization': f'Basic {base64_credentials}',
        'RqUID': rquid,
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    data = {
        'scope': scope
    }

    response = requests.post(
        'https://ngw.devices.sberbank.ru:9443/api/v2/oauth',
        headers=headers,
        data=data,
        verify=False  # !HTTPS
    )

    #Access token
    if response.status_code == 200:
        token_data = response.json()
        access_token = token_data.get('access_token')
        with open("access_token.txt", "w") as f:
            f.write(str(access_token))
        print("Токен успешно записан")
    else:
        print(f"Ошибка: {response.status_code}")
        print(response.text)
        return
    
# ФОРМАТ ВОПРОСА
# ДАЛЕЕ ДОЛЖЕН БЫТЬ ПРИВЕДЕН К СТРОКЕ
# question = json.dumps(question)
question = {
    "system_prompt": {
        "role": "Вы — AI-агент «БанкПоиск», эксперт по коммерческой недвижимости и анализу локаций для банковского бизнеса. Вы анализируете объявления, чтобы выбрать оптимальные помещения для банковских отделений, учитывая специфику банковских операций, потоки клиентов и нормативные требования.",
        "expertise": [
        "Анализ пешеходного и транспортного трафика",
        "Оценка коммерческой привлекательности локации",
        "Знание требований ЦБ РФ к банковским отделениям (безопасность, доступность, площадь)",
        "Финансовый анализ стоимости аренды и операционных расходов"
        ],
        "primary_goal": "Из предоставленных объявлений выбрать ТОП-3 варианта, максимально соответствующих критериям банка, и сформировать структурированный отчет с обоснованием выбора для сотрудника.",
        "output_language": "Русский"
    },
    "user_input_structure": {
        "search_parameters": {
        "target_rent_rate_per_sqm": "100000000", # question["user_input_structure"]["target_rent_rate_per_sqm"]
        "min_area_sqm": "50",  # question["user_input_structure"]["min_area_sqm"]
        "max_area_sqm": "100", # question["user_input_structure"]["max_area_sqm"]
        "districts": ["Люблино", "Центр", "Сортировка", "Завод"], # question["user_input_structure"]["districts"]
        "optional_requirements": #!! тут уже сомнительно question["user_input_structure"]["optional_requirements"]
        {
            "foot_traffic_priority": "высокий",
            "parking_required": "true",
            "ground_floor_mandatory": "true",
            "competitor_proximity_acceptable": "false"
        }
        },
        "parsed_ads_data": [ # question["user_input_structure"]["parsed_ads_data"].append({key:value,})
            {
                "ad_id": "1",
                "source": "Атом",
                "title": "Офис атом",
                "address": "Ленина 51",
                "district": "Люблино",
                "area_sqm": "60",
                "rent_rate_per_sqm": "20000",
                "total_rent_per_month": "10000",
                "floor": "20",
                "building_type": "отдельное здание",
                "additional_features": ["парковка", "ремонт", "кондиционер", "вход с улицы", "витринные окна"]
            },
            {
                "ad_id": "2",
                "source": "Новый лес",
                "title": "Лесная",
                "address": "Центральная 11",
                "district": "Люблино",
                "area_sqm": "40",
                "rent_rate_per_sqm": "15000",
                "total_rent_per_month": "12000",
                "floor": "10",
                "building_type": "отдельное здание",
                "additional_features": ["парковка", "ремонт"]
            },
            {
                "ad_id": "3",
                "source": "Муравейник",
                "title": "Кимпинтяу",
                "address": "Средняя 13",
                "district": "Люблино",
                "area_sqm": "80",
                "rent_rate_per_sqm": "20000",
                "total_rent_per_month": "9000",
                "floor": "13",
                "building_type": "отдельное здание",
                "additional_features": ["парковка", "витринные окна"]
            }
        ]
    },
    "processing_instructions": {
        "analysis_steps": [
        "1. **Первичная фильтрация**: Отбросить объявления, не соответствующие жестким критериям (район, минимальная площадь, превышение ставки более чем на 15%).",
        "2. **Балльная оценка по ключевым метрикам**: Каждому прошедшему фильтрацию объявлению присвоить баллы (от 1 до 10) по следующим критериям:",
        {
            "scoring_criteria": {
            "price_adequacy": "Соответствие ставки рыночной для района (ниже рынка = выше балл). Формула: (1 - (ставка_объявления / средняя_ставка_по_выборке)) * 10.",
            "location_suitability": "Оценка локации для банка: наличие входов с улицы, первый этаж, близость к остановкам/метро, пешеходный трафик (определяется по описанию и ключевым словам).",
            "infrastructure": "Наличие парковки, ремонта, отдельных коммуникаций, соответствия требованиям безопасности.",
            "area_efficiency": "Оптимальность площади (не слишком большая, чтобы не переплачивать, не слишком маленькая). Близость к целевому значению пользователя.",
            "description_quality_and_trust": "Полнота описания, наличие фото, указание контактов, отсутствие тревожных сигналов («срочно», «хозяин» и т.д.)."
            }
        },
        "3. **Анализ рисков и недостатков**: Для каждого кандидата выявить потенциальные проблемы (высокие эксплуатационные расходы, спорный район, плохая транспортная доступность).",
        "4. **Ранжирование**: Отсортировать варианты по сумме баллов. Выбрать ТОП-3.",
        "5. **Формулирование итогов**: Для каждого из ТОП-3 вариантов подготовить краткое, но содержательное обоснование."
        ],
        "reasoning_requirement": "Внутренние рассуждения о выборе (chain-of-thought) должны быть записаны кратко перед финальным ответом."
    },
    "output_format": {
        "required_sections": {
        "summary": "Краткая сводка: сколько объявлений обработано, сколько отфильтровано, общая характеристика рынка по заданным параметрам.",
        "top_3_recommendations": [
            {
            "rank": 1,
            "ad_id": "ид из входных данных",
            "justification": "Развернутое обоснование на 3-4 предложения: главные преимущества, почему подходит для банка, компромиссы.",
            "key_metrics": {
                "cost_efficiency_score": "оценка",
                "location_score": "оценка",
                "final_score": "суммарная оценка"
            },
            "next_step_suggestion": "Пример текста для первого контакта с арендодателем или запроса доп. информации."
            }
        ],
        "risk_warnings": "Список общих рисков по выбранным вариантам (например, 'во всех отобранных вариантах отсутствует выделенная парковка').",
        "draft_email_to_landlord": "Готовый шаблон делового письма для обращения по лучшему варианту (ad_id №1). Включает запрос на просмотр, уточнение условий и выражение заинтересованности."
        },
        "format": "Четкий, структурированный текст с подзаголовками. Данные из объявлений (адрес, ставка) должны быть точно цитированы."
    },
    "fallback_behavior": {
        "if_less_than_3": "Если после фильтрации осталось менее 3 объявлений, предложить 1-2 варианта, четко указав, по каким параметрам был ослаблен поиск. Сформулировать рекомендации по расширению критериев.",
        "if_no_matches": "Предоставить детальный анализ, почему ни одно объявление не подходит (например, 'ставки в указанном районе на 40% выше целевой'), и дать рыночные рекомендации."
    }
}