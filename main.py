import os
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

# تعریف متغیرهای مهم
TOKEN = "8030062261:AAFnC9AJ_2zvcaqC0LXe5Y3--d2FgxOx-fI"
ADMIN_ID = 5542927340
TRX_ADDRESS = "TJ4xrwKJzKjk6FgKfuuqwah3Az5Ur22kJb"

app = FastAPI()

# ساخت اپلیکیشن تلگرام بوت
application = Application.builder().token(TOKEN).build()

# دستور /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🏴‍☠️ به دنیای دزدان دریایی خوش آمدی، کاپیتان!\n\n"
        "برای شروع بازی /play را بزن."
    )

# ثبت هندلر /start
application.add_handler(CommandHandler("start", start))

# وبهوک برای دریافت آپدیت‌ها
@app.post(f"/webhook/{TOKEN}")
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data)
    await application.process_update(update)
    return {"ok": True}

if __name__ == "__main__":
    import uvicorn
    print("Starting server...")
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
