import os
import json
import logging
from fastapi import FastAPI, Request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application, CommandHandler, ContextTypes, MessageHandler, CallbackQueryHandler, filters
)
from datetime import datetime, timedelta
import random
import asyncio

TOKEN = "8030062261:AAFnC9AJ_2zvcaqC0LXe5Y3--d2FgxOx-fI"
WEBHOOK_PATH = f"/webhook/{TOKEN}"
WEBHOOK_URL = f"https://sea-2ri6.onrender.com{WEBHOOK_PATH}"
ADMIN_ID = 5542927340  # Admin numeric ID
DATA_FILE = "game_data.json"  # Data storage file

# ⚙️ Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 📦 FastAPI app
app = FastAPI()

# 🎯 Create Telegram bot
application = Application.builder().token(TOKEN).build()

# Language texts
TEXTS = {
    "en": {
        "start": "🏴‍☠️ Welcome to Pirates World! Please choose your language:",
        "language_selection": "Please enter your name in English (must be unique):",
        "username_taken": "⛔ This name is already taken! Try another one.",
        "invalid_username": "⛔ Please enter a name in English!",
        "welcome": "🏴‍☠️ Welcome to Pirates World, {username}!",
        "menu": [
            ["⚔️ Start Game", "🛒 Shop"],
            ["🏴‍☠️ Top Captains"],
            ["📕 Ship Info", "⚡ Warriors Energy"]
        ],
        "game_options": [
            ["Sailing ⛵️", "Cannon ☄️"],
            ["Drone 🛩️", "Strategy ⚔️"],
            ["Back to Menu 🔙"]
        ],
        "strategy_menu": {
            "aggressive": "Aggressive 🗡️",
            "defensive": "Defensive 🛡️",
            "balanced": "Balanced ⚖️",
            "text": "⚔️ Current strategy: {strategy}\n🗡️ Attack power: {attack}%\n🛡️ Defense power: {defense}%\n\n🌟 Choose new strategy:"
        },
        "shop": "🛒 Pirates Shop 🌊\n\n💎 Your gems: {gems}\n🪙 Gold bags: {gold}\n🥈 Silver bars: {silver}\n\n🌟 Choose an option:",
        "ship_info": "📕 Ship Info 🌟:\n💎 Gems: {gems}\n🪙 Gold bags: {gold}\n🥈 Silver bars: {silver}\n🏆 Win rate: {win_rate:.1f}%\n⚡ Energy: {energy}%\n⚔️ Current strategy: {strategy}\n🗡️ Attack power: {attack}%\n🛡️ Defense power: {defense}%\n🌟 Level: {level}\n📊 Score: {score}"
    },
    "fa": {
        "start": "🏴‍☠️ خوش آمدید به دنیای دزدان دریایی! لطفاً زبان خود را انتخاب کنید:",
        "language_selection": "لطفاً اسمت رو به انگلیسی وارد کن (نباید تکراری باشه):",
        "username_taken": "⛔ این اسم قبلاً انتخاب شده! یه اسم دیگه امتحان کن.",
        "invalid_username": "⛔ لطفاً اسم رو به انگلیسی وارد کن!",
        "welcome": "🏴‍☠️ خوش اومدی به دنیای دزدان دریایی، {username}!",
        "menu": [
            ["⚔️ شروع بازی", "🛒 فروشگاه"],
            ["🏴‍☠️ برترین ناخدایان"],
            ["📕 اطلاعات کشتی", "⚡️ انرژی جنگجویان"]
        ],
        "game_options": [
            ["دریانوردی ⛵️", "توپ ☄️"],
            ["پهباد 🛩️", "استراتژی ⚔️"],
            ["بازگشت به منو 🔙"]
        ],
        "strategy_menu": {
            "aggressive": "حمله گرایانه 🗡️",
            "defensive": "دفاعی 🛡️",
            "balanced": "متوازن ⚖️",
            "text": "⚔️ استراتژی فعلی: {strategy}\n🗡️ قدرت حمله: {attack}%\n🛡️ قدرت دفاع: {defense}%\n\n🌟 استراتژی جدید را انتخاب کنید:"
        },
        "shop": "🛒 فروشگاه دزدان دریایی 🌊\n\n💎 جم های شما: {gems}\n🪙 کیسه طلا: {gold}\n🥈 شمش نقره: {silver}\n\n🌟 گزینه مورد نظر را انتخاب کنید:",
        "ship_info": "📕 اطلاعات کشتی 🌟:\n💎 جم: {gems}\n🪙 کیسه طلا: {gold}\n🥈 شمش نقره: {silver}\n🏆 میانگین پیروزی: {win_rate:.1f}%\n⚡ انرژی: {energy}%\n⚔️ استراتژی فعلی: {strategy}\n🗡️ قدرت حمله: {attack}%\n🛡️ قدرت دفاع: {defense}%\n🌟 لِوِل: {level}\n📊 امتیاز: {score}"
    }
}

