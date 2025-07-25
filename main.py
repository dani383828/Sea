import os
import logging
from fastapi import FastAPI, Request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, ContextTypes, MessageHandler, CallbackQueryHandler, filters
)
from datetime import datetime, timedelta
import random

TOKEN = "8030062261:AAFnC9AJ_2zvcaqC0LXe5Y3--d2FgxOx-fI"
WEBHOOK_PATH = f"/webhook/{TOKEN}"
WEBHOOK_URL = f"https://sea-2ri6.onrender.com{WEBHOOK_PATH}"
ADMIN_ID = 123456789  # آیدی عددی ادمین (این رو تغییر بدید)

# ⚙️ لاگ‌گیری
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# 📦 FastAPI app
app = FastAPI()

# 🎯 ساخت ربات تلگرام
application = Application.builder().token(TOKEN).build()

# 📌 هندلر برای /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("username"):
        await update.message.reply_text("لطفاً اسمت رو به انگلیسی وارد کن (نباید تکراری باشه):")
        context.user_data["state"] = "waiting_for_username"
    else:
        # مقداردهی اولیه برای کاربر
        if not context.user_data.get("initialized"):
            context.user_data["gems"] = 5
            context.user_data["gold"] = 10
            context.user_data["silver"] = 15
            context.user_data["wins"] = 0
            context.user_data["games"] = 0
            context.user_data["energy"] = 100
            context.user_data["last_purchase"] = {}
            context.user_data["score"] = 0
            context.user_data["cannons"] = 0
            context.user_data["free_cannons"] = 3  # ۳ توپ رایگان
            context.user_data["initialized"] = True

        keyboard = [
            ["⚔️ شروع بازی", "🛒 فروشگاه"],
            ["🏴‍☠️ برترین ناخدایان", "🔍 جست و جوی کاربران"],
            ["📕 اطلاعات کشتی", "⚡️ انرژی جنگجویان"],
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
        await update.message.reply_text(f"🏴‍☠️ خوش اومدی به دنیای دزدان دریایی، {context.user_data['username']}!", reply_markup=reply_markup)

# 📌 هندلر برای دریافت نام کاربر
async def handle_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("state") != "waiting_for_username":
        return
    
    username = update.message.text.strip()
    if not username.isascii():
        await update.message.reply_text("لطفاً اسم رو به انگلیسی وارد کن!")
        return
    
    if not context.bot_data.get("usernames"):
        context.bot_data["usernames"] = {}
    
    if username.lower() in [u.lower() for u in context.bot_data["usernames"].values()]:
        await update.message.reply_text("این اسم قبلاً انتخاب شده! یه اسم دیگه امتحان کن.")
        return
    
    context.user_data["username"] = username
    context.user_data["state"] = None
    context.bot_data["usernames"][update.message.from_user.id] = username
    await start(update, context)  # نمایش منوی اصلی

# 📌 هندلر برای جست‌وجوی کاربران
async def search_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("لطفاً آیدی عددی یا نام کاربری دوستت رو وارد کن:")
    context.user_data["state"] = "waiting_for_search"

# 📌 هندلر برای پردازش جست‌وجو
async def handle_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("state") != "waiting_for_search":
        return
    
    search_query = update.message.text.strip()
    target_id = None
    usernames = context.bot_data.get("usernames", {})
    
    # جست‌وجو بر اساس آیدی عددی یا نام کاربری
    try:
        target_id = int(search_query)
        if target_id not in usernames:
            target_id = None
    except ValueError:
        for user_id, username in usernames.items():
            if username.lower() == search_query.lower():
                target_id = user_id
                break
    
    if not target_id:
        await update.message.reply_text("کاربر پیدا نشد! دوباره امتحان کن.")
        context.user_data["state"] = None
        return
    
    if target_id == update.message.from_user.id:
        await update.message.reply_text("نمی‌تونی خودت رو دعوت کنی!")
        context.user_data["state"] = None
        return
    
    keyboard = [
        [InlineKeyboardButton("قبول ✅", callback_data=f"accept_game_{update.message.from_user.id}")],
        [InlineKeyboardButton("رد ❌", callback_data="reject_game")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(
        target_id,
        f"کاربر {context.user_data['username']} ({update.message.from_user.id}) بهت درخواست بازی دوستانه داده!",
        reply_markup=reply_markup
    )
    await update.message.reply_text("درخواست بازی ارسال شد! منتظر جواب باش.")
    context.user_data["state"] = None

# 📌 هندلر برای شروع بازی
async def start_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("دریانوردی ⛵️", callback_data="sailing")],
        [InlineKeyboardButton("توپ ☄️", callback_data="cannon")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("انتخاب کن:", reply_markup=reply_markup)

# 📌 هندلر برای پردازش بازی و خرید توپ
async def handle_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "sailing":
        # شبیه‌سازی مچ‌میکینگ (۶۰ ثانیه برای پیدا کردن بازیکن آنلاین)
        opponent_id = None  # اینجا باید سیستم مچ‌میکینگ واقعی باشه
        await query.message.reply_text("در حال جست‌وجوی حریف... (تا ۶۰ ثانیه)")
        
        # اگر حریف آنلاین پیدا نشد، بازیکن فیک
        if not opponent_id:
            opponent_name = "دزد دریایی ناشناس"
        else:
            opponent_name = context.bot_data["usernames"].get(opponent_id, "ناشناس")
        
        # محاسبه شانس پیروزی
        cannons = context.user_data.get("cannons", 0)
        energy = context.user_data.get("energy", 100)
        win_chance = min(100, (cannons * 20) + (energy / 2))  # هر توپ ۲۰٪، هر ۱۰٪ انرژی ۵٪
        opponent_chance = random.uniform(20, 80)  # شانس حریف فیک
        win = random.random() * 100 < win_chance
        
        # گزارش بازی
        report = "کاپیتان، کشتیمون سوراخ شد!" if not win else "کاپیتان، دشمن رو غرق کردیم!"
        context.user_data["games"] = context.user_data.get("games", 0) + 1
        context.user_data["energy"] = max(0, context.user_data.get("energy", 100) - 5)  # کاهش انرژی با هر بازی
        
        if win:
            context.user_data["wins"] = context.user_data.get("wins", 0) + 1
            context.user_data["score"] = context.user_data.get("score", 0) + 30
            context.user_data["gold"] = context.user_data.get("gold", 10) + 3
            context.user_data["silver"] = context.user_data.get("silver", 15) + 5
            context.user_data["energy"] = min(100, context.user_data.get("energy", 100) + 10)
            if random.random() < 0.25:  # ۲۵٪ شانس جم
                context.user_data["gems"] = context.user_data.get("gems", 5) + 1
                report += "\nیه جم پیدا کردیم! 💎"
            report += "\nجایزه: ۳۰ امتیاز، ۳ کیسه طلا، ۵ شمش نقره، +۱۰٪ انرژی"
        else:
            context.user_data["score"] = context.user_data.get("score", 0) - 10
            if context.user_data.get("gold", 10) >= 3:
                context.user_data["gold"] -= 3
            if context.user_data.get("silver", 15) >= 5:
                context.user_data["silver"] -= 5
            if random.random() < 0.25 and context.user_data.get("gems", 5) >= 1:
                context.user_data["gems"] -= 1
                report += "\nیه جم از دست دادیم! 😢"
            context.user_data["energy"] = max(0, context.user_data.get("energy", 100) - 30)
            report += "\nجریمه: -۱۰ امتیاز، -۳ کیسه طلا، -۵ شمش نقره، -۳۰٪ انرژی"
        
        await query.message.reply_text(f"بازی با {opponent_name}:\n{report}")
    
    elif query.data == "cannon":
        free_cannons = context.user_data.get("free_cannons", 3)
        if free_cannons > 0:
            context.user_data["cannons"] = context.user_data.get("cannons", 0) + 1
            context.user_data["free_cannons"] = free_cannons - 1
            await query.message.reply_text(f"یه توپ رایگان گرفتی! ({free_cannons - 1} توپ رایگان باقی مونده)")
        else:
            keyboard = [
                [InlineKeyboardButton("خرید توپ (۱ جم)", callback_data="buy_cannon_gem")],
                [InlineKeyboardButton("خرید توپ (۵ کیسه طلا)", callback_data="buy_cannon_gold")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text("توپ رایگان تموم شده! می‌تونی با جم یا طلا بخری:", reply_markup=reply_markup)

# 📌 هندلر برای خرید توپ
async def handle_cannon_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "buy_cannon_gem":
        if context.user_data.get("gems", 5) >= 1:
            context.user_data["gems"] -= 1
            context.user_data["cannons"] = context.user_data.get("cannons", 0) + 1
            await query.message.reply_text("یه توپ با ۱ جم خریدی!")
        else:
            await query.message.reply_text("جم کافی نداری!")
    elif query.data == "buy_cannon_gold":
        if context.user_data.get("gold", 10) >= 5:
            context.user_data["gold"] -= 5
            context.user_data["cannons"] = context.user_data.get("cannons", 0) + 1
            await query.message.reply_text("یه توپ با ۵ کیسه طلا خریدی!")
        else:
            await query.message.reply_text("کیسه طلا کافی نداری!")
    await query.message.delete()

# 📌 هندلر برای پردازش درخواست بازی دوستانه
async def handle_friend_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "reject_game":
        await query.message.reply_text("درخواست بازی رد شد.")
        await query.message.edit_reply_markup(reply_markup=None)
        return
    
    if query.data.startswith("accept_game_"):
        requester_id = int(query.data.split("_")[2])
        requester_name = context.bot_data["usernames"].get(requester_id, "ناشناس")
        player_id = query.from_user.id
        
        # محاسبه شانس پیروزی برای هر دو بازیکن
        requester_data = context.user_data  # باید از سیستم ذخیره‌سازی واقعی داده‌های کاربر requester_id گرفته بشه
        requester_cannons = context.user_data.get("cannons", 0)
        requester_energy = context.user_data.get("energy", 100)
        player_cannons = context.user_data.get("cannons", 0)
        player_energy = context.user_data.get("energy", 100)
        
        requester_chance = min(100, (requester_cannons * 20) + (requester_energy / 2))
        player_chance = min(100, (player_cannons * 20) + (player_energy / 2))
        
        win = random.random() * (requester_chance + player_chance) < requester_chance
        
        # به‌روزرسانی برای بازیکن درخواست‌دهنده
        requester_data["games"] = requester_data.get("games", 0) + 1
        requester_data["energy"] = max(0, requester_data.get("energy", 100) - 5)
        report = "کاپیتان، کشتیمون سوراخ شد!" if not win else "کاپیتان، دشمن رو غرق کردیم!"
        
        if win:
            requester_data["wins"] = requester_data.get("wins", 0) + 1
            requester_data["score"] = requester_data.get("score", 0) + 30
            requester_data["gold"] = requester_data.get("gold", 10) + 3
            requester_data["silver"] = requester_data.get("silver", 15) + 5
            requester_data["energy"] = min(100, requester_data.get("energy", 100) + 10)
            if random.random() < 0.25:
                requester_data["gems"] = requester_data.get("gems", 5) + 1
                report += "\nیه جم پیدا کردیم! 💎"
            report += "\nجایزه: ۳۰ امتیاز، ۳ کیسه طلا، ۵ شمش نقره، +۱۰٪ انرژی"
        else:
            requester_data["score"] = requester_data.get("score", 0) - 10
            if requester_data.get("gold", 10) >= 3:
                requester_data["gold"] -= 3
            if requester_data.get("silver", 15) >= 5:
                requester_data["silver"] -= 5
            if random.random() < 0.25 and requester_data.get("gems", 5) >= 1:
                requester_data["gems"] -= 1
                report += "\nیه جم از دست دادیم! 😢"
            requester_data["energy"] = max(0, requester_data.get("energy", 100) - 30)
            report += "\nجریمه: -۱۰ امتیاز، -۳ کیسه طلا، -۵ شمش نقره، -۳۰٪ انرژی"
        
        await context.bot.send_message(requester_id, f"بازی دوستانه با {context.user_data['username']}:\n{report}")
        await query.message.reply_text(f"بازی دوستانه با {requester_name}:\n{'کاپیتان، دشمن رو غرق کردیم!' if not win else 'کاپیتان، کشتیمون سوراخ شد!'}")
        await query.message.edit_reply_markup(reply_markup=None)

# 📌 هندلر برای فروشگاه
async def shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("۲۵ جم = ۵ ترون", callback_data="buy_25_gems")],
        [InlineKeyboardButton("۵۰ جم = ۸ ترون", callback_data="buy_50_gems")],
        [InlineKeyboardButton("۱۰۰ جم = ۱۴ ترون", callback_data="buy_100_gems")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🛒 فروشگاه:\n"
        "انتخاب کن چه مقدار جم می‌خوای بخری:",
        reply_markup=reply_markup
    )

# 📌 هندلر برای اطلاعات کشتی
async def ship_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    gems = context.user_data.get("gems", 5)
    gold = context.user_data.get("gold", 10)
    silver = context.user_data.get("silver", 15)
    wins = context.user_data.get("wins", 0)
    games = context.user_data.get("games", 0)
    energy = context.user_data.get("energy", 100)
    
    win_rate = (wins / games * 100) if games > 0 else 0
    text = (
        "📕 اطلاعات کشتی:\n"
        f"جم: {gems}\n"
        f"کیسه طلا: {gold}\n"
        f"شمش نقره: {silver}\n"
        f"میانگین پیروزی: {win_rate:.0f}%\n"
        f"انرژی: {energy}%"
    )
    await update.message.reply_text(text)

# 📌 هندلر برای انرژی جنگجویان
async def warriors_energy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    energy = context.user_data.get("energy", 100)
    now = datetime.now()
    last_purchase = context.user_data.get("last_purchase", {})

    available_items = []
    items = [
        ("۱ بسته بیسکویت دریایی (۲۵٪ انرژی)", "biscuit", 0, 4, 25),
        ("۵ عدد ماهی خشک (۳۵٪ انرژی)", "fish", 1, 1, 35),
        ("۳ بسته میوه خشک‌شده (۳۰٪ انرژی)", "fruit", 1, 0, 30),
        ("۱۰ قالب پنیر کهنه (۵۰٪ انرژی)", "cheese", 1, 3, 50),
        ("۱۰ بطری آب (۲۰٪ انرژی)", "water", 0, 3, 20),
    ]
    
    for item_name, item_id, gold_cost, silver_cost, energy_gain in items:
        last_time = last_purchase.get(item_id)
        if not last_time or (now - last_time).total_seconds() >= 24 * 3600:
            available_items.append(
                [InlineKeyboardButton(f"{item_name} - قیمت: {gold_cost} طلا, {silver_cost} نقره", callback_data=f"buy_{item_id}")]
            )
    
    reply_markup = InlineKeyboardMarkup(available_items) if available_items else None
    text = f"⚡️ انرژی جنگجویان: {energy}%\n"
    if energy < 100:
        text += "اگه جنگجویانت خستن، باید براشون خوراکی بخری!"
    else:
        text += "جنگجویان تو پر از انرژی‌ان!"
    
    await update.message.reply_text(text, reply_markup=reply_markup)

# 📌 هندلر برای خرید جم
async def handle_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    gems = 0
    tron = 0
    if data == "buy_25_gems":
        gems, tron = 25, 5
    elif data == "buy_50_gems":
        gems, tron = 50, 8
    elif data == "buy_100_gems":
        gems, tron = 100, 14
    
    if gems:
        context.user_data["pending_gems"] = gems
        await query.message.reply_text(
            f"لطفاً {tron} ترون به آدرس زیر ارسال کنید و فیش پرداخت رو بفرستید:\n"
            "TJ4xrwKJzKjk6FgKfuuqwah3Az5Ur22kJb"
        )

# 📌 هندلر برای دریافت فیش
async def handle_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    pending_gems = context.user_data.get("pending_gems", 0)
    if pending_gems == 0:
        await update.message.reply_text("هیچ خریدی در انتظار تأیید نیست!")
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
            caption=f"فیش پرداخت از کاربر {user_id} برای {pending_gems} جم",
            reply_markup=reply_markup
        )
    elif update.message.text:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"فیش متنی از کاربر {user_id} برای {pending_gems} جم:\n{update.message.text}",
            reply_markup=reply_markup
        )
    
    await update.message.reply_text("فیش شما به ادمین ارسال شد. منتظر تأیید باشید!")

# 📌 هندلر برای تأیید/رد فیش توسط ادمین
async def handle_admin_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    if data.startswith("confirm_"):
        _, user_id, gems = data.split("_")
        user_id, gems = int(user_id), int(gems)
        await context.bot.send_message(user_id, f"خرید شما تأیید شد! {gems} جم به حسابتون اضافه شد.")
        context.user_data["gems"] = context.user_data.get("gems", 5) + gems
        context.user_data["pending_gems"] = 0
        await query.message.edit_reply_markup(reply_markup=None)
    elif data.startswith("reject_"):
        _, user_id = data.split("_")
        await context.bot.send_message(int(user_id), "خرید شما رد شد. لطفاً دوباره تلاش کنید.")
        context.user_data["pending_gems"] = 0
        await query.message.edit_reply_markup(reply_markup=None)

# 📌 هندلر برای خرید خوراکی
async def handle_food_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
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
        gold = context.user_data.get("gold", 10)
        silver = context.user_data.get("silver", 15)
        energy = context.user_data.get("energy", 100)
        
        if gold >= gold_cost and silver >= silver_cost:
            context.user_data["gold"] = gold - gold_cost
            context.user_data["silver"] = silver - silver_cost
            context.user_data["energy"] = min(100, energy + energy_gain)
            context.user_data["last_purchase"][data.replace("buy_", "")] = now
            await query.message.reply_text(f"خرید انجام شد! {energy_gain}% انرژی اضافه شد.")
        else:
            await query.message.reply_text("کیسه طلا یا شمش نقره کافی نیست!")
        await query.message.delete()
        await warriors_energy(update, context)

# 🔗 ثبت هندلرها
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.Regex("🛒 فروشگاه"), shop))
application.add_handler(MessageHandler(filters.Regex("📕 اطلاعات کشتی"), ship_info))
application.add_handler(MessageHandler(filters.Regex("⚡️ انرژی جنگجویان"), warriors_energy))
application.add_handler(MessageHandler(filters.Regex("⚔️ شروع بازی"), start_game))
application.add_handler(MessageHandler(filters.Regex("🔍 جست و جوی کاربران"), search_users))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex("^(🛒|📕|⚡️|⚔️|🔍|🏴‍☠️)"), handle_username))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex("^(🛒|📕|⚡️|⚔️|🔍|🏴‍☠️)"), handle_search))
application.add_handler(CallbackQueryHandler(handle_purchase, pattern="buy_.*_gems"))
application.add_handler(CallbackQueryHandler(handle_food_purchase, pattern="buy_(biscuit|fish|fruit|cheese|water)"))
application.add_handler(CallbackQueryHandler(handle_admin_response, pattern="(confirm|reject)_.*"))
application.add_handler(CallbackQueryHandler(handle_game, pattern="^(sailing|cannon)$"))
application.add_handler(CallbackQueryHandler(handle_cannon_purchase, pattern="buy_cannon_(gem|gold)"))
application.add_handler(CallbackQueryHandler(handle_friend_game, pattern="(accept_game|reject_game)_.*"))

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
    # راه‌اندازی بات
    await application.bot.set_webhook(url=WEBHOOK_URL)
    print("✅ Webhook set:", WEBHOOK_URL)
    await application.initialize()
    await application.start()
    

# 🛑 هنگام خاموشی
@app.on_event("shutdown")
async def on_shutdown():
    await application.updater.stop()
    await application.stop()
    await application.shutdown()
