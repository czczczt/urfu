# Получение остатка токенов запросов

import requests

actok = ''

with open("access_token.txt", "r") as f:
    actok = f.readline().replace("\n", "")

url = "https://gigachat.devices.sberbank.ru/api/v1/tokens/count"

payload={
  "model": "GigaChat",
  "input": [
    """Выведи id ТОП 3 наиболее похожих объектов на {"c":10000,"s":100,"t":1}
    из данных:
    [{"id":1,"c":5000,"s":90,"t":1},{"id":2,"c":11000,"s":400,"t":1},{"id":3,"c":10000,"s":100,"t":1},{"id":4,"c":10001,"s":101,"t":1}]
    ответ-списком"""
  ]
}

headers = {
'Accept': 'application/json',
'Authorization': 'Bearer ' + actok,
}

response = requests.request("POST", url, headers=headers, json=payload, verify=False)

print(response.text)