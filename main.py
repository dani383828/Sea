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
import uuid

# Configurations
TOKEN = "8030062261:AAFnC9AJ_2zvcaqC0LXe5Y3--d2FgxOx-fI"
ADMIN_ID = 5542927340
TRX_ADDRESS = "TJ4xrwKJzKjk6FgKfuuqwah3Az5Ur22kJb"
WEBHOOK_PATH = f"/webhook/{TOKEN}"
WEBHOOK_URL = f"https://sea-2ri6.onrender.com{WEBHOOK_PATH}"

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Game data structures
player_data = {}  # Stores all player data
ship_names = set()  # To track used ship names
battle_requests = {}  # Track battle requests between players
ongoing_battles = {}  # Track ongoing battles

# Strategies and their counters
strategies = {
    "استتار به عنوان کشتی تجاری": ["اتصال قلاب", "حمله با کمک جاسوس"],
    "حمله شبانه": ["استتار به عنوان کشتی تجاری", "کمین پشت صخره"],
    "آتش‌زدن کشتی دشمن": ["فریب با گنج جعلی", "حمله شبانه"],
    "اتصال قلاب": ["آتش‌زدن کشتی دشمن", "حمله شبانه"],
    "کمین پشت صخره": ["فریب با گنج جعلی", "حمله با کمک جاسوس"],
    "فریب با گنج جعلی": ["استتار به عنوان کشتی تجاری", "اتصال قلاب"],
    "حمله با کمک جاسوس": ["کمین پشت صخره", "آتش‌زدن کشتی دشمن"]
}

# Food items
food_items = {
    "1 بسته بیسکویت دریایی": {"energy": 25, "cost_silver": 4, "cost_gold": 0},
    "5 عدد ماهی خشک": {"energy": 35, "cost_silver": 1, "cost_gold": 1},
    "3 بسته میوه خشک‌شده": {"energy": 30, "cost_silver": 0, "cost_gold": 1},
    "10 قالب پنیر کهنه": {"energy": 50, "cost_silver": 3, "cost_gold": 1},
    "۱۰ بطری آب": {"energy": 20, "cost_silver": 3, "cost_gold": 0}
}

# FastAPI app
app = FastAPI()

# Telegram bot application
application = Application.builder().token(TOKEN).build()

# Helper functions
def get_player(user_id):
    if user_id not in player_data:
        player_data[user_id] = {
            "ship_name": "",
            "gems": 5,
            "gold": 10,
            "silver": 15,
            "score": 0,
            "wins": 0,
            "losses": 0,
            "cannons": 3,
            "energy": 100,
            "last_food_purchase": None,
            "battles": []
        }
    return player_data[user_id]

def can_buy_food(player):
    if player["last_food_purchase"] is None:
        return True
    last_purchase = datetime.fromisoformat(player["last_food_purchase"])
    return datetime.now() - last_purchase >= timedelta(hours=24)

def update_food_purchase(player):
    player["last_food_purchase"] = datetime.now().isoformat()

def calculate_victory_chance(player_strategy, enemy_strategy, player_energy, enemy_energy):
    base_chance = 50
    
    # Strategy advantage
    if enemy_strategy in strategies.get(player_strategy, []):
        base_chance += 20
    elif player_strategy in strategies.get(enemy_strategy, []):
        base_chance -= 20
    
    # Energy impact
    base_chance += (player_energy - enemy_energy) / 2
    
    return max(10, min(90, base_chance))

def generate_battle_report(player, enemy, player_strategy, enemy_strategy):
    reports = [
        "کشتیت سوراخ شد!",
        "دشمن به شما نزدیک میشه!",
        "باد شدیدی میوزد!",
        "مه غلیظی دیدگاه رو پوشونده!",
        "خدمه شما خسته به نظر میرسن!",
        "دشمن در حال آماده‌سازی حمله است!",
        "به دشمن نزدیک میشیم!",
        "دشمن در حال عقب‌نشینی است!",
        "خدمه شما پرانرژی و آماده نبردند!",
        "بهشون حمله شبانه کردیم!!"
    ]
    return random.choice(reports)

# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    player = get_player(user_id)
    
    if player["ship_name"]:
        await show_main_menu(update, context)
    else:
        await update.message.reply_text(
            "🏴‍☠️ به دنیای دزدان دریایی خوش اومدی، کاپیتان!\n\n"
            "🚢 آماده‌ای کشتی‌تو بسازی و راهی دریا بشی؟\n\n"
            "کشتیت در حال ساخته شدنه..\n"
            "ساخته شد!\n"
            "نام کشتیت رو بگو\n"
            "دقت کن که گزینه‌های منو و دستور استارت به عنوان اسم پذیرفته نشه\n"
            "و فقط اسم انگلیسی پذیرفته میشه (تکراری هم نباید باشه)"
        )

async def handle_ship_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    player = get_player(user_id)
    
    if player["ship_name"]:
        return
    
    text = update.message.text.strip()
    
    # Validate ship name
    if text.lower() in ["/start", "start", "menu"]:
        await update.message.reply_text("این نام قابل قبول نیست. لطفا نام دیگری انتخاب کنید.")
        return
    
    if not text.isalpha():
        await update.message.reply_text("فقط حروف انگلیسی مجاز هستند.")
        return
    
    if text in ship_names:
        await update.message.reply_text("این نام قبلا استفاده شده. لطفا نام دیگری انتخاب کنید.")
        return
    
    # Save ship name
    player["ship_name"] = text
    ship_names.add(text)
    
    await update.message.reply_text(f"✅ کشتی شما با نام {text} ثبت شد!")
    await show_main_menu(update, context)

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("شروع بازی ⚔️", callback_data="start_game")],
        [InlineKeyboardButton("فروشگاه 🛒", callback_data="shop")],
        [InlineKeyboardButton("برترین ناخدایان", callback_data="leaderboard")],
        [InlineKeyboardButton("جست و جوی کاربران", callback_data="find_player")],
        [InlineKeyboardButton("اطلاعات کشتی", callback_data="ship_info")],
        [InlineKeyboardButton("انرژی جنگجویان", callback_data="crew_energy")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            "🏴‍☠️ منوی اصلی:",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            "🏴‍☠️ منوی اصلی:",
            reply_markup=reply_markup
        )

# Callback handlers
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "start_game":
        await start_game_menu(update, context)
    elif data == "shop":
        await shop_menu(update, context)
    elif data == "leaderboard":
        await show_leaderboard(update, context)
    elif data == "find_player":
        await find_player(update, context)
    elif data == "ship_info":
        await show_ship_info(update, context)
    elif data == "crew_energy":
        await crew_energy_menu(update, context)
    elif data == "battle_sail":
        await start_battle(update, context)
    elif data == "battle_strategy":
        await select_strategy(update, context)
    elif data == "battle_cannon":
        await fire_cannon(update, context)
    elif data.startswith("strategy_"):
        await handle_strategy_selection(update, context)
    elif data.startswith("food_"):
        await handle_food_purchase(update, context)
    elif data.startswith("shop_"):
        await handle_shop_selection(update, context)
    elif data.startswith("confirm_battle_"):
        await handle_battle_confirmation(update, context)

