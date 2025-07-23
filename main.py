import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from dotenv import load_dotenv
import os
import random
import json
from datetime import datetime, timedelta

# تنظیمات لاگ
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# لود توکن از محیط
load_dotenv()
TOKEN = os.getenv("TOKEN", "8030062261:AAFnC9AJ_2zvcaqC0LXe5Y3--d2FgxOx-fI")
ADMIN_ID = int(os.getenv("ADMIN_ID", "5542927340"))
TRX_ADDRESS = os.getenv("TRX_ADDRESS", "TJ4xrwKJzKjk6FgKfuuqwah3Az5Ur22kJb")

# وضعیت‌های کاربر
(
    STATE_MAIN_MENU,
    STATE_SHOP,
    STATE_INVENTORY,
    STATE_SAILING,
    STATE_BATTLE,
    STATE_UPGRADE,
) = range(6)

# دیتابیس ساده کاربران
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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_id = user.id
    
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
        }
    
    keyboard = [
        [InlineKeyboardButton("دریانوردی ⛵", callback_data="sail")],
        [InlineKeyboardButton("فروشگاه 🏪", callback_data="shop")],
        [InlineKeyboardButton("موجودی 💰", callback_data="inventory")],
        [InlineKeyboardButton("ارتقاء کشتی ⚓", callback_data="upgrade")],
        [InlineKeyboardButton("حمایت از ما 💝", callback_data="donate")],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"به دنیای دزدان دریایی خوش آمدید، کاپیتان {user.full_name}! 🏴‍☠️\n\n"
        "شما می‌توانید با دریانوردی به دنبال گنج باشید، کشتی خود را ارتقا دهید "
        "و با دیگر دزدان دریایی مبارزه کنید.\n\n"
        "گزینه مورد نظر را انتخاب کنید:",
        reply_markup=reply_markup,
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if user_id not in users_db:
        await start(update, context)
        return
    
    user_data = users_db[user_id]
    
    if data == "sail":
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
        
        await query.edit_message_text(
            f"کشتی شما به دریا زده است! ⛵\n\n"
            f"سفر دریایی حدود {duration} ثانیه طول خواهد کشید...",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("برگشت ↩️", callback_data="main_menu")]]),
        )
        
    elif data == "shop":
        user_data["state"] = STATE_SHOP
        await show_shop(query, user_data)
        
    elif data == "inventory":
        user_data["state"] = STATE_INVENTORY
        await show_inventory(query, user_data)
        
    elif data == "upgrade":
        user_data["state"] = STATE_UPGRADE
        await show_upgrade(query, user_data)
        
    elif data == "donate":
        await query.edit_message_text(
            f"از حمایت شما سپاسگزاریم! 💝\n\n"
            f"برای حمایت از توسعه بازی می‌توانید به آدرس زیر ارز دیجیتال ارسال کنید:\n\n"
            f"TRX: {TRX_ADDRESS}\n\n"
            "هر مقدار کمک شما باعث انگیزه بیشتر ما می‌شود!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("برگشت ↩️", callback_data="main_menu")]]),
        )
        
    elif data == "main_menu":
        user_data["state"] = STATE_MAIN_MENU
        await query.edit_message_text(
            f"به منوی اصلی بازگشتید، کاپیتان {user_data['name']}! 🏴‍☠️",
            reply_markup=main_menu_keyboard(),
        )
        
    elif data.startswith("buy_"):
        item_name = data[4:]
        await buy_item(query, user_data, item_name)
        
    elif data.startswith("use_"):
        item_name = data[4:]
        await use_item(query, user_data, item_name)
        
    elif data.startswith("upgrade_"):
        ship_name = data[8:]
        await upgrade_ship(query, user_data, ship_name)

