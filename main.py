import os
import logging
import re
import random
import time
import asyncio
from datetime import datetime, timedelta
from fastapi import FastAPI, Request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler
)

# ⚙️ Configuration
TOKEN = "8030062261:AAFnC9AJ_2zvcaqC0LXe5Y3--d2FgxOx-fI"
WEBHOOK_PATH = f"/webhook/{TOKEN}"
WEBHOOK_URL = f"https://sea-2ri6.onrender.com{WEBHOOK_PATH}"
ADMIN_ID = 5542927340
TRX_ADDRESS = "TJ4xrwKJzKjk6FgKfuuqwah3Az5Ur22kJb"

# ⚙️ Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# 📦 FastAPI app
app = FastAPI()

# 🎯 Build Telegram bot
application = Application.builder().token(TOKEN).build()

# 📚 Data storage (in-memory for simplicity; consider database for production)
users = {}  # {user_id: {"ship_name": str, "gems": int, "gold": int, "silver": int, "score": int, "wins": int, "total_games": int, "energy": float, "cannonballs": int, "last_purchase": float, "strategy": str}}
ship_names = set()  # To track unique ship names
pending_games = {}  # {user_id: opponent_id} for friend battles
battle_reports = {}  # {user_id: [report_lines]}
last_cannonball = {}  # {user_id: timestamp}

# 📌 Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in users:
        users[user_id] = {
            "ship_name": None, "gems": 5, "gold": 10, "silver": 15, "score": 0,
            "wins": 0, "total_games": 0, "energy": 90.0, "cannonballs": 3,
            "last_purchase": 0.0, "strategy": None
        }
    keyboard = [
        [KeyboardButton("🏴‍☠️ شروع بازی ⚔️"), KeyboardButton("🛒 فروشگاه")],
        [KeyboardButton("🏆 برترین ناخدایان"), KeyboardButton("🔍 جست‌وجوی کاربران")],
        [KeyboardButton("ℹ️ اطلاعات کشتی"), KeyboardButton("⚡ انرژی جنگجویان")],
        [KeyboardButton("/start")]  # Added as per request
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "🏴‍☠️ به دنیای دزدان دریایی خوش اومدی، کاپیتان!\n\n"
        "🚢 آماده‌ای کشتی‌تو بسازی و راهی دریا بشی؟\n\nانتخاب کن:",
        reply_markup=reply_markup
    )

