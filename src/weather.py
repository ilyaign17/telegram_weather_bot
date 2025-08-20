import httpx
from typing import Optional
from .config import settings

BASE_URL = "https://api.openweathermap.org/data/2.5/weather"

async def fetch_weather(city: str) -> Optional[dict]:
    """
    Асинхронно запрашивает текущую погоду для города.
    Возвращает JSON-словарь при успехе или None при ошибке/неудаче.
    """
    params = {
        "q": city,
        "appid": settings.openweather_api_key,
        "units": settings.weather_units,  # metric = °C, m/s
        "lang": settings.weather_lang,    # ru = описания на русском
    }
    timeout = httpx.Timeout(10.0, read=10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            r = await client.get(BASE_URL, params=params)
            if r.status_code == 200:
                return r.json()
            return None
        except httpx.RequestError:
            return None

def pretty_weather(data: dict) -> str:
    """
    Превращает сырой JSON OpenWeather в читабельный текст с эмодзи.
    """
    name = data.get("name", "")
    weather = (data.get("weather") or [{}])[0]
    main = data.get("main", {})
    wind = data.get("wind", {})

    desc = str(weather.get("description", "—")).capitalize()
    temp = main.get("temp")
    feels = main.get("feels_like")
    humid = main.get("humidity")
    wind_s = wind.get("speed")

    parts = [f"🌍 {name}", f"☁️ {desc}"]
    if temp is not None:
        parts.append(f"🌡 Температура: {round(float(temp))}°")
    if feels is not None:
        parts.append(f"🤔 Ощущается как: {round(float(feels))}°")
    if humid is not None:
        parts.append(f"💧 Влажность: {humid}%")
    if wind_s is not None:
        parts.append(f"🍃 Ветер: {wind_s} м/с")
    return "\n".join(parts)
