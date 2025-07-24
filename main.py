import asyncio
import random
import logging
import sqlite3
from fastapi import FastAPI, Request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CallbackQueryHandler, CommandHandler,
    ContextTypes, MessageHandler, filters
)

# تنظیمات اولیه
BOT_TOKEN = "8030062261:AAFnC9AJ_2zvcaqC0LXe5Y3--d2FgxOx-fI"
ADMIN_ID = 5542927340
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
WEBHOOK_URL = f"https://sea-2ri6.onrender.com{WEBHOOK_PATH}"
SPIN_COST = 50000
HIDDEN_STAGE_COST = 5000
TRX_ADDRESS = "TJ4xrwKJzKjk6FgKfuuqwah3Az5Ur22kJb"

# لاگ‌گیری
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# اتصال به دیتابیس SQLite
conn = sqlite3.connect("pirate.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        balance INTEGER DEFAULT 0,
        hidden_stage INTEGER DEFAULT 0,
        invites INTEGER DEFAULT 0
    )
""")
conn.commit()

# FastAPI App
app = FastAPI()
application = Application.builder().token(BOT_TOKEN).build()

# تابع اضافه کردن یا به‌روزرسانی کاربر
def add_or_update_user(user_id: int):
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    if cursor.fetchone() is None:
        cursor.execute("INSERT INTO users (user_id, balance) VALUES (?, ?)", (user_id, 5))
        conn.commit()

# /start handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    add_or_update_user(user_id)
    await update.message.reply_text(
        "🏴‍☠️ به دنیای دزدان دریایی خوش آمدی، کاپیتان!\n\n"
        "🚢 آماده‌ای کشتی‌تو بسازی و راهی دریا بشی؟\n\n"
        "از منوی پایین استفاده کن."
    )

# وبهوک برای دریافت آپدیت‌ها
@app.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return {"ok": True}

# تنظیم وبهوک در تلگرام
async def set_webhook():
    await application.bot.set_webhook(url=WEBHOOK_URL)

# شروع وبهوک و مقداردهی اولیه اپلیکیشن
@app.on_event("startup")
async def startup_event():
    await application.initialize()
    await application.start()
    await set_webhook()

# پایان وبهوک و خاموش‌کردن اپلیکیشن
@app.on_event("shutdown")
async def shutdown_event():
    await application.stop()
    await application.shutdown()

# ثبت هندلرها
application.add_handler(CommandHandler("start", start))

# -- اینجا کد مربوط به ساخت کشتی و نام‌گذاری --

from telegram.ext import ConversationHandler

SHIP_NAME = 1

# بررسی نام کشتی (انگلیسی، تکراری نباشد، منو و کامند نباشد)
def is_valid_ship_name(name: str) -> bool:
    if not name.isalpha() or not name.isascii():
        return False
    forbidden = ["/start", "/help", "فروشگاه", "استراتژی", "توپ", "دریانوردی"]
    if name.lower() in [f.lower() for f in forbidden]:
        return False
    # بررسی تکراری بودن در دیتابیس
    cursor.execute("SELECT 1 FROM ships WHERE name = ?", (name,))
    if cursor.fetchone() is not None:
        return False
    return True

# ایجاد جدول کشتی‌ها
cursor.execute("""
CREATE TABLE IF NOT EXISTS ships (
    user_id INTEGER PRIMARY KEY,
    name TEXT UNIQUE,
    energy INTEGER DEFAULT 100,
    gold_bags INTEGER DEFAULT 10,
    silver_bars INTEGER DEFAULT 15,
    gems INTEGER DEFAULT 5
)
""")
conn.commit()

async def start_ship_creation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    # اگر قبلاً کشتی ساخته شده بود، پیام بده
    cursor.execute("SELECT name FROM ships WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    if res:
        await update.message.reply_text(f"کشتیت قبلا ساخته شده به اسم: {res[0]}")
        return ConversationHandler.END
    await update.message.reply_text("در حال ساخت کشتی... لطفا کمی صبر کن.")
    # شبیه‌سازی ساخت کشتی
    await asyncio.sleep(2)
    await update.message.reply_text("کشتیت ساخته شد! لطفا نام کشتی (انگلیسی و غیر تکراری) را وارد کن:")
    return SHIP_NAME

async def receive_ship_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    if not is_valid_ship_name(name):
        await update.message.reply_text("نام نامعتبر است. فقط حروف انگلیسی و غیرتکراری بفرست. نام‌های منو و کامندها پذیرفته نیست.")
        return SHIP_NAME
    user_id = update.effective_user.id
    try:
        cursor.execute(
            "INSERT INTO ships (user_id, name) VALUES (?, ?)", (user_id, name)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        await update.message.reply_text("این نام قبلا استفاده شده. نام دیگری انتخاب کن.")
        return SHIP_NAME
    await update.message.reply_text(f"کشتی شما با نام {name} ساخته شد! به منوی بازی خوش آمدی.")
    return ConversationHandler.END

# هندلر ساخت کشتی
ship_creation_handler = ConversationHandler(
    entry_points=[CommandHandler("buildship", start_ship_creation)],
    states={
        SHIP_NAME: [MessageHandler(filters.TEXT & (~filters.COMMAND), receive_ship_name)]
    },
    fallbacks=[]
)

application.add_handler(ship_creation_handler)

# --- ادامه: وب‌هوک و راه‌اندازی سرور ---

@app.post(f"/webhook/{TOKEN}")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()
        update = Update.de_json(data)
        await application.process_update(update)
    except Exception as e:
        print(f"Error processing update: {e}")
    return {"ok": True}

if __name__ == "__main__":
    import uvicorn

    print("Starting server...")
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