async def start_game_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("دریانوردی⛵️", callback_data="battle_sail")],
        [InlineKeyboardButton("استراتژی", callback_data="battle_strategy")],
        [InlineKeyboardButton("توپ", callback_data="battle_cannon")],
        [InlineKeyboardButton("بازگشت", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        "⚔️ گزینه مورد نظر را انتخاب کنید:",
        reply_markup=reply_markup
    )

async def start_battle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.callback_query.from_user.id
    player = get_player(user_id)
    
    if player["energy"] < 20:
        await update.callback_query.edit_message_text(
            "انرژی خدمه شما برای نبرد کافی نیست! لطفا ابتدا انرژی آنها را تامین کنید.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("بازگشت", callback_data="start_game")]])
        )
        return
    
    # Find opponent (or create AI opponent after 1 minute)
    opponent_id = None
    for uid, req in battle_requests.items():
        if uid != user_id and req["status"] == "waiting":
            opponent_id = uid
            break
    
    if opponent_id:
        # Create battle between two players
        battle_id = str(uuid.uuid4())
        ongoing_battles[battle_id] = {
            "player1": user_id,
            "player2": opponent_id,
            "status": "strategy_selection",
            "strategies": {},
            "reports": [],
            "cannon_used": {user_id: False, opponent_id: False},
            "start_time": datetime.now()
        }
        
        # Remove from battle requests
        del battle_requests[user_id]
        del battle_requests[opponent_id]
        
        # Notify both players
        player1 = get_player(user_id)
        player2 = get_player(opponent_id)
        
        await context.bot.send_message(
            user_id,
            f"⚔️ نبرد با {player2['ship_name']} شروع شد! لطفا استراتژی خود را انتخاب کنید."
        )
        await context.bot.send_message(
            opponent_id,
            f"⚔️ نبرد با {player1['ship_name']} شروع شد! لطفا استراتژی خود را انتخاب کنید."
        )
        
        await select_strategy(update, context, battle_id)
    else:
        # Add to waiting list
        battle_requests[user_id] = {
            "status": "waiting",
            "time": datetime.now()
        }
        
        await update.callback_query.edit_message_text(
            "در جستجوی حریف... لطفا 1 دقیقه صبر کنید.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("لغو", callback_data="start_game")]])
        )
        
        # Schedule AI opponent after 1 minute
        async def create_ai_battle(context: ContextTypes.DEFAULT_TYPE):
            if user_id in battle_requests and battle_requests[user_id]["status"] == "waiting":
                del battle_requests[user_id]
                
                # Create battle with AI
                battle_id = str(uuid.uuid4())
                ongoing_battles[battle_id] = {
                    "player1": user_id,
                    "player2": "AI",
                    "status": "strategy_selection",
                    "strategies": {},
                    "reports": [],
                    "cannon_used": {user_id: False, "AI": False},
                    "start_time": datetime.now()
                }
                
                await context.bot.send_message(
                    user_id,
                    "⚔️ نبرد با یک دشمن تصادفی شروع شد! لطفا استراتژی خود را انتخاب کنید."
                )
                
                await select_strategy(update, context, battle_id)
        
        context.job_queue.run_once(create_ai_battle, 60)

async def select_strategy(update: Update, context: ContextTypes.DEFAULT_TYPE, battle_id=None):
    if not battle_id:
        # Find battle for this user
        for bid, battle in ongoing_battles.items():
            if update.callback_query.from_user.id in [battle["player1"], battle["player2"]]:
                battle_id = bid
                break
    
    if not battle_id:
        await update.callback_query.edit_message_text(
            "نبرد پیدا نشد!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("بازگشت", callback_data="start_game")]])
        return
    
    keyboard = []
    for strategy in strategies:
        keyboard.append([InlineKeyboardButton(strategy, callback_data=f"strategy_{strategy}_{battle_id}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        "🎯 استراتژی خود را انتخاب کنید:",
        reply_markup=reply_markup
    )

async def handle_strategy_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data.split("_")
    strategy = "_".join(data[1:-1])
    battle_id = data[-1]
    
    user_id = query.from_user.id
    battle = ongoing_battles.get(battle_id)
    
    if not battle:
        await query.edit_message_text("این نبرد به پایان رسیده!")
        return
    
    # Record player's strategy
    if user_id == battle["player1"]:
        battle["strategies"]["player1"] = strategy
    else:
        battle["strategies"]["player2"] = strategy
    
    await query.edit_message_text(f"استراتژی شما ثبت شد: {strategy}")
    
    # Check if both players have selected strategies
    if len(battle["strategies"]) == 2:
        await execute_battle(battle_id, context)

async def execute_battle(battle_id: str, context: ContextTypes.DEFAULT_TYPE):
    battle = ongoing_battles[battle_id]
    player1_id = battle["player1"]
    player2_id = battle["player2"]
    
    player1 = get_player(player1_id)
    player2 = get_player(player2_id) if player2_id != "AI" else {
        "energy": random.randint(50, 100),
        "ship_name": "کشتی دشمن"
    }
    
    player1_strategy = battle["strategies"]["player1"]
    player2_strategy = battle["strategies"]["player2"] if player2_id != "AI" else random.choice(list(strategies.keys()))
    
    # Generate battle reports
    reports = []
    for _ in range(3):
        report = generate_battle_report(player1, player2, player1_strategy, player2_strategy)
        reports.append(report)
        time.sleep(2)
    
    # Calculate victory chance
    victory_chance = calculate_victory_chance(
        player1_strategy, 
        player2_strategy,
        player1["energy"],
        player2["energy"]
    )
    
    # Determine winner
    player1_wins = random.randint(1, 100) <= victory_chance
    
    # Update player stats
    if player1_wins:
        rewards = {
            "score": 30,
            "gold": 3,
            "silver": 5,
            "energy": player1["energy"] * 0.1,
            "gems": 1 if random.random() < 0.25 else 0
        }
        
        player1["score"] += rewards["score"]
        player1["gold"] += rewards["gold"]
        player1["silver"] += rewards["silver"]
        player1["energy"] = min(100, player1["energy"] + rewards["energy"])
        player1["gems"] += rewards["gems"]
        player1["wins"] += 1
        
        if player2_id != "AI":
            player2["score"] = max(0, player2["score"] - 10)
            player2["gold"] = max(0, player2["gold"] - 3)
            player2["silver"] = max(0, player2["silver"] - 5)
            player2["energy"] = max(0, player2["energy"] - 30)
            player2["gems"] = max(0, player2["gems"] - (1 if random.random() < 0.25 else 0))
            player2["losses"] += 1
    else:
        penalties = {
            "score": -10,
            "gold": -3,
            "silver": -5,
            "energy": -30,
            "gems": -1 if random.random() < 0.25 else 0
        }
        
        player1["score"] = max(0, player1["score"] + penalties["score"])
        player1["gold"] = max(0, player1["gold"] + penalties["gold"])
        player1["silver"] = max(0, player1["silver"] + penalties["silver"])
        player1["energy"] = max(0, player1["energy"] + penalties["energy"])
        player1["gems"] = max(0, player1["gems"] + penalties["gems"])
        player1["losses"] += 1
        
        if player2_id != "AI":
            player2["score"] += 30
            player2["gold"] += 3
            player2["silver"] += 5
            player2["energy"] = min(100, player2["energy"] + 10)
            player2["gems"] += 1 if random.random() < 0.25 else 0
            player2["wins"] += 1
    
    # Send results to players
    result_message = (
        f"⚔️ نتیجه نبرد:\n"
        f"استراتژی شما: {player1_strategy}\n"
        f"استراتژی حریف: {player2_strategy}\n\n"
    )
    
    if player1_wins:
        result_message += (
            "🎉 شما پیروز شدید!\n\n"
            f"🏆 امتیاز: +30 (جمع: {player1['score']})\n"
            f"💰 کیسه طلا: +3 (جمع: {player1['gold']})\n"
            f"🪙 شمش نقره: +5 (جمع: {player1['silver']})\n"
            f"⚡ انرژی: +10% (جمع: {player1['energy']}%)\n"
        )
        if rewards["gems"] > 0:
            result_message += f"💎 جم: +1 (جمع: {player1['gems']})\n"
    else:
        result_message += (
            "💀 شما شکست خوردید!\n\n"
            f"🏆 امتیاز: -10 (جمع: {player1['score']})\n"
            f"💰 کیسه طلا: -3 (جمع: {player1['gold']})\n"
            f"🪙 شمش نقره: -5 (جمع: {player1['silver']})\n"
            f"⚡ انرژی: -30% (جمع: {player1['energy']}%)\n"
        )
        if penalties["gems"] < 0:
            result_message += f"💎 جم: -1 (جمع: {player1['gems']})\n"
    
    await context.bot.send_message(player1_id, result_message)
    
    if player2_id != "AI":
        await context.bot.send_message(
            player2_id,
            f"⚔️ نتیجه نبرد:\n"
            f"استراتژی شما: {player2_strategy}\n"
            f"استراتژی حریف: {player1_strategy}\n\n"
            f"{'🎉 شما پیروز شدید!' if not player1_wins else '💀 شما شکست خوردید!'}"
        )
    
    # Remove battle
    del ongoing_battles[battle_id]

async def fire_cannon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.callback_query.from_user.id
    player = get_player(user_id)
    
    if player["cannons"] <= 0:
        await update.callback_query.edit_message_text(
            "توپ ندارید! لطفا به فروشگاه مراجعه کنید.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("فروشگاه", callback_data="shop")]])
        )
    else:
        await update.callback_query.edit_message_text(
            f"🔫 شما {player['cannons']} توپ دارید. در نبرد می‌توانید از آنها استفاده کنید."
        )

async def shop_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("خرید جم 💎", callback_data="shop_gems")],
        [InlineKeyboardButton("خرید توپ", callback_data="shop_cannons")],
        [InlineKeyboardButton("تبدیل جم به سکه و نقره", callback_data="shop_convert")],
        [InlineKeyboardButton("بازگشت", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        "🛒 فروشگاه:",
        reply_markup=reply_markup
    )

async def handle_shop_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data.split("_")[1]
    
    if data == "gems":
        keyboard = [
            [InlineKeyboardButton("25 جم = ۵ ترون", callback_data="buy_gems_25")],
            [InlineKeyboardButton("50 جم = ۸ ترون", callback_data="buy_gems_50")],
            [InlineKeyboardButton("100 جم = ۱۴ ترون", callback_data="buy_gems_100")],
            [InlineKeyboardButton("بازگشت", callback_data="shop")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "💎 خرید جم:\n\n"
            "آدرس ترون: TJ4xrwKJzKjk6FgKfuuqwah3Az5Ur22kJb\n\n"
            "پس از پرداخت، رسید پرداخت را ارسال کنید.",
            reply_markup=reply_markup
        )
    elif data == "cannons":
        user_id = query.from_user.id
        player = get_player(user_id)
        
        if player["gems"] < 3:
            await query.edit_message_text(
                "جم کافی برای خرید توپ ندارید! هر توپ 3 جم قیمت دارد.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("بازگشت", callback_data="shop")]])
            )
        else:
            player["gems"] -= 3
            player["cannons"] += 1
            await query.edit_message_text(
                f"✅ یک توپ خریداری شد!\n\n"
                f"جم باقیمانده: {player['gems']}\n"
                f"تعداد توپ: {player['cannons']}"
            )
    elif data == "convert":
        keyboard = [
            [InlineKeyboardButton("1 جم = 2 کیسه طلا", callback_data="convert_1")],
            [InlineKeyboardButton("3 جم = 6 کیسه طلا + 4 شمش نقره", callback_data="convert_3")],
            [InlineKeyboardButton("10 جم = 20 کیسه طلا + 15 شمش نقره", callback_data="convert_10")],
            [InlineKeyboardButton("بازگشت", callback_data="shop")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "تبدیل جم به سکه و نقره:",
            reply_markup=reply_markup
        )
    elif data.startswith("buy_gems_"):
        amount = int(data.split("_")[2])
        await query.edit_message_text(
            f"لطفا {amount} جم به آدرس زیر پرداخت کنید:\n\n"
            f"TRX: TJ4xrwKJzKjk6FgKfuuqwah3Az5Ur22kJb\n\n"
            "پس از پرداخت، رسید (عکس یا متن) را ارسال کنید."
        )

async def show_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Get top 10 players by score
    top_players = sorted(
        [(uid, data) for uid, data in player_data.items() if data["ship_name"]],
        key=lambda x: x[1]["score"],
        reverse=True
    )[:10]
    
    leaderboard = "🏆 برترین ناخدایان:\n\n"
    for i, (uid, player) in enumerate(top_players, 1):
        win_rate = (player["wins"] / (player["wins"] + player["losses"])) * 100 if (player["wins"] + player["losses"]) > 0 else 0
        leaderboard += (
            f"{i}. {player['ship_name']}\n"
            f"   امتیاز: {player['score']}\n"
            f"   میانگین برد: {win_rate:.1f}%\n\n"
        )
    
    await update.callback_query.edit_message_text(
        leaderboard,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("بازگشت", callback_data="main_menu")]])
    )

async def find_player(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.edit_message_text(
        "نام کشتی کاربر مورد نظر را وارد کنید:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("بازگشت", callback_data="main_menu")]])
    )

async def handle_find_player(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    ship_name = update.message.text.strip()
    
    found = False
    for uid, player in player_data.items():
        if player["ship_name"].lower() == ship_name.lower():
            found = True
            keyboard = [
                [InlineKeyboardButton("ارسال درخواست جنگ", callback_data=f"request_battle_{uid}")],
                [InlineKeyboardButton("بازگشت", callback_data="main_menu")]
            ]
            await update.message.reply_text(
                f"کشتی {ship_name} پیدا شد!",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            break
    
    if not found:
        await update.message.reply_text(
            "کشتی با این نام پیدا نشد!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("بازگشت", callback_data="main_menu")]])
        )

async def handle_battle_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    target_id = int(query.data.split("_")[2])
    requester_id = query.from_user.id
    
    # Store battle request
    battle_requests[requester_id] = {
        "target": target_id,
        "status": "pending",
        "time": datetime.now()
    }
    
    # Notify target player
    requester = get_player(requester_id)
    target = get_player(target_id)
    
    keyboard = [
        [InlineKeyboardButton("پذیرفتن", callback_data=f"confirm_battle_{requester_id}")],
        [InlineKeyboardButton("رد کردن", callback_data=f"reject_battle_{requester_id}")]
    ]
    
    await context.bot.send_message(
        target_id,
        f"⚔️ درخواست نبرد از {requester['ship_name']}:\n\n"
        "این یک نبرد دوستانه است با 20 توپ رایگان!",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    await query.edit_message_text("درخواست نبرد ارسال شد!")

async def handle_battle_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data.split("_")
    action = data[1]
    requester_id = int(data[2])
    
    responder_id = query.from_user.id
    
    if action == "confirm":
        # Create friendly battle
        battle_id = str(uuid.uuid4())
        ongoing_battles[battle_id] = {
            "player1": requester_id,
            "player2": responder_id,
            "status": "strategy_selection",
            "strategies": {},
            "reports": [],
            "cannon_used": {requester_id: False, responder_id: False},
            "start_time": datetime.now(),
            "friendly": True
        }
        
        # Give free cannons
        requester = get_player(requester_id)
        responder = get_player(responder_id)
        requester["cannons"] += 20
        responder["cannons"] += 20
        
        # Notify both players
        await context.bot.send_message(
            requester_id,
            "درخواست نبرد شما پذیرفته شد! 20 توپ رایگان دریافت کردید."
        )
        await context.bot.send_message(
            responder_id,
            "شما 20 توپ رایگان برای این نبرد دریافت کردید!"
        )
        
        await select_strategy(update, context, battle_id)
    else:
        await context.bot.send_message(
            requester_id,
            "درخواست نبرد شما رد شد."
        )
        await query.edit_message_text("درخواست نبرد رد شد.")

async def show_ship_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.callback_query.from_user.id
    player = get_player(user_id)
    
    win_rate = (player["wins"] / (player["wins"] + player["losses"])) * 100 if (player["wins"] + player["losses"]) > 0 else 0
    
    info = (
        f"🚢 اطلاعات کشتی {player['ship_name']}:\n\n"
        f"💎 جم: {player['gems']}\n"
        f"💰 کیسه طلا: {player['gold']}\n"
        f"🪙 شمش نقره: {player['silver']}\n"
        f"🏆 امتیاز: {player['score']}\n"
        f"🎯 میانگین پیروزی: {win_rate:.1f}%\n"
        f"⚡ انرژی: {player['energy']}%\n"
        f"🔫 توپ: {player['cannons']}"
    )
    
    await update.callback_query.edit_message_text(
        info,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("بازگشت", callback_data="main_menu")]])
    )

async def crew_energy_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.callback_query.from_user.id
    player = get_player(user_id)
    
    energy_status = ""
    if player["energy"] > 70:
        energy_status = "✅ خدمه پرانرژی هستند!"
    elif player["energy"] > 40:
        energy_status = "⚠️ خدمه کمی خسته هستند."
    else:
        energy_status = "❌ خدمه بسیار خسته و نیاز به استراحت دارند!"
    
    keyboard = []
    for food, details in food_items.items():
        if can_buy_food(player):
            keyboard.append([
                InlineKeyboardButton(
                    f"{food} (+{details['energy']}%) - قیمت: {details['cost_gold']} کیسه طلا و {details['cost_silver']} شمش نقره",
                    callback_data=f"food_{food}"
                )
            ])
    
    keyboard.append([InlineKeyboardButton("بازگشت", callback_data="main_menu")])
    
    await update.callback_query.edit_message_text(
        f"⚡ انرژی خدمه: {player['energy']}%\n\n"
        f"{energy_status}\n\n"
        "خوراکی‌های قابل خرید:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_food_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    food = query.data.split("_")[1]
    
    user_id = query.from_user.id
    player = get_player(user_id)
    
    if not can_buy_food(player):
        await query.edit_message_text(
            "شما امروز قبلا خوراکی خریده‌اید! 24 ساعت صبر کنید.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("بازگشت", callback_data="crew_energy")]])
        )
        return
    
    details = food_items[food]
    
    if (player["gold"] < details["cost_gold"]) or (player["silver"] < details["cost_silver"]):
        await query.edit_message_text(
            "موجودی کافی برای خرید این خوراکی ندارید!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("بازگشت", callback_data="crew_energy")]])
        )
        return
    
    # Process purchase
    player["gold"] -= details["cost_gold"]
    player["silver"] -= details["cost_silver"]
    player["energy"] = min(100, player["energy"] + details["energy"])
    update_food_purchase(player)
    
    await query.edit_message_text(
        f"✅ {food} خریداری شد!\n\n"
        f"⚡ انرژی جدید: {player['energy']}%",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("بازگشت", callback_data="crew_energy")]])
    )

async def handle_payment_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    player = get_player(user_id)
    
    # Forward to admin for confirmation
    await context.bot.send_message(
        ADMIN_ID,
        f"📩 رسید پرداخت از {player['ship_name']}:\n\n"
        f"User ID: {user_id}\n"
        f"Ship: {player['ship_name']}\n\n"
        "لطفا تایید یا رد کنید:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("تایید ✅", callback_data=f"admin_confirm_{user_id}")],
            [InlineKeyboardButton("رد ❌", callback_data=f"admin_reject_{user_id}")]
        ])
    )
    
    await update.message.reply_text("رسید شما به ادمین ارسال شد. لطفا منتظر تایید بمانید.")

async def handle_admin_decision(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data.split("_")
    action = data[1]
    target_id = int(data[2])
    
    if action == "confirm":
        # Find the last purchase request
        # In a real app, you'd have a proper tracking system
        player = get_player(target_id)
        player["gems"] += 25  # Default to 25 gems for demo
        
        await context.bot.send_message(
            target_id,
            "✅ پرداخت شما تایید شد! 25 جم به حساب شما واریز شد."
        )
        await query.edit_message_text("پرداخت تایید شد و جم واریز گردید.")
    else:
        await context.bot.send_message(
            target_id,
            "❌ پرداخت شما رد شد. لطفا با پشتیبانی تماس بگیرید."
        )
        await query.edit_message_text("پرداخت رد شد.")

# Register handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_ship_name))
application.add_handler(CallbackQueryHandler(button))
application.add_handler(MessageHandler(filters.PHOTO | filters.TEXT & ~filters.COMMAND, handle_payment_receipt))

# Webhook endpoint
@app.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, application.bot)
    await application.update_queue.put(update)
    return {"ok": True}

# Startup/shutdown events
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
