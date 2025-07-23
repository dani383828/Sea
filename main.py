import logging
import os
import random
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ApplicationBuilder
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# تنظیمات پایه
load_dotenv()
TOKEN = os.getenv("TOKEN", "8030062261:AAFnC9AJ_2zvcaqC0LXe5Y3--d2FgxOx-fI")
ADMIN_ID = int(os.getenv("ADMIN_ID", "5542927340"))
TRX_ADDRESS = os.getenv("TRX_ADDRESS", "TJ4xrwKJzKjk6FgKfuuqwah3Az5Ur22kJb")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://sea-2ri6.onrender.com")
PORT = int(os.getenv("PORT", 8443))

# تنظیمات لاگ
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# حالت‌های بازی
(
    STATE_MAIN_MENU,
    STATE_SHOP,
    STATE_INVENTORY,
    STATE_SAILING,
    STATE_BATTLE,
    STATE_UPGRADE,
) = range(6)

# دیتابیس موقت
users_db = {}

# انواع کشتی‌ها
SHIP_TYPES = {
    "قایق چوبی": {"price": 0, "speed": 1, "attack": 1, "defense": 1, "capacity": 10},
    "کشتی ماهیگیری": {"price": 100, "speed": 2, "attack": 2, "defense": 2, "capacity": 20},
    "کشتی جنگی": {"price": 500, "speed": 3, "attack": 5, "defense": 4, "capacity": 30},
    "ناو جنگی": {"price": 2000, "speed": 4, "attack": 8, "defense": 7, "capacity": 50},
    "کشتی افسانه‌ای": {"price": 10000, "speed": 5, "attack": 12, "defense": 10, "capacity": 100},
}

# آیتم‌های فروشگاه
SHOP_ITEMS = {
    "قلاب طلایی": {"price": 200, "type": "tool", "effect": "شانس بیشتر برای یافتن گنج"},
    "نقشه گنج": {"price": 500, "type": "map", "effect": "هدایت به سمت گنج‌های بزرگتر"},
    "توپ جنگی": {"price": 300, "type": "weapon", "effect": "+2 حمله در نبردها"},
    "زره مستحکم": {"price": 300, "type": "armor", "effect": "+2 دفاع در نبردها"},
    "جعبه کمک‌های اولیه": {"price": 150, "type": "heal", "effect": "بازیابی 50 انرژی"},
}

# رویدادهای دریایی
SEA_EVENTS = [
    {"name": "گنج معمولی", "reward": (50, 100), "chance": 0.4, "message": "یک صندوق گنج پیدا کردید!"},
    {"name": "گنج نادر", "reward": (200, 400), "chance": 0.2, "message": "یک گنجینه نادر کشف کردید!"},
    {"name": "کشتی تجاری", "reward": (100, 300), "chance": 0.25, "message": "یک کشتی تجاری غارت کردید!"},
    {"name": "طوفان", "reward": (-50, -20), "chance": 0.1, "message": "طوفان به کشتی شما آسیب زد!"},
    {"name": "دزدان دریایی", "reward": "battle", "chance": 0.05, "message": "دزدان دریایی به شما حمله کردند!"},
]

# --- توابع کمکی ---
def main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("دریانوردی ⛵", callback_data="sail")],
        [InlineKeyboardButton("فروشگاه 🏪", callback_data="shop")],
        [InlineKeyboardButton("موجودی 💰", callback_data="inventory")],
        [InlineKeyboardButton("ارتقاء کشتی ⚓", callback_data="upgrade")],
        [InlineKeyboardButton("حمایت از ما 💝", callback_data="donate")],
    ]
    return InlineKeyboardMarkup(keyboard)

def save_user_data():
    """ذخیره داده کاربران در فایل"""
    try:
        with open('user_data.json', 'w') as f:
            json.dump(users_db, f, indent=4)
    except Exception as e:
        logger.error(f"Error saving user data: {e}")

def load_user_data():
    """بارگذاری داده کاربران از فایل"""
    try:
        with open('user_data.json', 'r') as f:
            data = json.load(f)
            # تبدیل رشته‌های تاریخ به شیء datetime
            for user_id, user_data in data.items():
                if 'sailing_end' in user_data and user_data['sailing_end']:
                    user_data['sailing_end'] = datetime.fromisoformat(user_data['sailing_end'])
            return data
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    except Exception as e:
        logger.error(f"Error loading user data: {e}")
        return {}

