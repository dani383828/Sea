import logging
import random
import time
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

TOKEN = "8030062261:AAFnC9AJ_2zvcaqC0LXe5Y3--d2FgxOx-fI"
ADMIN_ID = 5542927340
TRX_ADDRESS = "TJ4xrwKJzKjk6FgKfuuqwah3Az5Ur22kJb"

app = Flask(__name__)
users = {}
application = Application.builder().token(TOKEN).build()


def is_valid_ship_name(name):
    return name.isalpha() and name.isascii()


def build_menu(buttons, n_cols):
    return [buttons[i:i + n_cols] for i in range(0, len(buttons), n_cols)]


@app.route(f"/webhook/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.process_update(update)
    return "ok"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    users[uid] = {
        "step": "awaiting_name", "ship": None, "ships": set(),
        "gems": 5, "gold": 10, "silver": 15,
        "energy": 90, "points": 0, "wins": 0, "games": 0,
        "cannons": 3,
    }
    await update.message.reply_text("🏴‍☠️ خوش آمدی کاپیتان! برای ساخت کشتی‌ات، یک نام انگلیسی انتخاب کن:")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    txt = update.message.text.strip()
    if uid not in users:
        return

    state = users[uid]
    if state["step"] == "awaiting_name":
        if not is_valid_ship_name(txt) or txt.lower() in ["start", "menu"] or txt in state["ships"]:
            await update.message.reply_text("❌ نام غیرمجاز یا تکراری. فقط نام انگلیسی یکتا مجاز است!")
            return

        state["ship"] = txt
        state["ships"].add(txt)
        state["step"] = "main_menu"

        buttons = [
            InlineKeyboardButton("۱- شروع بازی ⚔️", callback_data="play"),
            InlineKeyboardButton("۲- فروشگاه 🛒", callback_data="shop"),
            InlineKeyboardButton("۳- برترین ناخدایان", callback_data="leaders"),
            InlineKeyboardButton("۴- جستجوی کاربران", callback_data="find"),
            InlineKeyboardButton("۵- اطلاعات کشتی", callback_data="info"),
            InlineKeyboardButton("۶- انرژی جنگجویان", callback_data="energy"),
        ]

        await update.message.reply_text(
            f"✅ کشتی «{txt}» ساخته شد!\n\nچه کاری انجام بدهم کاپیتان؟",
            reply_markup=InlineKeyboardMarkup(build_menu(buttons, 2))
        )


async def button_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = query.from_user.id
    await query.answer()
    state = users.get(uid)
    if not state:
        return

    cmd = query.data
    if cmd == "play":
        await start_game(query, state)
    elif cmd == "fire":
        await handle_fire(update, context)


async def start_game(query, state):
    uid = query.from_user.id
    state["step"] = "in_game"
    # Fake opponent mockup
    opp = {"name": "BlackPearl", "strategy": "spy_attack", "energy": 80, "cannons": 3}
    msg = f"⚓️ جنگ شروع شد با {opp['name']}!\n"
    msg += f"گزارش: کشتی‌ات نزدیک شدیم...\n"
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("پرتاب توپ☄️", callback_data="fire")]])
    await query.edit_message_text(msg, reply_markup=keyboard)
    state["opponent"] = opp


async def handle_fire(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = query.from_user.id
    state = users[uid]
    opp = state.get("opponent")

    if not opp:
        return

    logical = random.random() < 0.7

    if state["cannons"] <= 0:
        res = "❌ توپ نداری! برو فروشگاه 🛒 توپ بخر!"
    else:
        state["cannons"] -= 1
        hit_chance = 0.65 if logical else 0.1
        if random.random() < hit_chance:
            res = "💥 توپ خورد به کشتی دشمن!"
            await query.edit_message_text(res)
            await conclude_game(uid, state, True)
            return
        else:
            res = "😐 توپ به هدف نخورد."

    await query.edit_message_text(res)


async def conclude_game(uid, state, victory):
    state["games"] += 1
    if victory:
        state["wins"] += 1
        state["points"] += 30
        state["gold"] += 3
        state["energy"] = min(100, state["energy"] + 10)
        if random.random() < 0.25:
            state["gems"] += 1
    else:
        state["points"] -= 10
        state["gold"] = max(0, state["gold"] - 3)
        state["energy"] = max(0, state["energy"] - 30)
        state["silver"] = max(0, state["silver"] - 5)
        if random.random() < 0.25:
            state["gems"] = max(0, state["gems"] - 1)


if __name__ == "__main__":
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_router))
    application.run_webhook(
        listen="0.0.0.0",
        port=10000,
        webhook_url=f"https://sea-2ri6.onrender.com/webhook/{TOKEN}"
    )
