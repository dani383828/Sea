import os
import logging
from fastapi import FastAPI, Request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, ContextTypes,
    MessageHandler, filters, CallbackQueryHandler
)
import random
from datetime import datetime, timedelta
import pytz

# Configurations
TOKEN = "8030062261:AAFnC9AJ_2zvcaqC0LXe5Y3--d2FgxOx-fI"
ADMIN_ID = 5542927340
TRX_ADDRESS = "TJ4xrwKJzKjk6FgKfuuqwah3Az5Ur22kJb"
WEBHOOK_PATH = f"/webhook/{TOKEN}"
WEBHOOK_URL = f"https://sea-2ri6.onrender.com{WEBHOOK_PATH}"

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Database simulation
users_db = {}
ships_db = {}
battle_requests = {}
fake_players = [
    {"name": "Blackbeard", "strategy": "camouflage"},
    {"name": "Red Anne", "strategy": "night_attack"},
    {"name": "Calico Jack", "strategy": "fire_ship"},
    {"name": "Captain Kidd", "strategy": "hook"},
    {"name": "Barbarossa", "strategy": "ambush"},
    {"name": "Davy Jones", "strategy": "fake_treasure"},
    {"name": "Long John", "strategy": "spy"}
]

# FastAPI app
app = FastAPI()

# Telegram bot
application = Application.builder().token(TOKEN).build()

# Helper functions
def get_user_data(user_id):
    if user_id not in users_db:
        users_db[user_id] = {
            "gems": 5,
            "gold": 10,
            "silver": 15,
            "points": 0,
            "wins": 0,
            "losses": 0,
            "last_energy_refill": None,
            "cannon_balls": 3
        }
    return users_db[user_id]

def get_ship_data(user_id):
    if user_id not in ships_db:
        ships_db[user_id] = {
            "name": None,
            "energy": 100,
            "in_battle": False,
            "current_strategy": None,
            "battle_report": []
        }
    return ships_db[user_id]

def calculate_win_rate(user_id):
    user = get_user_data(user_id)
    total = user["wins"] + user["losses"]
    return round((user["wins"] / total) * 100, 1) if total > 0 else 0

def update_energy(user_id, amount):
    ship = get_ship_data(user_id)
    ship["energy"] = max(0, min(100, ship["energy"] + amount))
    return ship["energy"]

def can_refill_energy(user_id):
    user = get_user_data(user_id)
    ship = get_ship_data(user_id)
    if ship["last_energy_refill"] is None:
        return True
    now = datetime.now(pytz.utc)
    return (now - ship["last_energy_refill"]).total_seconds() >= 86400  # 24 hours

def generate_battle_report(user_strategy, enemy_strategy):
    strategies = {
        "camouflage": "استتار به عنوان کشتی تجاری",
        "night_attack": "حمله شبانه",
        "fire_ship": "آتش‌زدن کشتی دشمن",
        "hook": "اتصال قلاب",
        "ambush": "کمین پشت صخره‌",
        "fake_treasure": "فریب با گنج جعلی",
        "spy": "حمله با کمک جاسوس"
    }
    
    # Strategy effectiveness matrix
    effectiveness = {
        "camouflage": {"weak": ["spy"], "strong": ["night_attack"]},
        "night_attack": {"weak": ["fake_treasure"], "strong": ["hook"]},
        "fire_ship": {"weak": ["ambush"], "strong": ["camouflage"]},
        "hook": {"weak": ["fire_ship"], "strong": ["fake_treasure"]},
        "ambush": {"weak": ["night_attack"], "strong": ["spy"]},
        "fake_treasure": {"weak": ["hook"], "strong": ["ambush"]},
        "spy": {"weak": ["camouflage"], "strong": ["fire_ship"]}
    }
    
    report = []
    report.append(f"استراتژی شما: {strategies[user_strategy]}")
    report.append(f"استراتژی دشمن: {strategies[enemy_strategy]}")
    
    # Determine effectiveness
    if enemy_strategy in effectiveness[user_strategy]["strong"]:
        report.append("✅ استراتژی شما بر ضد دشمن بسیار موثر است!")
        effectiveness_bonus = 1.3
    elif enemy_strategy in effectiveness[user_strategy]["weak"]:
        report.append("❌ استراتژی دشمن بر ضد شما موثر است!")
        effectiveness_bonus = 0.7
    else:
        report.append("⚔️ استراتژی‌ها با هم برابرند!")
        effectiveness_bonus = 1.0
    
    return report, effectiveness_bonus

# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ship = get_ship_data(user_id)
    
    if ship["name"] is None:
        await update.message.reply_text(
            "🏴‍☠️ به دنیای دزدان دریایی خوش اومدی، کاپیتان!\n\n"
            "🚢 آماده‌ای کشتی‌تو بسازی و راهی دریا بشی؟\n\n"
            "لطفا نام کشتی خود را وارد کن (فقط حروف انگلیسی، نه اسم تکراری و نه دستورات ربات):"
        )
    else:
        await show_main_menu(update, context)

async def handle_ship_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    ship = get_ship_data(user_id)
    
    if ship["name"] is not None:
        return
    
    # Validate ship name
    if any(cmd in text.lower() for cmd in ['/start', '/help', '/settings']):
        await update.message.reply_text("این نام قابل قبول نیست. لطفا یک نام مناسب برای کشتی انتخاب کن:")
        return
    
    if not text.isalpha():
        await update.message.reply_text("نام کشتی باید فقط شامل حروف انگلیسی باشد. لطفا دوباره وارد کن:")
        return
    
    # Check for duplicate names
    if any(ship["name"] == text for ship in ships_db.values() if ship["name"] is not None):
        await update.message.reply_text("این نام قبلا استفاده شده. لطفا نام دیگری انتخاب کن:")
        return
    
    # Save ship name
    ship["name"] = text
    await update.message.reply_text(f"✅ کشتی شما با نام {text} ثبت شد!")
    await show_main_menu(update, context)

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user_data(user_id)
    ship = get_ship_data(user_id)
    
    keyboard = [
        [InlineKeyboardButton("شروع بازی ⚔️", callback_data="start_game")],
        [InlineKeyboardButton("فروشگاه 🛒", callback_data="shop")],
        [InlineKeyboardButton("برترین ناخدایان", callback_data="top_players")],
        [InlineKeyboardButton("جستجوی کاربران", callback_data="search_players")],
        [InlineKeyboardButton("اطلاعات کشتی", callback_data="ship_info")],
        [InlineKeyboardButton("انرژی جنگجویان", callback_data="crew_energy")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = (
        f"🏴‍☠️ کاپیتان {ship['name']}\n\n"
        f"💎 جم: {user['gems']} | 🏆 امتیاز: {user['points']}\n"
        f"💰 کیسه طلا: {user['gold']} | 🪙 شمش نقره: {user['silver']}\n"
        f"⚡ انرژی: {ship['energy']}% | 🎯 میانگین پیروزی: {calculate_win_rate(user_id)}%\n"
        f"💣 توپ: {user['cannon_balls']}"
    )
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, reply_markup=reply_markup)

# Game handlers
async def start_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    ship = get_ship_data(user_id)
    
    if ship["in_battle"]:
        await query.edit_message_text("شما در حال حاضر در یک نبرد هستید!")
        return
    
    ship["in_battle"] = True
    ship["current_strategy"] = None
    ship["battle_report"] = []
    
    keyboard = [
        [InlineKeyboardButton("دریانوردی ⛵️", callback_data="sail")],
        [InlineKeyboardButton("استراتژی", callback_data="choose_strategy")],
        [InlineKeyboardButton("توپ", callback_data="cannon_info")],
        [InlineKeyboardButton("بازگشت", callback_data="main_menu")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "⚔️ بخش جنگ:\n\n"
        "گزینه مورد نظر را انتخاب کن:",
        reply_markup=reply_markup
    )

async def sail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user = get_user_data(user_id)
    ship = get_ship_data(user_id)
    
    if ship["energy"] < 20:
        await query.edit_message_text("انرژی جنگجویان شما کمتر از ۲۰٪ است! قبل از نبرد باید انرژی را تامین کنید.")
        return
    
    # Find opponent (real or fake)
    opponent_id = None
    for uid, req in battle_requests.items():
        if uid != user_id and req["status"] == "waiting":
            opponent_id = uid
            break
    
    if opponent_id is None:
        # Use fake player
        fake = random.choice(fake_players)
        opponent_id = f"fake_{fake['name']}"
        ship["opponent_strategy"] = fake["strategy"]
    else:
        # Real player
        ship["opponent_strategy"] = ships_db[opponent_id]["current_strategy"]
    
    # Start battle
    ship["battle_report"].append("⚔️ نبرد آغاز شد!")
    ship["battle_report"].append("کشتی دشمن در افق ظاهر شد...")
    
    keyboard = [
        [InlineKeyboardButton("پرتاب توپ ☄️", callback_data="fire_cannon")],
        [InlineKeyboardButton("ادامه گزارش", callback_data="continue_report")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        ship["battle_report"][-1],
        reply_markup=reply_markup
    )

async def continue_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    ship = get_ship_data(user_id)
    
    if len(ship["battle_report"]) < 3:
        ship["battle_report"].append("به کشتی دشمن نزدیک می‌شویم...")
    elif len(ship["battle_report"]) < 4:
        ship["battle_report"].append("دشمن در حال مانور است...")
    elif len(ship["battle_report"]) < 5:
        ship["battle_report"].append("آماده حمله هستیم!")
    
    keyboard = [
        [InlineKeyboardButton("پرتاب توپ ☄️", callback_data="fire_cannon")],
        [InlineKeyboardButton("ادامه گزارش", callback_data="continue_report")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "\n".join(ship["battle_report"]),
        reply_markup=reply_markup
    )

async def fire_cannon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user = get_user_data(user_id)
    ship = get_ship_data(user_id)
    
    if user["cannon_balls"] <= 0:
        await query.edit_message_text("توپ ندارید! لطفا به فروشگاه مراجعه کنید.")
        return
    
    user["cannon_balls"] -= 1
    
    # Determine hit probability based on timing and energy
    timing_factor = 0.65 if 2 <= len(ship["battle_report"]) < 5 else 0.1
    energy_factor = ship["energy"] / 100
    hit_probability = timing_factor * energy_factor
    
    if random.random() <= hit_probability:
        ship["battle_report"].append("🎯 توپ شما به کشتی دشمن اصابت کرد!")
        ship["battle_report"].append("دشمن آسیب دیده است!")
    else:
        ship["battle_report"].append("💥 توپ شما به هدف نخورد!")
    
    # Continue battle
    keyboard = [
        [InlineKeyboardButton("پرتاب توپ ☄️", callback_data="fire_cannon")],
        [InlineKeyboardButton("ادامه گزارش", callback_data="continue_report")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "\n".join(ship["battle_report"]),
        reply_markup=reply_markup
    )

async def choose_strategy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("استتار به عنوان کشتی تجاری", callback_data="strategy_camouflage")],
        [InlineKeyboardButton("حمله شبانه", callback_data="strategy_night_attack")],
        [InlineKeyboardButton("آتش‌زدن کشتی دشمن", callback_data="strategy_fire_ship")],
        [InlineKeyboardButton("اتصال قلاب", callback_data="strategy_hook")],
        [InlineKeyboardButton("کمین پشت صخره‌", callback_data="strategy_ambush")],
        [InlineKeyboardButton("فریب با گنج جعلی", callback_data="strategy_fake_treasure")],
        [InlineKeyboardButton("حمله با کمک جاسوس", callback_data="strategy_spy")],
        [InlineKeyboardButton("بازگشت", callback_data="start_game")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🎯 انتخاب کن که با کدوم استراتژی حمله کنیم:",
        reply_markup=reply_markup
    )

async def set_strategy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    ship = get_ship_data(user_id)
    
    strategy = query.data.replace("strategy_", "")
    ship["current_strategy"] = strategy
    
    strategy_names = {
        "camouflage": "استتار به عنوان کشتی تجاری",
        "night_attack": "حمله شبانه",
        "fire_ship": "آتش‌زدن کشتی دشمن",
        "hook": "اتصال قلاب",
        "ambush": "کمین پشت صخره‌",
        "fake_treasure": "فریب با گنج جعلی",
        "spy": "حمله با کمک جاسوس"
    }
    
    await query.edit_message_text(
        f"استراتژی شما تنظیم شد به: {strategy_names[strategy]}"
    )
    await start_game(update, context)

async def cannon_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user = get_user_data(user_id)
    
    await query.edit_message_text(
        f"💣 تعداد توپ‌های شما: {user['cannon_balls']}\n\n"
        "هر توپ 3 جم در فروشگاه قیمت دارد.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("خرید توپ", callback_data="buy_cannon")],
            [InlineKeyboardButton("بازگشت", callback_data="start_game")]
        ])
    )

# Shop handlers
async def shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("خرید جم 💎", callback_data="buy_gems")],
        [InlineKeyboardButton("خرید توپ", callback_data="buy_cannon")],
        [InlineKeyboardButton("تبدیل جم به سکه و نقره", callback_data="convert_gems")],
        [InlineKeyboardButton("بازگشت", callback_data="main_menu")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🛒 فروشگاه:\n\n"
        "گزینه مورد نظر را انتخاب کن:",
        reply_markup=reply_markup
    )

async def buy_gems(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("25 جم = ۵ ترون", callback_data="gem_25")],
        [InlineKeyboardButton("50 جم = ۸ ترون", callback_data="gem_50")],
        [InlineKeyboardButton("100 جم = ۱۴ ترون", callback_data="gem_100")],
        [InlineKeyboardButton("بازگشت", callback_data="shop")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "💎 خرید جم:\n\n"
        "لطفا مقدار مورد نظر را انتخاب کنید:\n"
        f"آدرس ترون: {TRX_ADDRESS}\n\n"
        "بعد از پرداخت، رسید پرداخت را ارسال کنید.",
        reply_markup=reply_markup
    )

async def handle_payment_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    # Forward to admin
    await context.bot.send_message(
        ADMIN_ID,
        f"درخواست خرید جم از کاربر {user_id}\n\n"
        f"رسید: {text}\n\n"
        "برای تایید /confirm_{user_id}\n"
        "برای رد /reject_{user_id}"
    )
    
    await update.message.reply_text("رسید شما به ادمین ارسال شد. پس از تایید، جم به حساب شما واریز می‌شود.")

async def buy_cannon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user = get_user_data(user_id)
    
    if user["gems"] < 3:
        await query.edit_message_text("جم کافی ندارید! حداقل 3 جم نیاز دارید.")
        return
    
    user["gems"] -= 3
    user["cannon_balls"] += 1
    
    await query.edit_message_text(
        f"✅ یک توپ خریداری شد!\n\n"
        f"💎 جم باقیمانده: {user['gems']}\n"
        f"💣 تعداد توپ‌ها: {user['cannon_balls']}",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("خرید مجدد", callback_data="buy_cannon")],
            [InlineKeyboardButton("بازگشت", callback_data="shop")]
        ])
    )

