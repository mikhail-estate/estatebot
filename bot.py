import logging
import os
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler
)

# Настройка логов
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Константы
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
NAME, AREA, GOAL, MORTGAGE, PHONE = range(5)

# --- Обработчики ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало диалога, запрос имени."""
    await update.message.reply_text(
        "👋 Привет! Я помогу тебе получить чек-лист по приёмке квартиры.\n\n"
        "Как тебя зовут? (Только имя, без фамилии)"
    )
    return NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохранение имени и запрос района."""
    context.user_data["name"] = update.message.text
    await update.message.reply_text("🗺️ В каком районе или ЖК ты покупаешь квартиру?")
    return AREA

async def get_area(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохранение района и уточнение цели."""
    context.user_data["area"] = update.message.text
    reply_keyboard = [["Для себя", "Инвестиция"]]
    await update.message.reply_text(
        "🏠 Покупаешь для себя или под инвестиции?",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )
    return GOAL

async def get_goal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохранение цели и вопрос про ипотеку."""
    context.user_data["goal"] = update.message.text
    await update.message.reply_text("💸 Есть ли ипотека? (Да/Нет)")
    return MORTGAGE

async def get_mortgage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохранение данных об ипотеке и запрос номера через кнопку."""
    context.user_data["mortgage"] = update.message.text
    
    # Жёсткое требование: только кнопка "Отправить номер"
    phone_btn = KeyboardButton("📞 Отправить номер", request_contact=True)
    markup = ReplyKeyboardMarkup([[phone_btn]], resize_keyboard=True, one_time_keyboard=True)
    
    await update.message.reply_text(
        "📲 Для получения чек-листа нам нужен ваш номер телефона.\n\n"
        "❗ **Обязательно нажмите кнопку ниже** — ручной ввод не принимается!",
        reply_markup=markup,
        parse_mode="Markdown"
    )
    return PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка номера телефона и завершение диалога."""
    if not update.message.contact:
        # Если пользователь попытался ввести номер вручную
        await update.message.reply_text(
            "❌ **Нужно отправить номер через кнопку!**\n\n"
            "Нажмите «📞 Отправить номер» ниже:",
            parse_mode="Markdown"
        )
        return PHONE
    
    # Сохранение номера
    context.user_data["phone"] = update.message.contact.phone_number
    
    # Отправка чек-листа
    try:
        with open("checklist.pdf", "rb") as file:
            await update.message.reply_document(
                document=file,
                caption="✅ Вот ваш чек-лист для приёмки квартиры!"
            )
    except Exception as e:
        logger.error(f"Ошибка отправки PDF: {e}")
        await update.message.reply_text("⚠️ Чек-лист временно недоступен. Попробуйте позже!")
    
    # Уведомление админа
    admin_message = (
        "📋 *Новая заявка на чек-лист:*\n"
        f"👤 *Имя:* {context.user_data['name']}\n"
        f"📞 *Телефон:* `{context.user_data['phone']}`\n"
        f"📍 *Район:* {context.user_data['area']}\n"
        f"🎯 *Цель:* {context.user_data['goal']}\n"
        f"🏦 *Ипотека:* {context.user_data['mortgage']}"
    )
    await context.bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=admin_message,
        parse_mode="Markdown"
    )
    
    await update.message.reply_text("Спасибо за обращение! Если остались вопросы — напишите нам.")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена диалога."""
    await update.message.reply_text("❌ Диалог прерван. Начните заново командой /start.")
    return ConversationHandler.END

# --- Запуск ---
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            AREA: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_area)],
            GOAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_goal)],
            MORTGAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_mortgage)],
            PHONE: [
                MessageHandler(filters.CONTACT, get_phone),
                # Блокируем любой текстовый ввод кроме команды /cancel
                MessageHandler(filters.TEXT & ~filters.COMMAND, 
                              lambda u, c: get_phone(u, c) if u.message.contact else None)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    app.add_handler(conv_handler)
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()