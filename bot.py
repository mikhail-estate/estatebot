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
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Константы
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
NAME, AREA, GOAL, MORTGAGE, PHONE = range(5)

# --- Обработчики ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало диалога."""
    await update.message.reply_text(
        "👋 Привет! Я помогу получить чек-лист для приёмки квартиры.\n\n"
        "Как вас зовут? (Только имя)"
    )
    return NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохраняем имя и спрашиваем район."""
    context.user_data['name'] = update.message.text
    await update.message.reply_text("🏙 В каком районе или ЖК квартира?")
    return AREA

async def get_area(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохраняем район и уточняем цель покупки."""
    context.user_data['area'] = update.message.text
    reply_keyboard = [["Для себя", "Инвестиция"]]
    await update.message.reply_text(
        "🏠 Покупаете для себя или как инвестицию?",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )
    return GOAL

async def get_goal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохраняем цель и спрашиваем про ипотеку."""
    context.user_data['goal'] = update.message.text
    await update.message.reply_text("💵 Будете оформлять ипотеку? (Да/Нет)")
    return MORTGAGE

async def get_mortgage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохраняем данные об ипотеке и запрашиваем номер ЧЕРЕЗ КНОПКУ."""
    context.user_data['mortgage'] = update.message.text
    
    # Жёсткое требование кнопки (без ручного ввода)
    phone_btn = KeyboardButton("📞 Отправить номер", request_contact=True)
    markup = ReplyKeyboardMarkup([[phone_btn]], resize_keyboard=True)
    
    await update.message.reply_text(
        "📱 Для отправки чек-листа нам нужен ваш номер.\n\n"
        "❗ **Обязательно нажмите кнопку ниже** — ручной ввод не принимается!",
        reply_markup=markup,
        parse_mode="Markdown"
    )
    return PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатываем номер ТОЛЬКО через кнопку, иначе переспрашиваем."""
    if update.message.contact:
        # Успех: сохраняем номер
        context.user_data['phone'] = update.message.contact.phone_number
        
        # Отправляем чек-лист
        try:
            with open("checklist.pdf", "rb") as file:
                await update.message.reply_document(
                    document=file,
                    caption="✅ Вот ваш чек-лист! Проверьте перед приёмкой."
                )
        except Exception as e:
            logger.error(f"Ошибка PDF: {e}")
            await update.message.reply_text("⚠️ Файл временно недоступен. Попробуйте позже!")
        
        # Уведомление админу
        admin_msg = (
            "📋 *Новая заявка:*\n"
            f"👤 Имя: {context.user_data['name']}\n"
            f"📞 Телефон: `{context.user_data['phone']}`\n"
            f"📍 Район: {context.user_data['area']}\n"
            f"🎯 Цель: {context.user_data['goal']}\n"
            f"🏦 Ипотека: {context.user_data['mortgage']}"
        )
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=admin_msg,
            parse_mode="Markdown"
        )
        
        return ConversationHandler.END
    
    else:
        # Если ввели вручную — повторяем запрос
        await update.message.reply_text(
            "❌ *Нужно отправить номер через кнопку!*\n\n"
            "Нажмите «📞 Отправить номер» ниже:",
            reply_markup=ReplyKeyboardMarkup(
                [[KeyboardButton("📞 Отправить номер", request_contact=True)]],
                resize_keyboard=True
            ),
            parse_mode="Markdown"
        )
        return PHONE  # Остаёмся в этом же состоянии

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена диалога."""
    await update.message.reply_text("🚫 Диалог прерван. Начните заново: /start")
    return ConversationHandler.END

# --- Запуск ---
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            AREA: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_area)],
            GOAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_goal)],
            MORTGAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_mortgage)],
            PHONE: [
                MessageHandler(filters.CONTACT, get_phone),
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)  # Ловим ручной ввод
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    
    app.add_handler(conv_handler)
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()