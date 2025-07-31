import os
import json
import logging
from fastapi import FastAPI, Request, HTTPException
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application, CommandHandler, ContextTypes, MessageHandler, CallbackQueryHandler, filters
)
from datetime import datetime, timedelta
import random
import asyncio
import uvicorn

# ⚙️ تنظیمات اولیه
TOKEN = "8030062261:AAFnC9AJ_2zvcaqC0LXe5Y3--d2FgxOx-fI"
WEBHOOK_PATH = f"/webhook/{TOKEN}"
WEBHOOK_URL = f"https://sea-2ri6.onrender.com{WEBHOOK_PATH}"
ADMIN_ID = 5542927340
DATA_FILE = "game_data.json"

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
    try:
        data = {
            "usernames": context.bot_data.get("usernames", {}),
            "user_data": {str(user_id): data for user_id, data in context.bot_data.get("user_data", {}).items()}
        }
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        logger.info("Data saved successfully")
    except Exception as e:
        logger.error(f"Error saving data: {e}")

# 📌 تابع برای بارگذاری داده‌ها
def load_data(context: ContextTypes.DEFAULT_TYPE):
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
                context.bot_data["usernames"] = data.get("usernames", {})
                user_data = {}
                for user_id_str, user_data_dict in data.get("user_data", {}).items():
                    try:
                        user_id = int(user_id_str)
                        user_data[user_id] = user_data_dict
                    except (ValueError, TypeError):
                        continue
                context.bot_data["user_data"] = user_data
            logger.info("Data loaded successfully")
        else:
            context.bot_data["usernames"] = {}
            context.bot_data["user_data"] = {}
            logger.info("No data file found, initialized empty data structures")
    except Exception as e:
        logger.error(f"Error loading data: {e}")
        context.bot_data["usernames"] = {}
        context.bot_data["user_data"] = {}

