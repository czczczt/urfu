# Проверка корректности acces_token
# если возвращается список моделей, то токен корректен

import requests

actok = ''

with open("access_token.txt", "r") as f:
    actok = f.readline().replace("\n", "")

url = "https://gigachat.devices.sberbank.ru/api/v1/models"

payload={}
headers = {
'Accept': 'application/json',
'Authorization': 'Bearer ' + actok,
}

response = requests.request("GET", url, headers=headers, data=payload, verify=False)

print(response.text)