async def convert_gems(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("1 جم = 2 کیسه طلا", callback_data="convert_1")],
        [InlineKeyboardButton("3 جم = 6 کیسه طلا + 4 شمش نقره", callback_data="convert_3")],
        [InlineKeyboardButton("10 جم = 20 کیسه طلا + 15 شمش نقره", callback_data="convert_10")],
        [InlineKeyboardButton("بازگشت", callback_data="shop")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "💱 تبدیل جم به سکه و نقره:\n\n"
        "گزینه مورد نظر را انتخاب کن:",
        reply_markup=reply_markup
    )

async def perform_conversion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user = get_user_data(user_id)
    
    conversion = query.data.replace("convert_", "")
    required_gems = int(conversion)
    
    if user["gems"] < required_gems:
        await query.edit_message_text(f"جم کافی ندارید! برای این تبدیل به {required_gems} جم نیاز دارید.")
        return
    
    user["gems"] -= required_gems
    
    if conversion == "1":
        user["gold"] += 2
        await query.edit_message_text(f"✅ تبدیل انجام شد!\n\n💎 جم باقیمانده: {user['gems']}\n💰 کیسه طلا: {user['gold']}")
    elif conversion == "3":
        user["gold"] += 6
        user["silver"] += 4
        await query.edit_message_text(f"✅ تبدیل انجام شد!\n\n💎 جم باقیمانده: {user['gems']}\n💰 کیسه طلا: {user['gold']}\n🪙 شمش نقره: {user['silver']}")
    elif conversion == "10":
        user["gold"] += 20
        user["silver"] += 15
        await query.edit_message_text(f"✅ تبدیل انجام شد!\n\n💎 جم باقیمانده: {user['gems']}\n💰 کیسه طلا: {user['gold']}\n🪙 شمش نقره: {user['silver']}")
    
    await shop(update, context)