async def show_shop(query, user_data):
    keyboard = []
    
    for item_name, item_data in SHOP_ITEMS.items():
        keyboard.append([
            InlineKeyboardButton(
                f"{item_name} - {item_data['price']} سکه ({item_data['effect']})",
                callback_data=f"buy_{item_name}",
            )
        ])
    
    keyboard.append([InlineKeyboardButton("برگشت ↩️", callback_data="main_menu")])
    
    await query.edit_message_text(
        "🏪 فروشگاه دزدان دریایی 🏪\n\n"
        "در اینجا می‌توانید وسایل مختلفی برای کمک در سفرهای دریایی خود خریداری کنید:\n\n"
        f"سکه‌های شما: {user_data['gold']}",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

async def buy_item(query, user_data, item_name):
    if item_name not in SHOP_ITEMS:
        await query.edit_message_text(
            "این آیتم در فروشگاه موجود نیست!",
            reply_markup=main_menu_keyboard(),
        )
        return
    
    item = SHOP_ITEMS[item_name]
    
    if user_data["gold"] < item["price"]:
        await query.edit_message_text(
            "سکه کافی برای خرید این آیتم ندارید!",
            reply_markup=main_menu_keyboard(),
        )
        return
    
    user_data["gold"] -= item["price"]
    user_data["inventory"].append(item_name)
    
    await query.edit_message_text(
        f"شما با موفقیت {item_name} را خریداری کردید! 🎉\n\n"
        f"سکه‌های باقی‌مانده: {user_data['gold']}",
        reply_markup=main_menu_keyboard(),
    )
    user_data["state"] = STATE_MAIN_MENU

async def show_inventory(query, user_data):
    if not user_data["inventory"]:
        await query.edit_message_text(
            "موجودی شما خالی است! به فروشگاه سر بزنید.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("برگشت ↩️", callback_data="main_menu")]]),
        )
        return
    
    keyboard = []
    
    for item in user_data["inventory"]:
        keyboard.append([InlineKeyboardButton(f"استفاده از {item}", callback_data=f"use_{item}")])
    
    keyboard.append([InlineKeyboardButton("برگشت ↩️", callback_data="main_menu")])
    
    await query.edit_message_text(
        "🎒 موجودی شما 🎒\n\n"
        f"سکه‌های شما: {user_data['gold']}\n"
        f"انرژی: {user_data['energy']}/100\n"
        f"کشتی فعلی: {user_data['ship']}\n\n"
        "آیتم‌های شما:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

async def use_item(query, user_data, item_name):
    if item_name not in user_data["inventory"]:
        await query.edit_message_text(
            "این آیتم در موجودی شما وجود ندارد!",
            reply_markup=main_menu_keyboard(),
        )
        return
    
    user_data["inventory"].remove(item_name)
    
    if item_name == "جعبه کمک‌های اولیه":
        user_data["energy"] = min(100, user_data["energy"] + 50)
        effect = "50 انرژی بازیابی شد!"
    elif item_name == "توپ جنگی":
        effect = "در نبرد بعدی حمله شما افزایش می‌یابد!"
    elif item_name == "زره مستحکم":
        effect = "در نبرد بعدی دفاع شما افزایش می‌یابد!"
    else:
        effect = "آیتم استفاده شد!"
    
    await query.edit_message_text(
        f"شما از {item_name} استفاده کردید! {effect}",
        reply_markup=main_menu_keyboard(),
    )
    user_data["state"] = STATE_MAIN_MENU

async def show_upgrade(query, user_data):
    current_ship = user_data["ship"]
    ship_names = list(SHIP_TYPES.keys())
    current_index = ship_names.index(current_ship)
    
    keyboard = []
    
    for i, (ship_name, ship_data) in enumerate(SHIP_TYPES.items()):
        if i <= current_index:
            status = "✅ (دارید)"
        elif i == current_index + 1:
            status = f"🔼 ({ship_data['price']} سکه)"
        else:
            status = "🔒 (قفل شده)"
        
        keyboard.append([
            InlineKeyboardButton(
                f"{ship_name}: سرعت {ship_data['speed']} - حمله {ship_data['attack']} - دفاع {ship_data['defense']} - ظرفیت {ship_data['capacity']} {status}",
                callback_data=f"upgrade_{ship_name}" if i == current_index + 1 else "none",
            )
        ])
    
    keyboard.append([InlineKeyboardButton("برگشت ↩️", callback_data="main_menu")])
    
    await query.edit_message_text(
        "⚓ ارتقاء کشتی ⚓\n\n"
        "کشتی بهتر به معنای سفرهای دریایی سودآورتر است!\n\n"
        f"سکه‌های شما: {user_data['gold']}\n"
        f"کشتی فعلی: {current_ship}",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

async def upgrade_ship(query, user_data, ship_name):
    if ship_name not in SHIP_TYPES:
        await query.edit_message_text(
            "این کشتی وجود ندارد!",
            reply_markup=main_menu_keyboard(),
        )
        return
    
    ship_data = SHIP_TYPES[ship_name]
    
    if user_data["gold"] < ship_data["price"]:
        await query.edit_message_text(
            "سکه کافی برای ارتقاء کشتی ندارید!",
            reply_markup=main_menu_keyboard(),
        )
        return
    
    user_data["gold"] -= ship_data["price"]
    user_data["ship"] = ship_name
    
    await query.edit_message_text(
        f"تبریک! کشتی شما به {ship_name} ارتقا یافت! 🎉⚓\n\n"
        f"مشخصات جدید:\n"
        f"سرعت: {ship_data['speed']}\n"
        f"حمله: {ship_data['attack']}\n"
        f"دفاع: {ship_data['defense']}\n"
        f"ظرفیت: {ship_data['capacity']}\n\n"
        f"سکه‌های باقی‌مانده: {user_data['gold']}",
        reply_markup=main_menu_keyboard(),
    )
    user_data["state"] = STATE_MAIN_MENU

async def check_sailing(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now()
    
    for user_id, user_data in users_db.items():
        if user_data["state"] == STATE_SAILING and user_data["sailing_end"] <= now:
            await complete_sailing(context, user_id)

async def complete_sailing(context: ContextTypes.DEFAULT_TYPE, user_id):
    user_data = users_db[user_id]
    ship_stats = SHIP_TYPES[user_data["ship"]]
    
    # انتخاب رویداد دریایی
    event = random.choices(
        SEA_EVENTS,
        weights=[e["chance"] for e in SEA_EVENTS],
    )[0]
    
    if event["reward"] == "battle":
        # نبرد با دزدان دریایی
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
        # رویداد عادی
        reward = random.randint(event["reward"][0], event["reward"][1])
        
        if "قلاب طلایی" in user_data["inventory"] and "گنج" in event["name"]:
            reward = int(reward * 1.5)
        
        if "نقشه گنج" in user_data["inventory"] and "گنج" in event["name"]:
            reward += 50
        
        user_data["gold"] += reward
        message = f"{event['message']}\n\nمقدار سکه به دست آمده: {reward} 🪙"
    
    user_data["state"] = STATE_MAIN_MENU
    
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

def main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("دریانوردی ⛵", callback_data="sail")],
        [InlineKeyboardButton("فروشگاه 🏪", callback_data="shop")],
        [InlineKeyboardButton("موجودی 💰", callback_data="inventory")],
        [InlineKeyboardButton("ارتقاء کشتی ⚓", callback_data="upgrade")],
        [InlineKeyboardButton("حمایت از ما 💝", callback_data="donate")],
    ]
    return InlineKeyboardMarkup(keyboard)

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        await update.message.reply_text("شما دسترسی به این فرمان را ندارید!")
        return
    
    if not context.args:
        await update.message.reply_text(
            "فرمان‌های ادمین:\n"
            "/admin stats - آمار کاربران\n"
            "/admin notify <پیام> - ارسال پیام به همه کاربران\n"
            "/admin gold <user_id> <amount> - اضافه کردن سکه به کاربر"
        )
        return
    
    command = context.args[0]
    
    if command == "stats":
        await update.message.reply_text(
            f"آمار کاربران:\n"
            f"تعداد کاربران: {len(users_db)}\n"
            f"سکه کل: {sum(user['gold'] for user in users_db.values())}"
        )
    elif command == "notify":
        message = " ".join(context.args[1:])
        success = 0
        failed = 0
        
        for user_id in users_db:
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"📢 اطلاعیه ادمین:\n\n{message}",
                )
                success += 1
            except Exception as e:
                logger.error(f"Error notifying {user_id}: {e}")
                failed += 1
        
        await update.message.reply_text(
            f"پیام به {success} کاربر ارسال شد. {failed} ارسال ناموفق بود."
        )
    elif command == "gold":
        if len(context.args) < 3:
            await update.message.reply_text("استفاده: /admin gold <user_id> <amount>")
            return
        
        try:
            target_id = int(context.args[1])
            amount = int(context.args[2])
            
            if target_id not in users_db:
                await update.message.reply_text("کاربر یافت نشد!")
                return
            
            users_db[target_id]["gold"] += amount
            await update.message.reply_text(
                f"{amount} سکه به کاربر {target_id} اضافه شد. موجودی جدید: {users_db[target_id]['gold']}"
            )
        except ValueError:
            await update.message.reply_text("شناسه کاربر و مقدار باید عددی باشند!")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(msg="Exception while handling an update:", exc_info=context.error)

def main() -> None:
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CallbackQueryHandler(button))
    
    application.add_error_handler(error_handler)
    
    # چک کردن سفرهای دریایی هر 5 ثانیه
    job_queue = application.job_queue
    job_queue.run_repeating(check_sailing, interval=5.0, first=5.0)
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
