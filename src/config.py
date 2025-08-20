from pydantic import BaseModel
import os
from dotenv import load_dotenv

# 1) Загружаем переменные окружения из файла .env (если он есть в корне проекта)
load_dotenv()

# 2) Описываем типизированные настройки проекта
class Settings(BaseModel):
    telegram_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    openweather_api_key: str = os.getenv("OPENWEATHER_API_KEY", "")
    weather_units: str = os.getenv("WEATHER_UNITS", "metric")
    weather_lang: str = os.getenv("WEATHER_LANG", "ru")
    database_url: str = os.getenv("DATABASE_URL", "weather.db")

# 3) Создаём единый экземпляр настроек для импорта из других модулей
settings = Settings()
