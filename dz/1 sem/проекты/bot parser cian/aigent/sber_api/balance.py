# Получение количества оставшихся токенов для запросов

import requests

actok = ''

with open("access_token.txt", "r") as f:
    actok = f.readline().replace("\n", "")

url = "https://gigachat.devices.sberbank.ru/api/v1/balance"

headers = {
'Accept': 'application/json',
'Authorization': 'Bearer ' + actok,
}

response = requests.request("GET", url, headers=headers, verify=False)

print(response.text)