# 🏴‍☠️ Start game
async def start_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if users[user_id]["ship_name"] is None:
        await update.message.reply_text("کشتیت در حال ساخته شدنه...\nساخته شد! 🛠️\nنام کشتیت رو بگو (فقط انگلیسی، بدون تکرار):")
        context.user_data["state"] = "awaiting_ship_name"
    else:
        keyboard = [
            [KeyboardButton("⛵️ دریانوردی"), KeyboardButton("🎯 استراتژی")],
            [KeyboardButton("☄️ توپ"), KeyboardButton("🏴‍☠️ بازگشت به منوی اصلی")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("🏴‍☠️ آماده جنگیدن، کاپیتان؟", reply_markup=reply_markup)

# 📝 Handle ship name
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    if context.user_data.get("state") == "awaiting_ship_name":
        if text in ["🏴‍☠️ شروع بازی ⚔️", "🛒 فروشگاه", "🏆 برترین ناخدایان", "🔍 جست‌وجوی کاربران", "ℹ️ اطلاعات کشتی", "⚡ انرژی جنگجویان", "/start"]:
            await update.message.reply_text("لطفاً یه نام معتبر انگلیسی برای کشتی وارد کن!")
            return
        if not re.match("^[A-Za-z0-9 ]+$", text):
            await update.message.reply_text("فقط حروف انگلیسی و اعداد مجازن!")
            return
        if text in ship_names:
            await update.message.reply_text("این نام قبلاً گرفته شده! یه نام دیگه انتخاب کن.")
            return
        ship_names.add(text)
        users[user_id]["ship_name"] = text
        context.user_data["state"] = None
        keyboard = [
            [KeyboardButton("⛵️ دریانوردی"), KeyboardButton("🎯 استراتژی")],
            [KeyboardButton("☄️ توپ"), KeyboardButton("🏴‍☠️ بازگشت به منوی اصلی")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(f"کشتی {text} آماده دریانوردیه! 🛳️", reply_markup=reply_markup)
    elif text == "🏴‍☠️ شروع بازی ⚔️":
        await start_game(update, context)
    elif text == "🛒 فروشگاه":
        await shop(update, context)
    elif text == "🏆 برترین ناخدایان":
        await leaderboard(update, context)
    elif text == "🔍 جست‌وجوی کاربران":
        await search_users(update, context)
    elif text == "ℹ️ اطلاعات کشتی":
        await ship_info(update, context)
    elif text == "⚡ انرژی جنگجویان":
        await energy(update, context)
    elif text == "⛵️ دریانوردی":
        await sail(update, context)
    elif text == "🎯 استراتژی":
        await strategy(update, context)
    elif text == "☄️ توپ":
        await cannonballs(update, context)
    elif text == "🏴‍☠️ بازگشت به منوی اصلی":
        await start(update, context)
    elif context.user_data.get("state") == "awaiting_friend_name":
        await process_friend_search(update, context, text)
    elif context.user_data.get("state") == "awaiting_receipt":
        await process_receipt(update, context)

# ⛵️ Sailing (Battle)
async def sail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if users[user_id]["ship_name"] is None:
        await start_game(update, context)
        return
    opponent_id = None
    for uid, data in pending_games.items():
        if data == user_id:
            opponent_id = uid
            break
    if opponent_id:
        del pending_games[opponent_id]
        await start_battle(update, context, opponent_id)
    else:
        start_time = time.time()
        while time.time() - start_time < 60:
            opponent_id = next((uid for uid in users.keys() if uid != user_id and users[uid]["ship_name"] and not uid.startswith("fake_")), None)
            if opponent_id:
                break
            await asyncio.sleep(1)
        if not opponent_id:
            opponent_id = f"fake_{random.randint(1000, 9999)}"
            users[opponent_id] = {
                "ship_name": f"Enemy_{random.randint(100, 999)}", "gems": 5, "gold": 10, "silver": 15,
                "score": 0, "wins": 0, "total_games": 0, "energy": 80.0, "cannonballs": 3,
                "last_purchase": 0.0, "strategy": random.choice(["استتار به عنوان کشتی تجاری", "حمله شبانه", "آتش‌زدن کشتی دشمن", "اتصال قلاب", "کمین پشت صخره‌", "فریب با گنج جعلی", "حمله با کمک جاسوس"])
            }
        await start_battle(update, context, opponent_id)

async def start_battle(update: Update, context: ContextTypes.DEFAULT_TYPE, opponent_id):
    user_id = update.effective_user.id
    battle_reports[user_id] = []
    last_cannonball[user_id] = 0
    reports = [
        "دشمن رو در افق دیدیم! ⛵️",
        "کشتی دشمن نزدیکه! آماده باش!",
        "خیلی بهشون نزدیک شدیم! 🏴‍☠️",
        "کشتیت سوراخ شد! عجله کن! ⚡",
        "دشمن داره فرار می‌کنه! 🚢"
    ]
    for report in reports:
        battle_reports[user_id].append(report)
        keyboard = [[InlineKeyboardButton("☄️ پرتاب توپ", callback_data="fire_cannon")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(report, reply_markup=reply_markup)
        await asyncio.sleep(5)
    await end_battle(update, context, opponent_id)

async def fire_cannon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    if users[user_id]["cannonballs"] <= 0:
        await query.message.reply_text("توپ نداری! به فروشگاه برو و بخر! 🛒")
        return
    users[user_id]["cannonballs"] -= 1
    current_time = time.time()
    last_shot = last_cannonball.get(user_id, 0)
    last_cannonball[user_id] = current_time
    hit_chance = 0.65 if current_time - last_shot < 10 and "خیلی بهشون نزدیک شدیم" in battle_reports[user_id][-1] else 0.10
    if random.random() < hit_chance:
        battle_reports[user_id].append("🎯 توپ به هدف خورد!")
    else:
        battle_reports[user_id].append("💨 توپ خطا رفت!")
    await query.message.reply_text(battle_reports[user_id][-1])

async def end_battle(update: Update, context: ContextTypes.DEFAULT_TYPE, opponent_id):
    user_id = update.effective_user.id
    user_strategy = users[user_id]["strategy"] or "حمله شبانه"
    opp_strategy = users[opponent_id]["strategy"] or "حمله شبانه"
    user_energy = users[user_id]["energy"]
    opp_energy = users[opponent_id]["energy"]
    strategy_scores = {
        "استتار به عنوان کشتی تجاری": {"حمله شبانه": 0.3, "آتش‌زدن کشتی دشمن": 0.7, "اتصال قلاب": 0.4, "کمین پشت صخره‌": 0.5, "فریب با گنج جعلی": 0.2, "حمله با کمک جاسوس": 0.1},
        "حمله شبانه": {"استتار به عنوان کشتی تجاری": 0.7, "آتش‌زدن کشتی دشمن": 0.5, "اتصال قلاب": 0.6, "کمین پشت صخره‌": 0.4, "فریب با گنج جعلی": 0.5, "حمله با کمک جاسوس": 0.2},
        "آتش‌زدن کشتی دشمن": {"استتار به عنوان کشتی تجاری": 0.3, "حمله شبانه": 0.5, "اتصال قلاب": 0.7, "کمین پشت صخره‌": 0.6, "فریب با گنج جعلی": 0.4, "حمله با کمک جاسوس": 0.3},
        "اتصال قلاب": {"استتار به عنوان کشتی تجاری": 0.6, "حمله شبانه": 0.4, "آتش‌زدن کشتی دشمن": 0.3, "کمین پشت صخره‌": 0.5, "فریب با گنج جعلی": 0.5, "حمله با کمک جاسوس": 0.4},
        "کمین پشت صخره‌": {"استتار به عنوان کشتی تجاری": 0.5, "حمله شبانه": 0.6, "آتش‌زدن کشتی دشمن": 0.4, "اتصال قلاب": 0.5, "فریب با گنج جعلی": 0.6, "حمله با کمک جاسوس": 0.3},
        "فریب با گنج جعلی": {"استتار به عنوان کشتی تجاری": 0.8, "حمله شبانه": 0.5, "آتش‌زدن کشتی دشمن": 0.6, "اتصال قلاب": 0.5, "کمین پشت صخره‌": 0.4, "حمله با کمک جاسوس": 0.2},
        "حمله با کمک جاسوس": {"استتار به عنوان کشتی تجاری": 0.9, "حمله شبانه": 0.8, "آتش‌زدن کشتی دشمن": 0.7, "اتصال قلاب": 0.6, "کمین پشت صخره‌": 0.7, "فریب با گنج جعلی": 0.8}
    }
    user_score = strategy_scores[user_strategy].get(opp_strategy, 0.5) * (user_energy / 100)
    opp_score = strategy_scores[opp_strategy].get(user_strategy, 0.5) * (opp_energy / 100)
    if "توپ به هدف خورد" in battle_reports[user_id]:
        user_score += 0.2
    if user_id in pending_games or opponent_id in pending_games:
        await update.message.reply_text("بازی دوستانه تموم شد! 🏴‍☠️")
        return
    if user_score > opp_score:
        users[user_id]["score"] += 30
        users[user_id]["gold"] += 3
        users[user_id]["silver"] += 5
        users[user_id]["energy"] = min(100, users[user_id]["energy"] + 10)
        users[user_id]["wins"] += 1
        if random.random() < 0.25:
            users[user_id]["gems"] += 1
        await update.message.reply_text("🏆 بردی! +30 امتیاز، +3 کیسه طلا، +5 شمش نقره، +10% انرژی" + (", +1 جم" if users[user_id]["gems"] % 1 == 0 else ""))
    else:
        users[user_id]["score"] = max(0, users[user_id]["score"] - 10)
        users[user_id]["gold"] = max(0, users[user_id]["gold"] - 3)
        users[user_id]["silver"] = max(0, users[user_id]["silver"] - 5)
        users[user_id]["energy"] = max(0, users[user_id]["energy"] - 30)
        if random.random() < 0.25:
            users[user_id]["gems"] = max(0, users[user_id]["gems"] - 1)
        await update.message.reply_text("💥 باختی! -10 امتیاز، -3 کیسه طلا، -5 شمش نقره، -30% انرژی" + (", -1 جم" if users[user_id]["gems"] % 1 == 0 else ""))
    users[user_id]["total_games"] += 1
    if opponent_id.startswith("fake_"):
        del users[opponent_id]
    del battle_reports[user_id]

# 🎯 Strategy
async def strategy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if users[user_id]["ship_name"] is None:
        await start_game(update, context)
        return
    keyboard = [
        [KeyboardButton("استتار به عنوان کشتی تجاری"), KeyboardButton("حمله شبانه")],
        [KeyboardButton("آتش‌زدن کشتی دشمن"), KeyboardButton("اتصال قلاب")],
        [KeyboardButton("کمین پشت صخره‌"), KeyboardButton("فریب با گنج جعلی")],
        [KeyboardButton("حمله با کمک جاسوس"), KeyboardButton("🏴‍☠️ بازگشت به منوی اصلی")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("🎯 کدوم استراتژی رو انتخاب می‌کنی؟", reply_markup=reply_markup)
    strategies = ["استتار به عنوان کشتی تجاری", "حمله شبانه", "آتش‌زدن کشتی دشمن", "اتصال قلاب", "کمین پشت صخره‌", "فریب با گنج جعلی", "حمله با کمک جاسوس"]
    if update.message.text in strategies:
        users[user_id]["strategy"] = update.message.text
        await update.message.reply_text(f"استراتژی {update.message.text} انتخاب شد! 🏴‍☠️")

# ☄️ Cannonballs
async def cannonballs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if users[user_id]["ship_name"] is None:
        await start_game(update, context)
        return
    if users[user_id]["cannonballs"] == 0:
        await update.message.reply_text("توپ نداری! به فروشگاه برو و بخر! 🛒")
    else:
        await update.message.reply_text(f"تعداد توپ‌ها: {users[user_id]['cannonballs']} ☄️")

# 🛒 Shop (Disabled purchases as per request)
async def shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if users[user_id]["ship_name"] is None:
        await start_game(update, context)
        return
    keyboard = [
        [KeyboardButton("💎 خرید جم"), KeyboardButton("☄️ خرید توپ")],
        [KeyboardButton("تبدیل جم"), KeyboardButton("🏴‍☠️ بازگشت به منوی اصلی")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "🛒 به فروشگاه خوش اومدی!\n\n"
        "💎 خرید جم:\n25 جم = ۵ ترون\n50 جم = ۸ ترون\n100 جم = ۱۴ ترون\n\n"
        "☄️ خرید توپ: هر توپ ۳ جم\n\n"
        "تبدیل جم:\n1 جم = 2 کیسه طلا\n3 جم = 6 کیسه طلا + 4 شمش نقره\n10 جم = 20 کیسه طلا + 15 شمش نقره\n\n"
        "⚠️ در حال حاضر خرید غیرفعال است!",
        reply_markup=reply_markup
    )

async def process_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("خرید در حال حاضر غیرفعال است! ⚠️")

# 🏆 Leaderboard
async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sorted_users = sorted(users.items(), key=lambda x: x[1]["score"], reverse=True)[:10]
    text = "🏆 برترین ناخدایان:\n\n"
    for user_id, data in sorted_users:
        win_rate = (data["wins"] / data["total_games"] * 100) if data["total_games"] > 0 else 0
        text += f"کشتی {data['ship_name']}: {data['score']} امتیاز (میانگین برد: {win_rate:.1f}%)\n"
    await update.message.reply_text(text or "هنوز ناخدایی ثبت نشده!")

# 🔍 Search users
async def search_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if users[user_id]["ship_name"] is None:
        await start_game(update, context)
        return
    await update.message.reply_text("نام کشتی دوستت رو وارد کن:")
    context.user_data["state"] = "awaiting_friend_name"

async def process_friend_search(update: Update, context: ContextTypes.DEFAULT_TYPE, ship_name):
    user_id = update.effective_user.id
    opponent_id = None
    for uid, data in users.items():
        if data["ship_name"] == ship_name and uid != user_id:
            opponent_id = uid
            break
    if not opponent_id:
        await update.message.reply_text("کشتی پیدا نشد!")
        context.user_data["state"] = None
        return
    pending_games[user_id] = opponent_id
    await context.bot.send_message(
        opponent_id,
        f"کشتی {users[user_id]['ship_name']} برای بازی دوستانه دعوتت کرده! قبول می‌کنی؟",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ قبول", callback_data=f"accept_friend_{user_id}"),
             InlineKeyboardButton("❌ رد", callback_data=f"reject_friend_{user_id}")]
        ])
    )
    await update.message.reply_text("درخواست ارسال شد! منتظر پاسخ باش.")
    context.user_data["state"] = None

async def friend_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data.split("_")
    user_id = int(data[2])
    if data[0] == "accept_friend":
        opponent_id = query.from_user.id
        users[user_id]["cannonballs"] += 20
        users[opponent_id]["cannonballs"] += 20
        await context.bot.send_message(user_id, "بازی دوستانه شروع شد! 🏴‍☠️")
        await context.bot.send_message(opponent_id, "بازی دوستانه شروع شد! 🏴‍☠️")
        await start_battle(query, context, opponent_id)
    else:
        del pending_games[user_id]
        await context.bot.send_message(user_id, "دوستت درخواست رو رد کرد!")
    await query.message.edit_text("پاسخ داده شد!")

# ℹ️ Ship info
async def ship_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if users[user_id]["ship_name"] is None:
        await start_game(update, context)
        return
    data = users[user_id]
    win_rate = (data["wins"] / data["total_games"] * 100) if data["total_games"] > 0 else 0
    await update.message.reply_text(
        f"ℹ️ اطلاعات کشتی {data['ship_name']}:\n"
        f"💎 جم: {data['gems']}\n"
        f"🪙 کیسه طلا: {data['gold']}\n"
        f"🥈 شمش نقره: {data['silver']}\n"
        f"🏆 میانگین پیروزی: {win_rate:.1f}%\n"
        f"⚡ انرژی: {data['energy']:.1f}%"
    )

# ⚡ Energy (Display only, no purchases as per request)
async def energy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if users[user_id]["ship_name"] is None:
        await start_game(update, context)
        return
    await update.message.reply_text(
        f"⚡ انرژی جنگجویان: {users[user_id]['energy']:.1f}%\n\n"
        "اگه جنگجویانت خستن، براشون خوراکی بخر (در حال حاضر غیرفعال):\n"
        "1 بسته بیسکویت دریایی: +25% انرژی (۴ شمش نقره)\n"
        "5 عدد ماهی خشک: +35% انرژی (1 کیسه طلا، 1 شمش نقره)\n"
        "3 بسته میوه خشک‌شده: +30% انرژی (1 کیسه طلا)\n"
        "10 قالب پنیر کهنه: +50% انرژی (1 کیسه طلا، ۳ شمش نقره)\n"
        "10 بطری آب: +20% انرژی (۳ شمش نقره)\n\n"
        "⚠️ خرید در حال حاضر غیرفعال است!"
    )

# 🔁 Webhook
@app.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, application.bot)
    await application.update_queue.put(update)
    return {"ok": True}

# 🔥 Startup
@app.on_event("startup")
async def on_startup():
    await application.bot.set_webhook(url=WEBHOOK_URL)
    print("✅ Webhook set:", WEBHOOK_URL)
    await application.initialize()
    await application.start()
    await application.updater.start_polling()

# 🛑 Shutdown
@app.on_event("shutdown")
async def on_shutdown():
    await application.updater.stop()
    await application.stop()
    await application.shutdown()

# 📌 Register handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
application.add_handler(CallbackQueryHandler(fire_cannon, pattern="fire_cannon"))
application.add_handler(CallbackQueryHandler(admin_response, pattern="^(approve|reject)_"))
application.add_handler(CallbackQueryHandler(friend_response, pattern="^(accept_friend|reject_friend)_"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)

Req..: python-telegram-bot==20.3
fastapi==0.111.0
uvicorn==0.29.0

Build command: pip install -r requirements.txt

Start command: uvicorn main:app --host=0.0.0.0 --port=10000
