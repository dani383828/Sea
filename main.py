import os
import logging
import re
import random
import asyncio
from typing import Dict, List
from fastapi import FastAPI, Request
from telegram import (
    Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
)
from telegram.ext import (
    Application, CommandHandler, ContextTypes, MessageHandler,
    filters, CallbackQueryHandler
)

# 🛡️ مشخصات
TOKEN = "8030062261:AAFnC9AJ_2zvcaqC0LXe5Y3--d2FgxOx-fI"
ADMIN_ID = 5542927340
WEBHOOK_PATH = f"/webhook/{TOKEN}"
WEBHOOK_URL = f"https://sea-2ri6.onrender.com{WEBHOOK_PATH}"
TRX_ADDRESS = "TJ4xrwKJzKjk6FgKfuuqwah3Az5Ur22kJb"

# 📦 دیتابیس موقت
users: Dict[int, Dict] = {}
pending_ship_name: Dict[int, bool] = {}

# 🪵 لاگ‌گیری
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

# 🎯 ساخت اپلیکیشن و ربات
app = FastAPI()
application = Application.builder().token(TOKEN).build()

# 📌 فرمان /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    users.setdefault(user_id, {
        "registered": False,
        "ship_name": None,
        "gems": 5,
        "gold": 10,
        "silver": 15,
        "strategy": None,
        "wins": 0,
        "losses": 0,
        "energy": 100,
        "cannonballs": 3
    })

    text = (
        "🏴‍☠️ به دنیای دزدان دریایی خوش اومدی، کاپیتان!\n\n"
        "🚢 آماده‌ای کشتی‌تو بسازی و راهی دریا بشی؟"
    )

    keyboard = [
        [InlineKeyboardButton("1- شروع بازی ⚔️", callback_data="start_game")],
        [InlineKeyboardButton("2- فروشگاه 🛒", callback_data="shop")],
        [InlineKeyboardButton("3- برترین ناخدایان", callback_data="top_players")],
        [InlineKeyboardButton("4- جست و جوی کاربران", callback_data="search_users")],
        [InlineKeyboardButton("5- اطلاعات کشتی", callback_data="ship_info")],
        [InlineKeyboardButton("6- انرژی جنگجویان", callback_data="energy_status")]
    ]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

# ⚓️ هندلر کلیک دکمه‌ها
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "start_game":
        if not users[user_id]["registered"]:
            pending_ship_name[user_id] = True
            await query.edit_message_text("🛠 نام کشتی‌تو بگو (فقط انگلیسی، تکراری نباشه):")
        else:
            await query.edit_message_text("⚓️ کشتی شما ساخته شده.\n\n⛵️ انتخاب کن:\n1- دریانوردی\n2- استراتژی\n3- توپ‌ها")

# 🛠️ هندلر دریافت نام کشتی
async def name_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if user_id in pending_ship_name and pending_ship_name[user_id]:
        if not re.match("^[A-Za-z0-9 _-]+$", text):
            await update.message.reply_text("❌ فقط از حروف انگلیسی استفاده کن.")
            return
        if text.lower() in [u["ship_name"].lower() for u in users.values() if u["ship_name"]]:
            await update.message.reply_text("❌ این اسم قبلاً انتخاب شده.")
            return
        if text.lower() in ["/start", "شروع بازی", "فروشگاه", "اطلاعات"]:
            await update.message.reply_text("❌ این اسم مجازه نیست.")
            return

        users[user_id]["registered"] = True
        users[user_id]["ship_name"] = text
        pending_ship_name[user_id] = False

        await update.message.reply_text(f"✅ کشتی `{text}` با موفقیت ساخته شد!", parse_mode="Markdown")
        await asyncio.sleep(1)
        await update.message.reply_text(
            "⛵️ انتخاب کن:\n1- دریانوردی\n2- استراتژی\n3- توپ‌ها",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("1- دریانوردی", callback_data="sail")],
                [InlineKeyboardButton("2- استراتژی", callback_data="strategy")],
                [InlineKeyboardButton("3- توپ‌ها", callback_data="cannons")]
            ])
        )

