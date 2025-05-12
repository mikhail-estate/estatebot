import logging
import os
import asyncio
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler
)
import httpx

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

# Обработчики команд (остаются без изменений)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Привет! Я помогу получить чек-лист для приёмки квартиры.\n\nКак вас зовут?")
    return NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['name'] = update.message.text
    await update.message.reply_text("🏙 В каком районе или ЖК квартира?")
    return AREA

async def get_area(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['area'] = update.message.text
    reply_keyboard = [["Для себя", "Инвестиция"]]
    await update.message.reply_text(
        "🏠 Покупаете для себя или как инвестицию?",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )
    return GOAL

async def get_goal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['goal'] = update.message.text
    await update.message.reply_text("💵 Будете оформлять ипотеку? (Да/Нет)")
    return MORTGAGE

async def get_mortgage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['mortgage'] = update.message.text
    phone_btn = KeyboardButton("📞 Отправить номер", request_contact=True)
    markup = ReplyKeyboardMarkup([[phone_btn]], resize_keyboard=True)
    await update.message.reply_text(
        "📱 Для получения чек-листа нам нужен ваш номер телефона.\n\n"
        "❗ Обязательно нажмите кнопку ниже — ручной ввод не принимается!",
        reply_markup=markup
    )
    return PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.contact:
        context.user_data['phone'] = update.message.contact.phone_number
        try:
            with open("checklist.pdf", "rb") as file:
                await update.message.reply_document(file)
        except Exception as e:
            logger.error(f"Ошибка PDF: {e}")
        return ConversationHandler.END
    else:
        await update.message.reply_text("Пожалуйста, используйте кнопку для отправки номера")
        return PHONE

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Диалог прерван. Начните заново: /start")
    return ConversationHandler.END

# Решение для Render без aiohttp (используем httpx)
async def health_check():
    """Минимальный HTTP-сервер для Render"""
    async def app(scope, receive, send):
        if scope['path'] == '/health':
            await send({
                'type': 'http.response.start',
                'status': 200,
                'headers': [[b'content-type', b'text/plain']]
            })
            await send({
                'type': 'http.response.body',
                'body': b'OK'
            })
    
    port = int(os.getenv("PORT", 8080))
    server = await asyncio.start_server(
        app,
        host='0.0.0.0',
        port=port
    )
    logger.info(f"HTTP-сервер запущен на порту {port}")
    return server

async def run_bot():
    # Запускаем health-check
    server = await health_check()
    
    # Инициализация бота
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Настройка диалога
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            AREA: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_area)],
            GOAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_goal)],
            MORTGAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_mortgage)],
            PHONE: [MessageHandler(filters.CONTACT | filters.TEXT, get_phone)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    
    app.add_handler(conv_handler)
    
    # Запуск
    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
    
    logger.info("Бот запущен")
    
    try:
        while True:
            await asyncio.sleep(3600)
    finally:
        await app.stop()
        server.close()

if __name__ == '__main__':
    try:
        asyncio.run(run_bot())
    except Exception as e:
        logger.error(f"Ошибка: {e}")