# syntax=docker/dockerfile:1

# 1) Лёгкий официальный образ с Python 3.11
FROM python:3.11-slim

# 2) Рабочая директория внутри контейнера
WORKDIR /app

# 3) Полезные флаги для предсказуемого поведения Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# 4) Устанавливаем зависимости из requirements.txt отдельно (кэш слоёв эффективнее)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 5) Подготовим папку для персистентной БД (на Render/Fly/VPS примонтируем сюда диск)
RUN mkdir -p /data

# 6) Кладём остальной код приложения
COPY . ./

# 7) Команда запуска: как ты запускаешь локально
CMD ["python", "-m", "src.bot"]