# 📌 هندلر برای /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.message.from_user.id
        username = update.message.from_user.username or f"user_{user_id}"
        
        if "user_data" not in context.bot_data:
            context.bot_data["user_data"] = {}
        if "usernames" not in context.bot_data:
            context.bot_data["usernames"] = {}
        
        if user_id not in context.bot_data["user_data"]:
            context.bot_data["user_data"][user_id] = {
                "state": "waiting_for_language",
                "language": "persian",
                "pending_gems": 0
            }
            keyboard = [
                [InlineKeyboardButton("🇬🇧 English", callback_data="set_language_english")],
                [InlineKeyboardButton("🇮🇷 Persian", callback_data="set_language_persian")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("🌐 Please select your language / لطفاً زبان خود را انتخاب کنید:", reply_markup=reply_markup)
            save_data(context)
            return
        
        user_data = context.bot_data["user_data"][user_id]
        language = user_data.get("language", "persian")
        
        required_fields = {
            "username": context.bot_data["usernames"].get(user_id, f"دزد دریایی {user_id}" if language == "persian" else f"Pirate {user_id}"),
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
            "drones": 0,
            "free_drones": 1,
            "level": 1,
            "initialized": True,
            "attack_strategy": 50,
            "defense_strategy": 50,
            "current_strategy": "balanced",
            "pending_gems": 0,
            "state": None
        }
        
        for field, default_value in required_fields.items():
            if field not in user_data:
                user_data[field] = default_value
        
        if user_data["username"] != context.bot_data["usernames"].get(user_id):
            context.bot_data["usernames"][user_id] = user_data["username"]
        
        score = user_data.get("score", 0)
        user_data["level"] = 5 if score >= 600 else 4 if score >= 450 else 3 if score >= 300 else 2 if score >= 150 else 1
        
        keyboard = [
            ["⚔️ شروع بازی" if language == "persian" else "⚔️ Start Game", "🛒 فروشگاه" if language == "persian" else "🛒 Shop"],
            ["🏴‍☠️ برترین ناخدایان" if language == "persian" else "🏴‍☠️ Top Captains"],
            ["📕 اطلاعات کشتی" if language == "persian" else "📕 Ship Info", "⚡️ انرژی جنگجویان" if language == "persian" else "⚡️ Warriors' Energy"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
        welcome_text = (
            f"🏴‍☠️ خوش اومدی به دنیای دزدان دریایی، {user_data['username']}!" if language == "persian" else
            f"🏴‍☠️ Welcome to the world of pirates, {user_data['username']}!"
        )
        await update.message.reply_text(welcome_text, reply_markup=reply_markup)
        save_data(context)
    except Exception as e:
        logger.error(f"Error in start handler: {e}")
        await update.message.reply_text("⛔ خطایی رخ داد! لطفاً دوباره امتحان کنید.")

# 📌 هندلر برای انتخاب زبان
async def handle_language_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        user_id = query.from_user.id
        await query.answer()
        
        language = "english" if query.data == "set_language_english" else "persian"
        context.bot_data["user_data"][user_id]["language"] = language
        context.bot_data["user_data"][user_id]["state"] = "waiting_for_username"
        
        prompt_text = (
            "🏴‍☠️ لطفاً اسمت رو به انگلیسی وارد کن (نباید تکراری باشه):" if language == "persian" else
            "🏴‍☠️ Please enter your name in English (must be unique):"
        )
        await query.message.reply_text(prompt_text, reply_markup=ReplyKeyboardRemove())
        await query.message.delete()
        save_data(context)
    except Exception as e:
        logger.error(f"Error in handle_language_selection: {e}")
        await query.message.reply_text("⛔ خطایی رخ داد! لطفاً دوباره امتحان کنید.")

# 📌 هندلر برای دریافت نام کاربر
async def handle_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.message.from_user.id
        if "user_data" not in context.bot_data or user_id not in context.bot_data["user_data"]:
            context.bot_data["user_data"][user_id] = {"state": "waiting_for_language", "language": "persian"}
        
        user_data = context.bot_data["user_data"][user_id]
        if user_data.get("state") != "waiting_for_username":
            return
        
        username = update.message.text.strip()
        language = user_data.get("language", "persian")
        if not username.isascii():
            error_text = "⛔ لطفاً اسم رو به انگلیسی وارد کن!" if language == "persian" else "⛔ Please enter the name in English!"
            await update.message.reply_text(error_text)
            return
        
        if username.lower() in [u.lower() for u in context.bot_data["usernames"].values()]:
            error_text = "⛔ این اسم قبلاً انتخاب شده! یه اسم دیگه امتحان کن." if language == "persian" else "⛔ This name is already taken! Try another one."
            await update.message.reply_text(error_text)
            return
        
        user_data["username"] = username
        user_data["state"] = None
        context.bot_data["usernames"][user_id] = username
        
        required_fields = {
            "gems": 5, "gold": 10, "silver": 15, "wins": 0, "games": 0, "energy": 100,
            "last_purchase": {}, "score": 0, "cannons": 0, "free_cannons": 3,
            "drones": 0, "free_drones": 1, "level": 1, "initialized": True,
            "attack_strategy": 50, "defense_strategy": 50, "current_strategy": "balanced",
            "pending_gems": 0
        }
        
        for field, default_value in required_fields.items():
            if field not in user_data:
                user_data[field] = default_value
        
        save_data(context)
        await start(update, context)
    except Exception as e:
        logger.error(f"Error in handle_username: {e}")
        await update.message.reply_text("⛔ خطایی رخ داد! لطفاً دوباره امتحان کنید.")

# 📌 هندلر برای برترین ناخدایان
async def top_captains(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.message.from_user.id
        user_data = context.bot_data.get("user_data", {})
        language = user_data.get(user_id, {}).get("language", "persian")
        if not user_data:
            text = "🏴‍☠️ هنوز هیچ ناخدایی در بازی ثبت نشده!" if language == "persian" else "🏴‍☠️ No captains registered in the game yet!"
            await update.message.reply_text(text)
            return
        
        sorted_players = sorted(
            user_data.items(),
            key=lambda x: x[1].get("score", 0),
            reverse=True
        )[:10]
        
        text = "🏴‍☠️ برترین ناخدایان:\n\n" if language == "persian" else "🏴‍☠️ Top Captains:\n\n"
        for i, (player_id, data) in enumerate(sorted_players, 1):
            username = data.get("username", f"دزد دریایی {player_id}" if language == "persian" else f"Pirate {player_id}")
            score = data.get("score", 0)
            wins = data.get("wins", 0)
            games = data.get("games", 0)
            win_rate = (wins / games * 100) if games > 0 else 0
            text += f"🌟 {i}. {username} - امتیاز: {score} - میانگین برد: {win_rate:.1f}%\n" if language == "persian" else f"🌟 {i}. {username} - Score: {score} - Win Rate: {win_rate:.1f}%\n"
            if player_id != user_id:
                keyboard = [[InlineKeyboardButton("دعوت به جنگ دوستانه ✅" if language == "persian" else "Invite to Friendly Battle ✅", callback_data=f"request_friend_game_{player_id}")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(text, reply_markup=reply_markup)
                text = ""
            else:
                await update.message.reply_text(text)
                text = ""
        
        save_data(context)
    except Exception as e:
        logger.error(f"Error in top_captains: {e}")
        await update.message.reply_text("⛔ خطایی رخ داد! لطفاً دوباره امتحان کنید.")

# 📌 هندلر برای شروع بازی
async def start_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.message.from_user.id
        language = context.bot_data["user_data"][user_id]["language"]
        context.bot_data["user_data"][user_id]["state"] = None
        keyboard = [
            ["دریانوردی ⛵️" if language == "persian" else "Sailing ⛵️", "توپ ☄️" if language == "persian" else "Cannon ☄️"],
            ["پهباد 🛩️" if language == "persian" else "Drone 🛩️", "استراتژی ⚔️" if language == "persian" else "Strategy ⚔️"],
            ["بازگشت به منو 🔙" if language == "persian" else "Back to Menu 🔙"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
        text = "⚓️ انتخاب کن:" if language == "persian" else "⚓️ Choose:"
        await update.message.reply_text(text, reply_markup=reply_markup)
        save_data(context)
    except Exception as e:
        logger.error(f"Error in start_game: {e}")
        await update.message.reply_text("⛔ خطایی رخ داد! لطفاً دوباره امتحان کنید.")

# 📌 هندلر برای استراتژی
async def strategy_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.message.from_user.id
        user_data = context.bot_data["user_data"][user_id]
        language = user_data.get("language", "persian")
        
        keyboard = [
            ["حمله گرایانه 🗡️" if language == "persian" else "Aggressive 🗡️", "دفاعی 🛡️" if language == "persian" else "Defensive 🛡️"],
            ["بازگشت به منو 🔙" if language == "persian" else "Back to Menu 🔙"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
        
        strategy_text = {
            "aggressive": "حمله گرایانه 🗡️" if language == "persian" else "Aggressive 🗡️",
            "defensive": "دفاعی 🛡️" if language == "persian" else "Defensive 🛡️",
            "balanced": "متوازن ⚖️" if language == "persian" else "Balanced ⚖️"
        }
        
        current_strategy = user_data.get("current_strategy", "balanced")
        attack_power = user_data.get("attack_strategy", 50)
        defense_power = user_data.get("defense_strategy", 50)
        
        text = (
            f"⚔️ استراتژی فعلی: {strategy_text.get(current_strategy, 'متوازن ⚖️')}\n"
            f"🗡️ قدرت حمله: {attack_power}%\n"
            f"🛡️ قدرت دفاع: {defense_power}%\n\n"
            "🌟 استراتژی جدید را انتخاب کنید:"
        ) if language == "persian" else (
            f"⚔️ Current Strategy: {strategy_text.get(current_strategy, 'Balanced ⚖️')}\n"
            f"🗡️ Attack Power: {attack_power}%\n"
            f"🛡️ Defense Power: {defense_power}%\n\n"
            "🌟 Choose a new strategy:"
        )
        
        await update.message.reply_text(text, reply_markup=reply_markup)
        save_data(context)
    except Exception as e:
        logger.error(f"Error in strategy_menu: {e}")
        await update.message.reply_text("⛔ خطایی رخ داد! لطفاً دوباره امتحان کنید.")

# 📌 هندلر برای تنظیم استراتژی
async def set_strategy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.message.from_user.id
        choice = update.message.text
        user_data = context.bot_data["user_data"][user_id]
        language = user_data.get("language", "persian")
        
        if choice == ("حمله گرایانه 🗡️" if language == "persian" else "Aggressive 🗡️"):
            keyboard = [
                ["0%", "10%", "20%"],
                ["35%", "50%", "65%"],
                ["80%", "90%", "100%"],
                ["بازگشت به منو 🔙" if language == "persian" else "Back to Menu 🔙"]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
            text = "🗡️ میزان قدرت حمله را انتخاب کنید:" if language == "persian" else "🗡️ Choose attack power:"
            await update.message.reply_text(text, reply_markup=reply_markup)
            user_data["state"] = "waiting_for_attack_strategy"
        elif choice == ("دفاعی 🛡️" if language == "persian" else "Defensive 🛡️"):
            keyboard = [
                ["0%", "10%", "20%"],
                ["35%", "50%", "65%"],
                ["80%", "90%", "100%"],
                ["بازگشت به منو 🔙" if language == "persian" else "Back to Menu 🔙"]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
            text = "🛡️ میزان قدرت دفاع را انتخاب کنید:" if language == "persian" else "🛡️ Choose defense power:"
            await update.message.reply_text(text, reply_markup=reply_markup)
            user_data["state"] = "waiting_for_defense_strategy"
        elif choice == ("بازگشت به منو 🔙" if language == "persian" else "Back to Menu 🔙"):
            await back_to_menu(update, context)
        
        save_data(context)
    except Exception as e:
        logger.error(f"Error in set_strategy: {e}")
        await update.message.reply_text("⛔ خطایی رخ داد! لطفاً دوباره امتحان کنید.")

# 📌 هندلر برای دریافت مقدار استراتژی
async def handle_strategy_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.message.from_user.id
        user_data = context.bot_data["user_data"].get(user_id)
        language = user_data.get("language", "persian")
        
        if not user_data:
            text = "⛔ لطفاً اول با دستور /start شروع کنید!" if language == "persian" else "⛔ Please start with /start first!"
            await update.message.reply_text(text)
            return
        
        state = user_data.get("state")
        
        if state not in ["waiting_for_attack_strategy", "waiting_for_defense_strategy"]:
            return
        
        try:
            percent_str = update.message.text.replace("%", "")
            value = int(percent_str)
            if value < 0 or value > 100:
                text = "⛔ لطفاً یکی از گزینه‌های معتبر را انتخاب کنید!" if language == "persian" else "⛔ Please select a valid option!"
                await update.message.reply_text(text)
                return
        except ValueError:
            text = "⛔ لطفاً یکی از گزینه‌های معتبر را انتخاب کنید!" if language == "persian" else "⛔ Please select a valid option!"
            await update.message.reply_text(text)
            return
        
        if state == "waiting_for_attack_strategy":
            user_data["attack_strategy"] = value
            user_data["defense_strategy"] = 100 - value
            user_data["current_strategy"] = "aggressive" if value > 50 else "defensive" if value < 50 else "balanced"
            text = f"✅ 🗡️ قدرت حمله {value}% ذخیره شد! دفاع: {100 - value}%" if language == "persian" else f"✅ 🗡️ Attack power {value}% saved! Defense: {100 - value}%"
            await update.message.reply_text(text)
        elif state == "waiting_for_defense_strategy":
            user_data["defense_strategy"] = value
            user_data["attack_strategy"] = 100 - value
            user_data["current_strategy"] = "defensive" if value > 50 else "aggressive" if value < 50 else "balanced"
            text = f"✅ 🛡️ قدرت دفاع {value}% ذخیره شد! حمله: {100 - value}%" if language == "persian" else f"✅ 🛡️ Defense power {value}% saved! Attack: {100 - value}%"
            await update.message.reply_text(text)
        
        user_data["state"] = None
        save_data(context)
        await strategy_menu(update, context)
    except Exception as e:
        logger.error(f"Error in handle_strategy_input: {e}")
        await update.message.reply_text("⛔ خطایی رخ داد! لطفاً دوباره امتحان کنید.")

# 📌 تابع برای جست‌وجوی حریف
async def search_opponent(update: Update, context: ContextTypes.DEFAULT_TYPE, cannons: int, energy: int, drones: int):
    try:
        user_id = update.message.from_user.id
        language = context.bot_data["user_data"][user_id]["language"]
        context.bot_data["user_data"][user_id]["state"] = "in_game"
        await update.message.reply_text(
            "⛵️ در حال جست‌وجوی حریف..." if language == "persian" else
            "⛵️ Searching for an opponent...",
            reply_markup=ReplyKeyboardRemove()
        )
        
        await asyncio.sleep(5)  # برای تست؛ برای تولید به 60 تغییر دهید
        
        opponent_name = "دزد دریایی ناشناس" if language == "persian" else "Unknown Pirate"
        opponent_cannons = random.randint(0, 3)
        opponent_drones = random.randint(0, 1)
        opponent_attack = random.randint(0, 100)
        opponent_defense = 100 - opponent_attack
        opponent_strategy = "aggressive" if opponent_attack > 50 else "defensive" if opponent_defense > 50 else "balanced"
        
        await send_game_reports(update, context, opponent_name, cannons, energy, opponent_cannons, drones, opponent_drones, opponent_attack, opponent_defense, opponent_strategy)
        
        context.bot_data["user_data"][user_id]["state"] = None
        save_data(context)
        await start(update, context)
    except Exception as e:
        logger.error(f"Error in search_opponent: {e}")
        await update.message.reply_text("⛔ خطایی رخ داد! لطفاً دوباره امتحان کنید.")

# 📌 تابع برای ارسال گزارش‌های بازی
async def send_game_reports(update: Update, context: ContextTypes.DEFAULT_TYPE, opponent_name: str, cannons: int, energy: int, opponent_cannons: int, drones: int, opponent_drones: int, opponent_attack: int, opponent_defense: int, opponent_strategy: str):
    try:
        user_id = update.message.from_user.id
        user_data = context.bot_data["user_data"].get(user_id)
        language = user_data.get("language", "persian")
        
        if not user_data:
            text = "⛔ خطا: اطلاعات کاربر یافت نشد!" if language == "persian" else "⛔ Error: User data not found!"
            await update.message.reply_text(text)
            return
        
        attack_power = user_data.get("attack_strategy", 50)
        defense_power = user_data.get("defense_strategy", 50)
        
        battle_reports = [
            ("🏴‍☠️ ناخدا، کشتی دشمن از مه بیرون اومد! آماده نبرد شو! ⚔️", "🏴‍☠️ Captain, enemy ship emerged from the fog! Prepare for battle! ⚔️"),
            ("⚔️ نیروهای دشمن با طناب به کشتی‌مون چنگ زدن! شمشیرها رو آماده کن! 🗡️", "⚔️ Enemy forces are boarding with ropes! Ready your swords! 🗡️"),
            ("💥 با یه شلیک توپ، عرشه دشمن شعله‌ور شد! 🔥", "💥 One cannon shot set the enemy deck ablaze! 🔥"),
            ("⛵️ دشمن داره از پهلو نزدیک می‌شه! دفاع رو تقویت کن! 🛡️", "⛵️ Enemy is approaching from the side! Strengthen defenses! 🛡️"),
            ("🗡️ ناخدا، ۳ نفر از خدمه دشمن رو با شمشیر انداختیم تو دریا! 🌊", "🗡️ Captain, we threw 3 enemy crew into the sea with swords! 🌊"),
            ("🌊 یه موج بزرگ کشتی دشمن رو تکون داد، حالا شانس ماست! 🎉", "🌊 A huge wave rocked the enemy ship, now’s our chance! 🎉"),
            ("☄️ توپچی‌ها شلیک کردن، ۲ نفر از دشمن کشته شدن! 💀", "☄️ Cannons fired, 2 enemies killed! 💀"),
            ("🪵 دشمن با یه تخته چوبی داره به کشتی‌مون می‌پره! 🚢", "🪵 Enemy is boarding with a wooden plank! 🚢"),
            ("🌫️ ناخدا، یه بمب دودزا از کشتی دشمن اومد، دید کم شده! 👀", "🌫️ Captain, enemy threw a smoke bomb, visibility is low! 👀"),
            ("⚔️ با حمله ناگهانی، ۴ نفر از اونا رو نابود کردیم! 💪", "⚔️ Sudden attack, we destroyed 4 of them! 💪"),
            ("💥 کشتی دشمن داره غرق می‌شه، یه شلیک دیگه بزن! ☄️", "💥 Enemy ship is sinking, fire another shot! ☄️"),
            ("🏹 نیروهای دشمن تو عرشه‌مون نفوذ کردن، به جنگشون برو! ⚔️", "🏹 Enemy forces infiltrated our deck, fight them! ⚔️"),
            ("🏹 یه تیر آرشه از کشتی دشمن اومد، یکی از خدمه زخمی شد! 😞", "🏹 An arrow from the enemy ship hit one of our crew! 😞"),
            ("🪓 ناخدا، با یه ضربه تبر، ۳ نفر از اونا رو نابود کردیم! 💥", "🪓 Captain, one axe swing took out 3 of them! 💥"),
            ("⛵️ دشمن داره فرار می‌کنه، تعقیبشون کنیم! 🚢", "⛵️ Enemy is fleeing, pursue them! 🚢"),
            ("💥 یه انفجار تو کشتی دشمن، ۵ نفرشون از بین رفتن! 🔥", "💥 Explosion on enemy ship, 5 of them are gone! 🔥"),
            ("🌪️ ناخدا، طوفان داره به نفع ما می‌چرخه! 🌊", "🌪️ Captain, the storm is turning in our favor! 🌊"),
            ("🔪 دشمن با چاقو به سمت خدمه‌مون حمله کرد، ۲ نفر کشته شدن! 💀", "🔪 Enemy attacked our crew with knives, 2 killed! 💀"),
            ("🌳 با شلیک دقیق، دکل دشمن شکسته شد! ⛵️", "🌳 Precise shot broke the enemy’s mast! ⛵️"),
            ("🏴‍☠️ نیروهای دشمن دارن تسلیم می‌شن، جلو برو! ⚔️", "🏴‍☠️ Enemy forces are surrendering, press forward! ⚔️"),
        ]
        
        num_reports = random.randint(6, 20)
        selected_messages = random.sample(battle_reports, min(num_reports, len(battle_reports)))
        selected_messages = [msg[0] if language == "persian" else msg[1] for msg in selected_messages]
        
        for i in range(drones):
            hit_chance = 0.9
            hit = random.random() < hit_chance
            msg = (
                f"🛩️ پهباد {i+1} ما شلیک کرد! {'برخورد کرد و خسارت سنگین وارد کرد! 💥' if hit else 'خطا رفت! 😞'}" if language == "persian" else
                f"🛩️ Our drone {i+1} fired! {'Hit and caused heavy damage! 💥' if hit else 'Missed! 😞'}"
            )
            selected_messages.append(msg)
        
        for i in range(opponent_drones):
            hit_chance = 0.9
            hit = random.random() < hit_chance
            msg = (
                f"🛩️ پهباد {i+1} دشمن شلیک کرد! {'برخورد کرد و خسارت وارد کرد! 😞' if hit else 'خطا رفت! 🎉'}" if language == "persian" else
                f"🛩️ Enemy drone {i+1} fired! {'Hit and caused damage! 😞' if hit else 'Missed! 🎉'}"
            )
            selected_messages.append(msg)
        
        total_duration = 60
        interval = total_duration / len(selected_messages)
        
        for msg in selected_messages:
            try:
                await update.message.reply_text(msg)
                await asyncio.sleep(interval)
            except Exception as e:
                logger.error(f"Error sending game report: {e}")
        
        base_win_chance = min(100, (cannons * 20) + (energy / 2) + (drones * 50))
        strategy_bonus = (attack_power - 50) * 0.5 - (opponent_defense / 100) * 30
        win_chance = min(100, base_win_chance + strategy_bonus)
        
        opponent_chance = min(100, (opponent_cannons * 20) + (opponent_drones * 50) + (opponent_attack - 50) * 0.5 - (defense_power / 100) * 30)
        win = random.random() * (win_chance + opponent_chance) < win_chance
        
        strategy_text = {
            "aggressive": "حمله گرایانه 🗡️" if language == "persian" else "Aggressive 🗡️",
            "defensive": "دفاعی 🛡️" if language == "persian" else "Defensive 🛡️",
            "balanced": "متوازن ⚖️" if language == "persian" else "Balanced ⚖️"
        }
        
        report = (
            f"🏴‍☠️ کاپیتان، کشتیمون سوراخ شد! ⛔\nاستراتژی دشمن: {strategy_text.get(opponent_strategy, 'متوازن ⚖️')}\nقدرت حمله دشمن: {opponent_attack}%\nقدرت دفاع دشمن: {opponent_defense}%" if language == "persian" else
            f"🏴‍☠️ Captain, our ship is wrecked! ⛔\nEnemy Strategy: {strategy_text.get(opponent_strategy, 'Balanced ⚖️')}\nEnemy Attack Power: {opponent_attack}%\nEnemy Defense Power: {opponent_defense}%"
        ) if not win else (
            f"🏴‍☠️ کاپیتان، دشمن رو غرق کردیم! 🏆\nاستراتژی دشمن: {strategy_text.get(opponent_strategy, 'متوازن ⚖️')}\nقدرت حمله دشمن: {opponent_attack}%\nقدرت دفاع دشمن: {opponent_defense}%" if language == "persian" else
            f"🏴‍☠️ Captain, we sank the enemy! 🏆\nEnemy Strategy: {strategy_text.get(opponent_strategy, 'Balanced ⚖️')}\nEnemy Attack Power: {opponent_attack}%\nEnemy Defense Power: {opponent_defense}%"
        )
        
        user_data["games"] += 1
        user_data["energy"] = max(0, user_data["energy"] - 5)
        user_data["cannons"] = max(0, user_data["cannons"] - cannons)
        user_data["drones"] = max(0, user_data["drones"] - drones)
        
        if win:
            user_data["wins"] += 1
            user_data["score"] += 30
            user_data["gold"] += 3
            user_data["silver"] += 5
            user_data["energy"] = min(100, user_data["energy"] + 10)
            if random.random() < 0.25:
                user_data["gems"] += 1
                report += "\n💎 یه جم پیدا کردیم! 🎉" if language == "persian" else "\n💎 We found a gem! 🎉"
            report += "\n🏆 جایزه: ۳۰ امتیاز, 3 🪙 کیسه طلا, 5 🥈 شمش نقره, +10% ⚡ انرژی" if language == "persian" else "\n🏆 Reward: 30 points, 3 🪙 gold bags, 5 🥈 silver bars, +10% ⚡ energy"
        else:
            user_data["score"] = max(0, user_data["score"] - 10)
            if user_data["gold"] >= 3:
                user_data["gold"] -= 3
            if user_data["silver"] >= 5:
                user_data["silver"] -= 5
            if random.random() < 0.25 and user_data["gems"] >= 1:
                user_data["gems"] -= 1
                report += "\n💎 یه جم از دست دادیم! 😢" if language == "persian" else "\n💎 We lost a gem! 😢"
            user_data["energy"] = max(0, user_data["energy"] - 30)
            report += "\n⛔ جریمه: -10 امتیاز, -3 🪙 کیسه طلا, -5 🥈 شمش نقره, -30% ⚡ انرژی" if language == "persian" else "\n⛔ Penalty: -10 points, -3 🪙 gold bags, -5 🥈 silver bars, -30% ⚡ energy"
        
        try:
            await update.message.reply_text(f"⚔️ {'بازی با' if language == 'persian' else 'Battle with'} {opponent_name}:\n{report}")
        except Exception as e:
            logger.error(f"Error sending final report: {e}")
        
        save_data(context)
    except Exception as e:
        logger.error(f"Error in send_game_reports: {e}")
        await update.message.reply_text("⛔ خطایی رخ داد! لطفاً دوباره امتحان کنید.")

# 📌 هندلر برای پردازش بازی و خرید توپ و پهباد
async def handle_game_options(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.message.from_user.id
        choice = update.message.text
        language = context.bot_data["user_data"][user_id]["language"]
        
        if choice == ("بازگشت به منو 🔙" if language == "persian" else "Back to Menu 🔙"):
            await back_to_menu(update, context)
            return
        
        if choice == ("دریانوردی ⛵️" if language == "persian" else "Sailing ⛵️"):
            if context.bot_data["user_data"][user_id]["state"] == "in_game":
                text = "⛵️ در حال بازی هستید! لطفاً تا پایان بازی صبر کنید." if language == "persian" else "⛵️ You are already in a game! Please wait until it ends."
                await update.message.reply_text(text)
                return
            cannons = context.bot_data["user_data"][user_id]["cannons"]
            energy = context.bot_data["user_data"][user_id]["energy"]
            drones = context.bot_data["user_data"][user_id]["drones"]
            asyncio.create_task(search_opponent(update, context, cannons, energy, drones))
        
        elif choice == ("توپ ☄️" if language == "persian" else "Cannon ☄️"):
            free_cannons = context.bot_data["user_data"][user_id]["free_cannons"]
            if free_cannons > 0:
                context.bot_data["user_data"][user_id]["cannons"] += 1
                context.bot_data["user_data"][user_id]["free_cannons"] -= 1
                text = f"☄️ یه توپ رایگان گرفتی! ({free_cannons - 1} توپ رایگان باقی مونده)" if language == "persian" else f"☄️ You got a free cannon! ({free_cannons - 1} free cannons left)"
                await update.message.reply_text(text)
            else:
                text = "☄️ توپ رایگان تموم شده! برای خرید توپ به فروشگاه برو:" if language == "persian" else "☄️ No free cannons left! Go to the shop to buy cannons:"
                await update.message.reply_text(text)
                await shop(update, context)
            save_data(context)
        
        elif choice == ("پهباد 🛩️" if language == "persian" else "Drone 🛩️"):
            free_drones = context.bot_data["user_data"][user_id]["free_drones"]
            if free_drones > 0:
                context.bot_data["user_data"][user_id]["drones"] += 1
                context.bot_data["user_data"][user_id]["free_drones"] -= 1
                text = f"🛩️ یه پهباد رایگان گرفتی! ({free_drones - 1} پهباد رایگان باقی مونده)" if language == "persian" else f"🛩️ You got a free drone! ({free_drones - 1} free drones left)"
                await update.message.reply_text(text)
            else:
                text = "🛩️ پهباد رایگان تموم شده! برای خرید پهباد به فروشگاه برو:" if language == "persian" else "🛩️ No free drones left! Go to the shop to buy drones:"
                await update.message.reply_text(text)
                await shop(update, context)
            save_data(context)
        
        elif choice == ("استراتژی ⚔️" if language == "persian" else "Strategy ⚔️"):
            await strategy_menu(update, context)
        
        elif choice in [("حمله گرایانه 🗡️" if language == "persian" else "Aggressive 🗡️"), ("دفاعی 🛡️" if language == "persian" else "Defensive 🛡️")]:
            await set_strategy(update, context)
    except Exception as e:
        logger.error(f"Error in handle_game_options: {e}")
        await update.message.reply_text("⛔ خطایی رخ داد! لطفاً دوباره امتحان کنید.")

# 📌 هندلر برای فروشگاه
async def shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.message.from_user.id
        user_data = context.bot_data["user_data"][user_id]
        language = user_data.get("language", "persian")
        
        keyboard = [
            ["💎 خرید جم" if language == "persian" else "💎 Buy Gems", "☄️ خرید توپ" if language == "persian" else "☄️ Buy Cannons"],
            ["🛩️ خرید پهباد" if language == "persian" else "🛩️ Buy Drones", "🔙 بازگشت به منو" if language == "persian" else "🔙 Back to Menu"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
        
        text = (
            f"🛒 فروشگاه دزدان دریایی 🌊\n\n"
            f"💎 جم های شما: {user_data.get('gems', 0)}\n"
            f"🪙 کیسه طلا: {user_data.get('gold', 0)}\n"
            f"🥈 شمش نقره: {user_data.get('silver', 0)}\n\n"
            "🌟 گزینه مورد نظر را انتخاب کنید:"
        ) if language == "persian" else (
            f"🛒 Pirate Shop 🌊\n\n"
            f"💎 Your Gems: {user_data.get('gems', 0)}\n"
            f"🪙 Gold Bags: {user_data.get('gold', 0)}\n"
            f"🥈 Silver Bars: {user_data.get('silver', 0)}\n\n"
            "🌟 Choose an option:"
        )
        
        await update.message.reply_text(text, reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Error in shop: {e}")
        await update.message.reply_text("⛔ خطایی رخ داد! لطفاً دوباره امتحان کنید.")

# 📌 هندلر برای خرید جم
async def buy_gems(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.message.from_user.id
        language = context.bot_data["user_data"][user_id]["language"]
        context.bot_data["user_data"][user_id]["pending_gems"] = 0
        
        keyboard = [
            [InlineKeyboardButton("25 جم - 5 ترون" if language == "persian" else "25 Gems - 5 TRON", callback_data="buy_25_gems")],
            [InlineKeyboardButton("50 جم - 8 ترون" if language == "persian" else "50 Gems - 8 TRON", callback_data="buy_50_gems")],
            [InlineKeyboardButton("100 جم - 14 ترون" if language == "persian" else "100 Gems - 14 TRON", callback_data="buy_100_gems")],
            [InlineKeyboardButton("🔙 بازگشت به فروشگاه" if language == "persian" else "🔙 Back to Shop", callback_data="back_to_shop")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = (
            "💎 خرید جم:\n\n"
            "1. 25 جم = 5 ترون\n"
            "2. 50 جم = 8 ترون\n"
            "3. 100 جم = 14 ترون\n\n"
            "آدرس ترون: TJ4xrw8KJz7jk6FjkVqRw8h3Az5Ur4kLkb\n\n"
            "پس از پرداخت، فیش پرداخت را ارسال کنید."
        ) if language == "persian" else (
            "💎 Buy Gems:\n\n"
            "1. 25 Gems = 5 TRON\n"
            "2. 50 Gems = 8 TRON\n"
            "3. 100 Gems = 14 TRON\n\n"
            "TRON Address: TJ4xrw8KJz7jk6FjkVqRw8h3Az5Ur4kLkb\n\n"
            "Send the payment receipt after payment."
        )
        
        await update.message.reply_text(text, reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Error in buy_gems: {e}")
        await update.message.reply_text("⛔ خطایی رخ داد! لطفاً دوباره امتحان کنید.")

# 📌 هندلر برای خرید توپ
async def buy_cannons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.message.from_user.id
        user_data = context.bot_data["user_data"][user_id]
        language = user_data.get("language", "persian")
        
        keyboard = [
            [InlineKeyboardButton("1 توپ - 3 جم" if language == "persian" else "1 Cannon - 3 Gems", callback_data="buy_1_cannon")],
            [InlineKeyboardButton("3 توپ - 7 جم" if language == "persian" else "3 Cannons - 7 Gems", callback_data="buy_3_cannons")],
            [InlineKeyboardButton("10 توپ - 18 جم" if language == "persian" else "10 Cannons - 18 Gems", callback_data="buy_10_cannons")],
            [InlineKeyboardButton("20 توپ - 30 جم" if language == "persian" else "20 Cannons - 30 Gems", callback_data="buy_20_cannons")],
            [InlineKeyboardButton("🔙 بازگشت به فروشگاه" if language == "persian" else "🔙 Back to Shop", callback_data="back_to_shop")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = (
            f"☄️ خرید توپ (توپ‌های فعلی: {user_data.get('cannons', 0)})\n\n"
            "1. 1 توپ = 3 جم\n"
            "2. 3 توپ = 7 جم (صرفه‌جویی 2 جم)\n"
            "3. 10 توپ = 18 جم (صرفه‌جویی 12 جم)\n"
            "4. 20 توپ = 30 جم (صرفه‌جویی 30 جم)\n\n"
            f"💎 جم های شما: {user_data.get('gems', 0)}"
        ) if language == "persian" else (
            f"☄️ Buy Cannons (Current Cannons: {user_data.get('cannons', 0)})\n\n"
            "1. 1 Cannon = 3 Gems\n"
            "2. 3 Cannons = 7 Gems (Save 2 Gems)\n"
            "3. 10 Cannons = 18 Gems (Save 12 Gems)\n"
            "4. 20 Cannons = 30 Gems (Save 30 Gems)\n\n"
            f"💎 Your Gems: {user_data.get('gems', 0)}"
        )
        
        await update.message.reply_text(text, reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Error in buy_cannons: {e}")
        await update.message.reply_text("⛔ خطایی رخ داد! لطفاً دوباره امتحان کنید.")

# 📌 هندلر برای خرید پهباد
async def buy_drones(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.message.from_user.id
        user_data = context.bot_data["user_data"][user_id]
        language = user_data.get("language", "persian")
        
        keyboard = [
            [InlineKeyboardButton("1 پهباد - 7 جم" if language == "persian" else "1 Drone - 7 Gems", callback_data="buy_1_drone")],
            [InlineKeyboardButton("3 پهباد - 18 جم" if language == "persian" else "3 Drones - 18 Gems", callback_data="buy_3_drones")],
            [InlineKeyboardButton("5 پهباد - 30 جم" if language == "persian" else "5 Drones - 30 Gems", callback_data="buy_5_drones")],
            [InlineKeyboardButton("🔙 بازگشت به فروشگاه" if language == "persian" else "🔙 Back to Shop", callback_data="back_to_shop")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = (
            f"🛩️ خرید پهباد (پهبادهای فعلی: {user_data.get('drones', 0)})\n\n"
            "1. 1 پهباد = 7 جم\n"
            "2. 3 پهباد = 18 جم (صرفه‌جویی 3 جم)\n"
            "3. 5 پهباد = 30 جم (صرفه‌جویی 5 جم)\n\n"
            f"💎 جم های شما: {user_data.get('gems', 0)}"
        ) if language == "persian" else (
            f"🛩️ Buy Drones (Current Drones: {user_data.get('drones', 0)})\n\n"
            "1. 1 Drone = 7 Gems\n"
            "2. 3 Drones = 18 Gems (Save 3 Gems)\n"
            "3. 5 Drones = 30 Gems (Save 5 Gems)\n\n"
            f"💎 Your Gems: {user_data.get('gems', 0)}"
        )
        
        await update.message.reply_text(text, reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Error in buy_drones: {e}")
        await update.message.reply_text("⛔ خطایی رخ داد! لطفاً دوباره امتحان کنید.")

# 📌 هندلر برای پردازش خرید توپ
async def handle_cannon_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        user_id = query.from_user.id
        language = context.bot_data["user_data"][user_id]["language"]
        await query.answer()
        
        user_data = context.bot_data["user_data"][user_id]
        gems = user_data.get("gems", 0)
        
        if query.data == "buy_1_cannon":
            if gems >= 3:
                user_data["gems"] -= 3
                user_data["cannons"] += 1
                text = "✅ 1 توپ با 3 جم خریداری شد!" if language == "persian" else "✅ 1 Cannon bought with 3 Gems!"
                await query.message.reply_text(text)
            else:
                text = "⛔ جم کافی ندارید!" if language == "persian" else "⛔ Not enough gems!"
                await query.message.reply_text(text)
        
        elif query.data == "buy_3_cannons":
            if gems >= 7:
                user_data["gems"] -= 7
                user_data["cannons"] += 3
                text = "✅ 3 توپ با 7 جم خریداری شد!" if language == "persian" else "✅ 3 Cannons bought with 7 Gems!"
                await query.message.reply_text(text)
            else:
                text = "⛔ جم کافی ندارید!" if language == "persian" else "⛔ Not enough gems!"
                await query.message.reply_text(text)
        
        elif query.data == "buy_10_cannons":
            if gems >= 18:
                user_data["gems"] -= 18
                user_data["cannons"] += 10
                text = "✅ 10 توپ با 18 جم خریداری شد!" if language == "persian" else "✅ 10 Cannons bought with 18 Gems!"
                await query.message.reply_text(text)
            else:
                text = "⛔ جم کافی ندارید!" if language == "persian" else "⛔ Not enough gems!"
                await query.message.reply_text(text)
        
        elif query.data == "buy_20_cannons":
            if gems >= 30:
                user_data["gems"] -= 30
                user_data["cannons"] += 20
                text = "✅ 20 توپ با 30 جم خریداری شد!" if language == "persian" else "✅ 20 Cannons bought with 30 Gems!"
                await query.message.reply_text(text)
            else:
                text = "⛔ جم کافی ندارید!" if language == "persian" else "⛔ Not enough gems!"
                await query.message.reply_text(text)
        
        elif query.data == "back_to_shop":
            await shop(update, context)
        
        await query.message.delete()
        save_data(context)
    except Exception as e:
        logger.error(f"Error in handle_cannon_purchase: {e}")
        await query.message.reply_text("⛔ خطایی رخ داد! لطفاً دوباره امتحان کنید.")

# 📌 هندلر برای پردازش خرید پهباد
async def handle_drone_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        user_id = query.from_user.id
        language = context.bot_data["user_data"][user_id]["language"]
        await query.answer()
        
        user_data = context.bot_data["user_data"][user_id]
        gems = user_data.get("gems", 0)
        
        if query.data == "buy_1_drone":
            if gems >= 7:
                user_data["gems"] -= 7
                user_data["drones"] += 1
                text = "✅ 1 پهباد با 7 جم خریداری شد!" if language == "persian" else "✅ 1 Drone bought with 7 Gems!"
                await query.message.reply_text(text)
            else:
                text = "⛔ جم کافی ندارید!" if language == "persian" else "⛔ Not enough gems!"
                await query.message.reply_text(text)
        
        elif query.data == "buy_3_drones":
            if gems >= 18:
                user_data["gems"] -= 18
                user_data["drones"] += 3
                text = "✅ 3 پهباد با 18 جم خریداری شد!" if language == "persian" else "✅ 3 Drones bought with 18 Gems!"
                await query.message.reply_text(text)
            else:
                text = "⛔ جم کافی ندارید!" if language == "persian" else "⛔ Not enough gems!"
                await query.message.reply_text(text)
        
        elif query.data == "buy_5_drones":
            if gems >= 30:
                user_data["gems"] -= 30
                user_data["drones"] += 5
                text = "✅ 5 پهباد با 30 جم خریداری شد!" if language == "persian" else "✅ 5 Drones bought with 30 Gems!"
                await query.message.reply_text(text)
            else:
                text = "⛔ جم کافی ندارید!" if language == "persian" else "⛔ Not enough gems!"
                await query.message.reply_text(text)
        
        elif query.data == "back_to_shop":
            await shop(update, context)
        
        await query.message.delete()
        save_data(context)
    except Exception as e:
        logger.error(f"Error in handle_drone_purchase: {e}")
        await query.message.reply_text("⛔ خطایی رخ داد! لطفاً دوباره امتحان کنید.")

# 📌 هندلر برای پردازش درخواست جنگ دوستانه
async def handle_friend_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        user_id = query.from_user.id
        language = context.bot_data["user_data"][user_id]["language"]
        await query.answer()
        
        data = query.data
        if data == "back_to_menu":
            await back_to_menu(update, context)
            return
        
        if data.startswith("request_friend_game_"):
            target_id = int(data.split("_")[3])
            requester_id = query.from_user.id
            requester_data = context.bot_data["user_data"].get(requester_id, {})
            requester_name = requester_data.get("username", f"دزد دریایی {requester_id}" if language == "persian" else f"Pirate {requester_id}")
            
            gems = requester_data.get("gems", 5)
            gold = requester_data.get("gold", 10)
            silver = requester_data.get("silver", 15)
            wins = requester_data.get("wins", 0)
            games = requester_data.get("games", 0)
            energy = requester_data.get("energy", 100)
            win_rate = (wins / games * 100) if games > 0 else 0
            
            text = (
                f"🏴‍☠️ کاربر {requester_name} با این اطلاعات کشتی بهت درخواست جنگ دوستانه داده! قبول می‌کنی? ⚔️\n"
                f"📕 اطلاعات کشتی {requester_name}:\n"
                f"💎 جم: {gems}\n"
                f"🪙 کیسه طلا: {gold}\n"
                f"🥈 شمش نقره: {silver}\n"
                f"🏆 میانگین پیروزی: {win_rate:.1f}%\n"
                f"⚡ انرژی: {energy}%"
            ) if language == "persian" else (
                f"🏴‍☠️ User {requester_name} sent you a friendly battle request! Accept? ⚔️\n"
                f"📕 {requester_name}'s Ship Info:\n"
                f"💎 Gems: {gems}\n"
                f"🪙 Gold Bags: {gold}\n"
                f"🥈 Silver Bars: {silver}\n"
                f"🏆 Win Rate: {win_rate:.1f}%\n"
                f"⚡ Energy: {energy}%"
            )
            
            keyboard = [
                [InlineKeyboardButton("قبول می‌کنم ✅" if language == "persian" else "I Accept ✅", callback_data=f"accept_friend_game_{requester_id}_{target_id}")],
                [InlineKeyboardButton("قبول نمی‌کنم ❌" if language == "persian" else "I Decline ❌", callback_data=f"reject_friend_game_{requester_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await context.bot.send_message(target_id, text, reply_markup=reply_markup)
            text = f"⚔️ درخواست جنگ دوستانه برای {context.bot_data['usernames'].get(target_id, 'ناشناس' if language == 'persian' else 'Unknown')} ارسال شد! ⏳" if language == "persian" else f"⚔️ Friendly battle request sent to {context.bot_data['usernames'].get(target_id, 'Unknown')}! ⏳"
            await query.message.reply_text(text)
            await query.message.delete()
            save_data(context)
            return
        
        if data.startswith("reject_friend_game_"):
            requester_id = int(data.split("_")[3])
            requester_name = context.bot_data["usernames"].get(requester_id, f"دزد دریایی {requester_id}" if language == "persian" else f"Pirate {requester_id}")
            text = "⛔ درخواست جنگ دوستانه رد شد! 😞" if language == "persian" else "⛔ Friendly battle request rejected! 😞"
            await query.message.reply_text(text)
            text = f"🏴‍☠️ کاربر {context.bot_data['usernames'].get(query.from_user.id, 'ناشناس' if language == 'persian' else 'Unknown')} درخواست جنگ دوستانه‌ات رو رد کرد! ⚠️" if language == "persian" else f"🏴‍☠️ User {context.bot_data['usernames'].get(query.from_user.id, 'Unknown')} rejected your friendly battle request! ⚠️"
            await context.bot.send_message(requester_id, text)
            await query.message.edit_reply_markup(reply_markup=None)
            save_data(context)
            return
        
        if data.startswith("accept_friend_game_"):
            requester_id, target_id = map(int, data.split("_")[3:5])
            requester_name = context.bot_data["usernames"].get(requester_id, f"دزد دریایی {requester_id}" if language == "persian" else f"Pirate {requester_id}")
            target_name = context.bot_data["usernames"].get(target_id, f"دزد دریایی {target_id}" if language == "persian" else f"Pirate {target_id}")
            
            requester_data = context.bot_data["user_data"].get(requester_id, {})
            target_data = context.bot_data["user_data"].get(target_id, {})
            
            requester_cannons = requester_data.get("cannons", 0)
            requester_energy = requester_data.get("energy", 100)
            requester_attack = requester_data.get("attack_strategy", 50)
            requester_defense = requester_data.get("defense_strategy", 50)
            requester_drones = requester_data.get("drones", 0)
            
            target_cannons = target_data.get("cannons", 0)
            target_energy = target_data.get("energy", 100)
            target_attack = target_data.get("attack_strategy", 50)
            target_defense = target_data.get("defense_strategy", 50)
            target_drones = target_data.get("drones", 0)
            
            requester_chance = min(100, (requester_cannons * 20) + (requester_energy / 2) + (requester_drones * 50))
            requester_chance += (requester_attack - 50) * 0.5 - (target_defense / 100) * 30
            
            target_chance = min(100, (target_cannons * 20) + (target_energy / 2) + (target_drones * 50))
            target_chance += (target_attack - 50) * 0.5 - (requester_defense / 100) * 30
            
            win = random.random() * (requester_chance + target_chance) < requester_chance
            
            requester_data["games"] = requester_data.get("games", 0) + 1
            target_data["games"] = target_data.get("games", 0) + 1
            requester_data["energy"] = max(0, requester_data.get("energy", 100) - 5)
            target_data["energy"] = max(0, target_data.get("energy", 100) - 5)
            requester_data["cannons"] = max(0, requester_data.get("cannons", 0) - requester_cannons)
            target_data["cannons"] = max(0, target_data.get("cannons", 0) - target_cannons)
            requester_data["drones"] = max(0, requester_data.get("drones", 0) - requester_drones)
            target_data["drones"] = max(0, target_data.get("drones", 0) - target_drones)
            
            requester_report = f"⚔️ {'بازی دوستانه با' if language == 'persian' else 'Friendly battle with'} {target_name}:\n"
            target_report = f"⚔️ {'بازی دوستانه با' if language == 'persian' else 'Friendly battle with'} {requester_name}:\n"
            
            if win:
                requester_data["wins"] = requester_data.get("wins", 0) + 1
                requester_data["score"] = requester_data.get("score", 0) + 30
                target_data["score"] = max(0, target_data.get("score", 0) - 10)
                requester_report += "🏴‍☠️ کاپیتان، دشمن رو غرق کردیم! 🏆 🎉" if language == "persian" else "🏴‍☠️ Captain, we sank the enemy! 🏆 🎉"
                target_report += "🏴‍☠️ کاپیتان، کشتیمون سوراخ شد! ⛔ 😞" if language == "persian" else "🏴‍☠️ Captain, our ship is wrecked! ⛔ 😞"
            else:
                target_data["wins"] = target_data.get("wins", 0) + 1
                target_data["score"] = target_data.get("score", 0) + 30
                requester_data["score"] = max(0, requester_data.get("score", 0) - 10)
                target_report += "🏴‍☠️ کاپیتان، دشمن رو غرق کردیم! 🏆 🎉" if language == "persian" else "🏴‍☠️ Captain, we sank the enemy! 🏆 🎉"
                requester_report += "🏴‍☠️ کاپیتان، کشتیمون سوراخ شد! ⛔ 😞" if language == "persian" else "🏴‍☠️ Captain, our ship is wrecked! ⛔ 😞"
            
            messages = [
                ("🏴‍☠️ نبرد دوستانه آغاز شد! کشتی‌ها در افق به هم نزدیک می‌شن! ⚔️", "🏴‍☠️ Friendly battle started! Ships are approaching on the horizon! ⚔️"),
                ("🌊 طوفان در راهه! دریا داره خشمگین می‌شه! 🌪️", "🌊 Storm is coming! The sea is getting rough! 🌪️"),
                (f"⚡ جنگجویان شما با انرژی {requester_energy}% آماده‌اند! 💪", f"⚡ Your warriors are ready with {requester_energy}% energy! 💪"),
                (f"⚡ جنگجویان حریف با انرژی {target_energy}% آماده‌اند! 💪", f"⚡ Enemy warriors are ready with {target_energy}% energy! 💪")
            ]
            
            for i in range(requester_cannons):
                hit_chance = 0.5 * (requester_attack / 100)
                hit = random.random() < hit_chance
                messages.append(
                    (f"☄️ شلیک توپ {i+1} از {requester_name}! {'برخورد کرد! 💥' if hit else 'خطا رفت! 😞'}", 
                     f"☄️ Cannon {i+1} shot from {requester_name}! {'Hit! 💥' if hit else 'Missed! 😞'}")
                )
            
            for i in range(target_cannons):
                hit_chance = 0.5 * (target_attack / 100)
                defense_reduction = (requester_defense / 100) * 0.3
                hit = random.random() < (hit_chance - defense_reduction)
                messages.append(
                    (f"☄️ شلیک توپ {i+1} از {target_name}! {'برخورد کرد! 💥' if hit else 'خطا رفت! 😞'}", 
                     f"☄️ Cannon {i+1} shot from {target_name}! {'Hit! 💥' if hit else 'Missed! 😞'}")
                )
            
            for i in range(requester_drones):
                hit_chance = 0.9
                hit = random.random() < hit_chance
                messages.append(
                    (f"🛩️ پهباد {i+1} از {requester_name} شلیک کرد! {'برخورد کرد و خسارت سنگین وارد کرد! 💥' if hit else 'خطا رفت! 😞'}", 
                     f"🛩️ Drone {i+1} from {requester_name} fired! {'Hit and caused heavy damage! 💥' if hit else 'Missed! 😞'}")
                )
            
            for i in range(target_drones):
                hit_chance = 0.9
                defense_reduction = (requester_defense / 100) * 0.3
                hit = random.random() < (hit_chance - defense_reduction)
                messages.append(
                    (f"🛩️ پهباد {i+1} از {target_name} شلیک کرد! {'برخورد کرد و خسارت وارد کرد! 😞' if hit else 'خطا رفت! 🎉'}", 
                     f"🛩️ Drone {i+1} from {target_name} fired! {'Hit and caused damage! 😞' if hit else 'Missed! 🎉'}")
                )
            
            num_reports = random.randint(5, 10)
            selected_messages = random.sample(messages, min(num_reports, len(messages)))
            selected_messages = [msg[0] if language == "persian" else msg[1] for msg in selected_messages]
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
    except Exception as e:
        logger.error(f"Error in handle_friend_game: {e}")
        await query.message.reply_text("⛔ خطایی رخ داد! لطفاً دوباره امتحان کنید.")

# 📌 هندلر برای بازگشت به منو
async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.callback_query.from_user.id if update.callback_query else update.message.from_user.id
        context.bot_data["user_data"][user_id]["state"] = None
        await start(update, context)
        if update.callback_query:
            await update.callback_query.message.delete()
    except Exception as e:
        logger.error(f"Error in back_to_menu: {e}")
        await (update.callback_query.message.reply_text("⛔ خطایی رخ داد! لطفاً دوباره امتحان کنید.") if update.callback_query else update.message.reply_text("⛔ خطایی رخ داد! لطفاً دوباره امتحان کنید."))

# 📌 هندلر برای اطلاعات کشتی
async def ship_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.message.from_user.id
        user_data = context.bot_data["user_data"].get(user_id, {})
        language = user_data.get("language", "persian")
        
        username = user_data.get("username", f"دزد دریایی {user_id}" if language == "persian" else f"Pirate {user_id}")
        gems = user_data.get("gems", 5)
        gold = user_data.get("gold", 10)
        silver = user_data.get("silver", 15)
        wins = user_data.get("wins", 0)
        games = user_data.get("games", 0)
        energy = user_data.get("energy", 100)
        score = user_data.get("score", 0)
        cannons = user_data.get("cannons", 0)
        free_cannons = user_data.get("free_cannons", 3)
        drones = user_data.get("drones", 0)
        free_drones = user_data.get("free_drones", 1)
        level = user_data.get("level", 1)
        attack_power = user_data.get("attack_strategy", 50)
        defense_power = user_data.get("defense_strategy", 50)
        strategy = user_data.get("current_strategy", "balanced")
        
        strategy_text = {
            "aggressive": "حمله گرایانه 🗡️" if language == "persian" else "Aggressive 🗡️",
            "defensive": "دفاعی 🛡️" if language == "persian" else "Defensive 🛡️",
            "balanced": "متوازن ⚖️" if language == "persian" else "Balanced ⚖️"
        }
        
        win_rate = (wins / games * 100) if games > 0 else 0
        text = (
            f"📕 اطلاعات کشتی {username}:\n\n"
            f"💎 جم: {gems}\n"
            f"🪙 کیسه طلا: {gold}\n"
            f"🥈 شمش نقره: {silver}\n"
            f"🏆 تعداد برد: {wins}\n"
            f"🎮 تعداد بازی: {games}\n"
            f"📈 میانگین برد: {win_rate:.1f}%\n"
            f"⚡ انرژی: {energy}%\n"
            f"📊 امتیاز: {score}\n"
            f"☄️ توپ‌ها: {cannons} (رایگان: {free_cannons})\n"
            f"🛩️ پهبادها: {drones} (رایگان: {free_drones})\n"
            f"🌟 سطح: {level}\n"
            f"⚔️ استراتژی: {strategy_text.get(strategy, 'متوازن ⚖️')}\n"
            f"🗡️ قدرت حمله: {attack_power}%\n"
            f"🛡️ قدرت دفاع: {defense_power}%"
        ) if language == "persian" else (
            f"📕 {username}'s Ship Info:\n\n"
            f"💎 Gems: {gems}\n"
            f"🪙 Gold Bags: {gold}\n"
            f"🥈 Silver Bars: {silver}\n"
            f"🏆 Wins: {wins}\n"
            f"🎮 Games Played: {games}\n"
            f"📈 Win Rate: {win_rate:.1f}%\n"
            f"⚡ Energy: {energy}%\n"
            f"📊 Score: {score}\n"
            f"☄️ Cannons: {cannons} (Free: {free_cannons})\n"
            f"🛩️ Drones: {drones} (Free: {free_drones})\n"
            f"🌟 Level: {level}\n"
            f"⚔️ Strategy: {strategy_text.get(strategy, 'Balanced ⚖️')}\n"
            f"🗡️ Attack Power: {attack_power}%\n"
            f"🛡️ Defense Power: {defense_power}%"
        )
        
        await update.message.reply_text(text)
    except Exception as e:
        logger.error(f"Error in ship_info: {e}")
        await update.message.reply_text("⛔ خطایی رخ داد! لطفاً دوباره امتحان کنید.")

# 📌 هندلر برای انرژی جنگجویان
