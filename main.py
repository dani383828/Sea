import logging
import sqlite3
import time
import random
import re
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Updater,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    Filters,
    JobQueue
)
from datetime import datetime, timedelta

# تنظیمات لاگینگ
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# توکن بات و اطلاعات دیگر
TOKEN = "8030062261:AAFnC9AJ_2zvcaqC0LXe5Y3--d2FgxOx-fI"
ADMIN_ID = 5542927340
TRX_ADDRESS = "TJ4xrwKJzKjk6FgKfuuqwah3Az5Ur22kJb"
WEBHOOK_URL = "https://sea-2ri6.onrender.com"

# تنظیمات دیتابیس
def init_db():
    conn = sqlite3.connect("pirates.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        ship_name TEXT UNIQUE,
        gems INTEGER DEFAULT 5,
        gold INTEGER DEFAULT 10,
        silver INTEGER DEFAULT 15,
        score INTEGER DEFAULT 0,
        wins INTEGER DEFAULT 0,
        total_games INTEGER DEFAULT 0,
        energy INTEGER DEFAULT 90,
        cannons INTEGER DEFAULT 3,
        last_food_purchase TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS strategies (
        user_id INTEGER,
        strategy TEXT,
        FOREIGN KEY (user_id) REFERENCES users (user_id)
    )''')
    conn.commit()
    conn.close()

# بررسی نام کشتی
def is_valid_ship_name(name):
    if not name or name.lower() in ["/start", "start"] or not re.match("^[A-Za-z0-9 ]+$", name):
        return False
    conn = sqlite3.connect("pirates.db")
    c = conn.cursor()
    c.execute("SELECT ship_name FROM users WHERE ship_name = ?", (name,))
    exists = c.fetchone()
    conn.close()
    return not exists

# منوی اصلی
def main_menu():
    keyboard = [
        [InlineKeyboardButton("شروع بازی ⚔️", callback_data="start_game")],
        [InlineKeyboardButton("فروشگاه 🛒", callback_data="shop")],
        [InlineKeyboardButton("برترین ناخدایان 🏆", callback_data="leaderboard")],
        [InlineKeyboardButton("جست‌وجوی کاربران 🔍", callback_data="search_users")],
        [InlineKeyboardButton("اطلاعات کشتی 🚢", callback_data="ship_info")],
        [InlineKeyboardButton("انرژی جنگجویان ⚡", callback_data="energy")]
    ]
    return InlineKeyboardMarkup(keyboard)

# دستور شروع
def start(update, context):
    user_id = update.effective_user.id
    conn = sqlite3.connect("pirates.db")
    c = conn.cursor()
    c.execute("SELECT ship_name FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()

    if result:
        update.message.reply_text(
            "🏴‍☠️ به دنیای دزدان دریایی خوش اومدی، کاپیتان!\n🚢 آماده‌ای کشتی‌تو بسازی و راهی دریا بشی؟",
            reply_markup=main_menu()
        )
    else:
        update.message.reply_text(
            "🏴‍☠️ به دنیای دزدان دریایی خوش اومدی، کاپیتان!\nکشتیت در حال ساخته شدنه...\nساخته شد! 🚢\nنام کشتیت رو بگو (فقط انگلیسی، بدون تکرار):"
        )
        context.user_data["awaiting_ship_name"] = True

# ثبت نام کشتی
def handle_message(update, context):
    user_id = update.effective_user.id
    if context.user_data.get("awaiting_ship_name"):
        ship_name = update.message.text.strip()
        if is_valid_ship_name(ship_name):
            conn = sqlite3.connect("pirates.db")
            c = conn.cursor()
            c.execute(
                "INSERT INTO users (user_id, ship_name) VALUES (?, ?)",
                (user_id, ship_name)
            )
            conn.commit()
            conn.close()
            context.user_data["awaiting_ship_name"] = False
            update.message.reply_text(
                f"کشتی {ship_name} آماده دریانوردیه! 🏴‍☠️",
                reply_markup=main_menu()
            )
        else:
            update.message.reply_text(
                "نام معتبر نیست! فقط حروف انگلیسی و بدون تکرار. دوباره امتحان کن:"
            )
    elif context.user_data.get("awaiting_search"):
        search_name = update.message.text.strip()
        conn = sqlite3.connect("pirates.db")
        c = conn.cursor()
        c.execute("SELECT user_id, ship_name FROM users WHERE ship_name = ?", (search_name,))
        result = c.fetchone()
        conn.close()
        if result:
            keyboard = [[InlineKeyboardButton("درخواست جنگ ⚔️", callback_data=f"challenge_{result[0]}")]]
            update.message.reply_text(
                f"کشتی {search_name} پیدا شد! می‌خوای باهاش بجنگی؟",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            update.message.reply_text("کشتی‌ای با این نام پیدا نشد!")
        context.user_data["awaiting_search"] = False
    elif context.user_data.get("awaiting_receipt"):
        receipt = update.message.text or update.message.photo
        context.bot.forward_message(
            chat_id=ADMIN_ID,
            from_chat_id=update.effective_chat.id,
            message_id=update.message.message_id
        )
        keyboard = [
            [InlineKeyboardButton("تایید ✅", callback_data=f"confirm_{user_id}_{context.user_data['gem_amount']}")],
            [InlineKeyboardButton("رد ❌", callback_data=f"reject_{user_id}")]
        ]
        context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"فیش پرداخت برای {context.user_data['gem_amount']} جم از کاربر {user_id}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        update.message.reply_text("فیش شما برای ادمین ارسال شد. منتظر تایید باشید!")
        context.user_data["awaiting_receipt"] = False

# منوی شروع بازی
def start_game_menu(update, context):
    query = update.callback_query
    query.answer()
    keyboard = [
        [InlineKeyboardButton("دریانوردی ⛵", callback_data="sail")],
        [InlineKeyboardButton("استراتژی 🎯", callback_data="strategy")],
        [InlineKeyboardButton("توپ ☄️", callback_data="cannon")],
        [InlineKeyboardButton("بازگشت ↩️", callback_data="main_menu")]
    ]
    query.message.edit_text("انتخاب کن:", reply_markup=InlineKeyboardMarkup(keyboard))

# منوی استراتژی
def strategy_menu(update, context):
    query = update.callback_query
    query.answer()
    keyboard = [
        [InlineKeyboardButton("استتار به عنوان کشتی تجاری", callback_data="strategy_disguise")],
        [InlineKeyboardButton("حمله شبانه", callback_data="strategy_night")],
        [InlineKeyboardButton("آتش‌زدن کشتی دشمن", callback_data="strategy_fire")],
        [InlineKeyboardButton("اتصال قلاب", callback_data="strategy_hook")],
        [InlineKeyboardButton("کمین پشت صخره", callback_data="strategy_ambush")],
        [InlineKeyboardButton("فریب با گنج جعلی", callback_data="strategy_decoy")],
        [InlineKeyboardButton("حمله با کمک جاسوس", callback_data="strategy_spy")]
    ]
    query.message.edit_text("🎯 استراتژی خودتو انتخاب کن:", reply_markup=InlineKeyboardMarkup(keyboard))

# ثبت استراتژی
def set_strategy(update, context):
    query = update.callback_query
    query.answer()
    strategy = query.data.split("_")[1]
    user_id = update.effective_user.id
    conn = sqlite3.connect("pirates.db")
    c = conn.cursor()
    c.execute("DELETE FROM strategies WHERE user_id = ?", (user_id,))
    c.execute("INSERT INTO strategies (user_id, strategy) VALUES (?, ?)", (user_id, strategy))
    conn.commit()
    conn.close()
    query.message.edit_text(f"استراتژی {strategy} انتخاب شد!", reply_markup=main_menu())

# دریانوردی
def sail(update, context):
    query = update.callback_query
    query.answer()
    user_id = update.effective_user.id
    conn = sqlite3.connect("pirates.db")
    c = conn.cursor()
    c.execute("SELECT strategy, cannons, energy FROM users u LEFT JOIN strategies s ON u.user_id = s.user_id WHERE u.user_id = ?", (user_id,))
    user_data = c.fetchone()
    strategy, cannons, energy = user_data if user_data else (None, 3, 90)

    # پیدا کردن حریف
    c.execute("SELECT user_id, strategy, cannons, energy FROM users u LEFT JOIN strategies s ON u.user_id = s.user_id WHERE u.user_id != ? ORDER BY RANDOM() LIMIT 1", (user_id,))
    opponent = c.fetchone()
    if not opponent:
        # حریف فیک
        opponent_strategy = random.choice(["disguise", "night", "fire", "hook", "ambush", "decoy", "spy"])
        opponent_cannons = random.randint(1, 5)
        opponent_energy = random.randint(50, 100)
        opponent = (None, opponent_strategy, opponent_cannons, opponent_energy)

    # منطق استراتژی‌ها
    strategy_outcomes = {
        ("night", "spy"): (False, "حمله شبانه لو رفت چون حریف جاسوس داشت!"),
        ("disguise", "spy"): (True, "استتار به عنوان کشتی تجاری موفق بود!"),
        ("fire", "hook"): (False, "حریف با قلاب کشتی را گرفت و آتش‌زدن ناکام ماند!"),
        ("hook", "ambush"): (False, "کمین پشت صخره حریف، قلاب را ناکام گذاشت!"),
        ("ambush", "decoy"): (False, "گنج جعلی حریف، کمین را بی‌اثر کرد!"),
        ("decoy", "spy"): (False, "جاسوس حریف، فریب گنج جعلی را کشف کرد!"),
        ("spy", "disguise"): (True, "جاسوس اطلاعات خوبی از کشتی تجاری به دست آورد!")
    }

    # تعیین برنده
    user_strategy = strategy or random.choice(["disguise", "night", "fire", "hook", "ambush", "decoy", "spy"])
    opponent_strategy = opponent[1] or random.choice(["disguise", "night", "fire", "hook", "ambush", "decoy", "spy"])
    context.user_data["battle"] = {
        "opponent": opponent,
        "user_cannons": cannons,
        "opponent_cannons": opponent[2],
        "user_strategy": user_strategy,
        "opponent_strategy": opponent_strategy,
        "stage": 0,
        "last_cannon_time": time.time()
    }

    # شروع جنگ
    query.message.edit_text(
        "دریانوردی آغاز شد! ⛵\nکشتی دشمن در افق پیداست! آماده باش!",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("پرتاب توپ ☄️", callback_data="fire_cannon")]])
    )
    context.job_queue.run_once(battle_update, 5, data={"user_id": user_id}, chat_id=query.message.chat_id)

# به‌روزرسانی جنگ
def battle_update(context):
    user_id = context.job.data["user_id"]
    battle = context.user_data.get("battle")
    if not battle:
        return

    stages = [
        "کشتی‌ها به هم نزدیک شدن! 🚢",
        "دشمن داره آماده حمله میشه! ⚔️",
        "کشتیت سوراخ شد! 🕳️ حالا وقتشه؟",
        "خیلی بهشون نزدیک شدیم! 🏴‍☠️"
    ]
    battle["stage"] += 1
    if battle["stage"] < len(stages):
        context.bot.send_message(
            chat_id=user_id,
            text=stages[battle["stage"]],
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("پرتاب توپ ☄️", callback_data="fire_cannon")]])
        )
        context.job_queue.run_once(battle_update, 5, data={"user_id": user_id}, chat_id=user_id)
    else:
        # پایان جنگ و تعیین نتیجه
        user_strategy = battle["user_strategy"]
        opponent_strategy = battle["opponent_strategy"]
        user_cannons = battle["user_cannons"]
        opponent_cannons = battle["opponent_cannons"]
        user_energy = context.user_data.get("energy", 90)
        opponent_energy = battle["opponent"][3]

        outcome = strategy_outcomes.get((user_strategy, opponent_strategy), (True, "استراتژی‌ها برابر بودند!"))
        win = outcome[0]
        message = outcome[1]

        if user_cannons > opponent_cannons:
            win = True
            message += "\nتوپ‌های بیشترت برتری رو بهت داد!"
        elif user_cannons < opponent_cannons:
            win = False
            message += "\nتوپ‌های کمترت باعث شکستت شد!"

        if user_energy > opponent_energy + 20:
            win = True
            message += "\nانرژی بالای جنگجوهات برتری رو بهت داد!"
        elif user_energy < opponent_energy - 20:
            win = False
            message += "\nانرژی کم جنگجوهات باعث شکستت شد!"

        conn = sqlite3.connect("pirates.db")
        c = conn.cursor()
        c.execute("SELECT gems, gold, silver, score, wins, total_games, energy FROM users WHERE user_id = ?", (user_id,))
        user_data = c.fetchone()
        gems, gold, silver, score, wins, total_games, energy = user_data

        if win:
            score += 30
            gold += 3
            silver += 5
            gems += 1 if random.random() < 0.25 else 0
            energy = min(100, energy + 10)
            wins += 1
            message += "\n🏆 برنده شدی!\n+30 امتیاز, +3 کیسه طلا, +5 شمش نقره, +10% انرژی"
            if gems > user_data[0]:
                message += ", +1 جم"
        else:
            score = max(0, score - 10)
            gold = max(0, gold - 3)
            silver = max(0, silver - 5)
            gems = max(0, gems - 1 if random.random() < 0.25 else 0)
            energy = max(0, energy - 30)
            message += "\n😔 باختی!\n-10 امتیاز, -3 کیسه طلا, -5 شمش نقره, -30% انرژی"
            if gems < user_data[0]:
                message += ", -1 جم"

        total_games += 1
        c.execute(
            "UPDATE users SET score = ?, gold = ?, silver = ?, gems = ?, wins = ?, total_games = ?, energy = ? WHERE user_id = ?",
            (score, gold, silver, gems, wins, total_games, energy, user_id)
        )
        conn.commit()
        conn.close()

        context.bot.send_message(chat_id=user_id, text=message, reply_markup=main_menu())
        context.user_data.pop("battle", None)

# پرتاب توپ
def fire_cannon(update, context):
    query = update.callback_query
    query.answer()
    user_id = update.effective_user.id
    battle = context.user_data.get("battle")
    if not battle:
        query.message.edit_text("هیچ جنگی در جریان نیست!", reply_markup=main_menu())
        return

    conn = sqlite3.connect("pirates.db")
    c = conn.cursor()
    c.execute("SELECT cannons FROM users WHERE user_id = ?", (user_id,))
    cannons = c.fetchone()[0]
    if cannons <= 0:
        query.message.edit_text("توپ نداری! برو به فروشگاه و توپ بخر!", reply_markup=main_menu())
        return

    cannons -= 1
    c.execute("UPDATE users SET cannons = ? WHERE user_id = ?", (cannons, user_id))
    conn.commit()
    conn.close()

    # منطق زمان‌بندی پرتاب
    time_diff = time.time() - battle["last_cannon_time"]
    hit_chance = 0.65 if 2 <= battle["stage"] <= 3 else 0.10
    if random.random() < hit_chance:
        battle["user_cannons"] += 1
        query.message.edit_text("🎯 توپ به هدف خورد! شانس برنده شدنت بیشتر شد!")
    else:
        query.message.edit_text("💨 توپ خطا رفت!")
    battle["last_cannon_time"] = time.time()

# منوی فروشگاه
def shop_menu(update, context):
    query = update.callback_query
    query.answer()
    keyboard = [
        [InlineKeyboardButton("خرید جم 💎", callback_data="buy_gems")],
        [InlineKeyboardButton("خرید توپ ☄️", callback_data="buy_cannons")],
        [InlineKeyboardButton("تبدیل جم", callback_data="convert_gems")],
        [InlineKeyboardButton("بازگشت ↩️", callback_data="main_menu")]
    ]
    query.message.edit_text("به فروشگاه خوش اومدی! 🛒", reply_markup=InlineKeyboardMarkup(keyboard))

# خرید جم
def buy_gems(update, context):
    query = update.callback_query
    query.answer()
    keyboard = [
        [InlineKeyboardButton("25 جم = ۵ ترون", callback_data="gem_25")],
        [InlineKeyboardButton("50 جم = ۸ ترون", callback_data="gem_50")],
        [InlineKeyboardButton("100 جم = ۱۴ ترون", callback_data="gem_100")]
    ]
    query.message.edit_text(
        f"💎 خرید جم:\nآدرس ترون: {TRX_ADDRESS}\nلطفا مقدار مورد نظر رو انتخاب کن و فیش پرداخت رو بفرست:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# انتخاب تعداد جم
def select_gems(update, context):
    query = update.callback_query
    query.answer()
    gem_amount = int(query.data.split("_")[1])
    context.user_data["gem_amount"] = gem_amount
    context.user_data["awaiting_receipt"] = True
    query.message.edit_text("لطفا فیش پرداخت رو بفرست (عکس یا متن):")

# تایید یا رد فیش
def handle_receipt(update, context):
    query = update.callback_query
    query.answer()
    data = query.data.split("_")
    action, user_id, *args = data
    user_id = int(user_id)
    conn = sqlite3.connect("pirates.db")
    c = conn.cursor()

    if action == "confirm":
        gem_amount = int(args[0])
        c.execute("UPDATE users SET gems = gems + ? WHERE user_id = ?", (gem_amount, user_id))
        conn.commit()
        context.bot.send_message(chat_id=user_id, text=f"{gem_amount} جم به حسابت اضافه شد! 💎")
    else:
        context.bot.send_message(chat_id=user_id, text="فیش پرداخت رد شد! ❌")

    conn.close()
    query.message.edit_text("اقدام انجام شد!")

# خرید توپ
def buy_cannons(update, context):
    query = update.callback_query
    query.answer()
    user_id = update.effective_user.id
    conn = sqlite3.connect("pirates.db")
    c = conn.cursor()
    c.execute("SELECT gems FROM users WHERE user_id = ?", (user_id,))
    gems = c.fetchone()[0]
    if gems >= 3:
        c.execute("UPDATE users SET gems = gems - 3, cannons = cannons + 1 WHERE user_id = ?", (user_id,))
        conn.commit()
        query.message.edit_text("یک توپ خریدی! ☄️")
    else:
        query.message.edit_text("جم کافی نداری! برو جم بخر 💎")
    conn.close()

# تبدیل جم
def convert_gems(update, context):
    query = update.callback_query
    query.answer()
    keyboard = [
        [InlineKeyboardButton("1 جم = 2 کیسه طلا", callback_data="convert_1")],
        [InlineKeyboardButton("3 جم = 6 کیسه طلا + 4 شمش نقره", callback_data="convert_3")],
        [InlineKeyboardButton("10 جم = 20 کیسه طلا + 15 شمش نقره", callback_data="convert_10")]
    ]
    query.message.edit_text("انتخاب کن:", reply_markup=InlineKeyboardMarkup(keyboard))

# انجام تبدیل جم
def do_convert_gems(update, context):
    query = update.callback_query
    query.answer()
    user_id = update.effective_user.id
    amount = int(query.data.split("_")[1])
    conn = sqlite3.connect("pirates.db")
    c = conn.cursor()
    c.execute("SELECT gems FROM users WHERE user_id = ?", (user_id,))
    gems = c.fetchone()[0]

    if amount == 1 and gems >= 1:
        c.execute("UPDATE users SET gems = gems - 1, gold = gold + 2 WHERE user_id = ?", (user_id,))
        message = "1 جم به 2 کیسه طلا تبدیل شد!"
    elif amount == 3 and gems >= 3:
        c.execute("UPDATE users SET gems = gems - 3, gold = gold + 6, silver = silver + 4 WHERE user_id = ?", (user_id,))
        message = "3 جم به 6 کیسه طلا و 4 شمش نقره تبدیل شد!"
    elif amount == 10 and gems >= 10:
        c.execute("UPDATE users SET gems = gems - 10, gold = gold + 20, silver = silver + 15 WHERE user_id = ?", (user_id,))
        message = "10 جم به 20 کیسه طلا و 15 شمش نقره تبدیل شد!"
    else:
        message = "جم کافی نداری!"

    conn.commit()
    conn.close()
    query.message.edit_text(message, reply_markup=main_menu())

# برترین ناخدایان
def leaderboard(update, context):
    query = update.callback_query
    query.answer()
    conn = sqlite3.connect("pirates.db")
    c = conn.cursor()
    c.execute("SELECT ship_name, score, wins, total_games FROM users ORDER BY score DESC LIMIT 5")
    leaders = c.fetchall()
    conn.close()
    text = "🏆 برترین ناخدایان:\n"
    for i, (ship, score, wins, total_games) in enumerate(leaders, 1):
        win_rate = (wins / total_games * 100) if total_games > 0 else 0
        text += f"{i}. {ship}: {score} امتیاز (میانگین برد: {win_rate:.1f}%)\n"
    query.message.edit_text(text, reply_markup=main_menu())

# جست‌وجوی کاربران
def search_users(update, context):
    query = update.callback_query
    query.answer()
    context.user_data["awaiting_search"] = True
    query.message.edit_text("اسم کشتی دوستت رو بنویس:")

# چالش دوستانه
def challenge_friend(update, context):
    query = update.callback_query
    query.answer()
    opponent_id = int(query.data.split("_")[1])
    user_id = update.effective_user.id
    context.bot.send_message(
        chat_id=opponent_id,
        text=f"کشتی {get_ship_name(user_id)} بهت چالش دوستانه داده! قبول می‌کنی؟",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("قبول ⚔️", callback_data=f"accept_{user_id}")]])
    )
    query.message.edit_text("درخواست جنگ فرستاده شد! منتظر جواب باش.")

# قبول چالش
def accept_challenge(update, context):
    query = update.callback_query
    query.answer()
    user_id = update.effective_user.id
    opponent_id = int(query.data.split("_")[1])
    conn = sqlite3.connect("pirates.db")
    c = conn.cursor()
    c.execute("SELECT strategy, energy FROM users u LEFT JOIN strategies s ON u.user_id = s.user_id WHERE u.user_id = ?", (user_id,))
    user_data = c.fetchone()
    c.execute("SELECT strategy, energy FROM users u LEFT JOIN strategies s ON u.user_id = s.user_id WHERE u.user_id = ?", (opponent_id,))
    opponent_data = c.fetchone()
    conn.close()

    user_strategy = user_data[0] or random.choice(["disguise", "night", "fire", "hook", "ambush", "decoy", "spy"])
    opponent_strategy = opponent_data[0] or random.choice(["disguise", "night", "fire", "hook", "ambush", "decoy", "spy"])
    context.user_data["battle"] = {
        "opponent": (opponent_id, opponent_strategy, 20, opponent_data[1]),
        "user_cannons": 20,
        "opponent_cannons": 20,
        "user_strategy": user_strategy,
        "opponent_strategy": opponent_strategy,
        "stage": 0,
        "last_cannon_time": time.time()
    }
    query.message.edit_text(
        "جنگ دوستانه شروع شد! ⛵\nکشتی دشمن در افق پیداست!",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("پرتاب توپ ☄️", callback_data="fire_cannon")]])
    )
    context.job_queue.run_once(battle_update, 5, data={"user_id": user_id}, chat_id=query.message.chat_id)

# اطلاعات کشتی
def get_ship_name(user_id):
    conn = sqlite3.connect("pirates.db")
    c = conn.cursor()
    c.execute("SELECT ship_name FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else "ناشناس"

def ship_info(update, context):
    query = update.callback_query
    query.answer()
    user_id = update.effective_user.id
    conn = sqlite3.connect("pirates.db")
    c = conn.cursor()
    c.execute("SELECT ship_name, gems, gold, silver, wins, total_games, energy FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    ship_name, gems, gold, silver, wins, total_games, energy = result
    win_rate = (wins / total_games * 100) if total_games > 0 else 0
    text = f"🚢 اطلاعات کشتی {ship_name}:\n💎 جم: {gems}\n🥇 کیسه طلا: {gold}\n🥈 شمش نقره: {silver}\n🏆 میانگین پیروزی: {win_rate:.1f}%\n⚡ انرژی: {energy}%"
    query.message.edit_text(text, reply_markup=main_menu())

# منوی انرژی
def energy_menu(update, context):
    query = update.callback_query
    query.answer()
    user_id = update.effective_user.id
    conn = sqlite3.connect("pirates.db")
    c = conn.cursor()
    c.execute("SELECT energy, last_food_purchase FROM users WHERE user_id = ?", (user_id,))
    energy, last_food_purchase = c.fetchone()
    conn.close()

    if last_food_purchase and (datetime.now() - datetime.fromisoformat(last_food_purchase)) < timedelta(hours=24):
        query.message.edit_text("فقط هر ۲۴ ساعت می‌تونی خوراکی بخری!", reply_markup=main_menu())
        return

    keyboard = [
        [InlineKeyboardButton("بیسکویت دریایی (۴ شمش نقره)", callback_data="food_biscuit")],
        [InlineKeyboardButton("ماهی خشک (۱ کیسه طلا + ۱ شمش نقره)", callback_data="food_fish")],
        [InlineKeyboardButton("میوه خشک (۱ کیسه طلا)", callback_data="food_fruit")],
        [InlineKeyboardButton("پنیر کهنه (۱ کیسه طلا + ۳ شمش نقره)", callback_data="food_cheese")],
        [InlineKeyboardButton("آب (۳ شمش نقره)", callback_data="food_water")]
    ]
    query.message.edit_text(
        f"⚡ انرژی جنگجویان: {energy}%\nاگه جنگجوهات خستن، براشون خوراکی بخر!",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# خرید خوراکی
def buy_food(update, context):
    query = update.callback_query
    query.answer()
    user_id = update.effective_user.id
    food = query.data.split("_")[1]
    conn = sqlite3.connect("pirates.db")
    c = conn.cursor()
    c.execute("SELECT gold, silver, energy, last_food_purchase FROM users WHERE user_id = ?", (user_id,))
    gold, silver, energy, last_food_purchase = c.fetchone()

    if last_food_purchase and (datetime.now() - datetime.fromisoformat(last_food_purchase)) < timedelta(hours=24):
        query.message.edit_text("فقط هر ۲۴ ساعت می‌تونی خوراکی بخری!", reply_markup=main_menu())
        conn.close()
        return

    food_prices = {
        "biscuit": (0, 4, 25),
        "fish": (1, 1, 35),
        "fruit": (1, 0, 30),
        "cheese": (1, 3, 50),
        "water": (0, 3, 20)
    }
    gold_cost, silver_cost, energy_gain = food_prices[food]

    if gold >= gold_cost and silver >= silver_cost:
        energy = min(100, energy + energy_gain)
        c.execute(
            "UPDATE users SET gold = ?, silver = ?, energy = ?, last_food_purchase = ? WHERE user_id = ?",
            (gold - gold_cost, silver - silver_cost, energy, datetime.now().isoformat(), user_id)
        )
        conn.commit()
        query.message.edit_text(f"خوراکی خریدی! +{energy_gain}% انرژی", reply_markup=main_menu())
    else:
        query.message.edit_text("منابع کافی نداری!", reply_markup=main_menu())
    conn.close()

# بازگشت به منوی اصلی
def back_to_main(update, context):
    query = update.callback_query
    query.answer()
    query.message.edit_text("🏴‍☠️ به دنیای دزدان دریایی خوش اومدی، کاپیتان!", reply_markup=main_menu())

# مدیریت کلیدهای اینلاین
def button_handler(update, context):
    query = update.callback_query
    data = query.data

    if data == "start_game":
        start_game_menu(update, context)
    elif data == "strategy":
        strategy_menu(update, context)
    elif data.startswith("strategy_"):
        set_strategy(update, context)
    elif data == "sail":
        sail(update, context)
    elif data == "cannon":
        user_id = update.effective_user.id
        conn = sqlite3.connect("pirates.db")
        c = conn.cursor()
        c.execute("SELECT cannons FROM users WHERE user_id = ?", (user_id,))
        cannons = c.fetchone()[0]
        conn.close()
        query.message.edit_text(f"توپ‌های تو: {cannons}\nبرای خرید توپ به فروشگاه برو!", reply_markup=main_menu())
    elif data == "fire_cannon":
        fire_cannon(update, context)
    elif data == "shop":
        shop_menu(update, context)
    elif data == "buy_gems":
        buy_gems(update, context)
    elif data.startswith("gem_"):
        select_gems(update, context)
    elif data.startswith("confirm_") or data.startswith("reject_"):
        handle_receipt(update, context)
    elif data == "buy_cannons":
        buy_cannons(update, context)
    elif data == "convert_gems":
        convert_gems(update, context)
    elif data.startswith("convert_"):
        do_convert_gems(update, context)
    elif data == "leaderboard":
        leaderboard(update, context)
    elif data == "search_users":
        search_users(update, context)
    elif data.startswith("challenge_"):
        challenge_friend(update, context)
    elif data.startswith("accept_"):
        accept_challenge(update, context)
    elif data == "ship_info":
        ship_info(update, context)
    elif data == "energy":
        energy_menu(update, context)
    elif data.startswith("food_"):
        buy_food(update, context)
    elif data == "main_menu":
        back_to_main(update, context)

def main():
    init_db()
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    dp.add_handler(CallbackQueryHandler(button_handler))
    updater.start_webhook(
        listen="0.0.0.0",
        port=8443,
        url_path=TOKEN,
        webhook_url=f"{WEBHOOK_URL}/{TOKEN}"
    )
    updater.idle()

if __name__ == "__main__":
    main()