# ⚔️ هندلر کلیک‌های بازی (دریانوردی، استراتژی، توپ‌ها)
async def game_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "sail":
        await query.edit_message_text("🌊 منتظر پیدا شدن رقیب هستیم...")
        await asyncio.sleep(3)
        # پیدا کردن رقیب یا ساخت رقیب فیک
        opponent_id = find_opponent(user_id)
        result = simulate_battle(user_id, opponent_id)
        await query.message.reply_text(result, reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("☄️ پرتاب توپ", callback_data="fire_cannon")]
        ]))

    elif query.data == "strategy":
        keyboard = [
            [InlineKeyboardButton("استتار به عنوان کشتی تجاری", callback_data="set_strategy_1")],
            [InlineKeyboardButton("حمله شبانه", callback_data="set_strategy_2")],
            [InlineKeyboardButton("آتش‌زدن کشتی دشمن", callback_data="set_strategy_3")],
            [InlineKeyboardButton("اتصال قلاب", callback_data="set_strategy_4")],
            [InlineKeyboardButton("کمین پشت صخره‌", callback_data="set_strategy_5")],
            [InlineKeyboardButton("فریب با گنج جعلی", callback_data="set_strategy_6")],
            [InlineKeyboardButton("حمله با کمک جاسوس", callback_data="set_strategy_7")]
        ]
        await query.edit_message_text("🎯 انتخاب کن که با کدوم استراتژی حمله کنیم:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "cannons":
        user = users[user_id]
        if user["cannonballs"] > 0:
            await query.edit_message_text(f"🧨 شما {user['cannonballs']} توپ داری.")
        else:
            await query.edit_message_text("💣 شما توپ نداری! برای خرید توپ به فروشگاه برو.")

# 🎯 انتخاب استراتژی
async def strategy_selector(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    strategy_map = {
        "set_strategy_1": "استتار",
        "set_strategy_2": "حمله شبانه",
        "set_strategy_3": "آتش‌زدن",
        "set_strategy_4": "اتصال قلاب",
        "set_strategy_5": "کمین",
        "set_strategy_6": "فریب",
        "set_strategy_7": "کمک جاسوس"
    }
    strategy = strategy_map[query.data]
    users[user_id]["strategy"] = strategy
    await query.edit_message_text(f"✅ استراتژی شما تنظیم شد: {strategy}")

# 💥 پرتاب توپ
async def fire_cannon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    user = users[user_id]

    if user["cannonballs"] <= 0:
        await query.edit_message_text("❌ شما توپ نداری! برو فروشگاه توپ بخر.")
        return

    user["cannonballs"] -= 1
    chance = random.randint(1, 100)
    if chance <= 65:
        await query.edit_message_text("🎯 شلیک موفقیت‌آمیز بود! دشمن آسیب دید.")
    else:
        await query.edit_message_text("💨 توپ به هدف نخورد!")

# 🛒 فروشگاه
async def shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("💎 خرید جم", callback_data="buy_gem")],
        [InlineKeyboardButton("💣 خرید توپ (3 جم)", callback_data="buy_cannon")],
        [InlineKeyboardButton("🔄 تبدیل جم به طلا/نقره", callback_data="convert_gem")]
    ]
    await query.edit_message_text("🛒 فروشگاه:\nانتخاب کن:", reply_markup=InlineKeyboardMarkup(keyboard))

# 🪙 خرید جم → فیش برای ادمین
async def buy_gem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        f"💎 بسته‌های جم:\n\n"
        f"1. 25 جم = ۵ ترون\n"
        f"2. 50 جم = ۸ ترون\n"
        f"3. 100 جم = ۱۴ ترون\n\n"
        f"آدرس ترون:\n`{TRX_ADDRESS}`\n\n"
        f"📤 لطفاً فیش واریز رو ارسال کن.",
        parse_mode="Markdown"
    )

# 📤 دریافت فیش
async def receipt_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if update.message.text or update.message.photo:
        admin_text = f"📥 فیش جدید از کاربر {user.id}:\n\n"
        if update.message.caption:
            admin_text += update.message.caption
        elif update.message.text:
            admin_text += update.message.text
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=admin_text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ تایید", callback_data=f"confirm:{user.id}")],
                [InlineKeyboardButton("❌ رد", callback_data=f"reject:{user.id}")]
            ])
        )
        await update.message.reply_text("📤 فیشت برای بررسی به ناخدای کل فرستاده شد.")

# 📦 خرید توپ
async def buy_cannon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    user = users[user_id]

    if user["gems"] >= 3:
        user["gems"] -= 3
        user["cannonballs"] += 1
        await query.edit_message_text("✅ یک توپ خریداری شد.")
    else:
        await query.edit_message_text("❌ جم کافی نداری.")