# --- دستورات اصلی ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_id = str(user.id)
    
    if user_id not in users_db:
        users_db[user_id] = {
            "name": user.full_name,
            "gold": 100,
            "ship": "قایق چوبی",
            "inventory": [],
            "energy": 100,
            "state": STATE_MAIN_MENU,
            "sailing_end": None,
            "battle": None,
            "created_at": datetime.now().isoformat()
        }
        save_user_data()
    
    await update.message.reply_text(
        f"به دنیای دزدان دریایی خوش آمدید، کاپیتان {user.full_name}! 🏴‍☠️\n\n"
        "شما می‌توانید با دریانوردی به دنبال گنج باشید، کشتی خود را ارتقا دهید "
        "و با دیگر دزدان دریایی مبارزه کنید.\n\n"
        "گزینه مورد نظر را انتخاب کنید:",
        reply_markup=main_menu_keyboard(),
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    
    if user_id not in users_db:
        await start(update, context)
        return
    
    data = query.data
    user_data = users_db[user_id]
    
    if data == "sail":
        await handle_sailing(query, user_data)
    elif data == "shop":
        await show_shop(query, user_data)
    elif data == "inventory":
        await show_inventory(query, user_data)
    elif data == "upgrade":
        await show_upgrade(query, user_data)
    elif data == "donate":
        await show_donate(query)
    elif data == "main_menu":
        await return_to_main_menu(query, user_data)
    elif data.startswith("buy_"):
        await buy_item(query, user_data, data[4:])
    elif data.startswith("use_"):
        await use_item(query, user_data, data[4:])
    elif data.startswith("upgrade_"):
        await upgrade_ship(query, user_data, data[8:])

# --- توابع پردازش ---
async def handle_sailing(query, user_data):
    if user_data["energy"] < 10:
        await query.edit_message_text(
            "انرژی شما برای دریانوردی کافی نیست! استراحت کنید یا از جعبه کمک‌های اولیه استفاده کنید.",
            reply_markup=main_menu_keyboard(),
        )
        return
    
    user_data["energy"] -= 10
    duration = random.randint(5, 15)
    user_data["sailing_end"] = datetime.now() + timedelta(seconds=duration)
    user_data["state"] = STATE_SAILING
    save_user_data()
    
    await query.edit_message_text(
        f"کشتی شما به دریا زده است! ⛵\n\n"
        f"سفر دریایی حدود {duration} ثانیه طول خواهد کشید...",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("برگشت ↩️", callback_data="main_menu")]]),
    )

async def check_sailing(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now()
    completed_users = []
    
    for user_id, user_data in users_db.items():
        if user_data["state"] == STATE_SAILING and user_data["sailing_end"] and user_data["sailing_end"] <= now:
            completed_users.append(user_id)
    
    for user_id in completed_users:
        await complete_sailing(context, user_id)

async def complete_sailing(context: ContextTypes.DEFAULT_TYPE, user_id: str):
    user_data = users_db[user_id]
    ship_stats = SHIP_TYPES[user_data["ship"]]
    
    # انتخاب رویداد دریایی
    event = random.choices(
        SEA_EVENTS,
        weights=[e["chance"] for e in SEA_EVENTS],
    )[0]
    
    if event["reward"] == "battle":
        enemy_power = random.randint(5, 15)
        user_power = ship_stats["attack"] + random.randint(1, 5)
        
        if "توپ جنگی" in user_data["inventory"]:
            user_power += 2
            user_data["inventory"].remove("توپ جنگی")
        
        if user_power > enemy_power:
            reward = random.randint(150, 300)
            user_data["gold"] += reward
            result = f"شما دزدان دریایی را شکست دادید و {reward} سکه به غنیمت گرفتید! 💰"
        else:
            penalty = random.randint(50, 100)
            user_data["gold"] = max(0, user_data["gold"] - penalty)
            result = f"دزدان دریایی شما را شکست دادند و {penalty} سکه از شما دزدیدند! 💢"
        
        message = f"{event['message']}\n\n{result}"
    else:
        reward = random.randint(event["reward"][0], event["reward"][1])
        
        if "قلاب طلایی" in user_data["inventory"] and "گنج" in event["name"]:
            reward = int(reward * 1.5)
        
        if "نقشه گنج" in user_data["inventory"] and "گنج" in event["name"]:
            reward += 50
        
        user_data["gold"] += reward
        message = f"{event['message']}\n\nمقدار سکه به دست آمده: {reward} 🪙"
    
    user_data["state"] = STATE_MAIN_MENU
    user_data["sailing_end"] = None
    save_user_data()
    
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=f"سفر دریایی شما به پایان رسید! ⛵\n\n{message}\n\n"
                 f"سکه‌های شما: {user_data['gold']}\n"
                 f"انرژی: {user_data['energy']}/100",
            reply_markup=main_menu_keyboard(),
        )
    except Exception as e:
        logger.error(f"Error sending message to {user_id}: {e}")

# --- توابع دیگر (مانند show_shop, buy_item, upgrade_ship و ...) ---
# [کدهای قبلی را اینجا قرار دهید، با تغییرات زیر:
# 1. تبدیل تمام user_idها به رشته (str)
# 2. اضافه کردن save_user_data() پس از هر تغییر در داده کاربر
# 3. اضافه کردن مدیریت خطاها]

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Exception while handling an update:", exc_info=context.error)

def setup_job_queue(application):
    """تنظیم JobQueue برای بررسی سفرهای دریایی"""
    job_queue = application.job_queue
    if job_queue:
        job_queue.run_repeating(check_sailing, interval=5.0, first=5.0)
    else:
        logger.warning("JobQueue is not available. Sailing completion checks will not work.")

async def post_init(application: Application):
    """عملیات پس از راه‌اندازی"""
    await application.bot.set_webhook(WEBHOOK_URL)
    logger.info(f"Webhook set to {WEBHOOK_URL}")

def main() -> None:
    # بارگذاری داده کاربران
    global users_db
    users_db = load_user_data()
    
    # ایجاد برنامه تلگرام
    application = ApplicationBuilder() \
        .token(TOKEN) \
        .post_init(post_init) \
        .build()
    
    # ثبت هندلرها
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_error_handler(error_handler)
    
    # تنظیم JobQueue
    setup_job_queue(application)
    
    # راه‌اندازی وب‌هوک
    if os.getenv('RENDER', 'false').lower() == 'true':
        application.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=TOKEN,
            webhook_url=f"{WEBHOOK_URL}/{TOKEN}"
        )
    else:
        application.run_polling()

if __name__ == "__main__":
    main()