# Other menu handlers
async def top_players(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # Get top 10 players by points
    top_players = sorted(users_db.items(), key=lambda x: x[1]["points"], reverse=True)[:10]
    
    text = "🏆 برترین ناخدایان:\n\n"
    for i, (user_id, data) in enumerate(top_players, 1):
        ship_name = ships_db.get(user_id, {}).get("name", "ناشناس")
        win_rate = calculate_win_rate(user_id)
        text += f"{i}. {ship_name} - 🏆 {data['points']} - 🎯 {win_rate}%\n"
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("بازگشت", callback_data="main_menu")]
        ])
    )

async def search_players(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "🔍 جستجوی کاربران:\n\n"
        "لطفا نام کشتی کاربر مورد نظر را ارسال کنید:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("بازگشت", callback_data="main_menu")]
        ])
    )

async def handle_player_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    search_term = update.message.text.strip().lower()
    
    found_players = []
    for uid, ship in ships_db.items():
        if ship["name"] and search_term in ship["name"].lower() and uid != user_id:
            found_players.append((uid, ship["name"]))
    
    if not found_players:
        await update.message.reply_text("کاربری با این نام یافت نشد.")
        return
    
    keyboard = []
    for uid, name in found_players[:5]:  # Limit to 5 results
        keyboard.append([InlineKeyboardButton(name, callback_data=f"request_battle_{uid}")])
    
    keyboard.append([InlineKeyboardButton("بازگشت", callback_data="main_menu")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "نتایج جستجو:",
        reply_markup=reply_markup
    )

async def request_battle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    opponent_id = int(query.data.replace("request_battle_", ""))
    
    battle_requests[user_id] = {
        "opponent_id": opponent_id,
        "status": "waiting"
    }
    
    # Notify opponent
    try:
        await context.bot.send_message(
            opponent_id,
            f"⚔️ درخواست نبرد از {ships_db[user_id]['name']}!\n\n"
            "آیا مایل به نبرد هستید؟",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ قبول", callback_data=f"accept_battle_{user_id}")],
                [InlineKeyboardButton("❌ رد", callback_data=f"reject_battle_{user_id}")]
            ])
        )
    except Exception as e:
        logger.error(f"Failed to send battle request: {e}")
        await query.edit_message_text("ارسال درخواست ناموفق بود. ممکن است کاربر ربات را مسدود کرده باشد.")
        return
    
    await query.edit_message_text("درخواست نبرد ارسال شد. منتظر پاسخ حریف باشید...")

