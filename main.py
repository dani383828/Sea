from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder

TOKEN = "توکن_تو"
WEBHOOK_PATH = f"/webhook/{TOKEN}"
WEBHOOK_URL = f"https://دامنه_تو{WEBHOOK_PATH}"

app = Flask(__name__)
application = ApplicationBuilder().token(TOKEN).build()

@app.route(WEBHOOK_PATH, methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    import asyncio
    asyncio.run(application.process_update(update))
    return "OK"

if __name__ == "__main__":
    import asyncio

    async def main():
        await application.bot.delete_webhook()
        await application.bot.set_webhook(WEBHOOK_URL)
        print("Webhook set")
        app.run(host="0.0.0.0", port=10000)

    asyncio.run(main())
