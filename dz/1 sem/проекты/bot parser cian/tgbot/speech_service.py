import logging
import uuid
import time
import httpx
import ssl
from config import SPEECH_TO_TEXT_API_KEY

logger = logging.getLogger(__name__)

class SpeechService:
    def __init__(self):
        self.auth_key = SPEECH_TO_TEXT_API_KEY
        self.access_token = None
        self.token_expires_at = 0
        self.scope = "SALUTE_SPEECH_PERS" # Usually this scope for personal use
        
    async def get_token(self):
        """Получает токен доступа"""
        if not self.auth_key:
            logger.error("SPEECH_TO_TEXT_API_KEY не установлен")
            return None
            
        # Если токен есть и не истек (с запасом 60 секунд)
        if self.access_token and time.time() < self.token_expires_at - 60:
            return self.access_token
            
        try:
            rq_uid = str(uuid.uuid4())
            url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
            
            headers = {
                "Authorization": f"Basic {self.auth_key}",
                "RqUID": rq_uid,
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            data = {
                "scope": self.scope
            }
            
            # Отключаем проверку SSL, так как у Сбера свои сертификаты
            async with httpx.AsyncClient(verify=False) as client:
                response = await client.post(url, headers=headers, data=data)
                
                if response.status_code == 200:
                    resp_data = response.json()
                    self.access_token = resp_data.get("access_token")
                    self.token_expires_at = resp_data.get("expires_at") / 1000 # timestamp in ms
                    logger.info("Получен новый токен SaluteSpeech")
                    return self.access_token
                else:
                    logger.error(f"Ошибка получения токена: {response.status_code} {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"Ошибка при запросе токена: {e}")
            return None

    async def recognize(self, audio_data: bytes) -> str:
        """
        Распознает речь из аудиоданных
        
        Args:
            audio_data: Байты аудиофайла (OGG/OPUS, MP3, WAV)
            
        Returns:
            Распознанный текст или None
        """
        # Ensure audio_data is bytes, as httpx might have issues with bytearray in async mode
        if isinstance(audio_data, bytearray):
            audio_data = bytes(audio_data)

        token = await self.get_token()
        if not token:
            return None
            
        try:
            url = "https://smartspeech.sber.ru/rest/v1/speech:recognize"
            
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "audio/ogg;codecs=opus" # Telegram voice messages are usually OGG Opus
            }
            
            # Отключаем проверку SSL
            async with httpx.AsyncClient(verify=False) as client:
                response = await client.post(url, headers=headers, content=audio_data)
                
                if response.status_code == 200:
                    # Ответ приходит в формате:
                    # {
                    #   "result": [
                    #     "текст"
                    #   ],
                    #   "emotions": [ ... ]
                    # }
                    resp_data = response.json()
                    results = resp_data.get("result")
                    if results and len(results) > 0:
                        text = results[0]
                        logger.info(f"Распознан текст: {text}")
                        return text
                    else:
                        logger.warning("Пустой результат распознавания")
                        return None
                else:
                    logger.error(f"Ошибка распознавания: {response.status_code} {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"Ошибка при распознавании речи: {e}")
            return None

    def is_available(self) -> bool:
        return bool(self.auth_key)

speech_service = SpeechService()
