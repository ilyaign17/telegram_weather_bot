import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, filters, MessageHandler
from telegram import ReplyKeyboardMarkup, KeyboardButton

from .weather import fetch_weather, pretty_weather
from .config import settings  # берем токен из настроек
from .db import init_db, add_favorite, remove_favorite, list_favorites



# 1) Настроим логирование, чтобы видеть, что происходит при запуске/ошибках
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# 2) Общий текст помощи (удобно хранить в одной константе)
HELP = (
    "Я бот погоды (в разработке). Команды:\n"
    "/start — приветствие\n"
    "/help — помощь\n"
    "/weather {город} — погода в выбранном городе\n"
    "Или просто отправь свой город в виде сообщения"
)

FAV_BUTTON_TEXT = "⭐ Избранное"

MAIN_KB = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(FAV_BUTTON_TEXT)],  # одна кнопка в первой строке
    ],
    resize_keyboard=True,   # подгонять под экран
    one_time_keyboard=False # оставить клавиатуру постоянно
)


# 3) Хендлеры команд (PTB v21 требует async-функции)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! " + HELP,
        reply_markup=MAIN_KB
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP)

async def weather_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает команду /weather <город>.
    Пример: /weather Москва
    """
    # 1) Проверяем, что пользователь передал аргументы
    if not context.args:
        await update.message.reply_text("Укажи город: /weather <город>")
        return

    # 2) Собираем город из слов после команды (поддержка многословных названий)
    city = " ".join(context.args).strip()

    # 3) Вызываем OpenWeather (асинхронно) и получаем JSON или None
    data = await fetch_weather(city)

    # 4) Обрабатываем неуспех: сеть/город не найден/ошибка ключа и т.п.
    if not data:
        await update.message.reply_text("Не удалось найти погоду для этого города 😕")
        return

    # 5) Превращаем JSON в красивый текст и отправляем
    text = pretty_weather(data)
    await update.message.reply_text(text)

async def text_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Если пользователь прислал обычный текст (не команду),
    считаем это названием города и пытаемся показать погоду.
    """
    if not update.message or not update.message.text:
        return

    city = update.message.text.strip()
    # Небольшая защита от слишком коротких/подозрительных сообщений
    if not city or city.startswith("/") or len(city) < 2:
        return

    # если нажата наша кнопка — эквивалент /fav
    if city == FAV_BUTTON_TEXT:
        # переиспользуем логику fav_cmd
        return await fav_cmd(update, context)


    data = await fetch_weather(city)
    if not data:
        await update.message.reply_text("Не нашёл такой город. Попробуй ещё раз.")
        return

    await update.message.reply_text(pretty_weather(data))

async def add_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /add <город> — добавляет город в избранное текущего пользователя.
    """
    if not context.args:
        await update.message.reply_text("Укажи город: /add <город>")
        return

    city = " ".join(context.args).strip()
    ok = add_favorite(update.effective_user.id, city)
    if ok:
        await update.message.reply_text(f"✅ Добавил {city} в избранное")
    else:
        await update.message.reply_text("⚠️ Уже в избранном или ошибка ввода")

async def remove_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /remove <город> — удаляет город из избранного.
    """
    if not context.args:
        await update.message.reply_text("Укажи город: /remove <город>")
        return

    city = " ".join(context.args).strip()
    ok = remove_favorite(update.effective_user.id, city)
    if ok:
        await update.message.reply_text(f"🗑 Удалил {city} из избранного")
    else:
        await update.message.reply_text("⚠️ Такого города нет в избранном")

async def list_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /list — показывает все избранные города пользователя.
    """
    favs = list_favorites(update.effective_user.id)
    if not favs:
        await update.message.reply_text("⭐ Пока нет избранных. Добавь: /add <город>")
        return

    text = "⭐ Избранные города:\n" + "\n".join(f"• {c}" for c in favs)
    await update.message.reply_text(text)

async def fav_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /fav — показывает погоду по всем избранным городам пользователя.
    """
    user_id = update.effective_user.id
    favs = list_favorites(user_id)

    if not favs:
        await update.message.reply_text("⭐ Пока нет избранных. Добавь: /add <город>")
        return

    lines = ["⭐ Погода в избранных:"]
    # Идём по городам последовательно (просто и надёжно)
    for city in favs:
        data = await fetch_weather(city)
        if not data:
            lines.append(f"\n• {city}\n  (не удалось получить данные)")
            continue
        # Используем pretty_weather и чуть-чуть форматируем
        text = pretty_weather(data)
        # Чтобы делать компактнее, заменим первую строку "🌍 {name}" на "• {name}"
        first_line, *rest = text.splitlines()
        name = first_line.replace("🌍", "•").strip()
        lines.append("\n" + name)
        for r in rest:
            lines.append(r)

    # Telegram ограничивает сообщение ~4096 символами — на наш объём хватит.
    await update.message.reply_text("\n".join(lines))


async def on_startup(app):
    # создаём таблицы, если их ещё нет
    init_db()

# 4) Точка входа: собираем приложение и запускаем long polling
def main():
    # Защита от забывчивости: без токена запускать нельзя
    if not settings.telegram_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN пуст. Заполни .env!")

    # Application — «движок» бота
    app = ApplicationBuilder().token(settings.telegram_token).build()
    app.post_init = on_startup

    # Регистрируем команды → говорим PTB, какие функции вызывать
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("weather", weather_cmd))

    app.add_handler(CommandHandler("add", add_cmd))
    app.add_handler(CommandHandler("remove", remove_cmd))
    app.add_handler(CommandHandler("list", list_cmd))
    app.add_handler(CommandHandler("fav", fav_cmd))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_city))

    logger.info("Bot starting (long polling)...")
    # long polling = регулярно спрашиваем у Telegram «есть ли обновления»
    app.run_polling(drop_pending_updates=True)
    # drop_pending_updates=True — не обрабатывать старую очередь апдейтов при первом старте

# Позволяет запускать «python -m src.bot»
if __name__ == "__main__":
    main()
