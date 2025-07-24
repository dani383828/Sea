from fastapi import FastAPI, Request
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, ContextTypes
import os

BOT_TOKEN = "8030062261:AAFnC9AJ_2zvcaqC0LXe5Y3--d2FgxOx-fI"
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
WEBHOOK_URL = f"https://sea-2ri6.onrender.com{WEBHOOK_PATH}"

bot = Bot(token=BOT_TOKEN)
app = FastAPI()
application = Application.builder().token(BOT_TOKEN).build()

# فرمان /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("سلام! به ربات دزدان دریایی خوش آمدی 🏴‍☠️")

# ثبت فرمان در ربات
application.add_handler(CommandHandler("start", start))

# Webhook endpoint
@app.post(WEBHOOK_PATH)
async def telegram_webhook(req: Request):
    data = await req.json()
    update = Update.de_json(data, bot)
    await application.process_update(update)
    return {"ok": True}

# هنگام استارت آپ، وب‌هوک تنظیم شود
@app.on_event("startup")
async def on_startup():
    await bot.delete_webhook()
    await bot.set_webhook(url=WEBHOOK_URL)
