# Отправление вопроса и получение ответа от gigachat

import requests

url = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"

actok = ""
try:
    with open("access_token.txt") as f:
        actok = f.readline().replace("\n", "")
except:
    print("Ошибка чтения")
    exit()


headers = {
    "Authorization": f"Bearer {actok}",
    "Content-Type": "application/json",
    'Accept': 'application/json',
}
question = \
"""Выведи только список id ТОП 3 наиболее похожих объектов на {"c":10000,"s":100,"t":1}
из данных:
[{"id":1,"c":5000,"s":90,"t":1},{"id":2,"c":11000,"s":400,"t":1},{"id":3,"c":10000,"s":100,"t":1},{"id":4,"c":10001,"s":101,"t":1}]"""
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

print(response.text)