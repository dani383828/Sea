import os
import json
import logging
from fastapi import FastAPI, Request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, ContextTypes, MessageHandler, CallbackQueryHandler, filters
)
from datetime import datetime, timedelta
import random
import asyncio

TOKEN = "8030062261:AAFnC9AJ_2zvcaqC0LXe5Y3--d2FgxOx-fI"
WEBHOOK_PATH = f"/webhook/{TOKEN}"
WEBHOOK_URL = f"https://sea-2ri6.onrender.com{WEBHOOK_PATH}"
ADMIN_ID = 5542927340  # آیدی عددی ادمین
DATA_FILE = "game_data.json"  # فایل ذخیره‌سازی داده‌ها

# ⚙️ لاگ‌گیری
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 📦 FastAPI app
app = FastAPI()

# 🎯 ساخت ربات تلگرام
application = Application.builder().token(TOKEN).build()

# 📌 تابع برای ذخیره‌سازی داده‌ها
def save_data(context: ContextTypes.DEFAULT_TYPE):
    data = {
        "usernames": context.bot_data.get("usernames", {}),
        "user_data": {str(user_id): data for user_id, data in context.bot_data.get("user_data", {}).items()}
    }
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False)

# 📌 تابع برای بارگذاری داده‌ها
def load_data(context: ContextTypes.DEFAULT_TYPE):
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
            context.bot_data["usernames"] = data.get("usernames", {})
            context.bot_data["user_data"] = {int(user_id): data for user_id, data in data.get("user_data", {}).items()}

