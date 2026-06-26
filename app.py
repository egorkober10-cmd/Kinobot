import os
import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from flask import Flask, request

# ===== НАСТРОЙКИ =====
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Берем ключи из переменных окружения
BOT_TOKEN = os.environ.get("BOT_TOKEN")
KINOPOISK_API_KEY = os.environ.get("KINOPOISK_API_KEY")

if not BOT_TOKEN or not KINOPOISK_API_KEY:
    logging.error("❌ Ошибка: BOT_TOKEN или KINOPOISK_API_KEY не заданы!")

app = Flask(__name__)

# ===== ФУНКЦИЯ ПОИСКА ФИЛЬМА =====
def search_movie(title):
    logging.info(f"🔍 Поиск фильма: {title}")
    
    # Пробуем два варианта URL
    urls = [
        f"https://api.kinopoisk.dev/v1.4/movie/search?query={title}&limit=1",
        f"https://api.kinopoisk.dev/v1.4/movie?query={title}&limit=1"
    ]
    
    headers = {"X-API-KEY": KINOPOISK_API_KEY}
    
    for url in urls:
        try:
            logging.info(f"📡 Запрос к: {url}")
            response = requests.get(url, headers=headers)
            logging.info(f"📊 Статус ответа: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                logging.info(f"📦 Данные получены: {data.keys() if isinstance(data, dict) else 'не словарь'}")
                
                if data.get("docs") and len(data["docs"]) > 0:
                    movie = data["docs"][0]
                    result = {
                        "name": movie.get("name", "Неизвестно"),
                        "year": movie.get("year", "Неизвестно"),
                        "rating": movie.get("rating", {}).get("kp", "Нет рейтинга"),
                        "description": movie.get("description", "Описание отсутствует"),
                        "poster": movie.get("poster", {}).get("url", None)
                    }
                    logging.info(f"✅ Фильм найден: {result['name']}")
                    return result
            else:
                logging.warning(f"⚠️ Ошибка {response.status_code}: {response.text}")
        except Exception as e:
            logging.error(f"❌ Ошибка при запросе к {url}: {e}")
    
    logging.warning(f"❌ Фильм не найден: {title}")
    return None

# ===== КОМАНДА /start =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.info(f"📩 Команда /start от {update.effective_user.first_name}")
    keyboard = [
        [InlineKeyboardButton("🎬 Поиск фильма", switch_inline_query_current_chat="")],
        [InlineKeyboardButton("📋 Топ-10 фильмов", callback_data="top")],
        [InlineKeyboardButton("🎭 По жанру", callback_data="genre")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"🍿 Привет, {update.effective_user.first_name}!\n\n"
        "Я твой личный кинотеатр. Вот что я умею:\n"
        "• Найти фильм по названию\n"
        "• Показать топ-10 лучших\n"
        "• Подобрать по жанру\n\n"
        "Просто напиши название фильма, и я найду его! 🎬",
        reply_markup=reply_markup
    )
    logging.info("✅ Ответ на /start отправлен")

# ===== ОБРАБОТЧИК ТЕКСТА =====
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    logging.info(f"📩 Получено сообщение: {user_text}")
    
    try:
        await update.message.reply_text("🔍 Ищу фильм... Подождите секунду!")
        logging.info("✅ Отправил сообщение 'Ищу...'")
        
        movie_data = search_movie(user_text)
        logging.info(f"📽️ Результат поиска: {'найден' if movie_data else 'не найден'}")
        
        if movie_data:
            rating = movie_data["rating"]
            rating_stars = "⭐" * min(5, int(rating)) if isinstance(rating, (int, float)) and rating > 0 else "Нет рейтинга"
            text = f"🎥 *{movie_data['name']}*\n"
            text += f"📅 {movie_data['year']} год\n"
            text += f"⭐ Рейтинг: {rating} {rating_stars}\n\n"
            text += f"📝 {movie_data['description'][:500]}..."
            
            keyboard = [
                [InlineKeyboardButton("🎞️ Смотреть онлайн", url="https://www.kinopoisk.ru/film/")],
                [InlineKeyboardButton("🔍 Найти другой фильм", switch_inline_query_current_chat="")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            if movie_data["poster"]:
                await update.message.reply_photo(
                    photo=movie_data["poster"],
                    caption=text,
                    parse_mode="Markdown",
                    reply_markup=reply_markup
                )
                logging.info("✅ Отправлен постер с описанием")
            else:
                await update.message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)
                logging.info("✅ Отправлен текст без постера")
        else:
            await update.message.reply_text(
                "😕 Фильм не найден. Попробуйте написать название точнее.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔍 Попробовать снова", switch_inline_query_current_chat="")]
                ])
            )
            logging.info("✅ Отправлено сообщение 'Фильм не найден'")
    except Exception as e:
        logging.error(f"💥 Критическая ошибка в handle_message: {e}")
        await update.message.reply_text("⚠️ Произошла ошибка. Попробуйте позже.")

# ===== СОЗДАЁМ БОТА =====
application = Application.builder().token(BOT_TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# ===== МАРШРУТЫ FLASK =====
@app.route("/")
def index():
    return "✅ Бот работает на Render!"

@app.route("/health")
def health():
    return "OK"

@app.route(f"/webhook/{BOT_TOKEN}", methods=["POST"])
def webhook():
    try:
        update = Update.de_json(request.get_json(force=True), application.bot)
        application.process_update(update)
        return "ok", 200
    except Exception as e:
        logging.error(f"Webhook error: {e}")
        return "error", 500

# ===== УСТАНОВКА WEBHOOK =====
def set_webhook():
    webhook_url = f"{os.environ.get('RENDER_EXTERNAL_URL', '')}/webhook/{BOT_TOKEN}"
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={webhook_url}"
    try:
        response = requests.get(url)
        logging.info(f"✅ Webhook set to: {webhook_url} - {response.json()}")
    except Exception as e:
        logging.error(f"❌ Failed to set webhook: {e}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    set_webhook()
    app.run(host="0.0.0.0", port=port)
