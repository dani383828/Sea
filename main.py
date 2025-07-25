import os
import logging
from fastapi import FastAPI, Request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, ContextTypes, MessageHandler, CallbackQueryHandler, filters
)
from datetime import datetime, timedelta

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
    # مقداردهی اولیه برای کاربر جدید
    if not context.user_data.get("initialized"):
        context.user_data["gems"] = 5  # جم اولیه
        context.user_data["gold"] = 10  # کیسه طلا
        context.user_data["silver"] = 15  # شمش نقره
        context.user_data["wins"] = 0  # تعداد برد
        context.user_data["games"] = 0  # تعداد بازی‌ها
        context.user_data["energy"] = 100  # انرژی اولیه (درصد)
        context.user_data["last_purchase"] = {}  # برای محدودیت ۲۴ ساعته
        context.user_data["initialized"] = True

    # تعریف کیبورد معمولی
    keyboard = [
        ["⚔️ شروع بازی", "🛒 فروشگاه"],
        ["🏴‍☠️ برترین ناخدایان", "🔍 جست و جوی کاربران"],
        ["📕 اطلاعات کشتی", "⚡️ انرژی جنگجویان"],
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
    
    await update.message.reply_text("🏴‍☠️ خوش اومدی به دنیای دزدان دریایی!", reply_markup=reply_markup)

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
    
    # محاسبه میانگین پیروزی
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

    # بررسی محدودیت ۲۴ ساعته
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
    
    # ارسال فیش به ادمین
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
        await query.message.delete()  # حذف پیام قبلی برای به‌روزرسانی کیبورد
        await warriors_energy(update, context)

# 🔗 ثبت هندلرها
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.Regex("🛒 فروشگاه"), shop))
application.add_handler(MessageHandler(filters.Regex("📕 اطلاعات کشتی"), ship_info))
application.add_handler(MessageHandler(filters.Regex("⚡️ انرژی جنگجویان"), warriors_energy))
application.add_handler(CallbackQueryHandler(handle_purchase, pattern="buy_.*_gems"))
application.add_handler(CallbackQueryHandler(handle_food_purchase, pattern="buy_(biscuit|fish|fruit|cheese|water)"))
application.add_handler(CallbackQueryHandler(handle_admin_response, pattern="(confirm|reject)_.*"))
application.add_handler(MessageHandler(filters.PHOTO | filters.TEXT & ~filters.COMMAND, handle_receipt))

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
