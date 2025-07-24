import os
import logging
import asyncio
import random
import sqlite3
from fastapi import FastAPI, Request
from telegram import (
    InlineKeyboardButton, InlineKeyboardMarkup, Update
)
from telegram.ext import (
    Application, CallbackContext, CommandHandler, CallbackQueryHandler, ContextTypes
)

TOKEN = "توکن رباتتو اینجا بزار"
ADMIN_ID = 5542927340  # آیدی عددی ادمین
WEBHOOK_URL = "https://sea-2ri6.onrender.com/webhook"  # آدرس درست سایتت

# ⚙️ راه‌اندازی لاگ‌ها
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 📦 دیتابیس
def init_db():
    conn = sqlite3.connect("pirate.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    gold INTEGER DEFAULT 100,
                    cannonballs INTEGER DEFAULT 1,
                    invited_by INTEGER DEFAULT NULL,
                    hidden_stage_code INTEGER DEFAULT 0
                )''')
    conn.commit()
    conn.close()
    logger.info("Database initialized successfully")

init_db()

# 💾 ابزارهای دیتابیس
def get_user(user_id):
    conn = sqlite3.connect("pirate.db")
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = c.fetchone()
    if not user:
        c.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()
        c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = c.fetchone()
    conn.close()
    return user

def update_user(user_id, **kwargs):
    conn = sqlite3.connect("pirate.db")
    c = conn.cursor()
    for key, value in kwargs.items():
        c.execute(f"UPDATE users SET {key} = ? WHERE user_id = ?", (value, user_id))
    conn.commit()
    conn.close()

# 🎯 منوی اصلی
def main_menu():
    buttons = [
        [InlineKeyboardButton("🏴‍☠️ حمله با توپ", callback_data="attack")],
        [InlineKeyboardButton("💰 وضعیت من", callback_data="profile")],
        [InlineKeyboardButton("🛒 فروشگاه", callback_data="shop")],
        [InlineKeyboardButton("🕵️ مرحله پنهان", callback_data="hidden")],
    ]
    return InlineKeyboardMarkup(buttons)

# 🪙 دکمه برگشت
def back_button():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🏴 بازگشت به منو", callback_data="main_menu")]])

# ▶️ /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    get_user(user.id)
    text = f"""🏴‍☠️ سلام {user.first_name}!
به دنیای دزدان دریایی خوش اومدی!

با توپ شلیک کن، طلا غارت کن و توی مرحله پنهان جایزه ببر!
"""
    await update.message.reply_text(text, reply_markup=main_menu())

# 📲 هندلر منوی اینلاین
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    get_user(user_id)

    if query.data == "main_menu":
        await query.edit_message_text("🏴‍☠️ منوی اصلی:", reply_markup=main_menu())

    elif query.data == "attack":
        user = get_user(user_id)
        cannonballs = user[2]
        if cannonballs <= 0:
            await query.edit_message_text(
                "توپ نداری! برو فروشگاه بخر 🛒",
                reply_markup=back_button()
            )
            return

        reward = random.choice([0, 20, 50, 100, 200])
        gold = user[1] + reward
        update_user(user_id, gold=gold, cannonballs=cannonballs - 1)

        await query.edit_message_text(
            f"💥 شلیک کردی و {reward} طلا به دست آوردی!",
            reply_markup=back_button()
        )

    elif query.data == "profile":
        user = get_user(user_id)
        await query.edit_message_text(
            f"🧾 پروفایل شما:\n\n"
            f"💰 طلا: {user[1]}\n"
            f"🔥 توپ: {user[2]}\n",
            reply_markup=back_button()
        )

    elif query.data == "shop":
        buttons = [
            [InlineKeyboardButton("1 توپ = 10 طلا", callback_data="buy_cannon")],
            [InlineKeyboardButton("🏴 بازگشت", callback_data="main_menu")]
        ]
        await query.edit_message_text("🛒 فروشگاه:", reply_markup=InlineKeyboardMarkup(buttons))

    elif query.data == "buy_cannon":
        user = get_user(user_id)
        if user[1] < 10:
            await query.edit_message_text("💢 طلات کمه! حداقل 10 طلا لازم داری.", reply_markup=back_button())
        else:
            update_user(user_id, gold=user[1] - 10, cannonballs=user[2] + 1)
            await query.edit_message_text("✅ توپ خریدی!", reply_markup=back_button())

    elif query.data == "hidden":
        user = get_user(user_id)
        if user[4] != 0:
            await query.edit_message_text("❌ قبلاً وارد مرحله پنهان شدی.", reply_markup=back_button())
        elif user[1] < 50:
            await query.edit_message_text("💸 برای ورود به مرحله پنهان ۵۰ طلا لازم داری.", reply_markup=back_button())
        else:
            secret_code = random.randint(1, 300)
            update_user(user_id, gold=user[1] - 50, hidden_stage_code=secret_code)
            await query.edit_message_text(
                "🤫 وارد مرحله پنهان شدی!\n\nیک عدد بین 1 تا 300 حدس بزن. فقط یک شانس داری.",
                reply_markup=back_button()
            )
            context.user_data["guess_mode"] = True

# 🤔 هندلر پیام متنی (حدس عدد)
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)

    if context.user_data.get("guess_mode"):
        try:
            guess = int(update.message.text)
            if not (1 <= guess <= 300):
                raise ValueError
        except ValueError:
            await update.message.reply_text("عدد نامعتبر! عددی بین 1 تا 300 بفرست.")
            return

        secret_code = user[4]
        context.user_data["guess_mode"] = False
        update_user(user_id, hidden_stage_code=0)

        if guess == secret_code:
            update_user(user_id, cannonballs=user[2] + 1)
            await update.message.reply_text(
                f"🎉 درست گفتی! جایزه‌ات: 1 توپ رایگان!",
                reply_markup=main_menu()
            )
        else:
            await update.message.reply_text(
                f"❌ اشتباه گفتی. عدد درست {secret_code} بود.",
                reply_markup=main_menu()
            )
    else:
        await update.message.reply_text("از منوی اصلی یکی رو انتخاب کن:", reply_markup=main_menu())

# ✅ Webhook با FastAPI برای Render
@app.on_event("startup")
async def startup():
    logger.info("Starting bot via webhook...")
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    await application.bot.set_webhook(f"{BASE_WEBHOOK_URL}/webhook")
    app.bot_app = application
    logger.info("Bot is ready.")

@app.post("/webhook")
async def telegram_webhook(req: Request):
    body = await req.body()
    await app.bot_app.update_queue.put(Update.de_json(json.loads(body), app.bot_app.bot))
    return Response(status_code=200)

# 🚀 اجرای FastAPI (فقط در صورت اجرا مستقیم)
if __name__ == "__main__":
    import uvicorn
    logger.info("Database initialized successfully")
    uvicorn.run("main:app", host="0.0.0.0", port=10000)
    app = FastAPI()
