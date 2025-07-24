import logging
import random
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, ApplicationBuilder, CommandHandler,
    CallbackQueryHandler, MessageHandler, ContextTypes, filters
)

# 🔐 اطلاعات کلیدی
TOKEN = "8030062261:AAFnC9AJ_2zvcaqC0LXe5Y3--d2FgxOx-fI"
ADMIN_ID = 5542927340
WEBHOOK_PATH = f"/webhook/{TOKEN}"
WEBHOOK_URL = f"https://sea-2ri6.onrender.com{WEBHOOK_PATH}"

# ⚙️ ساخت اپلیکیشن Flask و Telegram
app = Flask(__name__)
users = {}

# ⚙️ تنظیم لاگ
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
application: Application = ApplicationBuilder().token(TOKEN).build()


# ✅ /start - ورود به بازی
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    users[uid] = {
        "step": "awaiting_ship_name",
        "ships": set()
    }
    await update.message.reply_text(
        "🏴‍☠️ به دنیای دزدان دریایی خوش اومدی، کاپیتان!\n\n"
        "🚢 برای شروع، یه اسم انگلیسی برای کشتی‌ت انتخاب کن:"
    )


# 📥 مدیریت پیام‌ها (برای نام‌گذاری کشتی)
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text.strip()
    if uid not in users:
        return

    user = users[uid]
    if user["step"] == "awaiting_ship_name":
        if not text.isascii() or not text.isalpha() or text.lower() in ["start", "menu"] or text in user["ships"]:
            await update.message.reply_text("❌ فقط نام انگلیسی غیرتکراری مجازه! یه اسم دیگه بده:")
            return

        user["ship_name"] = text
        user["ships"].add(text)
        user["step"] = "main_menu"

        # دکمه‌های اصلی
        buttons = [
            [InlineKeyboardButton("⚔️ شروع بازی", callback_data="play")],
            [InlineKeyboardButton("🛒 فروشگاه", callback_data="shop")],
            [InlineKeyboardButton("🏆 برترین ناخدایان", callback_data="top")],
            [InlineKeyboardButton("🔍 جستجوی کاربران", callback_data="search")],
            [InlineKeyboardButton("🚢 اطلاعات کشتی", callback_data="info")],
            [InlineKeyboardButton("⚡ انرژی جنگجویان", callback_data="energy")],
        ]

        await update.message.reply_text(
            f"✅ کشتی «{text}» با موفقیت ساخته شد!\n\nاز منوی زیر انتخاب کن:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )


# 📌 هندلر دکمه‌ها
async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = query.from_user.id
    await query.answer()

    if uid not in users:
        return

    data = query.data
    if data == "play":
        await query.edit_message_text("🎮 بخش نبرد هنوز در حال توسعه‌ست...")
    elif data == "shop":
        await query.edit_message_text("🛒 فروشگاه به‌زودی فعال میشه...")
    elif data == "top":
        await query.edit_message_text("🏆 لیست برترین‌ها به‌زودی نمایش داده میشه...")
    elif data == "search":
        await query.edit_message_text("🔍 جستجوی کاربران به‌زودی فعال میشه...")
    elif data == "info":
        ship = users[uid].get("ship_name", "نامشخص")
        await query.edit_message_text(f"🚢 نام کشتی شما: {ship}")
    elif data == "energy":
        await query.edit_message_text("⚡ انرژی جنگجویان: 90% (پیش‌فرض)")


# 🛰 وب‌هوک
@app.route(WEBHOOK_PATH, methods=["POST"])
def telegram_webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.update_queue.put_nowait(update)
    return "OK"


# 🚀 اجرای برنامه
if __name__ == "__main__":
    # افزودن هندلرها
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(handle_buttons))

    # راه‌اندازی webhook
    application.run_webhook(
        listen="0.0.0.0",
        port=10000,
        webhook_url=WEBHOOK_URL
    )
