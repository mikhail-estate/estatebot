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

# --- Обработчики команд ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Я помогу получить чек-лист для приёмки квартиры.\n\n"
        "Как вас зовут? (Только имя)"
    )
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
                await update.message.reply_document(
                    document=file,
                    caption="✅ Вот ваш чек-лист! Проверьте перед приёмкой."
                )
        except Exception as e:
            logger.error(f"Ошибка отправки PDF: {e}")
            await update.message.reply_text("⚠️ Чек-лист временно недоступен. Попробуйте позже!")
        
        admin_msg = (
            "📋 Новая заявка:\n"
            f"👤 Имя: {context.user_data['name']}\n"
            f"📞 Телефон: {context.user_data['phone']}\n"
            f"📍 Район: {context.user_data['area']}\n"
            f"🎯 Цель: {context.user_data['goal']}\n"
            f"🏦 Ипотека: {context.user_data['mortgage']}"
        )
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=admin_msg
        )
        return ConversationHandler.END
    
    else:
        await update.message.reply_text(
            "❌ Нужно отправить номер через кнопку!\n\n"
            "Нажмите «📞 Отправить номер» ниже:",
            reply_markup=ReplyKeyboardMarkup(
                [[KeyboardButton("📞 Отправить номер", request_contact=True)]],
                resize_keyboard=True
            )
        )
        return PHONE

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚫 Диалог прерван. Начните заново: /start")
    return ConversationHandler.END

# --- Решение для Render ---
async def run_server():
    """Минимальный HTTP-сервер для Render"""
    async def handle(request):
        return web.Response(text="OK")

    app = web.Application()
    app.router.add_get('/health', handle)
    
    port = int(os.getenv("PORT", 8080))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"Сервер запущен на порту {port}")
    return runner

async def run_bot():
    # Запускаем сервер для Render
    server = await run_server()
    
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
    
    # Запуск с защитой от конфликтов
    await app.initialize()
    await app.start()
    await app.updater.start_polling(
        drop_pending_updates=True,
        timeout=30,
        allowed_updates=Update.ALL_TYPES
    )
    
    logger.info("Бот запущен и готов к работе")
    
    # Бесконечный цикл
    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        pass
    finally:
        await app.stop()
        await server.cleanup()

if __name__ == '__main__':
    try:
        asyncio.run(run_bot())
    except Exception as e:
        logger.error(f"Фатальная ошибка: {e}")