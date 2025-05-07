import logging
import os  # Импортируем модуль os
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler
)

# Включаем логирование
logging.basicConfig(level=logging.INFO)

# Этапы
NAME, AREA, GOAL, MORTGAGE, PHONE = range(5)

# Твой Telegram chat_id
ADMIN_CHAT_ID = 992184941

# Старт
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Привет! Я помогу тебе получить чек-лист по приёмке квартиры.\n\nКак тебя зовут?")
    return NAME

# Имя
async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text
    await update.message.reply_text("🗺️ В каком районе или ЖК ты покупаешь квартиру?")
    return AREA

# Район
async def get_area(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["area"] = update.message.text
    await update.message.reply_text("🏠 Покупаешь для себя или под инвестиции?")
    return GOAL

# Цель
async def get_goal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["goal"] = update.message.text
    await update.message.reply_text("💸 Есть ли ипотека?")
    return MORTGAGE

# Ипотека
async def get_mortgage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mortgage"] = update.message.text
    phone_btn = KeyboardButton("📞 Отправить номер", request_contact=True)
    markup = ReplyKeyboardMarkup([[phone_btn]], resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(
        "📲 Пожалуйста, нажми кнопку «Отправить номер», чтобы поделиться номером телефона.\n\n✍️ Ввод вручную не принимается.",
        reply_markup=markup
    )
    return PHONE

# Телефон + отправка PDF + отправка администратору
async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.contact:
        phone = update.message.contact.phone_number
        context.user_data["phone"] = phone

        # Отправка PDF пользователю
        await update.message.reply_text("✅ Спасибо! Вот твой чек-лист по приёмке квартиры.")
        try:
            with open("checklist.pdf", "rb") as pdf_file:
                await update.message.reply_document(document=pdf_file)
        except Exception as e:
            logging.error(f"Ошибка при отправке PDF: {e}")
            await update.message.reply_text(f"❌ Не удалось отправить файл. Ошибка: {e}")

        # Отправка тебе анкеты
        message = (
            "📩 *Новая заявка:*\n"
            f"👤 Имя: {context.user_data['name']}\n"
            f"📍 Район/ЖК: {context.user_data['area']}\n"
            f"🎯 Цель: {context.user_data['goal']}\n"
            f"💰 Ипотека: {context.user_data['mortgage']}\n"
            f"📞 Телефон: {context.user_data['phone']}"
        )
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=message, parse_mode="Markdown")

        return ConversationHandler.END
    else:
        # Если пользователь не отправил контакт, а ввёл вручную
        await update.message.reply_text("❗ Пожалуйста, не вводи номер вручную. Нажми кнопку «Отправить номер».")
        phone_btn = KeyboardButton("📞 Отправить номер", request_contact=True)
        markup = ReplyKeyboardMarkup([[phone_btn]], resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text(
            "📲 Пожалуйста, нажми кнопку «Отправить номер», чтобы поделиться номером телефона.\n\n✍️ Ввод вручную не принимается.",
            reply_markup=markup
        )
        return PHONE

# Главная функция
def main():
    app = ApplicationBuilder().token("7318408114:AAFz7ZrQN6GuT0WJcCMplTvqVL2PLISTrn8").build()  # Указываем токен напрямую

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            AREA: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_area)],
            GOAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_goal)],
            MORTGAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_mortgage)],
            PHONE: [
                MessageHandler(filters.CONTACT, get_phone),
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)
            ],
        },
        fallbacks=[],
    )

    app.add_handler(conv_handler)
    app.run_polling()

if __name__ == "__main__":
    main()