async def ship_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user = get_user_data(user_id)
    ship = get_ship_data(user_id)
    win_rate = calculate_win_rate(user_id)
    
    text = (
        f"🚢 اطلاعات کشتی {ship['name']}:\n\n"
        f"💎 جم: {user['gems']}\n"
        f"💰 کیسه طلا: {user['gold']}\n"
        f"🪙 شمش نقره: {user['silver']}\n"
        f"🎯 میانگین پیروزی: {win_rate}%\n"
        f"⚡ انرژی: {ship['energy']}%\n"
        f"💣 توپ: {user['cannon_balls']}"
    )
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("بازگشت", callback_data="main_menu")]
        ])
    )

async def crew_energy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    ship = get_ship_data(user_id)
    user = get_user_data(user_id)
    
    can_refill = can_refill_energy(user_id)
    
    text = (
        f"⚡ انرژی جنگجویان: {ship['energy']}%\n\n"
    )
    
    if ship["energy"] < 50:
        text += "⚠️ انرژی جنگجویان شما کم است! برای نبرد بهتر انرژی را افزایش دهید.\n\n"
    
    if can_refill:
        text += "🛒 می‌توانید از گزینه‌های زیر برای افزایش انرژی استفاده کنید:"
        keyboard = [
            [InlineKeyboardButton("1 بسته بیسکویت دریایی (25%) - 4 شمش", callback_data="buy_biscuit")],
            [InlineKeyboardButton("5 عدد ماهی خشک (35%) - 1 کیسه + 1 شمش", callback_data="buy_fish")],
            [InlineKeyboardButton("3 بسته میوه خشک (30%) - 1 کیسه", callback_data="buy_fruit")],
            [InlineKeyboardButton("10 قالب پنیر کهنه (50%) - 1 کیسه + 3 شمش", callback_data="buy_cheese")],
            [InlineKeyboardButton("10 بطری آب (20%) - 3 شمش", callback_data="buy_water")],
            [InlineKeyboardButton("بازگشت", callback_data="main_menu")]
        ]
    else:
        last_refill = ship["last_energy_refill"].astimezone(pytz.timezone("Asia/Tehran")).strftime("%Y-%m-%d %H:%M")
        next_refill = (ship["last_energy_refill"] + timedelta(days=1)).astimezone(pytz.timezone("Asia/Tehran")).strftime("%Y-%m-%d %H:%M")
        text += (
            f"⏳ شما امروز قبلا از فروشگاه خرید کرده‌اید.\n"
            f"آخرین خرید: {last_refill}\n"
            f"خرید بعدی: {next_refill}"
        )
        keyboard = [[InlineKeyboardButton("بازگشت", callback_data="main_menu")]]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup)

