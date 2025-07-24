import telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from flask import Flask, request
import sqlite3
import random
import time
import asyncio
import re
from datetime import datetime, timedelta
import os
import logging

# تنظیم لاگ برای دیباگ
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# توکن بات و اطلاعات مورد نیاز
TOKEN = "8030062261:AAFnC9AJ_2zvcaqC0LXe5Y3--d2FgxOx-fI"
ADMIN_ID = 5542927340
TRX_ADDRESS = "TJ4xrwKJzKjk6FgKfuuqwah3Az5Ur22kJb"

# تنظیمات Flask
app = Flask(__name__)

# مسیر دیتابیس
DATABASE_PATH = os.environ.get('DATABASE_PATH', '/tmp/pirates.db')  # در صورت عدم تنظیم دیسک پایدار، از /tmp استفاده می‌شود

# دیتابیس برای ذخیره اطلاعات کاربران
def init_db():
    try:
        # اطمینان از وجود دایرکتوری
        os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
        conn = sqlite3.connect(DATABASE_PATH)
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
            cannonballs INTEGER DEFAULT 3,
            strategy TEXT,
            last_purchase_time TEXT
        )''')
        conn.commit()
        conn.close()
        logger.info(f"Database initialized at {DATABASE_PATH}")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

init_db()

# مسیر اصلی Flask
@app.route('/')
def home():
    return "Pirate Bot is running!"

# مسیر Webhook
@app.route(f'/{TOKEN}', methods=['POST'])
async def webhook():
    update = telegram.Update.de_json(request.get_json(force=True), application.bot)
    await application.process_update(update)
    return "OK"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("شروع بازی ⚔️", callback_data='start_game')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🏴‍☠️ به دنیای دزدان دریایی خوش اومدی، کاپیتان!\n🚢 آماده‌ای کشتی‌تو بسازی و راهی دریا بشی؟",
        reply_markup=reply_markup
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == 'start_game':
        await query.message.reply_text("کشتیت در حال ساخته شدنه...\nساخته شد! 🚢\nنام کشتیت رو بگو (فقط انگلیسی، بدون تکرار):")
        context.user_data['awaiting_ship_name'] = True

    elif data == 'main_menu':
        await show_main_menu(query, context)

    elif data == 'navigate':
        await start_navigation(query, context)

    elif data == 'strategy':
        await show_strategy_menu(query, context)

    elif data.startswith('strategy_'):
        strategy = data.split('_')[1]
        await set_strategy(query, context, strategy)

    elif data == 'cannonballs':
        await check_cannonballs(query, context)

    elif data == 'shop':
        await show_shop_menu(query, context)

    elif data.startswith('buy_gems_'):
        amount = int(data.split('_')[2])
        await buy_gems(query, context, amount)

    elif data == 'buy_cannonball':
        await buy_cannonball(query, context)

    elif data.startswith('convert_gems_'):
        option = data.split('_')[2]
        await convert_gems(query, context, option)

    elif data == 'leaderboard':
        await show_leaderboard(query, context)

    elif data == 'search_users':
        await query.message.reply_text("نام کشتی دوستت رو وارد کن (به انگلیسی):")
        context.user_data['awaiting_search'] = True

    elif data == 'ship_info':
        await show_ship_info(query, context)

    elif data == 'energy':
        await show_energy_menu(query, context)

    elif data == 'fire_cannon':
        await fire_cannon(query, context)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text

    if context.user_data.get('awaiting_ship_name'):
        if re.match("^[a-zA-Z0-9 ]+$", text) and text not in ['start', 'menu']:
            conn = sqlite3.connect(DATABASE_PATH)
            c = conn.cursor()
            c.execute("SELECT ship_name FROM users WHERE ship_name = ?", (text,))
            if c.fetchone():
                await update.message.reply_text("این نام قبلاً انتخاب شده! یه نام دیگه انتخاب کن:")
                conn.close()
                return
            c.execute("INSERT OR REPLACE INTO users (user_id, ship_name) VALUES (?, ?)", (user_id, text))
            conn.commit()
            conn.close()
            context.user_data['awaiting_ship_name'] = False
            await update.message.reply_text(f"کشتیت به نام **{text}** ساخته شد! 🚢")
            await show_main_menu(update, context)
        else:
            await update.message.reply_text("لطفاً یه نام انگلیسی معتبر وارد کن (بدون استفاده از منو یا دستورات):")

    elif context.user_data.get('awaiting_search'):
        await search_and_challenge(update, context, text)

    elif context.user_data.get('awaiting_receipt'):
        await handle_receipt(update, context)

async def show_main_menu(update, context):
    user_id = update.callback_query.from_user.id if update.callback_query else update.message.from_user.id
    keyboard = [
        [InlineKeyboardButton("دریانوردی ⛵️", callback_data='navigate'),
         InlineKeyboardButton("استراتژی 🎯", callback_data='strategy')],
        [InlineKeyboardButton("توپ ☄️", callback_data='cannonballs'),
         InlineKeyboardButton("فروشگاه 🛒", callback_data='shop')],
        [InlineKeyboardButton("برترین ناخدایان 🏆", callback_data='leaderboard'),
         InlineKeyboardButton("جست‌وجوی کاربران 🔍", callback_data='search_users')],
        [InlineKeyboardButton("اطلاعات کشتی 📊", callback_data='ship_info'),
         InlineKeyboardButton("انرژی جنگجویان ⚡", callback_data='energy')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.callback_query:
        await update.callback_query.message.edit_text("🏴‍☠️ منوی اصلی:", reply_markup=reply_markup)
    else:
        await update.message.reply_text("🏴‍☠️ منوی اصلی:", reply_markup=reply_markup)

async def start_navigation(query, context):
    user_id = query.from_user.id
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    c.execute("SELECT ship_name, strategy, cannonballs, energy FROM users WHERE user_id = ?", (user_id,))
    user = c.fetchone()
    if not user:
        await query.message.reply_text("اول باید کشتیت رو بسازی!")
        conn.close()
        return
    ship_name, strategy, cannonballs, energy = user

    # جست‌وجوی حریف
    c.execute("SELECT user_id, ship_name, strategy, energy FROM users WHERE user_id != ?", (user_id,))
    opponents = c.fetchall()
    opponent = random.choice(opponents) if opponents else None

    if not opponent:
        # حریف فیک
        opponent = (999999, "FakePirate", random.choice(["merchant", "night_attack", "burn_ship", "hook", "ambush", "fake_treasure", "spy"]), 80)
        context.user_data['opponent'] = opponent
        await simulate_battle(query, context, user_id, ship_name, strategy, cannonballs, energy, opponent, is_fake=True)
    else:
        context.user_data['opponent'] = opponent
        await simulate_battle(query, context, user_id, ship_name, strategy, cannonballs, energy, opponent, is_fake=False)
    conn.close()

async def simulate_battle(query, context, user_id, ship_name, strategy, cannonballs, energy, opponent, is_fake):
    opponent_id, opponent_ship, opponent_strategy, opponent_energy = opponent
    report = f"⚔️ نبرد آغاز شد!\nکشتی تو (**{ship_name}**) در برابر **{opponent_ship}**!\n"

    # منطق استراتژی‌ها
    strategy_effectiveness = {
        "merchant": {"night_attack": 0.3, "burn_ship": 0.6, "hook": 0.5, "ambush": 0.4, "fake_treasure": 0.7, "spy": 0.2},
        "night_attack": {"merchant": 0.7, "burn_ship": 0.4, "hook": 0.6, "ambush": 0.3, "fake_treasure": 0.5, "spy": 0.1},
        "burn_ship": {"merchant": 0.5, "night_attack": 0.6, "hook": 0.4, "ambush": 0.7, "fake_treasure": 0.3, "spy": 0.5},
        "hook": {"merchant": 0.6, "night_attack": 0.4, "burn_ship": 0.5, "ambush": 0.6, "fake_treasure": 0.4, "spy": 0.5},
        "ambush": {"merchant": 0.7, "night_attack": 0.6, "burn_ship": 0.3, "hook": 0.5, "fake_treasure": 0.6, "spy": 0.4},
        "fake_treasure": {"merchant": 0.3, "night_attack": 0.5, "burn_ship": 0.6, "hook": 0.4, "ambush": 0.5, "spy": 0.7},
        "spy": {"merchant": 0.8, "night_attack": 0.7, "burn_ship": 0.5, "hook": 0.6, "ambush": 0.6, "fake_treasure": 0.3}
    }

    # محاسبه شانس برد
    base_win_chance = 0.5
    strategy_impact = strategy_effectiveness.get(strategy, {}).get(opponent_strategy, 0.5)
    energy_impact = (energy - opponent_energy) / 100
    win_chance = base_win_chance + strategy_impact - 0.1 + energy_impact
    if cannonballs > 0:
        win_chance += 0.2
    win_chance = max(0.1, min(0.9, win_chance))

    context.user_data['battle_active'] = True
    context.user_data['cannonballs'] = cannonballs
    context.user_data['win_chance'] = win_chance
    context.user_data['battle_reports'] = []

    # گزارش نبرد
    reports = [
        "کشتی دشمن در افق پیداست!",
        "خیلی بهشون نزدیک شدیم! 🛥️",
        "دشمن داره آماده حمله میشه!",
        "کشتیت سوراخ شد! 🚨",
        "دشمن داره فرار می‌کنه!"
    ]
    for i, report_text in enumerate(reports):
        context.user_data['battle_reports'].append(report_text)
        keyboard = [[InlineKeyboardButton("پرتاب توپ ☄️", callback_data='fire_cannon')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text(report + report_text, reply_markup=reply_markup)
        if i < len(reports) - 1:
            await asyncio.sleep(5)

    # نتیجه نهایی
    if random.random() < win_chance:
        await handle_win(query, context, user_id, is_fake)
    else:
        await handle_loss(query, context, user_id, is_fake)
    context.user_data['battle_active'] = False

async def fire_cannon(query, context):
    if not context.user_data.get('battle_active'):
        await query.message.reply_text("نبردی در جریان نیست!")
        return
    cannonballs = context.user_data.get('cannonballs', 0)
    if cannonballs <= 0:
        await query.message.reply_text("توپ نداری! برو به فروشگاه و توپ بخر 🛒")
        return
    report = context.user_data['battle_reports'][-1]
    logical_timing = "خیلی بهشون نزدیک شدیم!" in report
    hit_chance = 0.65 if logical_timing else 0.1
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET cannonballs = cannonballs - 1 WHERE user_id = ?", (query.from_user.id,))
    conn.commit()
    conn.close()
    context.user_data['cannonballs'] -= 1
    if random.random() < hit_chance:
        context.user_data['win_chance'] = min(context.user_data.get('win_chance', 0.5) + 0.2, 0.9)
        await query.message.reply_text("🎯 توپ به هدف خورد! شانس بردنت بیشتر شد!")
    else:
        await query.message.reply_text("💨 توپ خطا رفت!")

async def handle_win(query, context, user_id, is_fake):
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    gems_add = 1 if random.random() < 0.25 else 0
    c.execute(
        """UPDATE users SET score = score + 30, gold = gold + 3, gems = gems + ?, silver = silver + 5, 
        energy = energy + 10, wins = wins + 1, total_games = total_games + 1 WHERE user_id = ?""",
        (gems_add, user_id)
    )
    conn.commit()
    conn.close()
    await query.message.reply_text(
        f"🏆 بردی کاپیتان! 🎉\n+۳۰ امتیاز\n+۳ کیسه طلا\n+{gems_add} جم\n+۵ شمش نقره\n+۱۰٪ انرژی",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("منوی اصلی 🏴‍☠️", callback_data='main_menu')]])
    )

async def handle_loss(query, context, user_id, is_fake):
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    c.execute("SELECT gold, silver, gems FROM users WHERE user_id = ?", (user_id,))
    gold, silver, gems = c.fetchone()
    gems_loss = 1 if random.random() < 0.25 and gems > 0 else 0
    gold_loss = min(gold, 3)
    silver_loss = min(silver, 5)
    c.execute(
        """UPDATE users SET score = score - 10, gold = gold - ?, gems = gems - ?, silver = silver - ?, 
        energy = energy - 30, total_games = total_games + 1 WHERE user_id = ?""",
        (gold_loss, gems_loss, silver_loss, user_id)
    )
    conn.commit()
    conn.close()
    await query.message.reply_text(
        f"😔 باختی کاپیتان!\n-۱۰ امتیاز\n-{gold_loss} کیسه طلا\n-{gems_loss} جم\n-{silver_loss} شمش نقره\n-۳۰٪ انرژی",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("منوی اصلی 🏴‍☠️", callback_data='main_menu')]])
    )

async def show_strategy_menu(query, context):
    keyboard = [
        [InlineKeyboardButton("استتار به عنوان کشتی تجاری", callback_data='strategy_merchant'),
         InlineKeyboardButton("حمله شبانه", callback_data='strategy_night_attack')],
        [InlineKeyboardButton("آتش‌زدن کشتی دشمن", callback_data='strategy_burn_ship'),
         InlineKeyboardButton("اتصال قلاب", callback_data='strategy_hook')],
        [InlineKeyboardButton("کمین پشت صخره", callback_data='strategy_ambush'),
         InlineKeyboardButton("فریب با گنج جعلی", callback_data='strategy_fake_treasure')],
        [InlineKeyboardButton("حمله با کمک جاسوس", callback_data='strategy_spy')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.edit_text("🎯 استراتژی حمله رو انتخاب کن:", reply_markup=reply_markup)

async def set_strategy(query, context, strategy):
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET strategy = ? WHERE user_id = ?", (strategy, query.from_user.id))
    conn.commit()
    conn.close()
    await query.message.edit_text(f"استراتژی **{strategy}** انتخاب شد!",
                                 reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("منوی اصلی 🏴‍☠️", callback_data='main_menu')]]))

async def check_cannonballs(query, context):
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    c.execute("SELECT cannonballs FROM users WHERE user_id = ?", (query.from_user.id,))
    cannonballs = c.fetchone()[0]
    conn.close()
    if cannonballs == 0:
        await query.message.reply_text("توپ نداری! برو به فروشگاه و توپ بخر 🛒",
                                      reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("منوی اصلی 🏴‍☠️", callback_data='main_menu')]]))
    else:
        await query.message.reply_text(f"تعداد توپ‌ها: {cannonballs} ☄️",
                                      reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("منوی اصلی 🏴‍☠️", callback_data='main_menu')]]))

async def show_shop_menu(query, context):
    keyboard = [
        [InlineKeyboardButton("خرید جم 💎", callback_data='buy_gems'),
         InlineKeyboardButton("خرید توپ ☄️", callback_data='buy_cannonball')],
        [InlineKeyboardButton("تبدیل جم به سکه و نقره", callback_data='convert_gems'),
         InlineKeyboardButton("منوی اصلی 🏴‍☠️", callback_data='main_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.edit_text("🛒 به فروشگاه خوش اومدی!", reply_markup=reply_markup)

async def buy_gems(query, context, amount=None):
    if not amount:
        keyboard = [
            [InlineKeyboardButton("۲۵ جم = ۵ ترون", callback_data='buy_gems_25'),
             InlineKeyboardButton("۵۰ جم = ۸ ترون", callback_data='buy_gems_50')],
            [InlineKeyboardButton("۱۰۰ جم = ۱۴ ترون", callback_data='buy_gems_100'),
             InlineKeyboardButton("منوی اصلی 🏴‍☠️", callback_data='main_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text("💎 مقدار جم مورد نظر رو انتخاب کن:", reply_markup=reply_markup)
    else:
        tron_amount = {25: 5, 50: 8, 100: 14}[amount]
        context.user_data['awaiting_receipt'] = {'gems': amount}
        await query.message.reply_text(
            f"لطفاً {tron_amount} ترون به آدرس زیر بفرست و فیش رو بفرست:\n{TRX_ADDRESS}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("منوی اصلی 🏴‍☠️", callback_data='main_menu')]])
        )

async def handle_receipt(update, context):
    user_id = update.message.from_user.id
    receipt = context.user_data.get('awaiting_receipt')
    if not receipt:
        await update.message.reply_text("هیچ تراکنشی در انتظار نیست!")
        return
    gems = receipt['gems']
    await context.bot.forward_message(ADMIN_ID, user_id, update.message.message_id)
    await update.message.reply_text("فیش ارسال شد! منتظر تأیید ادمین باش ✅")
    context.user_data['awaiting_receipt'] = None
    context.user_data['pending_gems'] = {'user_id': user_id, 'gems': gems}

async def handle_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return
    text = update.message.text
    if text == "/confirm":
        pending = context.user_data.get('pending_gems')
        if pending:
            user_id, gems = pending['user_id'], pending['gems']
            conn = sqlite3.connect(DATABASE_PATH)
            c = conn.cursor()
            c.execute("UPDATE users SET gems = gems + ? WHERE user_id = ?", (gems, user_id))
            conn.commit()
            conn.close()
            await context.bot.send_message(user_id, f"✅ تراکنش تأیید شد! {gems} جم به حسابت اضافه شد.")
            context.user_data['pending_gems'] = None
    elif text == "/reject":
        pending = context.user_data.get('pending_gems')
        if pending:
            user_id = pending['user_id']
            await context.bot.send_message(user_id, "❌ تراکنش رد شد! لطفاً دوباره تلاش کن.")
            context.user_data['pending_gems'] = None

async def buy_cannonball(query, context):
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    c.execute("SELECT gems FROM users WHERE user_id = ?", (query.from_user.id,))
    gems = c.fetchone()[0]
    if gems < 3:
        await query.message.reply_text("جم کافی نداری! برو جم بخر 💎")
        return
    c.execute("UPDATE users SET gems = gems - 3, cannonballs = cannonballs + 1 WHERE user_id = ?", (query.from_user.id,))
    conn.commit()
    conn.close()
    await query.message.reply_text("☄️ یک توپ خریدی!",
                                  reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("منوی اصلی 🏴‍☠️", callback_data='main_menu')]]))

async def convert_gems(query, context, option=None):
    if not option:
        keyboard = [
            [InlineKeyboardButton("۱ جم = ۲ کیسه طلا", callback_data='convert_gems_1'),
             InlineKeyboardButton("۳ جم = ۶ کیسه طلا + ۴ شمش نقره", callback_data='convert_gems_3')],
            [InlineKeyboardButton("۱۰ جم = ۲۰ کیسه طلا + ۱۵ شمش نقره", callback_data='convert_gems_10'),
             InlineKeyboardButton("منوی اصلی 🏴‍☠️", callback_data='main_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text("تبدیل جم به سکه و نقره:", reply_markup=reply_markup)
    else:
        conn = sqlite3.connect(DATABASE_PATH)
        c = conn.cursor()
        c.execute("SELECT gems FROM users WHERE user_id = ?", (query.from_user.id,))
        gems = c.fetchone()[0]
        if option == '1' and gems >= 1:
            c.execute("UPDATE users SET gems = gems - 1, gold = gold + 2 WHERE user_id = ?", (query.from_user.id,))
            await query.message.reply_text("تبدیل شد: ۱ جم به ۲ کیسه طلا 🪙")
        elif option == '3' and gems >= 3:
            c.execute("UPDATE users SET gems = gems - 3, gold = gold + 6, silver = silver + 4 WHERE user_id = ?", (query.from_user.id,))
            await query.message.reply_text("تبدیل شد: ۳ جم به ۶ کیسه طلا + ۴ شمش نقره 🪙⚪")
        elif option == '10' and gems >= 10:
            c.execute("UPDATE users SET gems = gems - 10, gold = gold + 20, silver = silver + 15 WHERE user_id = ?", (query.from_user.id,))
            await query.message.reply_text("تبدیل شد: ۱۰ جم به ۲۰ کیسه طلا + ۱۵ شمش نقره 🪙⚪")
        else:
            await query.message.reply_text("جم کافی نداری!")
        conn.commit()
        conn.close()
        await query.message.reply_text("برمی‌گردی به منوی اصلی؟",
                                      reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("منوی اصلی 🏴‍☠️", callback_data='main_menu')]]))

async def show_leaderboard(query, context):
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    c.execute("SELECT ship_name, score, wins, total_games FROM users ORDER BY score DESC LIMIT 10")
    leaders = c.fetchall()
    conn.close()
    text = "🏆 برترین ناخدایان:\n"
    for i, (ship_name, score, wins, total_games) in enumerate(leaders, 1):
        win_rate = (wins / total_games * 100) if total_games > 0 else 0
        text += f"{i}. {ship_name}: {score} امتیاز (میانگین برد: {win_rate:.1f}%)\n"
    await query.message.reply_text(text,
                                  reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("منوی اصلی 🏴‍☠️", callback_data='main_menu')]]))

async def search_and_challenge(update, context, ship_name):
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    c.execute("SELECT user_id FROM users WHERE ship_name = ?", (ship_name,))
    result = c.fetchone()
    conn.close()
    if not result:
        await update.message.reply_text("کشتی‌ای با این نام پیدا نشد!",
                                       reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("منوی اصلی 🏴‍☠️", callback_data='main_menu')]]))
        return
    opponent_id = result[0]
    context.user_data['awaiting_search'] = False
    keyboard = [[InlineKeyboardButton("ارسال درخواست جنگ ⚔️", callback_data=f'challenge_{opponent_id}')]]
    await update.message.reply_text(f"کشتی **{ship_name}** پیدا شد! می‌خوای باهاش بجنگی؟",
                                   reply_markup=InlineKeyboardMarkup(keyboard))

async def show_ship_info(query, context):
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    c.execute("SELECT ship_name, gems, gold, silver, wins, total_games, energy FROM users WHERE user_id = ?", (query.from_user.id,))
    user = c.fetchone()
    conn.close()
    if not user:
        await query.message.reply_text("اول باید کشتیت رو بسازی!")
        return
    ship_name, gems, gold, silver, wins, total_games, energy = user
    win_rate = (wins / total_games * 100) if total_games > 0 else 0
    text = (f"🚢 اطلاعات کشتی:\n"
            f"نام کشتی: {ship_name}\n"
            f"جم: {gems} 💎\n"
            f"کیسه طلا: {gold} 🪙\n"
            f"شمش نقره: {silver} ⚪\n"
            f"میانگین پیروزی: {win_rate:.1f}%\n"
            f"انرژی: {energy}% ⚡")
    await query.message.reply_text(text,
                                  reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("منوی اصلی 🏴‍☠️", callback_data='main_menu')]]))

async def show_energy_menu(query, context):
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    c.execute("SELECT energy, last_purchase_time FROM users WHERE user_id = ?", (query.from_user.id,))
    energy, last_purchase_time = c.fetchone()
    conn.close()
    can_buy = True
    if last_purchase_time:
        last_time = datetime.fromisoformat(last_purchase_time)
        if datetime.now() < last_time + timedelta(hours=24):
            can_buy = False
    text = f"⚡ انرژی جنگجویان: {energy}%\n"
    if energy < 50:
        text += "جنگجویانت خستن! باید براشون خوراکی بخری!"
    if can_buy:
        keyboard = [
            [InlineKeyboardButton("بیسکویت دریایی (۴ شمش نقره)", callback_data='buy_food_biscuit'),
             InlineKeyboardButton("ماهی خشک (۱ طلا + ۱ نقره)", callback_data='buy_food_fish')],
            [InlineKeyboardButton("میوه خشک (۱ طلا)", callback_data='buy_food_fruit'),
             InlineKeyboardButton("پنیر کهنه (۱ طلا + ۳ نقره)", callback_data='buy_food_cheese')],
            [InlineKeyboardButton("آب (۳ نقره)", callback_data='buy_food_water'),
             InlineKeyboardButton("منوی اصلی 🏴‍☠️", callback_data='main_menu')]
        ]
    else:
        keyboard = [[InlineKeyboardButton("منوی اصلی 🏴‍☠️", callback_data='main_menu')]]
        text += "\nفقط هر ۲۴ ساعت می‌تونی خوراکی بخری!"
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def buy_food(query, context, food):
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    c.execute("SELECT gold, silver, last_purchase_time FROM users WHERE user_id = ?", (query.from_user.id,))
    gold, silver, last_purchase_time = c.fetchone()
    can_buy = True
    if last_purchase_time:
        last_time = datetime.fromisoformat(last_purchase_time)
        if datetime.now() < last_time + timedelta(hours=24):
            can_buy = False
    if not can_buy:
        await query.message.reply_text("فقط هر ۲۴ ساعت می‌تونی خوراکی بخری!")
        return
    food_options = {
        'biscuit': {'energy': 25, 'silver': 4, 'gold': 0},
        'fish': {'energy': 35, 'silver': 1, 'gold': 1},
        'fruit': {'energy': 30, 'silver': 0, 'gold': 1},
        'cheese': {'energy': 50, 'silver': 3, 'gold': 1},
        'water': {'energy': 20, 'silver': 3, 'gold': 0}
    }
    cost = food_options[food]
    if gold < cost['gold'] or silver < cost['silver']:
        await query.message.reply_text("منابع کافی نداری!")
        return
    c.execute(
        """UPDATE users SET gold = gold - ?, silver = silver - ?, energy = energy + ?, 
        last_purchase_time = ? WHERE user_id = ?""",
        (cost['gold'], cost['silver'], cost['energy'], datetime.now().isoformat(), query.from_user.id)
    )
    conn.commit()
    conn.close()
    await query.message.reply_text(f"خرید موفق! +{cost['energy']}% انرژی ⚡",
                                  reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("منوی اصلی 🏴‍☠️", callback_data='main_menu')]]))

async def main():
    global application
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CommandHandler("confirm", handle_admin_command))
    application.add_handler(CommandHandler("reject", handle_admin_command))
    await application.initialize()
    await application.start()
    await application.updater.start_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get('PORT', 10000)),
        url_path=TOKEN,
        webhook_url=f"https://sea-2ri6.onrender.com/{TOKEN}"
    )

if __name__ == '__main__':
    import threading
    port = int(os.environ.get('PORT', 10000))
    threading.Thread(target=app.run, kwargs={'host': '0.0.0.0', 'port': port}).start()
    asyncio.run(main())
