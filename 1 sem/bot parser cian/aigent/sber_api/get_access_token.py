# Получение сессионного токена

import requests
import uuid
import base64


# Данные авторизации
client_id = ''
client_secret = ''
scope = 'GIGACHAT_API_PERS'
base64_credentials = ""

try:
    with open("authorization_key.txt", "r+") as f:
        client_id = f.readline().replace("\n", "")
        client_secret = f.readline().replace("\n", "")
        base64_credentials = f.readline().replace("\n", "")
except:
    print("Не удалось прочитать данные")
    exit()


# Генерация RqUID
rquid = str(uuid.uuid4())

# Подготовка Basic Auth
credentials = f"{client_id}:{client_secret}"

#base64_credentials = base64.b64encode(credentials.encode()).decode()

# Заголовки
headers = {
    'Authorization': f'Basic {base64_credentials}',
    'RqUID': rquid,
    'Content-Type': 'application/x-www-form-urlencoded'
}

# Тело запроса
data = {
    'scope': scope
}

# Отправка запроса
response = requests.post(
    'https://ngw.devices.sberbank.ru:9443/api/v2/oauth',
    headers=headers,
    data=data,
    verify=False  # !HTTPS
)

#Access token
actok = ""
if response.status_code == 200:
    token_data = response.json()
    access_token = token_data.get('access_token')
    with open("access_token.txt", "w") as f:
        f.write(str(access_token))
    actok = access_token
else:
    print(f"Ошибка: {response.status_code}")
    print(response.text)
    exit()