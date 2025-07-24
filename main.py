import os
import re
import random
import sqlite3
import threading
from datetime import datetime, timedelta

from flask import Flask, request, jsonify
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot, ParseMode
)
from telegram.ext import (
    Dispatcher, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, CallbackContext
)

TOKEN = "8030062261:AAFnC9AJ_2zvcaqC0LXe5Y3--d2FgxOx-fI"
ADMIN_ID = 5542927340
TRX_ADDRESS = "TJ4xrwKJzKjk6FgKfuuqwah3Az5Ur22kJb"
BASE_URL = "https://sea-2ri6.onrender.com"

app = Flask(__name__)
bot = Bot(TOKEN)
dp = Dispatcher(bot, None, workers=4, use_context=True)

DB_NAME = "pirate_game.db"

# ====== DATABASE SETUP ======

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # کاربران
    c.execute("""CREATE TABLE IF NOT EXISTS players (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        ship_name TEXT UNIQUE,
        gold_bags INTEGER DEFAULT 10,
        silver_ingots INTEGER DEFAULT 15,
        gems INTEGER DEFAULT 5,
        energy INTEGER DEFAULT 90,
        wins INTEGER DEFAULT 0,
        losses INTEGER DEFAULT 0,
        strategy TEXT DEFAULT 'حمله شبانه',
        cannons INTEGER DEFAULT 3,
        last_food_time TEXT DEFAULT '',
        friend_request_from INTEGER DEFAULT NULL
    )""")
    # گزارشات بازی
    c.execute("""CREATE TABLE IF NOT EXISTS game_reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        player1 INTEGER,
        player2 INTEGER,
        winner INTEGER,
        report TEXT,
        date_played TEXT
    )""")
    # ذخیره استراتژی ها
    c.execute("""CREATE TABLE IF NOT EXISTS strategies (
        name TEXT PRIMARY KEY,
        description TEXT
    )""")
    # ثبت درخواست های خرید جم و تایید ادمین
    c.execute("""CREATE TABLE IF NOT EXISTS gem_purchases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount INTEGER,
        status TEXT DEFAULT 'pending',
        proof TEXT
    )""")
    conn.commit()
    conn.close()

init_db()

# ====== UTILS ======

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def valid_ship_name(name):
    # فقط انگلیسی بدون تکرار، حداقل 3 تا کاراکتر، حروف و اعداد
    if len(name) < 3:
        return False
    if not re.fullmatch(r'[A-Za-z0-9]+', name):
        return False
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT 1 FROM players WHERE ship_name=?", (name,))
    exists = c.fetchone()
    conn.close()
    return not exists

