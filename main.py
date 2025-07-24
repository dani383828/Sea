import os
from fastapi import FastAPI, Request
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, ContextTypes

# مشخصات ربات
TOKEN = "8030062261:AAFnC9AJ_2zvcaqC0LXe5Y3--d2FgxOx-fI"
BOT = Bot(token=TOKEN)
ADMIN_ID = 5542927340
TRX_ADDRESS = "TJ4xrwKJzKjk6FgKfuuqwah3Az5Ur22kJb"

# ساخت اپلیکیشن تلگرام
application = Application.builder().token(TOKEN).build()

# هندلر استارت
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🏴‍☠️ به دنیای دزدان دریایی خوش اومدی کاپیتان!\n\n"
        "برای شروع بازی دستور /play رو بفرست."
    )

# ثبت هندلر
application.add_handler(CommandHandler("start", start))

# ساخت FastAPI
app = FastAPI()

@app.post(f"/webhook/{TOKEN}")
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, BOT)
    await application.process_update(update)
    return {"ok": True}

# اجرای لوکال یا روی Render
if __name__ == "__main__":
    import uvicorn
    print("Server starting...")
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
