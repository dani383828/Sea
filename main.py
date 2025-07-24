import logging
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes,
    CallbackQueryHandler, MessageHandler, filters
)

TOKEN = "8030062261:AAFnC9AJ_2zvcaqC0LXe5Y3--d2FgxOx-fI"
WEBHOOK_PATH = f"/webhook/{TOKEN}"
WEBHOOK_URL = f"https://sea-2ri6.onrender.com{WEBHOOK_PATH}"

app = Flask(__name__)
users = {}

logging.basicConfig(level=logging.INFO)
app_telegram = ApplicationBuilder().token(TOKEN).build()

# ✅ فرمان /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    users[uid] = {"step": "awaiting_ship_name"}
    await update.message.reply_text(
        "🏴‍☠️ به دنیای دزدان دریایی خوش اومدی!\n\n"
        "یه اسم انگلیسی برای کشتی‌ت انتخاب کن:"
    )

# ✅ مدیریت پیام برای نام کشتی
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text.strip()
    if uid not in users or users[uid]["step"] != "awaiting_ship_name":
        return

    if not text.isascii() or not text.isalpha():
        await update.message.reply_text("❌ فقط نام انگلیسی مجازه! دوباره تلاش کن:")
        return

    users[uid]["ship_name"] = text
    users[uid]["step"] = "main_menu"

    keyboard = [
        [InlineKeyboardButton("⚔️ شروع بازی", callback_data="play")],
        [InlineKeyboardButton("🛒 فروشگاه", callback_data="shop")],
    ]
    await update.message.reply_text(
        f"✅ کشتی «{text}» ساخته شد!\n\nاز منوی زیر انتخاب کن:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ✅ هندل دکمه‌ها
async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data == "play":
        await query.edit_message_text("🎮 بازی هنوز آماده نیست.")
    elif data == "shop":
        await query.edit_message_text("🛒 فروشگاه به زودی راه‌اندازی میشه.")

# ✅ مسیر وب‌هوک در Flask
@app.post(WEBHOOK_PATH)
async def webhook():
    data = request.get_json()
    update = Update.de_json(data, app_telegram.bot)
    await app_telegram.process_update(update)
    return "OK"

# ✅ اجرای اصلی
if __name__ == "__main__":
    app_telegram.add_handler(CommandHandler("start", start))
    app_telegram.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app_telegram.add_handler(CallbackQueryHandler(handle_buttons))

    # تنظیم وب‌هوک
    import asyncio
    async def setup():
        await app_telegram.bot.delete_webhook()
        await app_telegram.bot.set_webhook(WEBHOOK_URL)
        print("✅ Webhook set:", WEBHOOK_URL)

    asyncio.run(setup())

    # اجرای Flask روی پورت 10000
    app.run(host="0.0.0.0", port=10000)