def get_player(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM players WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row

def create_player(user_id, username, ship_name):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO players(user_id, username, ship_name)
        VALUES (?, ?, ?)""", (user_id, username, ship_name))
    conn.commit()
    conn.close()

def update_player_field(user_id, field, value):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(f"UPDATE players SET {field}=? WHERE user_id=?", (value, user_id))
    conn.commit()
    conn.close()

def add_gems(user_id, amount):
    player = get_player(user_id)
    if player:
        new_amount = player["gems"] + amount
        update_player_field(user_id, "gems", new_amount)
        return new_amount
    return None

def add_gold(user_id, amount):
    player = get_player(user_id)
    if player:
        new_amount = max(0, player["gold_bags"] + amount)
        update_player_field(user_id, "gold_bags", new_amount)
        return new_amount
    return None

def add_silver(user_id, amount):
    player = get_player(user_id)
    if player:
        new_amount = max(0, player["silver_ingots"] + amount)
        update_player_field(user_id, "silver_ingots", new_amount)
        return new_amount
    return None

def add_energy(user_id, amount_percent):
    player = get_player(user_id)
    if player:
        new_energy = player["energy"] + int(player["energy"] * amount_percent / 100)
        new_energy = min(100, max(0, new_energy))
        update_player_field(user_id, "energy", new_energy)
        return new_energy
    return None

def update_strategy(user_id, strategy):
    update_player_field(user_id, "strategy", strategy)

def update_cannons(user_id, number):
    update_player_field(user_id, "cannons", number)

def record_win(user_id):
    player = get_player(user_id)
    if player:
        new_wins = player["wins"] + 1
        update_player_field(user_id, "wins", new_wins)

def record_loss(user_id):
    player = get_player(user_id)
    if player:
        new_losses = player["losses"] + 1
        update_player_field(user_id, "losses", new_losses)

def calculate_winrate(user):
    total = user["wins"] + user["losses"]
    if total == 0:
        return "0%"
    return f"{int(user['wins'] * 100 / total)}%"

# ... (ادامه در بخش بعد) ---

# ====== COMMANDS ======

START_TEXT = """
🏴‍☠️ به دنیای دزدان دریایی خوش آمدی، کاپیتان!

🚢 آماده‌ای کشتی‌ات را بسازی و راهی دریا شوی؟

برای شروع بازی /start را بزن یا از دکمه‌ها استفاده کن.
"""

MAIN_MENU_TEXT = """
کاپیتان، انتخاب کن:

1️⃣ شروع بازی ⚔️  
2️⃣ فروشگاه 🛒  
3️⃣ برترین ناخدایان 👑  
4️⃣ جستجوی کاربران 🔍  
5️⃣ اطلاعات کشتی ⛵️  
6️⃣ انرژی جنگجویان 🍗  
"""

# کلیدهای منو اصلی
def main_menu_keyboard():
    buttons = [
        [InlineKeyboardButton("شروع بازی ⚔️", callback_data="start_game")],
        [InlineKeyboardButton("فروشگاه 🛒", callback_data="shop")],
        [InlineKeyboardButton("برترین ناخدایان 👑", callback_data="top_captains")],
        [InlineKeyboardButton("جستجوی کاربران 🔍", callback_data="search_users")],
        [InlineKeyboardButton("اطلاعات کشتی ⛵️", callback_data="ship_info")],
        [InlineKeyboardButton("انرژی جنگجویان 🍗", callback_data="energy_warriors")],
    ]
    return InlineKeyboardMarkup(buttons)

# /start command handler
def start(update: Update, context: CallbackContext):
    user = update.effective_user
    player = get_player(user.id)
    if player:
        # اگر قبلا ثبت شده بود، منوی اصلی بده
        update.message.reply_text(f"خوش برگشتی کاپیتان {player['ship_name']}!", reply_markup=main_menu_keyboard())
    else:
        update.message.reply_text(START_TEXT, reply_markup=main_menu_keyboard())

dp.add_handler(CommandHandler("start", start))

# هندل کلیک دکمه‌های منو
def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    player = get_player(user_id)

    data = query.data
    query.answer()

    if data == "start_game":
        if player and player["ship_name"]:
            # کشتی ساخته شده
            query.edit_message_text("کاپیتان، وارد دریانوردی می‌شوی یا استراتژی را انتخاب می‌کنی؟",
                                    reply_markup=start_game_menu())
        else:
            # هنوز کشتی نداره، شروع ساخت کشتی
            query.edit_message_text("در حال ساخت کشتی... لطفا نام کشتی انگلیسی و غیرتکراری را ارسال کن.")
            context.user_data["creating_ship"] = True

    elif data == "shop":
        # فروشگاه
        query.edit_message_text(shop_text(), reply_markup=shop_keyboard())

    elif data == "top_captains":
        text = get_top_captains_text()
        query.edit_message_text(text, reply_markup=back_to_main_keyboard())

    elif data == "search_users":
        query.edit_message_text("لطفا نام کشتی یا نام کاربری دوستت را ارسال کن تا جستجو کنم.")
        context.user_data["searching_user"] = True

    elif data == "ship_info":
        if player:
            text = get_ship_info_text(player)
            query.edit_message_text(text, reply_markup=back_to_main_keyboard())
        else:
            query.edit_message_text("شما هنوز کشتی نسازی. لطفا ابتدا بازی را شروع کن.", reply_markup=main_menu_keyboard())

    elif data == "energy_warriors":
        if player:
            text = get_energy_info_text(player)
            query.edit_message_text(text, reply_markup=energy_food_keyboard())
        else:
            query.edit_message_text("شما هنوز کشتی نسازی. لطفا ابتدا بازی را شروع کن.", reply_markup=main_menu_keyboard())

    elif data == "back_main":
        query.edit_message_text("بازگشت به منوی اصلی.", reply_markup=main_menu_keyboard())

    elif data.startswith("strategy_"):
        strategy = data.replace("strategy_", "")
        if player:
            update_strategy(user_id, strategy)
            query.edit_message_text(f"استراتژی شما به '{strategy}' تغییر کرد.", reply_markup=start_game_menu())

    elif data == "navigation":
        # شروع دریانوردی
        start_navigation(update, context)

    elif data == "throw_cannon":
        # پرتاب توپ
        handle_throw_cannon(update, context)

    # ... (بخش های بعدی اضافه خواهد شد)

dp.add_handler(CallbackQueryHandler(button_handler))

# منوی شروع بازی بعد از ساخت کشتی
def start_game_menu():
    buttons = [
        [InlineKeyboardButton("دریانوردی ⛵️", callback_data="navigation")],
        [InlineKeyboardButton("استراتژی 🎯", callback_data="strategy_menu")],
        [InlineKeyboardButton("توپ 🎯", callback_data="cannons")],
        [InlineKeyboardButton("بازگشت به منوی اصلی", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(buttons)

# منوی استراتژی
def strategy_menu_keyboard():
    strategies = [
        "استتار به عنوان کشتی تجاری",
        "حمله شبانه",
        "آتش‌زدن کشتی دشمن",
        "اتصال قلاب",
        "کمین پشت صخره‌",
        "فریب با گنج جعلی",
        "حمله با کمک جاسوس"
    ]
    buttons = []
    for s in strategies:
        buttons.append([InlineKeyboardButton(s, callback_data=f"strategy_{s}")])
    buttons.append([InlineKeyboardButton("بازگشت", callback_data="start_game")])
    return InlineKeyboardMarkup(buttons)

# متن فروشگاه
def shop_text():
    return f"""
💎 فروش جم:

۲۵ جم = ۵ ترون  
۵۰ جم = ۸ ترون  
۱۰۰ جم = ۱۴ ترون  

آدرس ترون برای پرداخت:  
`{TRX_ADDRESS}`

پس از پرداخت فیش را ارسال کن تا بررسی شود.
"""

# صفحه کلید فروشگاه
def shop_keyboard():
    buttons = [
        [InlineKeyboardButton("خرید ۲۵ جم", callback_data="buy_gems_25")],
        [InlineKeyboardButton("خرید ۵۰ جم", callback_data="buy_gems_50")],
        [InlineKeyboardButton("خرید ۱۰۰ جم", callback_data="buy_gems_100")],
        [InlineKeyboardButton("خرید توپ (۳ جم)", callback_data="buy_cannon")],
        [InlineKeyboardButton("تبدیل جم به کیسه طلا و شمش نقره", callback_data="convert_gems")],
        [InlineKeyboardButton("بازگشت", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(buttons)

# دکمه بازگشت
def back_to_main_keyboard():
    buttons = [[InlineKeyboardButton("بازگشت به منوی اصلی", callback_data="back_main")]]
    return InlineKeyboardMarkup(buttons)

# پیام بهترین ناخدایان
def get_top_captains_text():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM players ORDER BY wins DESC LIMIT 10")
    rows = c.fetchall()
    text = "👑 برترین ناخدایان بازی:\n\n"
    for i, row in enumerate(rows, 1):
        winrate = calculate_winrate(row)
        text += f"{i}. {row['ship_name']} - امتیاز: {row['wins']*30 - row['losses']*10} - میانگین برد: {winrate}\n"
    conn.close()
    return text or "فعلا بازیکنی وجود ندارد."

# اطلاعات کشتی
def get_ship_info_text(player):
    text = f"""
🏴‍☠️ اطلاعات کشتی {player['ship_name']}:

💎 جم: {player['gems']}  
💰 کیسه طلا: {player['gold_bags']}  
🪙 شمش نقره: {player['silver_ingots']}  
⚔️ توپ‌ها: {player['cannons']}  
📊 میانگین پیروزی: {calculate_winrate(player)}  
⚡️ انرژی: {player['energy']}%
"""
    return text

# اطلاعات انرژی جنگجویان
def get_energy_info_text(player):
    text = f"""
⚡️ انرژی جنگجویان: {player['energy']}%

اگر جنگجویانت خسته‌اند، برایشان خوراکی بخرید!

🌊 خوراکی‌ها:
1⃣ 1 بسته بیسکویت دریایی - ۲۵٪ انرژی - ۴ شمش نقره  
2⃣ 5 عدد ماهی خشک - ۳۵٪ انرژی - ۱ کیسه طلا و ۱ شمش نقره  
3⃣ 3 بسته میوه خشک‌شده - ۳۰٪ انرژی - ۱ کیسه طلا  
4⃣ 10 قالب پنیر کهنه - ۵۰٪ انرژی - ۱ کیسه طلا و ۳ شمش نقره  
5⃣ 10 بطری آب - ۲۰٪ انرژی - ۳ شمش نقره

*هر خوراکی را فقط یکبار در هر ۲۴ ساعت می‌توان خرید.
"""
    return text

# صفحه کلید خوراکی
def energy_food_keyboard():
    buttons = [
        [InlineKeyboardButton("1 بسته بیسکویت دریایی", callback_data="buy_food_biscuit")],
        [InlineKeyboardButton("5 عدد ماهی خشک", callback_data="buy_food_fish")],
        [InlineKeyboardButton("3 بسته میوه خشک‌شده", callback_data="buy_food_fruit")],
        [InlineKeyboardButton("10 قالب پنیر کهنه", callback_data="buy_food_cheese")],
        [InlineKeyboardButton("10 بطری آب", callback_data="buy_food_water")],
        [InlineKeyboardButton("بازگشت", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(buttons)

# ====== HANDLERS FOR TEXT MESSAGES ======

def text_message_handler(update: Update, context: CallbackContext):
    user = update.effective_user
    user_id = user.id
    text = update.message.text.strip()

    # ساخت کشتی
    if context.user_data.get("creating_ship"):
        if text.lower() in ["/start", "شروع بازی", "فروشگاه", "برترین ناخدایان", "جستجوی کاربران", "اطلاعات کشتی", "انرژی جنگجویان"]:
            update.message.reply_text("این نام قابل قبول نیست. لطفا نام کشتی انگلیسی و غیرتکراری ارسال کن.")
            return
        if not valid_ship_name(text):
            update.message.reply_text("نام کشتی باید انگلیسی، بدون فاصله، تکراری نباشد و حداقل ۳ کاراکتر داشته باشد.")
            return
        create_player(user_id, user.username or "", text)
        context.user_data["creating_ship"] = False
        update.message.reply_text(f"کشتی '{text}' ساخته شد! اکنون می‌توانی بازی را شروع کنی.", reply_markup=main_menu_keyboard())
        return

    # جستجوی کاربران
    if context.user_data.get("searching_user"):
        context.user_data["searching_user"] = False
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM players WHERE ship_name LIKE ?", (f"%{text}%",))
        rows = c.fetchall()
        if not rows:
            update.message.reply_text("هیچ کاربری با این نام پیدا نشد.", reply_markup=main_menu_keyboard())
        else:
            buttons = []
            for r in rows:
                buttons.append([InlineKeyboardButton(f"{r['ship_name']}", callback_data=f"friend_request_{r['user_id']}")])
            buttons.append([InlineKeyboardButton("بازگشت", callback_data="back_main")])
            update.message.reply_text("کاربران پیدا شده:", reply_markup=InlineKeyboardMarkup(buttons))
        conn.close()
        return

    update.message.reply_text("لطفا از منو استفاده کنید.", reply_markup=main_menu_keyboard())

dp.add_handler(MessageHandler(Filters.text & ~Filters.command, text_message_handler))


# === بخش دریانوردی و جنگ (شروع جنگ، پرتاب توپ و گزارش) ===

def start_navigation(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    player = get_player(user_id)
    if not player:
        query.edit_message_text("ابتدا کشتی خود را بسازید.", reply_markup=main_menu_keyboard())
        return

    # تلاش برای پیدا کردن رقیب همزمان
    opponent = find_opponent(user_id)
    if not opponent:
        # اگر ۱ دقیقه کسی نبود، رقیب فیک میسازیم
        opponent = create_fake_opponent()

    # بازی شروع می‌شود و گزارش‌ها ساخته می‌شود
    report_text = play_battle(player, opponent, user_id, context)
    buttons = [[InlineKeyboardButton("پرتاب توپ ☄️", callback_data="throw_cannon")],
               [InlineKeyboardButton("بازگشت", callback_data="start_game")]]
    query.edit_message_text(report_text, reply_markup=InlineKeyboardMarkup(buttons))

def find_opponent(user_id):
    # ساده‌ترین مدل: دنبال بازیکنی که الان بازی می‌خواد انجام بده و غیر از خود ما باشد
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM players WHERE user_id != ? LIMIT 1", (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return row
    return None

def create_fake_opponent():
    # ساخت یک بازیکن جعلی با استراتژی و انرژی رندوم
    fake = {
        "user_id": 0,
        "ship_name": "DavyJones",
        "gems": 5,
        "gold_bags": 10,
        "silver_ingots": 15,
        "energy": random.randint(60, 100),
        "strategy": random.choice([
            "استتار به عنوان کشتی تجاری",
            "حمله شبانه",
            "آتش‌زدن کشتی دشمن",
            "اتصال قلاب",
            "کمین پشت صخره‌",
            "فریب با گنج جعلی",
            "حمله با کمک جاسوس"
        ]),
        "cannons": 3,
    }
    return fake

# تابع اجرای جنگ و منطق پیروزی - شکست با منطق استراتژی و انرژی
def play_battle(player, opponent, user_id, context):
    # استراتژی دو بازیکن
    p_strategy = player["strategy"]
    o_strategy = opponent["strategy"]
    p_energy = player["energy"]
    o_energy = opponent["energy"]
    p_cannons = player["cannons"]
    o_cannons = opponent.get("cannons", 3)

    # منطق مقابله استراتژی‌ها
    # استراتژی ها به ترتیب قدرت نسبی فرضی (قابل توسعه):
    # حمله شبانه > اتصال قلاب > کمین پشت صخره > استتار به عنوان کشتی تجاری > فریب با گنج جعلی > آتش‌زدن کشتی دشمن > حمله با کمک جاسوس
    # این ترتیب برای مثال است. در صورت تقابل اینطور نتیجه می‌گیرد:
    strat_power = {
        "حمله شبانه": 7,
        "اتصال قلاب": 6,
        "کمین پشت صخره": 5,
        "استتار به عنوان کشتی تجاری": 4,
        "فریب با گنج جعلی": 3,
        "آتش‌زدن کشتی دشمن": 2,
        "حمله با کمک جاسوس": 1
    }

    p_power = strat_power.get(p_strategy, 4) * (p_energy / 100) * (p_cannons / 3)
    o_power = strat_power.get(o_strategy, 4) * (o_energy / 100) * (o_cannons / 3)

    # مقابله استراتژی خاص: حمله شبانه لو میره اگر حریف حمله با کمک جاسوس داشته باشه
    if p_strategy == "حمله شبانه" and o_strategy == "حمله با کمک جاسوس":
        p_power *= 0.5  # حمله لو رفته، نصف قدرت
    if o_strategy == "حمله شبانه" and p_strategy == "حمله با کمک جاسوس":
        o_power *= 0.5

    # پرتاب توپ منطق:
    # 65 درصد احتمال زدن توپ در زمان منطقی، 10 درصد در غیر منطقی (در اینجا فرضا همیشه منطقی است چون بازیکن داره کلیک می‌کنه)
    # اگر توپ نداشت، احتمال برد کاهش می‌یابد
    p_has_cannon = p_cannons > 0
    o_has_cannon = o_cannons > 0

    if not p_has_cannon:
        p_power *= 0.5  # قدرت کمتر بدون توپ
    if not o_has_cannon:
        o_power *= 0.5

    # تصمیم نهایی بر اساس قدرت نسبی
    if p_power > o_power:
        winner = user_id
        loser = opponent["user_id"]
        result_text = f"کاپیتان {player['ship_name']} برنده شد! 🎉\n"
        # جوایز
        add_gold(user_id, 3)
        add_silver(user_id, 5)
        add_gems(user_id, 1 if random.random() < 0.25 else 0)
        add_energy(user_id, 10)
        record_win(user_id)
        if loser != 0:
            record_loss(loser)
            add_gold(loser, -3)
            add_silver(loser, -5)
            add_gems(loser, -1 if random.random() < 0.25 else 0)
            add_energy(loser, -30)
        else:
            # بازیکن فیک - هیچ تغییری ندارد
            pass
    else:
        winner = opponent["user_id"]
        loser = user_id
        result_text = f"کاپیتان {player['ship_name']} شکست خورد... 😞\n"
        add_gold(user_id, -3)
        add_silver(user_id, -5)
        add_gems(user_id, -1 if random.random() < 0.25 else 0)
        add_energy(user_id, -30)
        record_loss(user_id)
        if winner != 0:
            record_win(winner)
            add_gold(winner, 3)
            add_silver(winner, 5)
            add_gems(winner, 1 if random.random() < 0.25 else 0)
            add_energy(winner, 10)

    # گزارش نهایی
    report = f"""
🔥 گزارش نبرد:
کاپیتان شما: {player['ship_name']}  
استراتژی: {p_strategy}  
انرژی: {p_energy}%  
توپ: {p_cannons}  

رقیب: {opponent['ship_name']}  
استراتژی: {o_strategy}  
انرژی: {o_energy}%  
توپ: {o_cannons}  

نتیجه:  
{result_text}
"""

    # ذخیره گزارش در دیتابیس
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO game_reports(player1, player2, winner, report, date_played)
        VALUES (?, ?, ?, ?, ?)""",
              (user_id, opponent["user_id"], winner, report, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

    return report

# هندل پرتاب توپ (ساده در اینجا - اثر در قدرت بازی اعمال شد)
def handle_throw_cannon(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    player = get_player(user_id)
    if not player or player["cannons"] <= 0:
        query.answer("توپ نداری! باید توپ بخری.", show_alert=True)
        query.edit_message_text("توپ نداری! برای خرید به فروشگاه برو.", reply_markup=main_menu_keyboard())
        return
    # کاهش توپ
    update_cannons(user_id, player["cannons"] - 1)
    query.answer("توپ پرتاب شد!")
    query.edit_message_text("توپ پرتاب شد! منتظر گزارش نبرد بعدی باشید.", reply_markup=main_menu_keyboard())

# ====== فروشگاه و خرید جم، توپ، تبدیل جم ======

def buy_gems(update: Update, context: CallbackContext, amount: int):
    user_id = update.callback_query.from_user.id
    update.callback_query.answer()
    text = f"""
برای خرید {amount} جم، لطفا مبلغ زیر را به آدرس TRX واریز کن و سپس فیش پرداخت را به ربات ارسال کن:

💎 مقدار: {amount} جم  
💰 مبلغ (ترون): {trx_price(amount)}  
آدرس پرداخت: {TRX_ADDRESS}

بعد از پرداخت، رسید یا فیش پرداخت را همینجا ارسال کن.
"""
    update.callback_query.edit_message_text(text)

def trx_price(amount):
    if amount == 25:
        return 5
    elif amount == 50:
        return 8
    elif amount == 100:
        return 14
    else:
        return 0

def buy_cannon(update: Update, context: CallbackContext):
    user_id = update.callback_query.from_user.id
    player = get_player(user_id)
    if player["gems"] < 3:
        update.callback_query.answer("جم کافی نداری!", show_alert=True)
        update.callback_query.edit_message_text("جم کافی برای خرید توپ نداری.", reply_markup=shop_keyboard())
        return
    # کم کردن ۳ جم و اضافه کردن ۱ توپ
    add_gems(user_id, -3)
    update_cannons(user_id, player["cannons"] + 1)
    update.callback_query.answer("توپ خریداری شد!")
    update.callback_query.edit_message_text("توپ با موفقیت خریداری شد.", reply_markup=shop_keyboard())

def convert_gems(update: Update, context: CallbackContext):
    user_id = update.callback_query.from_user.id
    text = """
💎 تبدیل جم به کیسه طلا و شمش نقره:

1 جم = 2 کیسه طلا  
3 جم = 6 کیسه طلا + 4 شمش نقره  
10 جم = 20 کیسه طلا + 15 شمش نقره  

لطفا مقدار جم را ارسال کن (فقط 1، 3 یا 10):
"""
    update.callback_query.answer()
    update.callback_query.edit_message_text(text)
    context.user_data["converting_gems"] = True

def handle_convert_gems(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    if not context.user_data.get("converting_gems"):
        return

    if text not in ["1", "3", "10"]:
        update.message.reply_text("مقدار معتبر نیست. فقط 1، 3 یا 10 را وارد کن.")
        return

    amount = int(text)
    player = get_player(user_id)
    if player["gems"] < amount:
        update.message.reply_text("جم کافی نداری.", reply_markup=main_menu_keyboard())
        context.user_data["converting_gems"] = False
        return

    add_gems(user_id, -amount)
    if amount == 1:
        add_gold(user_id, 2)
    elif amount == 3:
        add_gold(user_id, 6)
        add_silver(user_id, 4)
    elif amount == 10:
        add_gold(user_id, 20)
        add_silver(user_id, 15)

    update.message.reply_text("تبدیل جم انجام شد.", reply_markup=main_menu_keyboard())
    context.user_data["converting_gems"] = False

# ====== خرید خوراکی ======

FOODS = {
    "buy_food_biscuit": {"name": "بیسکویت دریایی", "energy": 25, "cost_gold": 0, "cost_silver": 4},
    "buy_food_fish": {"name": "ماهی خشک", "energy": 35, "cost_gold": 1, "cost_silver": 1},
    "buy_food_fruit": {"name": "میوه خشک‌شده", "energy": 30, "cost_gold": 1, "cost_silver": 0},
    "buy_food_cheese": {"name": "پنیر کهنه", "energy": 50, "cost_gold": 1, "cost_silver": 3},
    "buy_food_water": {"name": "آب", "energy": 20, "cost_gold": 0, "cost_silver": 3},
}

def can_buy_food(user_id, food_key):
    conn = get_db_connection()
    c = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    c.execute("SELECT last_food_time FROM players WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    if not row or not row[0]:
        return True
    last_time_str = row[0]
    try:
        last_time = datetime.strptime(last_time_str, "%Y-%m-%d %H:%M:%S")
    except Exception:
        return True
    # حداقل 24 ساعت باید گذشته باشد
    return datetime.now() - last_time > timedelta(hours=24)

def buy_food(update: Update, context: CallbackContext, food_key: str):
    user_id = update.callback_query.from_user.id
    player = get_player(user_id)
    if not player:
        update.callback_query.answer("ابتدا کشتی بسازید.", show_alert=True)
        update.callback_query.edit_message_text("ابتدا کشتی بسازید.", reply_markup=main_menu_keyboard())
        return

    food = FOODS.get(food_key)
    if not food:
        update.callback_query.answer("خوراکی نامعتبر.", show_alert=True)
        return

    # چک کردن زمان خرید
    if not can_buy_food(user_id, food_key):
        update.callback_query.answer("فقط یک بار در ۲۴ ساعت می‌توان این خوراکی را خرید.", show_alert=True)
        return

    # بررسی هزینه
    if player["gold_bags"] < food["cost_gold"] or player["silver_ingots"] < food["cost_silver"]:
        update.callback_query.answer("کیسه طلا یا شمش نقره کافی نداری!", show_alert=True)
        return

    # کم کردن هزینه و افزایش انرژی
    add_gold(user_id, -food["cost_gold"])
    add_silver(user_id, -food["cost_silver"])
    add_energy(user_id, food["energy"])

    # به روز رسانی زمان خرید خوراکی
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("UPDATE players SET last_food_time=? WHERE user_id=?", (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_id))
    conn.commit()
    conn.close()

    update.callback_query.answer(f"{food['name']} خریداری شد و انرژی افزایش یافت.")
    update.callback_query.edit_message_text(get_energy_info_text(get_player(user_id)), reply_markup=energy_food_keyboard())

# ====== تایید و رد فیش پرداخت جم توسط ادمین ======

def handle_purchase_proof(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if user_id == ADMIN_ID:
        return  # ادمین فیش نمیفرسته

    # چک میکنیم آیا کاربر منتظر تایید فیش خرید جم است
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM gem_purchases WHERE user_id=? AND status='pending'", (user_id,))
    pending = c.fetchone()
    if pending:
        update.message.reply_text("در انتظار تایید فیش قبلی هستید.")
        conn.close()
        return

    # ذخیره فیش در دیتابیس با وضعیت pending
    proof = None
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        proof = f"photo:{file_id}"
    elif update.message.text:
        proof = update.message.text

    if not proof:
        update.message.reply_text("لطفا عکس یا متن رسید پرداخت را ارسال کنید.")
        conn.close()
        return

    c.execute("INSERT INTO gem_purchases(user_id, amount, proof) VALUES (?, ?, ?)", (user_id, 0, proof))
    conn.commit()
    conn.close()

    # ارسال به ادمین برای تایید یا رد
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("تایید ✅", callback_data=f"approve_purchase_{user_id}"),
         InlineKeyboardButton("رد ❌", callback_data=f"reject_purchase_{user_id}")]
    ])
    bot.send_message(ADMIN_ID, f"فیش خرید جم از کاربر {user_id} دریافت شد. لطفا تایید یا رد کنید.", reply_markup=keyboard)
    update.message.reply_text("رسید پرداخت ارسال شد. منتظر تایید ادمین باشید.")

def admin_purchase_decision(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data
    admin_id = query.from_user.id
    if admin_id != ADMIN_ID:
        query.answer("شما ادمین نیستید!", show_alert=True)
        return

    if data.startswith("approve_purchase_"):
        user_id = int(data.split("_")[-1])
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("UPDATE gem_purchases SET status='approved' WHERE user_id=? AND status='pending'", (user_id,))
        c.execute("SELECT amount FROM gem_purchases WHERE user_id=? AND status='approved' ORDER BY id DESC LIMIT 1", (user_id,))
        row = c.fetchone()
        amount = row["amount"] if row else 0
        add_gems(user_id, amount)
        conn.commit()
        conn.close()
        bot.send_message(user_id, f"خرید جم شما تایید شد و {amount} جم به حساب شما اضافه شد.")
        query.edit_message_text(f"خرید جم کاربر {user_id} تایید شد.")
        query.answer()

    elif data.startswith("reject_purchase_"):
        user_id = int(data.split("_")[-1])
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("UPDATE gem_purchases SET status='rejected' WHERE user_id=? AND status='pending'", (user_id,))
        conn.commit()
        conn.close()
        bot.send_message(user_id, "خرید جم شما رد شد. لطفا مجددا اقدام کنید.")
        query.edit_message_text(f"خرید جم کاربر {user_id} رد شد.")
        query.answer()

dp.add_handler(MessageHandler(Filters.photo | Filters.text & ~Filters.command, handle_purchase_proof))
dp.add_handler(CallbackQueryHandler(admin_purchase_decision, pattern="^(approve_purchase_|reject_purchase_).*$"))

# ====== مدیریت callback خریدها ======

def shop_callback_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data
    if data == "buy_gems_25":
        buy_gems(update, context, 25)
    elif data == "buy_gems_50":
        buy_gems(update, context, 50)
    elif data == "buy_gems_100":
        buy_gems(update, context, 100)
    elif data == "buy_cannon":
        buy_cannon(update, context)
    elif data == "convert_gems":
        convert_gems(update, context)
    elif data in FOODS:
        buy_food(update, context, data)
    elif data == "back_main":
        query.edit_message_text("بازگشت به منوی اصلی.", reply_markup=main_menu_keyboard())
    else:
        query.answer()

dp.add_handler(CallbackQueryHandler(shop_callback_handler, pattern="^(buy_gems_|buy_cannon|convert_gems|buy_food_).*|back_main$"))

# ====== ادامه هندل متن تبدیل جم ======
dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_convert_gems))

# ====== برترین ناخدایان ======

def get_top_captains():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
        SELECT user_id, ship_name, score, 
        CASE WHEN total_battles>0 THEN ROUND(100.0 * wins / total_battles, 1) ELSE 0 END AS win_rate
        FROM players ORDER BY score DESC LIMIT 10
    """)
    rows = c.fetchall()
    conn.close()
    return rows

def top_captains_text():
    captains = get_top_captains()
    text = "🏆 برترین ناخدایان:\n\n"
    for i, cpt in enumerate(captains, 1):
        text += f"{i}. {cpt['ship_name']} — امتیاز: {cpt['score']} — درصد برد: {cpt['win_rate']}%\n"
    return text

def top_captains_handler(update: Update, context: CallbackContext):
    update.message.reply_text(top_captains_text(), reply_markup=main_menu_keyboard())

# ====== جستجوی کاربران و درخواست جنگ دوستانه ======

def search_user(update: Update, context: CallbackContext):
    text = update.message.text.strip()
    user_id = update.effective_user.id
    player = get_player(user_id)
    if not player:
        update.message.reply_text("ابتدا کشتی خود را بسازید.", reply_markup=main_menu_keyboard())
        return
    # جستجو بر اساس ship_name
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT user_id, ship_name FROM players WHERE ship_name LIKE ?", (f"%{text}%",))
    rows = c.fetchall()
    conn.close()
    if not rows:
        update.message.reply_text("هیچ کشتی‌ای با این نام پیدا نشد.", reply_markup=main_menu_keyboard())
        return

    buttons = []
    for row in rows:
        if row["user_id"] == user_id:
            continue
        buttons.append([InlineKeyboardButton(f"{row['ship_name']}", callback_data=f"friend_war_request_{row['user_id']}")])
    if not buttons:
        update.message.reply_text("هیچ کشتی‌ای به جز کشتی خودتان پیدا نشد.", reply_markup=main_menu_keyboard())
        return

    update.message.reply_text("کشتی‌های یافت شده:", reply_markup=InlineKeyboardMarkup(buttons))

def friend_war_request_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    from_id = query.from_user.id
    data = query.data
    if data.startswith("friend_war_request_"):
        to_id = int(data.split("_")[-1])
        player = get_player(from_id)
        if not player:
            query.answer("ابتدا کشتی خود را بسازید.", show_alert=True)
            return
        # ارسال درخواست به طرف مقابل
        buttons = [
            [InlineKeyboardButton("قبول ⚔️", callback_data=f"friend_war_accept_{from_id}")],
            [InlineKeyboardButton("رد ❌", callback_data=f"friend_war_reject_{from_id}")]
        ]
        bot.send_message(to_id, f"درخواست جنگ دوستانه از کشتی {player['ship_name']} دریافت کردی. قبول می‌کنی؟", reply_markup=InlineKeyboardMarkup(buttons))
        query.answer("درخواست برای طرف مقابل ارسال شد.")
        query.edit_message_text("درخواست جنگ دوستانه ارسال شد.", reply_markup=main_menu_keyboard())

def friend_war_response_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id
    if data.startswith("friend_war_accept_"):
        from_id = int(data.split("_")[-1])
        # شروع بازی دوستانه با توپ 20 رایگان، بدون امتیاز و جایزه
        context.user_data["friend_war"] = True
        context.user_data["friend_opponent"] = from_id
        context.user_data["friend_cannons"] = 20
        bot.send_message(user_id, "جنگ دوستانه شروع شد! ۲۰ توپ رایگان داری.")
        bot.send_message(from_id, f"درخواست جنگ دوستانه‌ات قبول شد توسط {get_player(user_id)['ship_name']}.")
        query.edit_message_text("درخواست قبول شد. بازی شروع شد.")
    elif data.startswith("friend_war_reject_"):
        from_id = int(data.split("_")[-1])
        bot.send_message(from_id, f"درخواست جنگ دوستانه توسط {get_player(user_id)['ship_name']} رد شد.")
        query.edit_message_text("درخواست رد شد.")

# ====== نمایش اطلاعات کشتی ======

def ship_info_text(player):
    if not player:
        return "کشتی ساخته نشده."
    avg_win = 0
    if player["total_battles"] > 0:
        avg_win = round(100 * player["wins"] / player["total_battles"], 1)
    text = f"""
🏴‍☠️ اطلاعات کشتی {player['ship_name']}:

💎 جم: {player['gems']}
🪙 کیسه طلا: {player['gold_bags']}
⚪ شمش نقره: {player['silver_ingots']}
🎯 امتیاز: {player['score']}
📊 میانگین برد: {avg_win}%
⚡ انرژی: {player['energy']}%
    """
    return text

def ship_info_handler(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    player = get_player(user_id)
    update.message.reply_text(ship_info_text(player), reply_markup=main_menu_keyboard())

# ====== انرژی جنگجویان و خرید خوراکی ======

def energy_info_text(player):
    text = f"""
⚡ انرژی جنگجویان شما: {player['energy']}%

اگر جنگجویانت خسته‌اند، می‌توانی برایشان خوراکی بخری.
"""
    return text

def energy_handler(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    player = get_player(user_id)
    update.message.reply_text(energy_info_text(player), reply_markup=energy_food_keyboard())

# ====== منوهای کیبورد ======

def main_menu_keyboard():
    buttons = [
        [InlineKeyboardButton("شروع بازی ⚔️", callback_data="start_game")],
        [InlineKeyboardButton("فروشگاه 🛒", callback_data="shop")],
        [InlineKeyboardButton("برترین ناخدایان 🏆", callback_data="top_captains")],
        [InlineKeyboardButton("جستجوی کاربران 🔍", callback_data="search_users")],
        [InlineKeyboardButton("اطلاعات کشتی 🛳️", callback_data="ship_info")],
        [InlineKeyboardButton("انرژی جنگجویان ⚡", callback_data="energy")],
    ]
    return InlineKeyboardMarkup(buttons)

def energy_food_keyboard():
    buttons = [
        [InlineKeyboardButton("بیسکویت دریایی (۴ شمش نقره)", callback_data="buy_food_biscuit")],
        [InlineKeyboardButton("ماهی خشک (1 کیسه طلا + 1 شمش نقره)", callback_data="buy_food_fish")],
        [InlineKeyboardButton("میوه خشک‌شده (1 کیسه طلا)", callback_data="buy_food_fruit")],
        [InlineKeyboardButton("پنیر کهنه (1 کیسه طلا + 3 شمش نقره)", callback_data="buy_food_cheese")],
        [InlineKeyboardButton("آب (۳ شمش نقره)", callback_data="buy_food_water")],
        [InlineKeyboardButton("بازگشت به منوی اصلی", callback_data="back_main")]
    ]
    return InlineKeyboardMarkup(buttons)

# ====== هندل callback های منو ======

def main_menu_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data

    if data == "start_game":
        start_game_handler(update, context)
    elif data == "shop":
        shop_menu_handler(update, context)
    elif data == "top_captains":
        top_captains_handler(update, context)
    elif data == "search_users":
        query.answer()
        query.edit_message_text("لطفا نام کشتی یا کاربر را ارسال کن:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("بازگشت به منوی اصلی", callback_data="back_main")]]))
        context.user_data["searching_user"] = True
    elif data == "ship_info":
        ship_info_handler(update, context)
    elif data == "energy":
        energy_handler(update, context)
    elif data == "back_main":
        query.edit_message_text("به منوی اصلی برگشتی.", reply_markup=main_menu_keyboard())
    else:
        query.answer()

dp.add_handler(CallbackQueryHandler(main_menu_handler, pattern="^(start_game|shop|top_captains|search_users|ship_info|energy|back_main)$"))

# ====== هندل پیام های جستجوی کاربر ======

def message_handler(update: Update, context: CallbackContext):
    if context.user_data.get("searching_user"):
        search_user(update, context)
        context.user_data["searching_user"] = False
        return
    handle_convert_gems(update, context)  # برای تبدیل جم
    handle_purchase_proof(update, context)  # مدیریت فیش خرید

dp.add_handler(MessageHandler(Filters.text & ~Filters.command, message_handler))