# 📌 Function to save data
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

# 📌 Function to load data
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

# 📌 Handler for /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    
    if "user_data" not in context.bot_data:
        context.bot_data["user_data"] = {}
    if "usernames" not in context.bot_data:
        context.bot_data["usernames"] = {}
    
    if user_id not in context.bot_data["user_data"]:
        context.bot_data["user_data"][user_id] = {
            "state": "waiting_for_language",
            "pending_gems": 0,
            "language": "en"  # Default language
        }
        keyboard = [
            [InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"),
            InlineKeyboardButton("🇮🇷 فارسی", callback_data="lang_fa")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(TEXTS["en"]["start"], reply_markup=reply_markup)
        save_data(context)
        return
    
    user_data = context.bot_data["user_data"][user_id]
    lang = user_data.get("language", "en")
    
    if user_data.get("state") == "waiting_for_username":
        return
    
    required_fields = {
        "username": context.bot_data["usernames"].get(user_id, f"Pirate {user_id}" if lang == "en" else f"دزد دریایی {user_id}"),
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
    
    # Update level based on score
    score = user_data.get("score", 0)
    if score >= 600:
        user_data["level"] = 5
    elif score >= 450:
        user_data["level"] = 4
    elif score >= 300:
        user_data["level"] = 3
    elif score >= 150:
        user_data["level"] = 2
    else:
        user_data["level"] = 1
    
    reply_markup = ReplyKeyboardMarkup(TEXTS[lang]["menu"], resize_keyboard=True, one_time_keyboard=False)
    await update.message.reply_text(
        TEXTS[lang]["welcome"].format(username=user_data['username']),
        reply_markup=reply_markup
    )
    save_data(context)

# 📌 Handler for language selection
async def handle_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    lang = query.data.split("_")[1]
    
    if "user_data" not in context.bot_data:
        context.bot_data["user_data"] = {}
    
    if user_id not in context.bot_data["user_data"]:
        context.bot_data["user_data"][user_id] = {}
    
    context.bot_data["user_data"][user_id]["language"] = lang
    context.bot_data["user_data"][user_id]["state"] = "waiting_for_username"
    
    await query.message.reply_text(TEXTS[lang]["language_selection"])
    await query.message.delete()
    save_data(context)

# 📌 Handler for username input
async def handle_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    
    if "user_data" not in context.bot_data or user_id not in context.bot_data["user_data"]:
        context.bot_data["user_data"][user_id] = {"state": "waiting_for_username"}
    
    user_data = context.bot_data["user_data"][user_id]
    lang = user_data.get("language", "en")
    
    if user_data.get("state") != "waiting_for_username":
        return
    
    username = update.message.text.strip()
    logger.info(f"User {user_id} entered username: {username}")
    
    if not username.isascii():
        await update.message.reply_text(TEXTS[lang]["invalid_username"])
        return
    
    if "usernames" not in context.bot_data:
        context.bot_data["usernames"] = {}
    
    if username.lower() in [u.lower() for u in context.bot_data["usernames"].values()]:
        await update.message.reply_text(TEXTS[lang]["username_taken"])
        return
    
    user_data["username"] = username
    user_data["state"] = None
    context.bot_data["usernames"][user_id] = username
    
    required_fields = {
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
        "pending_gems": 0
    }
    
    for field, default_value in required_fields.items():
        if field not in user_data:
            user_data[field] = default_value
    
    save_data(context)
    await start(update, context)

# 📌 Function to search for opponent with random strategy
async def search_opponent(update: Update, context: ContextTypes.DEFAULT_TYPE, cannons: int, energy: int, drones: int):
    user_id = update.message.from_user.id
    user_data = context.bot_data["user_data"][user_id]
    lang = user_data.get("language", "en")
    
    context.bot_data["user_data"][user_id]["state"] = "in_game"
    await update.message.reply_text(
        "⛵️ Searching for opponent... (up to 60 seconds)" if lang == "en" else "⛵️ در حال جست‌وجوی حریف... (تا ۶۰ ثانیه)",
        reply_markup=ReplyKeyboardRemove()
    )
    
    await asyncio.sleep(5)  # Reduced wait time for testing
    
    # Generate random strategy for opponent (20-80% range)
    opponent_attack = random.randint(20, 80)
    opponent_defense = 100 - opponent_attack
    
    opponent_cannons = random.randint(0, 3)
    opponent_drones = random.randint(0, 1)
    
    opponent_name = "Unknown Pirate" if lang == "en" else "دزد دریایی ناشناس"
    
    await send_game_reports(update, context, opponent_name, cannons, energy, opponent_cannons, drones, opponent_drones, opponent_attack, opponent_defense)
    
    context.bot_data["user_data"][user_id]["state"] = None
    save_data(context)
    await start(update, context)

# 📌 Function to send game reports (updated with opponent strategy)
async def send_game_reports(update: Update, context: ContextTypes.DEFAULT_TYPE, opponent_name: str, cannons: int, energy: int, opponent_cannons: int, drones: int, opponent_drones: int, opponent_attack: int, opponent_defense: int):
    user_id = update.message.from_user.id
    user_data = context.bot_data["user_data"].get(user_id)
    lang = user_data.get("language", "en")
    
    if not user_data:
        await update.message.reply_text("⛔ Error: User data not found!" if lang == "en" else "⛔ خطا: اطلاعات کاربر یافت نشد!")
        return
    
    attack_power = user_data.get("attack_strategy", 50)
    defense_power = user_data.get("defense_strategy", 50)
    
    # Battle reports in both languages
    battle_reports = {
        "en": [
            "🏴‍☠️ Captain, enemy ship emerged from the fog! Prepare for battle! ⚔️",
            "⚔️ Enemy forces are boarding our ship! Ready your swords! 🗡️",
            "💥 A cannon shot set the enemy deck ablaze! 🔥",
            "⛵️ The enemy is approaching from the side! Strengthen defenses! 🛡️",
            "🗡️ Captain, we threw 3 enemies overboard with our swords! 🌊",
            "🌊 A big wave rocked the enemy ship, now's our chance! 🎉",
            "☄️ Cannons fired, 2 enemies killed! 💀",
            "🪵 The enemy is boarding with a wooden plank! 🚢",
            "🌫️ Captain, a smoke bomb from the enemy ship reduced visibility! 👀",
            "⚔️ With a sudden attack, we destroyed 4 of them! 💪",
            "💥 The enemy ship is sinking, fire another shot! ☄️",
            "🏹 Enemy forces infiltrated our deck, fight them! ⚔️",
            "🏹 An arrow from the enemy ship wounded one of our crew! 😞",
            "🪓 Captain, with an axe strike we destroyed 3 enemies! 💥",
            "⛵️ The enemy is retreating, should we pursue? 🚢",
            "💥 An explosion on the enemy ship killed 5 of them! 🔥",
            "🌪️ Captain, the storm is turning in our favor! 🌊",
            "🔪 The enemy attacked our crew with knives, 2 killed! 💀",
            "🌳 With precise shooting, we broke the enemy mast! ⛵️",
            "🏴‍☠️ Enemy forces are surrendering, move forward! ⚔️"
        ],
        "fa": [
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
            "🏴‍☠️ نیروهای دشمن دارن تسلیم می‌شن، جلو برو! ⚔️"
        ]
    }
    
    num_reports = random.randint(6, 20)
    selected_messages = random.sample(battle_reports[lang], min(num_reports, len(battle_reports[lang])))
    
    # Add drone messages
    for i in range(drones):
        hit_chance = 0.9
        hit = random.random() < hit_chance
        selected_messages.append(
            f"🛩️ Our drone {i+1} fired! {'Hit and caused heavy damage! 💥' if hit else 'Missed! 😞'}" if lang == "en" 
            else f"🛩️ پهباد {i+1} ما شلیک کرد! {'برخورد کرد و خسارت سنگین وارد کرد! 💥' if hit else 'خطا رفت! 😞'}"
        )
    
    for i in range(opponent_drones):
        hit_chance = 0.9
        hit = random.random() < hit_chance
        selected_messages.append(
            f"🛩️ Enemy drone {i+1} fired! {'Hit and caused damage! 😞' if hit else 'Missed! 🎉'}" if lang == "en"
            else f"🛩️ پهباد {i+1} دشمن شلیک کرد! {'برخورد کرد و خسارت وارد کرد! 😞' if hit else 'خطا رفت! 🎉'}"
        )
    
    total_duration = 60
    interval = total_duration / len(selected_messages)
    
    for msg in selected_messages:
        try:
            await update.message.reply_text(msg)
            await asyncio.sleep(interval)
        except Exception as e:
            logger.error(f"Error sending game report: {e}")
    
    # Calculate win chance considering opponent's strategy
    base_win_chance = min(100, (cannons * 20) + (energy / 2) + (drones * 50))
    strategy_bonus = (attack_power - 50) * 0.5
    opponent_defense_penalty = (opponent_defense / 100) * 30
    win_chance = min(100, base_win_chance + strategy_bonus - opponent_defense_penalty)
    
    opponent_chance = min(100, (opponent_cannons * 20) + (100 / 2) + (opponent_drones * 50))
    opponent_strategy_bonus = (opponent_attack - 50) * 0.5
    player_defense_penalty = (defense_power / 100) * 30
    opponent_chance = opponent_chance + opponent_strategy_bonus - player_defense_penalty
    
    win = random.random() * (win_chance + opponent_chance) < win_chance
    
    # Update game stats
    context.bot_data["user_data"][user_id]["games"] += 1
    context.bot_data["user_data"][user_id]["energy"] = max(0, context.bot_data["user_data"][user_id]["energy"] - 5)
    context.bot_data["user_data"][user_id]["cannons"] = max(0, context.bot_data["user_data"][user_id]["cannons"] - cannons)
    context.bot_data["user_data"][user_id]["drones"] = max(0, context.bot_data["user_data"][user_id]["drones"] - drones)
    
    if win:
        report = "🏴‍☠️ Captain, we sank the enemy! 🏆" if lang == "en" else "🏴‍☠️ کاپیتان، دشمن رو غرق کردیم! 🏆"
        context.bot_data["user_data"][user_id]["wins"] += 1
        context.bot_data["user_data"][user_id]["score"] += 30
        context.bot_data["user_data"][user_id]["gold"] += 3
        context.bot_data["user_data"][user_id]["silver"] += 5
        context.bot_data["user_data"][user_id]["energy"] = min(100, context.bot_data["user_data"][user_id]["energy"] + 10)
        if random.random() < 0.25:
            context.bot_data["user_data"][user_id]["gems"] += 1
            report += "\n💎 Found a gem! 🎉" if lang == "en" else "\n💎 یه جم پیدا کردیم! 🎉"
        report += "\n🏆 Reward: 30 points, 3 🪙 gold, 5 🥈 silver, +10% ⚡ energy" if lang == "en" else "\n🏆 جایزه: ۳۰ امتیاز, 3 🪙 کیسه طلا, 5 🥈 شمش نقره, +10% ⚡ انرژی"
    else:
        report = "🏴‍☠️ Captain, our ship is holed! ⛔" if lang == "en" else "🏴‍☠️ کاپیتان، کشتیمون سوراخ شد! ⛔"
        context.bot_data["user_data"][user_id]["score"] = max(0, context.bot_data["user_data"][user_id]["score"] - 10)
        if context.bot_data["user_data"][user_id]["gold"] >= 3:
            context.bot_data["user_data"][user_id]["gold"] -= 3
        if context.bot_data["user_data"][user_id]["silver"] >= 5:
            context.bot_data["user_data"][user_id]["silver"] -= 5
        if random.random() < 0.25 and context.bot_data["user_data"][user_id]["gems"] >= 1:
            context.bot_data["user_data"][user_id]["gems"] -= 1
            report += "\n💎 Lost a gem! 😢" if lang == "en" else "\n💎 یه جم از دست دادیم! 😢"
        context.bot_data["user_data"][user_id]["energy"] = max(0, context.bot_data["user_data"][user_id]["energy"] - 30)
        report += "\n⛔ Penalty: -10 points, -3 🪙 gold, -5 🥈 silver, -30% ⚡ energy" if lang == "en" else "\n⛔ جریمه: -10 امتیاز, -3 🪙 کیسه طلا, -5 🥈 شمش نقره, -30% ⚡ انرژی"
    
    try:
        await update.message.reply_text(f"⚔️ Battle with {opponent_name}:\n{report}")
    except Exception as e:
        logger.error(f"Error sending final report: {e}")
    
    save_data(context)

# ... [rest of the handlers remain the same, just make sure to use the TEXTS dictionary for all messages]

# 🔗 Register handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(handle_language, pattern="^lang_(en|fa)$"))
application.add_handler(MessageHandler(filters.Regex("^🛒 فروشگاه$") | filters.Regex("^🛒 Shop$"), shop))
application.add_handler(MessageHandler(filters.Regex("^📕 اطلاعات کشتی$") | filters.Regex("^📕 Ship Info$"), ship_info))
application.add_handler(MessageHandler(filters.Regex("^⚡️ انرژی جنگجویان$") | filters.Regex("^⚡ Warriors Energy$"), warriors_energy))
application.add_handler(MessageHandler(filters.Regex("^⚔️ شروع بازی$") | filters.Regex("^⚔️ Start Game$"), start_game))
application.add_handler(MessageHandler(filters.Regex("^🏴‍☠️ برترین ناخدایان$") | filters.Regex("^🏴‍☠️ Top Captains$"), top_captains))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex("^(🛒|📕|⚡️|⚔️|🏴‍☠️)"), handle_username))

# 🔁 Telegram webhook
@app.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, application.bot)
    await application.update_queue.put(update)
    return {"ok": True}

# 🔥 Server startup
@app.on_event("startup")
async def on_startup():
    load_data(application)
    await application.bot.set_webhook(url=WEBHOOK_URL)
    print("✅ Webhook set:", WEBHOOK_URL)
    await application.initialize()
    await application.start()

# 🛑 Server shutdown
@app.on_event("shutdown")
async def on_shutdown():
    save_data(application)
    await application.updater.stop()
    await application.stop()
    await application.shutdown()