# ♻️ تبدیل جم به طلا و نقره
async def convert_gem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    user = users[user_id]
    gems = user["gems"]

    if gems >= 10:
        user["gems"] -= 10
        user["gold"] += 20
        user["silver"] += 15
        await query.edit_message_text("🔁 تبدیل موفق: 10 جم → 20 کیسه طلا + 15 شمش نقره")
    elif gems >= 3:
        user["gems"] -= 3
        user["gold"] += 6
        user["silver"] += 4
        await query.edit_message_text("🔁 تبدیل موفق: 3 جم → 6 کیسه طلا + 4 شمش نقره")
    elif gems >= 1:
        user["gems"] -= 1
        user["gold"] += 2
        await query.edit_message_text("🔁 تبدیل موفق: 1 جم → 2 کیسه طلا")
    else:
        await query.edit_message_text("❌ جم کافی برای تبدیل نداری.")

# 🎮 شبیه‌سازی جنگ دریایی
def find_opponent(user_id: int) -> int:
    # شبیه‌سازی یک رقیب فیک
    fake_id = -random.randint(10000, 99999)
    users[fake_id] = {
        "registered": True,
        "ship_name": f"EnemyShip{abs(fake_id)}",
        "gems": 0, "gold": 10, "silver": 10,
        "strategy": random.choice(["استتار", "حمله شبانه", "کمین"]),
        "wins": 0, "losses": 0, "energy": random.randint(60, 100),
        "cannonballs": random.randint(0, 2)
    }
    return fake_id

def simulate_battle(uid1: int, uid2: int) -> str:
    u1, u2 = users[uid1], users[uid2]

    score1 = 0
    score2 = 0

    # استراتژی‌ها
    beat_map = {
        "حمله شبانه": ["استتار", "فریب"],
        "حمله با کمک جاسوس": ["حمله شبانه", "کمین"],
        "کمین": ["اتصال قلاب", "آتش‌زدن"],
        "اتصال قلاب": ["استتار"],
        "استتار": ["کمک جاسوس"],
        "آتش‌زدن": ["حمله شبانه"],
        "فریب": ["آتش‌زدن"]
    }

    s1 = u1.get("strategy", "")
    s2 = u2.get("strategy", "")
    if s2 in beat_map.get(s1, []):
        score1 += 30
    elif s1 in beat_map.get(s2, []):
        score2 += 30

    # انرژی
    score1 += u1["energy"] // 10
    score2 += u2["energy"] // 10

    # توپ
    if u1["cannonballs"] > 0:
        score1 += 10
    if u2["cannonballs"] > 0:
        score2 += 10

    # نتیجه نهایی
    if score1 > score2:
        u1["wins"] += 1
        u2["losses"] += 1
        u1["gold"] += 3
        u1["silver"] += 5
        u1["energy"] = min(u1["energy"] + 10, 100)
        if random.randint(1, 4) == 1:
            u1["gems"] += 1
        return "🏆 شما پیروز شدی!"
    else:
        u1["losses"] += 1
        u1["gold"] = max(0, u1["gold"] - 3)
        u1["silver"] = max(0, u1["silver"] - 5)
        u1["energy"] = max(0, u1["energy"] - 30)
        if random.randint(1, 4) == 1 and u1["gems"] > 0:
            u1["gems"] -= 1
        return "💥 شما شکست خوردی."

