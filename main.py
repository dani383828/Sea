import os
import logging
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, ContextTypes,
)

TOKEN = "8030062261:AAFnC9AJ_2zvcaqC0LXe5Y3--d2FgxOx-fI"
WEBHOOK_PATH = f"/webhook/{TOKEN}"
WEBHOOK_URL = f"https://sea-2ri6.onrender.com{WEBHOOK_PATH}"

# ⚙️ لاگ‌گیری
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# 📦 FastAPI app
app = FastAPI()

# 🎯 ساخت ربات تلگرام
application = Application.builder().token(TOKEN).build()

# 📌 هندلر برای /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🏴‍☠️ خوش اومدی به دنیای دزدان دریایی!")

# 🔗 ثبت هندلر
application.add_handler(CommandHandler("start", start))

# 🔁 وب‌هوک تلگرام
@app.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, application.bot)
    await application.update_queue.put(update)
    return {"ok": True}

# 🔥 زمان بالا آمدن سرور
@app.on_event("startup")
async def on_startup():
    # راه‌اندازی بات
    await application.bot.set_webhook(url=WEBHOOK_URL)
    print("✅ Webhook set:", WEBHOOK_URL)
    await application.initialize()
    await application.start()
    await application.updater.start_polling()

# 🛑 هنگام خاموشی
@app.on_event("shutdown")
async def on_shutdown():
    await application.updater.stop()
    await application.stop()
    await application.shutdown()