# 📌 هندلر برای /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if not context.bot_data.get("user_data"):
        context.bot_data["user_data"] = {}
    
    if user_id not in context.bot_data["user_data"]:
        context.bot_data["user_data"][user_id] = {"state": "waiting_for_username"}
        await update.message.reply_text("🏴‍☠️ لطفاً اسمت رو به انگلیسی وارد کن (نباید تکراری باشه):")
        save_data(context)
        return
    
    context.bot_data["user_data"][user_id]["state"] = None
    if not context.bot_data["user_data"][user_id].get("initialized"):
        context.bot_data["user_data"][user_id].update({
            "username": context.bot_data.get("usernames", {}).get(user_id, f"دزد دریایی {user_id}"),
            "gems": 5,
            "gold": 10,
            "silver": 15,
            "wins": 0,
            "games": 0,
            "energy": 100,
            "last_purchase": {},
            "score": 0,
            "cannons": 0,
            "free_cannons": 3,
            "initialized": True,
            "attack_strategy": 50,  # Default attack strategy (50%)
            "defense_strategy": 50,  # Default defense strategy (50%)
            "current_strategy": "balanced"  # Default strategy
        })
    
    keyboard = [
        ["⚔️ شروع بازی", "🛒 فروشگاه"],
        ["🏴‍☠️ برترین ناخدایان"],
        ["📕 اطلاعات کشتی", "⚡️ انرژی جنگجویان"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
    await update.message.reply_text(
        f"🏴‍☠️ خوش اومدی به دنیای دزدان دریایی، {context.bot_data['user_data'][user_id]['username']}!",
        reply_markup=reply_markup
    )
    save_data(context)

# 📌 هندلر برای دریافت نام کاربر
async def handle_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if context.bot_data.get("user_data", {}).get(user_id, {}).get("state") != "waiting_for_username":
        return
    
    username = update.message.text.strip()
    logger.info(f"User {user_id} entered username: {username}")
    if not username.isascii():
        await update.message.reply_text("⛔ لطفاً اسم رو به انگلیسی وارد کن!")
        return
    
    if not context.bot_data.get("usernames"):
        context.bot_data["usernames"] = {}
    
    if username.lower() in [u.lower() for u in context.bot_data["usernames"].values()]:
        await update.message.reply_text("⛔ این اسم قبلاً انتخاب شده! یه اسم دیگه امتحان کن.")
        return
    
    context.bot_data["user_data"][user_id]["username"] = username
    context.bot_data["user_data"][user_id]["state"] = None
    context.bot_data["usernames"][user_id] = username
    await start(update, context)
    save_data(context)

# 📌 هندلر برای برترین ناخدایان
async def top_captains(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data = context.bot_data.get("user_data", {})
    if not user_data:
        await update.message.reply_text("🏴‍☠️ هنوز هیچ ناخدایی در بازی ثبت نشده!")
        return
    
    sorted_players = sorted(
        user_data.items(),
        key=lambda x: x[1].get("score", 0),
        reverse=True
    )[:10]
    
    text = "🏴‍☠️ برترین ناخدایان:\n\n"
    for i, (player_id, data) in enumerate(sorted_players, 1):
        username = data.get("username", f"دزد دریایی {player_id}")
        score = data.get("score", 0)
        wins = data.get("wins", 0)
        games = data.get("games", 0)
        win_rate = (wins / games * 100) if games > 0 else 0
        text += f"🌟 {i}. {username} - امتیاز: {score} - میانگین برد: {win_rate:.1f}%\n"
        if player_id != user_id:  # فقط برای بازیکن‌های غیر از خود کاربر دکمه اضافه کن
            keyboard = [[InlineKeyboardButton("دعوت به جنگ دوستانه ✅", callback_data=f"request_friend_game_{player_id}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(text, reply_markup=reply_markup)
            text = ""  # برای بازیکن بعدی متن جدید شروع بشه
        else:
            await update.message.reply_text(text)
            text = ""
    
    save_data(context)

# 📌 هندلر برای شروع بازی
async def start_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    context.bot_data["user_data"][user_id]["state"] = None
    keyboard = [
        ["دریانوردی ⛵️", "توپ ☄️"],
        ["استراتژی ⚔️", "بازگشت به منو 🔙"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
    await update.message.reply_text("⚓️ انتخاب کن:", reply_markup=reply_markup)
    save_data(context)

# 📌 هندلر برای استراتژی
async def strategy_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data = context.bot_data["user_data"][user_id]
    
    keyboard = [
        ["حمله گرایانه 🗡️", "دفاعی 🛡️"],
        ["بازگشت به منو 🔙"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
    
    strategy_text = {
        "aggressive": "حمله گرایانه 🗡️",
        "defensive": "دفاعی 🛡️",
        "balanced": "متوازن ⚖️"
    }
    
    current_strategy = user_data.get("current_strategy", "balanced")
    attack_power = user_data.get("attack_strategy", 50)
    defense_power = user_data.get("defense_strategy", 50)
    
    text = (
        f"⚔️ استراتژی فعلی: {strategy_text.get(current_strategy, 'متوازن ⚖️')}\n"
        f"🗡️ قدرت حمله: {attack_power}%\n"
        f"🛡️ قدرت دفاع: {defense_power}%\n\n"
        "🌟 استراتژی جدید را انتخاب کنید:"
    )
    
    await update.message.reply_text(text, reply_markup=reply_markup)
    save_data(context)

# 📌 هندلر برای تنظیم استراتژی
async def set_strategy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    choice = update.message.text
    user_data = context.bot_data["user_data"][user_id]
    
    if choice == "حمله گرایانه 🗡️":
        keyboard = [
            ["0%", "10%", "20%"],
            ["35%", "50%", "65%"],
            ["80%", "90%", "100%"],
            ["بازگشت به منو 🔙"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
        await update.message.reply_text("🗡️ میزان قدرت حمله را انتخاب کنید:", reply_markup=reply_markup)
        user_data["state"] = "waiting_for_attack_strategy"
    elif choice == "دفاعی 🛡️":
        keyboard = [
            ["0%", "10%", "20%"],
            ["35%", "50%", "65%"],
            ["80%", "90%", "100%"],
            ["بازگشت به منو 🔙"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
        await update.message.reply_text("🛡️ میزان قدرت دفاع را انتخاب کنید:", reply_markup=reply_markup)
        user_data["state"] = "waiting_for_defense_strategy"
    elif choice == "بازگشت به منو 🔙":
        await back_to_menu(update, context)
    
    save_data(context)

# 📌 هندلر برای دریافت مقدار استراتژی
async def handle_strategy_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data = context.bot_data["user_data"].get(user_id)
    
    if not user_data:
        await update.message.reply_text("⛔ لطفاً اول با دستور /start شروع کنید!")
        return
    
    state = user_data.get("state")
    
    if state not in ["waiting_for_attack_strategy", "waiting_for_defense_strategy"]:
        return
    
    try:
        percent_str = update.message.text.replace("%", "")
        value = int(percent_str)
        if value < 0 or value > 100:
            await update.message.reply_text("⛔ لطفاً یکی از گزینه‌های معتبر را انتخاب کنید!")
            return
    except ValueError:
        await update.message.reply_text("⛔ لطفاً یکی از گزینه‌های معتبر را انتخاب کنید!")
        return
    
    if state == "waiting_for_attack_strategy":
        user_data["attack_strategy"] = value
        user_data["current_strategy"] = "aggressive" if value > 50 else "balanced"
        await update.message.reply_text(f"✅ 🗡️ قدرت حمله {value}% ذخیره شد!")
    elif state == "waiting_for_defense_strategy":
        user_data["defense_strategy"] = value
        user_data["current_strategy"] = "defensive" if value > 50 else "balanced"
        await update.message.reply_text(f"✅ 🛡️ قدرت دفاع {value}% ذخیره شد!")
    
    user_data["state"] = None
    save_data(context)
    await strategy_menu(update, context)

# 📌 هندلر برای بازگشت به منو
async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.callback_query.from_user.id if update.callback_query else update.message.from_user.id
    context.bot_data["user_data"][user_id]["state"] = None
    await start(update, context)
    if update.callback_query:
        await update.callback_query.message.delete()

# 📌 تابع برای جست‌وجوی حریف
async def search_opponent(update: Update, context: ContextTypes.DEFAULT_TYPE, cannons: int, energy: int):
    user_id = update.message.from_user.id
    await update.message.reply_text("⛵️ در حال جست‌وجوی حریف... (تا ۶۰ ثانیه)")
    await asyncio.sleep(60)
    
    opponent_id = None
    if not opponent_id:
        opponent_name = "دزد دریایی ناشناس"
    else:
        opponent_name = context.bot_data["usernames"].get(opponent_id, "ناشناس")
    
    opponent_cannons = random.randint(0, 3)
    await send_game_reports(update, context, opponent_name, cannons, energy, opponent_cannons)
    save_data(context)

# 📌 تابع برای ارسال گزارش‌های بازی
async def send_game_reports(update: Update, context: ContextTypes.DEFAULT_TYPE, opponent_name: str, cannons: int, energy: int, opponent_cannons: int):
    user_id = update.message.from_user.id
    user_data = context.bot_data["user_data"][user_id]
    
    # Calculate strategy effects
    attack_power = user_data.get("attack_strategy", 50)
    defense_power = user_data.get("defense_strategy", 50)
    
    # 100 random battle reports with emojis
    battle_reports = [
        "🏴‍☠️ ناخدا، کشتی دشمن از مه بیرون اومد! آماده نبرد شو! ⚔️",
        "⚔️ نیروهای دشمن با طناب به کشتی‌مون چنگ زدن! شمشیرها رو آماده کن! 🗡️",
        "💥 با یه شلیک توپ، عرشه دشمن شعله‌ور شد! 🔥",
        "⛵️ دشمن داره از پهلو نزدیک می‌شه! دفاع رو تقویت کن! 🛡️",
        "🗡️ ناخدا، ۳ نفر از خدمه دشمن رو با شمشیر انداختیم تو دریا! 🌊",
        "🌊 یه موج بزرگ کشتی دشمن رو تکون داد، حالا شانس ماست! 🎉",
        "☄️ توپچی‌ها شلیک کردن، ۲ نفر از دشمن کشته شدن! 💀",
        "🪵 دشمن با یه تخته چوبی داره به کشتی‌مون می‌پره! 🚢",
        "🌫️ ناخدا، یه بمب دودزا از کشتی دشمن اومد، دید کم شده! 👀",
        "⚔️ با حمله ناگهانی، ۴ نفر از اونا رو نابود کردیم! 💪",
        "💥 کشتی دشمن داره غرق می‌شه، یه شلیک دیگه بزن! ☄️",
        "🏹 نیروهای دشمن تو عرشه‌مون نفوذ کردن، به جنگشون برو! ⚔️",
        "🏹 یه تیر آرشه از کشتی دشمن اومد، یکی از خدمه زخمی شد! 😞",
        "🪓 ناخدا، با یه ضربه تبر، ۳ نفر از اونا رو نابود کردیم! 💥",
        "⛵️ دشمن داره فرار می‌کنه، تعقیبشون کنیم! 🚢",
        "💥 یه انفجار تو کشتی دشمن، ۵ نفرشون از بین رفتن! 🔥",
        "🌪️ ناخدا، طوفان داره به نفع ما می‌چرخه! 🌊",
        "🔪 دشمن با چاقو به سمت خدمه‌مون حمله کرد، ۲ نفر کشته شدن! 💀",
        "🌳 با شلیک دقیق، دکل دشمن شکسته شد! ⛵️",
        "🏴‍☠️ نیروهای دشمن دارن تسلیم می‌شن، جلو برو! ⚔️",
        "🪢 ناخدا، یه گروه از اونا با قایق به کشتی‌مون چسبیدن! 🚤",
        "🗡️ با شمشیر هامون، ۶ نفر از اونا رو به زانو درآوردیم! 💪",
        "🌫️ دشمن داره از دود استفاده می‌کنه، مراقب باش! 👀",
        "💥 با شلیک توپ، عرشه دشمن نابود شد! 🔥",
        "🔫 ناخدا، ۴ نفر از خدمه دشمن رو با تفنگ زدیم! 💥",
        "⛵️ کشتی دشمن داره می‌لرزه، شانس ماست! 🎉",
        "🪢 دشمن با یه طناب بزرگ داره به کشتی‌مون میاد! 🚢",
        "🗡️ ناخدا، با یه ضربه، ۵ نفر از اونا رو کشتیم! 💀",
        "🌊 یه موج، قایق دشمن رو واژگون کرد! ⛵️",
        "🎯 دشمن داره با نیزه حمله می‌کنه، دفاع کن! 🛡️",
        "💥 با شلیک توپ، ۳ نفر از اونا تو دریا غرق شدن! 🌊",
        "🏚️ ناخدا، یه گروه کوچک از دشمن تو انبار پنهان شدن! 👀",
        "💣 دشمن با باروت حمله می‌کنه، عقب‌نشینی کن! ⚠️",
        "🪓 با تبر هامون، ۷ نفر از اونا رو از بین بردیم! 💪",
        "🔥 کشتی دشمن داره آتش می‌گیره، ادامه بده! ⛵️",
        "🏹 ناخدا، یه تیر کمان از دشمن به بادبانمون خورد! 😞",
        "🪵 دشمن با یه تخته چوب داره به عرشه می‌پره! 🚢",
        "🔫 با شلیک، ۴ نفر از خدمه دشمن کشته شدن! 💥",
        "🌪️ ناخدا، طوفان داره کشتی دشمن رو نابود می‌کنه! 🌊",
        "🔪 دشمن داره با شمشیر به سمت ما می‌دوه! ⚔️",
        "🗡️ با یه ضربه قوی، ۶ نفر از اونا رو نابود کردیم! 💪",
        "💥 کشتی دشمن داره غرق می‌شه، شلیک دیگه‌ای بزن! ☄️",
        "🏹 ناخدا، یه گروه از اونا دارن از پشت حمله می‌کنن! ⚠️",
        "🔫 با تفنگ، ۳ نفر از دشمن رو از پای درآوردیم! 💥",
        "🌫️ دشمن داره با دود غلیظ ما رو گیج می‌کنه! 👀",
        "💥 ناخدا، با یه شلیک، دکل دشمن شکست! ⛵️",
        "⛵️ دشمن با قایق‌های کوچک نزدیک می‌شه! 🚤",
        "🗡️ با شمشیر، ۵ نفر از اونا رو به دریا انداختیم! 🌊",
        "🔥 ناخدا، یه انفجار تو کشتی دشمن رخ داد! 💥",
        "🔪 دشمن با چاقو به خدمه‌مون حمله می‌کنه! ⚔️",
        "💥 با توپ، ۴ نفر از اونا رو نابود کردیم! ☄️",
        "🌪️ ناخدا، طوفان به ضرر دشمن می‌چرخه! 🌊",
        "🪢 دشمن با طناب به دکل ما چسبیده! 🚢",
        "🪓 با تبر، ۶ نفر از اونا رو کشتیم! 💪",
        "🔥 کشتی دشمن داره می‌شکنه، ادامه بده! ⛵️",
        "🏹 ناخدا، یه تیر آرشه به سینه یکی از اونا خورد! 💀",
        "🌫️ دشمن با بمب دودزا داره ما رو محاصره می‌کنه! ⚠️",
        "💥 با شلیک، ۵ نفر از خدمه دشمن غرق شدن! 🌊",
        "🌊 ناخدا، یه موج بزرگ کشتی دشمن رو واژگون کرد! ⛵️",
        "🎯 دشمن با نیزه به سمت عرشه میاد! 🛡️",
        "🗡️ با شمشیر، ۷ نفر از اونا رو نابود کردیم! 💪",
        "🔥 کشتی دشمن داره می‌سوزه، شانس ماست! 🎉",
        "🏚️ ناخدا، یه گروه از اونا تو زیرزمین پنهان شدن! 👀",
        "💣 دشمن با باروت به ما حمله می‌کنه! ⚠️",
        "🪓 با تبر، ۴ نفر از اونا رو از پای درآوردیم! 💥",
        "🌪️ ناخدا، طوفان داره کشتی‌مون رو نجات می‌ده! 🌊",
        "🔪 دشمن با چاقو به خدمه حمله می‌کنه! ⚔️",
        "💥 با شلیک توپ، ۶ نفر از اونا کشته شدن! ☄️",
        "⛵️ کشتی دشمن داره غرق می‌شه، تعقیب کن! 🚢",
        "🏹 ناخدا، یه تیر کمان به دکل دشمن خورد! 💥",
        "🪵 دشمن با تخته چوب به عرشه می‌پره! 🚢",
        "🔫 با تفنگ، ۵ نفر از اونا رو نابود کردیم! 💪",
        "🔥 ناخدا، یه انفجار تو انبار دشمن رخ داد! 💥",
        "🪢 دشمن با طناب به کشتی‌مون میاد! 🚤",
        "🗡️ با شمشیر، ۸ نفر از اونا رو به دریا انداختیم! 🌊",
        "🔥 کشتی دشمن داره می‌شکنه، شانس ماست! 🎉",
        "🌪️ ناخدا، طوفان به نفع ما می‌چرخه! 🌊",
        "🎯 دشمن با نیزه به سمت ما حمله می‌کنه! 🛡️",
        "💥 با شلیک، ۴ نفر از خدمه دشمن کشته شدن! 💀",
        "🌊 ناخدا، یه موج کشتی دشمن رو نابود کرد! ⛵️",
        "🌫️ دشمن با دود ما رو گیج می‌کنه! 👀",
        "🪓 با تبر، ۶ نفر از اونا رو از بین بردیم! 💪",
        "🔥 کشتی دشمن داره می‌سوزه، ادامه بده! ⛵️",
        "🏹 ناخدا، یه تیر آرشه به دشمن برخورد کرد! 💥",
        "🌫️ دشمن با بمب دودزا ما رو محاصره می‌کنه! ⚠️",
        "💥 با توپ، ۵ نفر از اونا غرق شدن! 🌊",
        "🌪️ ناخدا، طوفان دشمن رو نابود می‌کنه! 🌊",
        "🔪 دشمن با چاقو به خدمه‌مون حمله کرد! ⚔️",
        "💥 با شلیک، ۷ نفر از اونا رو نابود کردیم! 💪",
        "🔥 کشتی دشمن داره غرق می‌شه، شانس ماست! 🎉",
        "🏹 ناخدا، یه گروه از اونا دارن فرار می‌کنن! ⛵️",
        "🪢 دشمن با طناب به دکل ما چسبیده! 🚢",
        "🗡️ با شمشیر، ۶ نفر از اونا رو کشتیم! 💀",
        "🔥 ناخدا، یه انفجار تو کشتی دشمن رخ داد! 💥",
        "⛵️ دشمن با قایق‌های کوچک نزدیک می‌شه! 🚤",
        "🪓 با تبر، ۵ نفر از اونا رو نابود کردیم! 💪",
        "🔥 کشتی دشمن داره می‌شکنه، ادامه بده! ⛵️",
        "🌪️ ناخدا، طوفان به نفع ماست! 🌊",
        "🎯 دشمن با نیزه به عرشه حمله می‌کنه! 🛡️",
        "💥 با شلیک، ۴ نفر از اونا کشته شدن! 💀",
        "🌊 ناخدا، یه موج بزرگ دشمن رو غرق کرد! ⛵️",
        "🌫️ دشمن با دود داره ما رو گیج می‌کنه! 👀",
        "🗡️ با شمشیر، ۷ نفر از اونا رو از پای درآوردیم! 💪"
    ]
    
    num_reports = random.randint(6, 20)
    selected_messages = random.sample(battle_reports, min(num_reports, len(battle_reports)))
    
    total_duration = 60
    interval = total_duration / len(selected_messages)
    
    for msg in selected_messages:
        await update.message.reply_text(msg)
        await asyncio.sleep(interval)
    
    # Calculate win chance considering strategies
    base_win_chance = min(100, (cannons * 20) + (energy / 2))
    strategy_bonus = (attack_power - 50) * 0.5  # Up to +25% for full attack
    win_chance = min(100, base_win_chance + strategy_bonus)
    
    opponent_chance = random.uniform(20, 80)
    win = random.random() * 100 < win_chance
    
    report = "🏴‍☠️ کاپیتان، کشتیمون سوراخ شد! ⛔" if not win else "🏴‍☠️ کاپیتان، دشمن رو غرق کردیم! 🏆"
    context.bot_data["user_data"][user_id]["games"] += 1
    context.bot_data["user_data"][user_id]["energy"] = max(0, context.bot_data["user_data"][user_id]["energy"] - 5)
    
    if win:
        context.bot_data["user_data"][user_id]["wins"] += 1
        context.bot_data["user_data"][user_id]["score"] += 30
        context.bot_data["user_data"][user_id]["gold"] += 3
        context.bot_data["user_data"][user_id]["silver"] += 5
        context.bot_data["user_data"][user_id]["energy"] = min(100, context.bot_data["user_data"][user_id]["energy"] + 10)
        if random.random() < 0.25:
            context.bot_data["user_data"][user_id]["gems"] += 1
            report += "\n💎 یه جم پیدا کردیم! 🎉"
        report += "\n🏆 جایزه: ۳۰ امتیاز, 3 🪙 کیسه طلا, 5 🥈 شمش نقره, +10% ⚡ انرژی"
    else:
        context.bot_data["user_data"][user_id]["score"] = max(0, context.bot_data["user_data"][user_id]["score"] - 10)
        if context.bot_data["user_data"][user_id]["gold"] >= 3:
            context.bot_data["user_data"][user_id]["gold"] -= 3
        if context.bot_data["user_data"][user_id]["silver"] >= 5:
            context.bot_data["user_data"][user_id]["silver"] -= 5
        if random.random() < 0.25 and context.bot_data["user_data"][user_id]["gems"] >= 1:
            context.bot_data["user_data"][user_id]["gems"] -= 1
            report += "\n💎 یه جم از دست دادیم! 😢"
        context.bot_data["user_data"][user_id]["energy"] = max(0, context.bot_data["user_data"][user_id]["energy"] - 30)
        report += "\n⛔ جریمه: -10 امتیاز, -3 🪙 کیسه طلا, -5 🥈 شمش نقره, -30% ⚡ انرژی"
    
    await update.message.reply_text(f"⚔️ بازی با {opponent_name}:\n{report}")
    save_data(context)

# 📌 هندلر برای پردازش بازی و خرید توپ
async def handle_game_options(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    choice = update.message.text
    if choice == "بازگشت به منو 🔙":
        await back_to_menu(update, context)
        return
    
    if choice == "دریانوردی ⛵️":
        cannons = context.bot_data["user_data"][user_id]["cannons"]
        energy = context.bot_data["user_data"][user_id]["energy"]
        asyncio.create_task(search_opponent(update, context, cannons, energy))
    
    elif choice == "توپ ☄️":
        free_cannons = context.bot_data["user_data"][user_id]["free_cannons"]
        if free_cannons > 0:
            context.bot_data["user_data"][user_id]["cannons"] += 1
            context.bot_data["user_data"][user_id]["free_cannons"] -= 1
            await update.message.reply_text(f"☄️ یه توپ رایگان گرفتی! ({free_cannons - 1} توپ رایگان باقی مونده)")
        else:
            keyboard = [
                [InlineKeyboardButton("خرید توپ (۱ جم)", callback_data="buy_cannon_gem")],
                [InlineKeyboardButton("خرید توپ (۵ کیسه طلا)", callback_data="buy_cannon_gold")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("☄️ توپ رایگان تموم شده! می‌تونی با جم یا طلا بخری:", reply_markup=reply_markup)
        save_data(context)
    
    elif choice == "استراتژی ⚔️":
        await strategy_menu(update, context)
    
    elif choice in ["حمله گرایانه 🗡️", "دفاعی 🛡️"]:
        await set_strategy(update, context)

# 📌 هندلر برای خرید توپ
async def handle_cannon_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    
    if query.data == "buy_cannon_gem":
        if context.bot_data["user_data"][user_id]["gems"] >= 1:
            context.bot_data["user_data"][user_id]["gems"] -= 1
            context.bot_data["user_data"][user_id]["cannons"] += 1
            await query.message.reply_text("☄️ 💎 یه توپ با ۱ جم خریدی!")
        else:
            await query.message.reply_text("⛔ 💎 جم کافی نداری!")
    elif query.data == "buy_cannon_gold":
        if context.bot_data["user_data"][user_id]["gold"] >= 5:
            context.bot_data["user_data"][user_id]["gold"] -= 5
            context.bot_data["user_data"][user_id]["cannons"] += 1
            await query.message.reply_text("☄️ 🪙 یه توپ با ۵ کیسه طلا خریدی!")
        else:
            await query.message.reply_text("⛔ 🪙 کیسه طلا کافی نداری!")
    await query.message.delete()
    save_data(context)

# 📌 هندلر برای پردازش درخواست جنگ دوستانه
async def handle_friend_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    
    if query.data == "back_to_menu":
        await back_to_menu(update, context)
        return
    
    if query.data.startswith("request_friend_game_"):
        target_id = int(query.data.split("_")[3])
        requester_id = user_id
        requester_data = context.bot_data["user_data"].get(requester_id, {})
        requester_name = requester_data.get("username", f"دزد دریایی {requester_id}")
        
        # اطلاعات کشتی درخواست‌دهنده
        gems = requester_data.get("gems", 5)
        gold = requester_data.get("gold", 10)
        silver = requester_data.get("silver", 15)
        wins = requester_data.get("wins", 0)
        games = requester_data.get("games", 0)
        energy = requester_data.get("energy", 100)
        attack = requester_data.get("attack_strategy", 50)
        defense = requester_data.get("defense_strategy", 50)
        win_rate = (wins / games * 100) if games > 0 else 0
        
        text = (
            f"🏴‍☠️ کاربر {requester_name} با این اطلاعات کشتی بهت درخواست جنگ دوستانه داده! قبول می‌کنی? ⚔️\n"
            f"📕 اطلاعات کشتی {requester_name}:\n"
            f"💎 جم: {gems}\n"
            f"🪙 کیسه طلا: {gold}\n"
            f"🥈 شمش نقره: {silver}\n"
            f"🏆 میانگین پیروزی: {win_rate:.1f}%\n"
            f"⚡ انرژی: {energy}%\n"
            f"🗡️ قدرت حمله: {attack}%\n"
            f"🛡️ قدرت دفاع: {defense}%"
        )
        
        keyboard = [
            [InlineKeyboardButton("قبول می‌کنم ✅", callback_data=f"accept_friend_game_{requester_id}_{target_id}")],
            [InlineKeyboardButton("قبول نمی‌کنم ❌", callback_data=f"reject_friend_game_{requester_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(target_id, text, reply_markup=reply_markup)
        await query.message.reply_text(f"⚔️ درخواست جنگ دوستانه برای {context.bot_data['usernames'].get(target_id, 'ناشناس')} ارسال شد! ⏳")
        await query.message.delete()
        save_data(context)
        return
    
    if query.data.startswith("reject_friend_game_"):
        requester_id = int(query.data.split("_")[3])
        requester_name = context.bot_data["usernames"].get(requester_id, f"دزد دریایی {requester_id}")
        await query.message.reply_text("⛔ درخواست جنگ دوستانه رد شد! 😞")
        await context.bot.send_message(requester_id, f"🏴‍☠️ کاربر {context.bot_data['usernames'].get(user_id, 'ناشناس')} درخواست جنگ دوستانه‌ات رو رد کرد! ⚠️")
        await query.message.edit_reply_markup(reply_markup=None)
        save_data(context)
        return
    
    if query.data.startswith("accept_friend_game_"):
        requester_id, target_id = map(int, query.data.split("_")[3:5])
        requester_name = context.bot_data["usernames"].get(requester_id, f"دزد دریایی {requester_id}")
        target_name = context.bot_data["usernames"].get(target_id, f"دزد دریایی {target_id}")
        
        requester_data = context.bot_data["user_data"].get(requester_id, {})
        target_data = context.bot_data["user_data"].get(target_id, {})
        
        requester_cannons = requester_data.get("cannons", 0)
        requester_energy = requester_data.get("energy", 100)
        requester_attack = requester_data.get("attack_strategy", 50)
        requester_defense = requester_data.get("defense_strategy", 50)
        
        target_cannons = target_data.get("cannons", 0)
        target_energy = target_data.get("energy", 100)
        target_attack = target_data.get("attack_strategy", 50)
        target_defense = target_data.get("defense_strategy", 50)
        
        # Calculate win chance considering strategies
        requester_chance = min(100, (requester_cannons * 20) + (requester_energy / 2))
        requester_chance += (requester_attack - 50) * 0.5  # Attack bonus
        
        target_chance = min(100, (target_cannons * 20) + (target_energy / 2))
        target_chance += (target_attack - 50) * 0.5  # Attack bonus
        
        # Apply defense reductions
        requester_chance -= (target_defense / 100) * 30  # Defense can reduce by up to 30%
        target_chance -= (requester_defense / 100) * 30  # Defense can reduce by up to 30%
        
        win = random.random() * (requester_chance + target_chance) < requester_chance
        
        requester_data["games"] = requester_data.get("games", 0) + 1
        target_data["games"] = target_data.get("games", 0) + 1
        requester_data["energy"] = max(0, requester_data.get("energy", 100) - 5)
        target_data["energy"] = max(0, target_data.get("energy", 100) - 5)
        
        requester_report = f"⚔️ بازی دوستانه با {target_name}:\n"
        target_report = f"⚔️ بازی دوستانه با {requester_name}:\n"
        
        if win:
            requester_data["wins"] = requester_data.get("wins", 0) + 1
            requester_report += "🏴‍☠️ کاپیتان، دشمن رو غرق کردیم! 🏆 🎉"
            target_report += "🏴‍☠️ کاپیتان، کشتیمون سوراخ شد! ⛔ 😞"
        else:
            target_data["wins"] = target_data.get("wins", 0) + 1
            target_report += "🏴‍☠️ کاپیتان، دشمن رو غرق کردیم! 🏆 🎉"
            requester_report += "🏴‍☠️ کاپیتان، کشتیمون سوراخ شد! ⛔ 😞"
        
        # ارسال گزارش بازی
        messages = [
            "🏴‍☠️ نبرد دوستانه آغاز شد! کشتی‌ها در افق به هم نزدیک می‌شن! ⚔️",
            "🌊 طوفان در راهه! دریا داره خشمگین می‌شه! 🌪️",
            f"⚡ جنگجویان شما با انرژی {requester_energy}% آماده‌اند! 💪",
            f"⚡ جنگجویان حریف با انرژی {target_energy}% آماده‌اند! 💪",
            f"🗡️ قدرت حمله شما: {requester_attack}% - 🛡️ قدرت دفاع شما: {requester_defense}%",
            f"🗡️ قدرت حمله حریف: {target_attack}% - 🛡️ قدرت دفاع حریف: {target_defense}%"
        ]
        
        for i in range(requester_cannons):
            hit_chance = 0.5 * (requester_attack / 100)
            hit = random.random() < hit_chance
            messages.append(f"☄️ شلیک توپ {i+1} از {requester_name}! {'برخورد کرد! 💥' if hit else 'خطا رفت! 😞'}")
        
        for i in range(target_cannons):
            hit_chance = 0.5 * (target_attack / 100)
            defense_reduction = (requester_defense / 100) * 0.3
            hit = random.random() < (hit_chance - defense_reduction)
            messages.append(f"☄️ شلیک توپ {i+1} از {target_name}! {'برخورد کرد! 💥' if hit else 'خطا رفت! 😞'}")
        
        num_reports = random.randint(5, 10)
        selected_messages = random.sample(messages, min(num_reports, len(messages)))
        total_duration = 30
        interval = total_duration / len(selected_messages)
        
        for msg in selected_messages:
            await context.bot.send_message(requester_id, msg)
            await context.bot.send_message(target_id, msg)
            await asyncio.sleep(interval)
        
        await context.bot.send_message(requester_id, requester_report)
        await query.message.reply_text(target_report)
        await query.message.edit_reply_markup(reply_markup=None)
        save_data(context)

# 📌 هندلر برای فروشگاه
async def shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["💎 خرید جم"],
        ["☄️ خرید توپ"],
        ["🔙 بازگشت به منو"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
    await update.message.reply_text(
        "🛒 فروشگاه دزدان دریایی 🌊:\n🌟 گزینه‌ها رو انتخاب کن:",
        reply_markup=reply_markup
    )
    save_data(context)

# 📌 هندلر برای خرید جم
async def buy_gems(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("25 جم - 5 ترون", callback_data="buy_25_gems")],
        [InlineKeyboardButton("50 جم - 8 ترون", callback_data="buy_50_gems")],
        [InlineKeyboardButton("100 جم - 14 ترون", callback_data="buy_100_gems")],
        [InlineKeyboardButton("🔙 بازگشت به فروشگاه", callback_data="back_to_shop")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "💎 خرید جم:\n"
        "25 جم = 5 ترون\n"
        "50 جم = 8 ترون\n"
        "100 جم = 14 ترون\n\n"
        "آدرس ترون: TJ4xrw8KJz7jk6FjkVqRw8h3Az5Ur4kLkb\n"
        "پس از پرداخت، فیش رو بفرست تا تأیید بشه.",
        reply_markup=reply_markup
    )

# 📌 هندلر برای خرید توپ
async def buy_cannons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("1 توپ - 3 جم", callback_data="buy_1_cannon")],
        [InlineKeyboardButton("3 توپ - 7 جم", callback_data="buy_3_cannons")],
        [InlineKeyboardButton("10 توپ - 18 جم", callback_data="buy_10_cannons")],
        [InlineKeyboardButton("20 توپ - 30 جم", callback_data="buy_20_cannons")],
        [InlineKeyboardButton("🔙 بازگشت به فروشگاه", callback_data="back_to_shop")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "☄️ خرید توپ:\n"
        "1 توپ = 3 جم\n"
        "3 توپ = 7 جم\n"
        "10 توپ = 18 جم\n"
        "20 توپ = 30 جم",
        reply_markup=reply_markup
    )

# 📌 هندلر برای پردازش خریدها
async def handle_shop_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    
    if query.data == "back_to_shop":
        await shop(update, context)
        await query.message.delete()
        return
    
    if query.data.startswith("buy_") and "_gems" in query.data:
        await buy_gems(update, context)
        await query.message.delete()
        return
    
    if query.data.startswith("buy_") and "_cannon" in query.data:
        if query.data == "buy_1_cannon":
            gems_needed = 3
            cannons = 1
        elif query.data == "buy_3_cannons":
            gems_needed = 7
            cannons = 3
        elif query.data == "buy_10_cannons":
            gems_needed = 18
            cannons = 10
        elif query.data == "buy_20_cannons":
            gems_needed = 30
            cannons = 20
        
        if context.bot_data["user_data"][user_id]["gems"] >= gems_needed:
            context.bot_data["user_data"][user_id]["gems"] -= gems_needed
            context.bot_data["user_data"][user_id]["cannons"] += cannons
            await query.message.reply_text(f"✅ {cannons} توپ با {gems_needed} جم خریداری شد! ☄️")
        else:
            await query.message.reply_text("⛔ جم کافی ندارید!")
        await query.message.delete()
        return
    
    save_data(context)

# 📌 هندلر برای اطلاعات کشتی
async def ship_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data = context.bot_data["user_data"][user_id]
    gems = user_data.get("gems", 5)
    gold = user_data.get("gold", 10)
    silver = user_data.get("silver", 15)
    wins = user_data.get("wins", 0)
    games = user_data.get("games", 0)
    energy = user_data.get("energy", 100)
    attack = user_data.get("attack_strategy", 50)
    defense = user_data.get("defense_strategy", 50)
    strategy = user_data.get("current_strategy", "balanced")
    
    strategy_text = {
        "aggressive": "حمله گرایانه 🗡️",
        "defensive": "دفاعی 🛡️",
        "balanced": "متوازن ⚖️"
    }
    
    win_rate = (wins / games * 100) if games > 0 else 0
    text = (
        "📕 اطلاعات کشتی 🌟:\n"
        f"💎 جم: {gems}\n"
        f"🪙 کیسه طلا: {gold}\n"
        f"🥈 شمش نقره: {silver}\n"
        f"🏆 میانگین پیروزی: {win_rate:.1f}%\n"
        f"⚡ انرژی: {energy}%\n"
        f"⚔️ استراتژی فعلی: {strategy_text.get(strategy, 'متوازن ⚖️')}\n"
        f"🗡️ قدرت حمله: {attack}%\n"
        f"🛡️ قدرت دفاع: {defense}%"
    )
    await update.message.reply_text(text)

# 📌 هندلر برای انرژی جنگجویان
async def warriors_energy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data = context.bot_data["user_data"][user_id]
    energy = user_data.get("energy", 100)
    now = datetime.now()
    last_purchase = user_data.get("last_purchase", {})
    
    available_items = []
    items = [
        ("۱ بسته بیسکویت دریایی (۲۵٪ ⚡ انرژی)", "biscuit", 0, 4, 25),
        ("۵ عدد ماهی خشک (۳۵٪ ⚡ انرژی)", "fish", 1, 1, 35),
        ("۳ بسته میوه خشک‌شده (۳۰٪ ⚡ انرژی)", "fruit", 1, 0, 30),
        ("۱۰ قالب پنیر کهنه (۵۰٪ ⚡ انرژی)", "cheese", 1, 3, 50),
        ("۱۰ بطری آب (۲۰٪ ⚡ انرژی)", "water", 0, 3, 20),
    ]
    
    for item_name, item_id, gold_cost, silver_cost, energy_gain in items:
        last_time = last_purchase.get(item_id)
        if not last_time or (now - last_time).total_seconds() >= 24 * 3600:
            available_items.append(
                [InlineKeyboardButton(f"{item_name} - قیمت: {gold_cost} 🪙, {silver_cost} 🥈", callback_data=f"buy_{item_id}")]
            )
    
    reply_markup = InlineKeyboardMarkup(available_items) if available_items else None
    text = f"⚡ انرژی جنگجویان: {energy}%\n"
    if energy < 100:
        text += "🏴‍☠️ اگر جنگجویان خسته‌اند، خوراکی بخر! 🌟"
    else:
        text += "✅ جنگجویان پر از انرژی‌اند! 💪"
    
    await update.message.reply_text(text, reply_markup=reply_markup)

# 📌 هندلر برای پردازش پیام‌های فروشگاه
async def handle_shop_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "💎 خرید جم":
        await buy_gems(update, context)
    elif text == "☄️ خرید توپ":
        await buy_cannons(update, context)
    elif text == "🔙 بازگشت به منو":
        await back_to_menu(update, context)

# 📌 هندلر برای دریافت فیش
async def handle_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    pending_gems = context.bot_data["user_data"][user_id].get("pending_gems", 0)
    if pending_gems == 0:
        await update.message.reply_text("⛔ هیچ خریدی در انتظار تأیید نیست! 😞")
        return
    
    keyboard = [
        [InlineKeyboardButton("تأیید ✅", callback_data=f"confirm_{user_id}_{pending_gems}")],
        [InlineKeyboardButton("رد ❌", callback_data=f"reject_{user_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.message.photo:
        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=update.message.photo[-1].file_id,
            caption=f"💰 فیش پرداخت از کاربر {user_id} برای {pending_gems} جم 🌟",
            reply_markup=reply_markup
        )
    elif update.message.text:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"💰 فیش متنی از کاربر {user_id} برای {pending_gems} جم:\n{update.message.text} 🌟",
            reply_markup=reply_markup
        )
    
    await update.message.reply_text("💌 فیش به ادمین ارسال شد! منتظر تأیید باش ⏳")
    save_data(context)

# 📌 هندلر برای تأیید/رد فیش توسط ادمین
async def handle_admin_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    if data.startswith("confirm_"):
        _, user_id, gems = data.split("_")
        user_id, gems = int(user_id), int(gems)
        context.bot_data["user_data"][user_id]["gems"] += gems
        context.bot_data["user_data"][user_id]["pending_gems"] = 0
        await context.bot.send_message(user_id, f"✅ 💎 خریدت تأیید شد! {gems} جم اضافه شد! 🎉")
        await query.message.edit_reply_markup(reply_markup=None)
    elif data.startswith("reject_"):
        _, user_id = data.split("_")
        user_id = int(user_id)
        context.bot_data["user_data"][user_id]["pending_gems"] = 0
        await context.bot.send_message(user_id, "⛔ خریدت رد شد! دوباره تلاش کن 😞")
        await query.message.edit_reply_markup(reply_markup=None)
    save_data(context)

# 📌 هندلر برای خرید خوراکی
async def handle_food_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    
    data = query.data
    now = datetime.now()
    items = {
        "buy_biscuit": (0, 4, 25),
        "buy_fish": (1, 1, 35),
        "buy_fruit": (1, 0, 30),
        "buy_cheese": (1, 3, 50),
        "buy_water": (0, 3, 20),
    }
    
    if data in items:
        gold_cost, silver_cost, energy_gain = items[data]
        gold = context.bot_data["user_data"][user_id]["gold"]
        silver = context.bot_data["user_data"][user_id]["silver"]
        energy = context.bot_data["user_data"][user_id]["energy"]
        
        if gold >= gold_cost and silver >= silver_cost:
            context.bot_data["user_data"][user_id]["gold"] -= gold_cost
            context.bot_data["user_data"][user_id]["silver"] -= silver_cost
            context.bot_data["user_data"][user_id]["energy"] = min(100, energy + energy_gain)
            context.bot_data["user_data"][user_id]["last_purchase"][data.replace("buy_", "")] = now
            await query.message.reply_text(f"✅ 🌟 خرید انجام شد! {energy_gain}% ⚡ انرژی اضافه شد! 🎉")
        else:
            await query.message.reply_text("⛔ 🪙 یا 🥈 کافی نیست! 😞")
        await query.message.delete()
        await warriors_energy(update, context)
    save_data(context)

# 🔗 ثبت هندلرها
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.Regex("^🛒 فروشگاه$"), shop))
application.add_handler(MessageHandler(filters.Regex("^📕 اطلاعات کشتی$"), ship_info))
application.add_handler(MessageHandler(filters.Regex("^⚡️ انرژی جنگجویان$"), warriors_energy))
application.add_handler(MessageHandler(filters.Regex("^⚔️ شروع بازی$"), start_game))
application.add_handler(MessageHandler(filters.Regex("^🏴‍☠️ برترین ناخدایان$"), top_captains))
application.add_handler(MessageHandler(filters.Regex("^(دریانوردی ⛵️|توپ ☄️|بازگشت به منو 🔙|استراتژی ⚔️)$"), handle_game_options))
application.add_handler(MessageHandler(filters.Regex("^(حمله گرایانه 🗡️|دفاعی 🛡️)$"), set_strategy))
application.add_handler(MessageHandler(filters.Regex("^(0%|10%|20%|35%|50%|65%|80%|90%|100%)$"), handle_strategy_input))
application.add_handler(MessageHandler(filters.Regex("^(💎 خرید جم|☄️ خرید توپ|🔙 بازگشت به منو)$"), handle_shop_message))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex("^(🛒|📕|⚡️|⚔️|🏴‍☠️|دریانوردی ⛵️|توپ ☄️|بازگشت به منو 🔙|استراتژی ⚔️|حمله گرایانه 🗡️|دفاعی 🛡️|0%|10%|20%|35%|50%|65%|80%|90%|100%|💎 خرید جم|☄️ خرید توپ|🔙 بازگشت به منو)$") & filters.UpdateType.MESSAGE, handle_username))
application.add_handler(CallbackQueryHandler(handle_purchase, pattern="buy_.*_gems"))
application.add_handler(CallbackQueryHandler(handle_shop_purchase, pattern="buy_.*_cannon"))
application.add_handler(CallbackQueryHandler(handle_food_purchase, pattern="buy_(biscuit|fish|fruit|cheese|water)"))
application.add_handler(CallbackQueryHandler(handle_admin_response, pattern="(confirm|reject)_.*"))
application.add_handler(CallbackQueryHandler(handle_cannon_purchase, pattern="buy_cannon_(gem|gold)"))
application.add_handler(CallbackQueryHandler(handle_friend_game, pattern="^(request_friend_game|accept_friend_game|reject_friend_game|back_to_menu|back_to_shop)_.*"))

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
    load_data(application)
    await application.bot.set_webhook(url=WEBHOOK_URL)
    print("✅ Webhook set:", WEBHOOK_URL)
    await application.initialize()
    await application.start()

# 🛑 هنگام خاموشی
@app.on_event("shutdown")
async def on_shutdown():
    save_data(application)
    await application.updater.stop()
    await application.stop()
    await application.shutdown()