# 🏅 رتبه‌بندی
async def top_players(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    ranking = sorted([(uid, u["wins"]) for uid, u in users.items() if u["registered"]], key=lambda x: x[1], reverse=True)
    text = "🏴‍☠️ برترین ناخدایان:\n"
    for idx, (uid, wins) in enumerate(ranking[:10], start=1):
        total = users[uid]["wins"] + users[uid]["losses"]
        avg = f"{int(users[uid]['wins'] / total * 100)}%" if total > 0 else "0%"
        text += f"{idx}. {users[uid]['ship_name']} - برد: {wins} - میانگین: {avg}\n"
    await query.edit_message_text(text)

# 🔍 جست‌وجو
async def search_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.edit_message_text("🕵️‍♂️ نام کشتی دوستت رو بفرست:")

# 📄 اطلاعات کشتی
async def ship_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = users[query.from_user.id]
    total = user["wins"] + user["losses"]
    avg = f"{int(user['wins']/total*100)}%" if total > 0 else "0%"
    text = (
        f"🚢 کشتی: {user['ship_name']}\n"
        f"💎 جم: {user['gems']}\n"
        f"💰 کیسه طلا: {user['gold']}\n"
        f"🥈 شمش نقره: {user['silver']}\n"
        f"📊 میانگین پیروزی: {avg}\n"
        f"⚡️ انرژی: {user['energy']}%"
    )
    await query.edit_message_text(text)

# 🍱 انرژی و خوراکی‌ها
async def energy_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    energy = users[user_id]["energy"]

    text = f"⚡️ انرژی فعلی جنگجویان: {energy}%\n\nاگر خستن باید خوراکی بخری:"
    keyboard = [
        [InlineKeyboardButton("1 بسته بیسکویت دریایی (۴ نقره)", callback_data="buy_food_1")],
        [InlineKeyboardButton("۵ ماهی خشک (۱ طلا، ۱ نقره)", callback_data="buy_food_2")],
        [InlineKeyboardButton("۳ میوه خشک (۱ طلا)", callback_data="buy_food_3")],
        [InlineKeyboardButton("۱۰ پنیر کهنه (۱ طلا، ۳ نقره)", callback_data="buy_food_4")],
        [InlineKeyboardButton("۱۰ بطری آب (۳ نقره)", callback_data="buy_food_5")]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

# 🍽 خرید خوراکی
async def buy_food(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = users[query.from_user.id]

    foods = {
        "buy_food_1": {"energy": 25, "silver": 4},
        "buy_food_2": {"energy": 35, "silver": 1, "gold": 1},
        "buy_food_3": {"energy": 30, "gold": 1},
        "buy_food_4": {"energy": 50, "gold": 1, "silver": 3},
        "buy_food_5": {"energy": 20, "silver": 3}
    }

    item = foods[query.data]
    if user.get("bought_food") == query.data:
        await query.edit_message_text("⏱ هر ۲۴ ساعت فقط یکبار می‌تونی اینو بخری.")
        return

    if user.get("gold", 0) < item.get("gold", 0) or user.get("silver", 0) < item.get("silver", 0):
        await query.edit_message_text("❌ منابع کافی نداری.")
        return

    user["gold"] -= item.get("gold", 0)
    user["silver"] -= item.get("silver", 0)
    user["energy"] = min(user["energy"] + item["energy"], 100)
    user["bought_food"] = query.data
    await query.edit_message_text("✅ خوراکی خریداری شد و انرژی افزایش یافت.")

# 🧩 ثبت همه هندلرها
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, name_handler))
application.add_handler(MessageHandler(filters.PHOTO | filters.TEXT, receipt_handler))
application.add_handler(CallbackQueryHandler(button_handler, pattern="^start_game|shop|top_players|search_users|ship_info|energy_status$"))
application.add_handler(CallbackQueryHandler(game_menu_handler, pattern="^sail|strategy|cannons$"))
application.add_handler(CallbackQueryHandler(strategy_selector, pattern="^set_strategy_"))
application.add_handler(CallbackQueryHandler(fire_cannon, pattern="^fire_cannon$"))
application.add_handler(CallbackQueryHandler(shop, pattern="^shop$"))
application.add_handler(CallbackQueryHandler(buy_gem, pattern="^buy_gem$"))
application.add_handler(CallbackQueryHandler(buy_cannon, pattern="^buy_cannon$"))
application.add_handler(CallbackQueryHandler(convert_gem, pattern="^convert_gem$"))
application.add_handler(CallbackQueryHandler(top_players, pattern="^top_players$"))
application.add_handler(CallbackQueryHandler(search_users, pattern="^search_users$"))
application.add_handler(CallbackQueryHandler(ship_info, pattern="^ship_info$"))
application.add_handler(CallbackQueryHandler(energy_status, pattern="^energy_status$"))
application.add_handler(CallbackQueryHandler(buy_food, pattern="^buy_food_"))

# 🌐 وب‌هوک
@app.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, application.bot)
    await application.update_queue.put(update)
    return {"ok": True}

@app.on_event("startup")
async def on_startup():
    await application.bot.set_webhook(url=WEBHOOK_URL)
    await application.initialize()
    await application.start()
    print("✅ Webhook فعال شد:", WEBHOOK_URL)

@app.on_event("shutdown")
async def on_shutdown():
    await application.stop()
    await application.shutdown()
