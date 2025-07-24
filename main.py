from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder
import asyncio

TOKEN = "8030062261:AAFnC9AJ_2zvcaqC0LXe5Y3--d2FgxOx-fI"
WEBHOOK_PATH = f"/webhook/{TOKEN}"
WEBHOOK_URL = f"https://sea-2ri6.onrender.com{WEBHOOK_PATH}"

app = Flask(__name__)
application = ApplicationBuilder().token(TOKEN).build()

@app.route(WEBHOOK_PATH, methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    # چون توی توابع sync هستیم باید از asyncio.create_task یا loop.run_until_complete استفاده کنیم
    # ولی چون در فلکسی توابع sync داریم، برای ساده‌ترین حالت:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(application.process_update(update))
    loop.close()
    return "OK"

async def setup():
    await application.initialize()
    await application.start()
    await application.bot.set_webhook(WEBHOOK_URL)
    print(f"Webhook set to {WEBHOOK_URL}")

if __name__ == "__main__":
    # ابتدا اپ را مقداردهی اولیه می‌کنیم
    asyncio.run(setup())
    # سپس سرور Flask را اجرا می‌کنیم
    app.run(host="0.0.0.0", port=10000)
