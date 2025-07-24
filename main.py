import random
import sqlite3
from datetime import datetime
from fastapi import FastAPI, Request
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CallbackContext, CommandHandler,
    CallbackQueryHandler, MessageHandler, filters
)
import asyncio
import os

TOKEN = "8030062261:AAFnC9AJ_2zvcaqC0LXe5Y3--d2FgxOx-fI"
ADMIN_ID = 5542927340
WEBHOOK_URL = "https://sea-2ri6.onrender.com"

app = FastAPI()
bot = Bot(token=TOKEN)
application = Application.builder().token(TOKEN).build()

DB_PATH = "pirate_game.db"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS players (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        ship_name TEXT,
        energy INTEGER DEFAULT 100,
        gems INTEGER DEFAULT 0,
        cannons INTEGER DEFAULT 1,
        last_fight TEXT
    )""")
    c.execute("""
    CREATE TABLE IF NOT EXISTS game_reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        player1 INTEGER,
        player2 INTEGER,
        winner INTEGER,
        report TEXT,
        date_played TEXT
    )""")
    c.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount INTEGER,
        trx TEXT,
        confirmed INTEGER DEFAULT 0
    )""")
    conn.commit()
    conn.close()

init_db()

def get_player(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM players WHERE user_id=?", (user_id,))
    player = c.fetchone()
    conn.close()
    return player

def create_player(user_id, username):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO players (user_id, username, ship_name, energy, gems, cannons) VALUES (?, ?, ?, ?, ?, ?)",
              (user_id, username, f"Ship-{user_id}", 100, 0, 1))
    conn.commit()
    conn.close()

def update_energy(user_id, amount):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("UPDATE players SET energy = energy + ? WHERE user_id=?", (amount, user_id))
    conn.commit()
    conn.close()

def update_gems(user_id, amount):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("UPDATE players SET gems = gems + ? WHERE user_id=?", (amount, user_id))
    conn.commit()
    conn.close()

def update_cannons(user_id, amount):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("UPDATE players SET cannons = cannons + ? WHERE user_id=?", (amount, user_id))
    conn.commit()
    conn.close()

def set_last_fight(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    now = datetime.utcnow().isoformat()
    c.execute("UPDATE players SET last_fight = ? WHERE user_id=?", (now, user_id))
    conn.commit()
    conn.close()

def get_enemy(exclude_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM players WHERE user_id != ? ORDER BY RANDOM() LIMIT 1", (exclude_id,))
    enemy = c.fetchone()
    conn.close()
    return enemy

def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🚢 کشتی من", callback_data="my_ship")],
        [InlineKeyboardButton("⚔️ شروع نبرد", callback_data="battle")],
        [InlineKeyboardButton("💰 فروشگاه", callback_data="shop")],
        [InlineKeyboardButton("🧭 کاوش", callback_data="explore")],
        [InlineKeyboardButton("🪙 دریافت جم (TRX)", callback_data="get_gems")],
    ])

async def start(update: Update, context: CallbackContext):
    user = update.effective_user
    create_player(user.id, user.username or "")
    await update.message.reply_text(
        f"🏴‍☠️ خوش‌اومدی کاپیتان {user.first_name}!\nکشتی‌تو آماده کن و به نبرد وارد شو!",
        reply_markup=main_menu_keyboard()
    )