async def buy_energy_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user = get_user_data(user_id)
    ship = get_ship_data(user_id)
    
    if not can_refill_energy(user_id):
        await query.edit_message_text("شما امروز قبلا از فروشگاه خرید کرده‌اید. لطفا فردا مجددا مراجعه کنید.")
        return
    
    item = query.data.replace("buy_", "")
    success = False
    
    if item == "biscuit":
        if user["silver"] >= 4:
            user["silver"] -= 4
            update_energy(user_id, 25)
            success = True
        else:
            await query.edit_message_text("شمش نقره کافی ندارید!")
    elif item == "fish":
        if user["gold"] >= 1 and user["silver"] >= 1:
            user["gold"] -= 1
            user["silver"] -= 1
            update_energy(user_id, 35)
            success = True
        else:
            await query.edit_message_text("کیسه طلا یا شمش نقره کافی ندارید!")
    elif item == "fruit":
        if user["gold"] >= 1:
            user["gold"] -= 1
            update_energy(user_id, 30)
            success = True
        else:
            await query.edit_message_text("کیسه طلا کافی ندارید!")
    elif item == "cheese":
        if user["gold"] >= 1 and user["silver"] >= 3:
            user["gold"] -= 1
            user["silver"] -= 3
            update_energy(user_id, 50)
            success = True
        else:
            await query.edit_message_text("کیسه طلا یا شمش نقره کافی ندارید!")
    elif item == "water":
        if user["silver"] >= 3:
            user["silver"] -= 3
            update_energy(user_id, 20)
            success = True
        else:
            await query.edit_message_text("شمش نقره کافی ندارید!")
    
    if success:
        ship["last_energy_refill"] = datetime.now(pytz.utc)
        await query.edit_message_text(
            f"✅ خرید با موفقیت انجام شد!\n\n"
            f"⚡ انرژی جدید: {ship['energy']}%",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("بازگشت", callback_data="crew_energy")]
            ])
        )
    else:
        await crew_energy(update, context)

# Webhook handler
@app.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, application.bot)
    await application.update_queue.put(update)
    return {"ok": True}

# Startup and shutdown
@app.on_event("startup")
async def on_startup():
    await application.bot.set_webhook(url=WEBHOOK_URL)
    print("✅ Webhook set:", WEBHOOK_URL)
    await application.initialize()
    await application.start()
    await application.updater.start_polling()

@app.on_event("shutdown")
async def on_shutdown():
    await application.updater.stop()
    await application.stop()
    await application.shutdown()

# Register handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_ship_name))
application.add_handler(CallbackQueryHandler(show_main_menu, pattern="^main_menu$"))
application.add_handler(CallbackQueryHandler(start_game, pattern="^start_game$"))
application.add_handler(CallbackQueryHandler(sail, pattern="^sail$"))
application.add_handler(CallbackQueryHandler(continue_report, pattern="^continue_report$"))
application.add_handler(CallbackQueryHandler(fire_cannon, pattern="^fire_cannon$"))
application.add_handler(CallbackQueryHandler(choose_strategy, pattern="^choose_strategy$"))
application.add_handler(CallbackQueryHandler(set_strategy, pattern="^strategy_"))
application.add_handler(CallbackQueryHandler(cannon_info, pattern="^cannon_info$"))
application.add_handler(CallbackQueryHandler(shop, pattern="^shop$"))
application.add_handler(CallbackQueryHandler(buy_gems, pattern="^buy_gems$"))
application.add_handler(CallbackQueryHandler(buy_cannon, pattern="^buy_cannon$"))
application.add_handler(CallbackQueryHandler(convert_gems, pattern="^convert_gems$"))
application.add_handler(CallbackQueryHandler(perform_conversion, pattern="^convert_"))
application.add_handler(CallbackQueryHandler(top_players, pattern="^top_players$"))
application.add_handler(CallbackQueryHandler(search_players, pattern="^search_players$"))
application.add_handler(CallbackQueryHandler(ship_info, pattern="^ship_info$"))
application.add_handler(CallbackQueryHandler(crew_energy, pattern="^crew_energy$"))
application.add_handler(CallbackQueryHandler(buy_energy_item, pattern="^buy_"))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_player_search))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_payment_receipt))
