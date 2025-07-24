from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes,
    CallbackQueryHandler, MessageHandler, filters
)
import asyncio

TOKEN = "8030062261:AAFnC9AJ_2zvcaqC0LXe5Y3--d2FgxOx-fI"
WEBHOOK_PATH = f"/webhook/{TOKEN}"
WEBHOOK_URL = f"https://sea-2ri6.onrender.com{WEBHOOK_PATH}"

app = Flask(__name__)
application = ApplicationBuilder().token(TOKEN).build()
users = {}

@app.route(WEBHOOK_PATH, methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    asyncio.run(application.process_update(update))
    return "OK"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    users[uid] = {"step": "awaiting_ship_name"}
    await update.message.reply_text(
        "🏴‍☠️ به دنیای دزدان دریایی خوش آمدی!\n\n"
        "لطفا یک اسم انگلیسی برای کشتی‌ات انتخاب کن:"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text.strip()
    if uid not in users or users[uid].get("step") != "awaiting_ship_name":
        return

    if not text.isascii() or not text.isalpha():
        await update.message.reply_text("❌ فقط نام انگلیسی مجاز است. لطفا دوباره تلاش کن:")
        return

    users[uid]["ship_name"] = text
    users[uid]["step"] = "main_menu"

    keyboard = [
        [InlineKeyboardButton("⚔️ شروع بازی", callback_data="play")],
        [InlineKeyboardButton("🛒 فروشگاه", callback_data="shop")]
    ]
    await update.message.reply_text(
        f"✅ کشتی «{text}» ساخته شد!\n\nاز منوی زیر انتخاب کن:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_buttons(update, context):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "play":
        await query.edit_message_text("🎮 بازی هنوز آماده نیست.")
    elif data == "shop":
        await query.edit_message_text("🛒 فروشگاه به زودی راه‌اندازی می‌شود.")

if __name__ == "__main__":
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(handle_buttons))

    async def main():
        await application.bot.delete_webhook()
        await application.bot.set_webhook(WEBHOOK_URL)
        print("Webhook set to:", WEBHOOK_URL)
        app.run(host="0.0.0.0", port=10000)

    asyncio.run(main())