async def handle_button(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data
    player = get_player(user_id)

    if data == "my_ship":
        text = f"""
🚢 نام کشتی: {player['ship_name']}
⚡️ انرژی: {player['energy']}٪
🪙 جم: {player['gems']}
🔥 توپ: {player['cannons']}
"""
        await query.answer()
        await query.edit_message_text(text=text, reply_markup=main_menu_keyboard())

    elif data == "battle":
        enemy = get_enemy(user_id)
        if not enemy:
            await query.answer("فعلاً رقیبی پیدا نشد!", show_alert=True)
            return

        result = simulate_battle(player, enemy)
        await query.answer()
        await query.edit_message_text(result, reply_markup=main_menu_keyboard())

    elif data == "explore":
        await query.answer("در حال توسعه...", show_alert=True)

    elif data == "shop":
        shop_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🧨 خرید توپ (1 جم)", callback_data="buy_cannon")],
            [InlineKeyboardButton("⚡️ انرژی (1 جم)", callback_data="buy_energy")],
            [InlineKeyboardButton("⬅️ بازگشت", callback_data="back_to_main")]
        ])
        await query.edit_message_text("🛒 فروشگاه:", reply_markup=shop_keyboard)

    elif data == "get_gems":
        await query.edit_message_text(
            "برای دریافت جم، مبلغ موردنظر را به آدرس زیر ارسال کن:\n\n"
            "TRX Address: `TJ4xrwKJzKjk6FgKfuuqwah3Az5Ur22kJb`\n\n"
            "سپس رسید پرداخت (TXID) را برای ما ارسال کن.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ بازگشت", callback_data="back_to_main")]]),
            parse_mode="Markdown"
        )

    elif data == "buy_cannon":
        if player["gems"] >= 1:
            update_gems(user_id, -1)
            update_cannons(user_id, 1)
            await query.answer("توپ خریداری شد!")
        else:
            await query.answer("جم کافی نداری!", show_alert=True)
        await query.edit_message_text("توپ خریداری شد.", reply_markup=main_menu_keyboard())

    elif data == "buy_energy":
        if player["gems"] >= 1:
            update_gems(user_id, -1)
            update_energy(user_id, 20)
            await query.answer("انرژی افزایش یافت!")
        else:
            await query.answer("جم کافی نداری!", show_alert=True)
        await query.edit_message_text("انرژی افزایش یافت.", reply_markup=main_menu_keyboard())

    elif data == "back_to_main":
        await query.edit_message_text("به منوی اصلی برگشتیم.", reply_markup=main_menu_keyboard())

def simulate_battle(player, enemy):
    player_power = player["cannons"] + random.randint(0, 5)
    enemy_power = enemy["cannons"] + random.randint(0, 5)

    if player["energy"] < 10:
        return "⚡️ انرژی‌ات کافی نیست برای نبرد. برو تو فروشگاه انرژی بخر یا صبر کن تا شارژ بشی."

    update_energy(player["user_id"], -10)
    set_last_fight(player["user_id"])

    if player_power > enemy_power:
        reward = random.randint(1, 3)
        update_gems(player["user_id"], reward)
        return f"🏴‍☠️ پیروز شدی! به کشتی {enemy['ship_name']} حمله کردی و {reward} جم غارت کردی!"
    elif player_power < enemy_power:
        loss = min(player["gems"], random.randint(0, 2))
        update_gems(player["user_id"], -loss)
        return f"💥 شکست خوردی! دشمن {loss} جم ازت گرفت!"
    else:
        return "🤝 نبرد مساوی شد. کسی برنده یا بازنده نبود."

# هندلر رسید پرداخت (ساده‌شده)
@dp.message(Command("receipt"))
async def handle_receipt(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    txid = update.message.text.split(maxsplit=1)[-1]
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"🧾 رسید جدید از کاربر {user_id}:\nTXID: {txid}",
    )
    await update.message.reply_text("📨 رسیدت برای ادمین ارسال شد. پس از بررسی جم به حسابت واریز می‌شه.")

# Webhook FastAPI
@app.post(f"/{BOT_TOKEN}")
async def telegram_webhook(update: dict):
    update = Update.de_json(update, bot)
    await dp.process_update(update)
    return {"ok": True}

# راه‌اندازی اولیه
@app.on_event("startup")
async def on_startup():
    init_db()
    await bot.set_webhook(f"{WEBHOOK_URL}/{BOT_TOKEN}")
    print("✅ وب‌هوک فعال شد")

# اجرای برنامه FastAPI
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=10000)
