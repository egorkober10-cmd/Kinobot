import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ===== ВАШИ КЛЮЧИ =====
# Ключ бота от @BotFather
BOT_TOKEN = "8841912812:AAEJ4T52xeFPXwDPJk85-HaqWCjS8AEIbQY"

# Ключ для API Кинопоиска (получили на api.kinopoisk.dev)
KINOPOISK_API_KEY = "PRBMPGQ-754MP5N-K5Y8A55-BYZY4W9"

# ===== НАСТРОЙКИ =====
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# ===== ФУНКЦИЯ ПОИСКА ФИЛЬМА =====
def search_movie(title):
    url = "https://api.kinopoisk.dev/v1.4/movie/search"
    headers = {
        "X-API-KEY": KINOPOISK_API_KEY
    }
    params = {
        "query": title,
        "limit": 1  # Показываем только первый результат
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        data = response.json()
        
        if data.get("docs") and len(data["docs"]) > 0:
            movie = data["docs"][0]
            return {
                "name": movie.get("name", "Неизвестно"),
                "year": movie.get("year", "Неизвестно"),
                "rating": movie.get("rating", {}).get("kp", "Нет рейтинга"),
                "description": movie.get("description", "Описание отсутствует"),
                "poster": movie.get("poster", {}).get("url", None)
            }
        return None
    except Exception as e:
        logging.error(f"Ошибка поиска: {e}")
        return None

# ===== КОМАНДА /start =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

# ===== ОБРАБОТЧИК ТЕКСТА (ПОИСК ФИЛЬМА) =====
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    
    # Показываем, что бот думает
    await update.message.reply_text("🔍 Ищу фильм... Подождите секунду!")
    
    movie_data = search_movie(user_text)
    
    if movie_data:
        # Формируем красивое сообщение
        rating = movie_data["rating"]
        rating_stars = "⭐" * min(5, int(rating)) if isinstance(rating, (int, float)) and rating > 0 else "Нет рейтинга"
        
        text = f"🎥 *{movie_data['name']}*\n"
        text += f"📅 {movie_data['year']} год\n"
        text += f"⭐ Рейтинг: {rating} {rating_stars}\n\n"
        text += f"📝 {movie_data['description'][:500]}..."
        
        # Клавиатура с кнопками
        keyboard = [
            [InlineKeyboardButton("🎞️ Смотреть онлайн", url="https://www.kinopoisk.ru/film/")],
            [InlineKeyboardButton("🔍 Найти другой фильм", switch_inline_query_current_chat="")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Отправляем постер (если есть)
        if movie_data["poster"]:
            await update.message.reply_photo(
                photo=movie_data["poster"],
                caption=text,
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                text,
                parse_mode="Markdown",
                reply_markup=reply_markup
)
    else:
        await update.message.reply_text(
            "😕 Фильм не найден. Попробуйте написать название точнее или проверьте орфографию.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔍 Попробовать снова", switch_inline_query_current_chat="")]
            ])
        )

# ===== ЗАПУСК БОТА =====
def main():
    print("🚀 Бот запускается...")
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("✅ Бот активен! Нажмите Ctrl+C для остановки.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
