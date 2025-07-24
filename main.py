import os
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List
from fastapi import FastAPI, Request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters
)

# Configuration
TOKEN = "8030062261:AAFnC9AJ_2zvcaqC0LXe5Y3--d2FgxOx-fI"
WEBHOOK_PATH = f"/webhook/{TOKEN}"
WEBHOOK_URL = f"https://sea-2ri6.onrender.com{WEBHOOK_PATH}"
ADMIN_ID = 5542927340
TRX_ADDRESS = "TJ4xrwKJzKjk6FgKfuuqwah3Az5Ur22kJb"

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI()

# Telegram bot application
application = Application.builder().token(TOKEN).build()

# In-memory storage (replace with database in production)
users: Dict[int, Dict] = {}  # {user_id: {ship_name, gems, gold, silver, energy, wins, total_games, cannons, last_purchase}}
ships: Dict[str, int] = {}  # {ship_name: user_id}
leaderboard: List[Dict] = []  # [{user_id, ship_name, score, win_rate}]

# Strategies and their counters
STRATEGIES = [
    "Camouflage as merchant ship",
    "Night attack",
    "Set enemy ship on fire",
    "Board with grappling hooks",
    "Ambush behind rocks",
    "Deceive with fake treasure",
    "Attack with spy assistance"
]
STRATEGY_COUNTERS = {
    "Camouflage as merchant ship": ["Attack with spy assistance", "Ambush behind rocks"],
    "Night attack": ["Attack with spy assistance"],
    "Set enemy ship on fire": ["Board with grappling hooks"],
    "Board with grappling hooks": ["Ambush behind rocks"],
    "Ambush behind rocks": ["Deceive with fake treasure"],
    "Deceive with fake treasure": ["Attack with spy assistance"],
    "Attack with spy assistance": ["Camouflage as merchant ship"]
}

# Initialize user data
def init_user(user_id: int, ship_name: str):
    users[user_id] = {
        "ship_name": ship_name,
        "gems": 5,
        "gold": 10,
        "silver": 15,
        "energy": 90,
        "wins": 0,
        "total_games": 0,
        "cannons": 3,
        "last_purchase": {},
        "strategy": None
    }
    ships[ship_name] = user_id
    update_leaderboard(user_id)

# Update leaderboard
def update_leaderboard(user_id: int):
    user = users.get(user_id)
    if not user:
        return
    win_rate = (user["wins"] / user["total_games"] * 100) if user["total_games"] > 0 else 0
    score = user["wins"] * 10
    leaderboard[:] = [entry for entry in leaderboard if entry["user_id"] != user_id]
    leaderboard.append({"user_id": user_id, "ship_name": user["ship_name"], "score": score, "win_rate": win_rate})
    leaderboard.sort(key=lambda x: x["score"], reverse=True)

# Validate ship name
def is_valid_ship_name(name: str) -> bool:
    return (
        bool(re.match("^[A-Za-z ]+$", name)) and
        name.lower() not in ["start", "menu"] and
        name not in ships
    )

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in users:
        await show_main_menu(update, context)
    else:
        await update.message.reply_text(
            "🏴‍☠️ Welcome to the Pirate World, Captain!\n\n"
            "🚢 Ready to build your ship and sail the seas?\n"
            "Enter your ship's name (English only, no duplicates, not 'start' or 'menu'):"
        )
        context.user_data["state"] = "awaiting_ship_name"

# Handle text messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    state = context.user_data.get("state")
    text = update.message.text

    if state == "awaiting_ship_name":
        if is_valid_ship_name(text):
            init_user(user_id, text)
            context.user_data.pop("state")
            await update.message.reply_text(
                f"🏗️ Your ship '{text}' is being built...\n"
                "⚓ Built! Ready to sail, Captain!"
            )
            await show_main_menu(update, context)
        else:
            await update.message.reply_text(
                "❌ Invalid ship name! Use English letters, no duplicates, and avoid 'start' or 'menu'."
            )
    elif state == "awaiting_payment_proof":
        await forward_payment_proof(update, context, text)
    elif state == "searching_user":
        await handle_user_search(update, context, text)

# Show main menu
async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("⚔️ Start Game", callback_data="start_game")],
        [InlineKeyboardButton("🛒 Shop", callback_data="shop")],
        [InlineKeyboardButton("🏆 Top Captains", callback_data="leaderboard")],
        [InlineKeyboardButton("🔍 Search Users", callback_data="search_users")],
        [InlineKeyboardButton("🚢 Ship Info", callback_data="ship_info")],
        [InlineKeyboardButton("⚡️ Warriors' Energy", callback_data="energy")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🏴‍☠️ Pirate World Menu:", reply_markup=reply_markup)

# Handle button clicks
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data == "start_game":
        await show_game_menu(query, context)
    elif data == "shop":
        await show_shop_menu(query, context)
    elif data == "leaderboard":
        await show_leaderboard(query, context)
    elif data == "search_users":
        await start_user_search(query, context)
    elif data == "ship_info":
        await show_ship_info(query, context)
    elif data == "energy":
        await show_energy_menu(query, context)
    elif data == "sailing":
        await start_sailing(query, context)
    elif data == "strategy":
        await show_strategy_menu(query, context)
    elif data == "cannons":
        await check_cannons(query, context)
    elif data.startswith("strategy_"):
        await set_strategy(query, context, data.split("_")[1])
    elif data == "fire_cannon":
        await fire_cannon(query, context)
    elif data == "shop_gems":
        await show_gems_shop(query, context)
    elif data == "shop_cannons":
        await buy_cannons(query, context)
    elif data == "shop_convert":
        await show_convert_menu(query, context)
    elif data.startswith("buy_gems_"):
        await handle_gem_purchase(query, context, data.split("_")[2])
    elif data.startswith("convert_"):
        await handle_conversion(query, context, data.split("_")[1])
    elif data.startswith("buy_energy_"):
        await buy_energy_item(query, context, data.split("_")[2])
    elif data == "back_to_menu":
        await show_main_menu(query, context)

# Game menu
async def show_game_menu(query: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("⛵️ Sailing", callback_data="sailing")],
        [InlineKeyboardButton("🎯 Strategy", callback_data="strategy")],
        [InlineKeyboardButton("☄️ Cannons", callback_data="cannons")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text("⚔️ Game Menu:", reply_markup=reply_markup)

# Sailing (battle)
async def start_sailing(query: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = query.from_user.id
    user = users.get(user_id)
    if not user:
        await query.message.reply_text("❌ Please start the game with /start first!")
        return

    # Find opponent (real or fake)
    opponent_id = None
    for uid, data in users.items():
        if uid != user_id and data["energy"] > 0:
            opponent_id = uid
            break
    if not opponent_id:
        opponent_id = -1  # Fake player
        users[opponent_id] = {
            "ship_name": "Ghost Ship",
            "energy": 80,
            "strategy": STRATEGIES[2],  # Random strategy for fake player
            "cannons": 3
        }

    context.user_data["opponent_id"] = opponent_id
    context.user_data["battle_state"] = {
        "stage": 0,
        "cannon_fired": False,
        "cannon_hit": False
    }
    await run_battle(query, context)

async def run_battle(query: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = query.from_user.id
    opponent_id = context.user_data["opponent_id"]
    user = users[user_id]
    opponent = users[opponent_id]
    battle_state = context.user_data["battle_state"]
    stage = battle_state["stage"]

    reports = [
        "🏴‍☠️ Your ship spots the enemy in the distance!",
        "⛵ The enemy ship is closing in fast!",
        "🔥 We're very close to the enemy now!"
    ]

    if stage < len(reports):
        keyboard = [[InlineKeyboardButton("☄️ Fire Cannon", callback_data="fire_cannon")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text(reports[stage], reply_markup=reply_markup)
        battle_state["stage"] += 1
    else:
        await end_battle(query, context)

async def fire_cannon(query: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = query.from_user.id
    user = users[user_id]
    battle_state = context.user_data["battle_state"]

    if user["cannons"] <= 0:
        await query.message.reply_text("❌ No cannons left! Head to the shop to buy more.")
        return
    if battle_state["cannon_fired"]:
        await query.message.reply_text("❌ You've already fired in this battle!")
        return

    user["cannons"] -= 1
    battle_state["cannon_fired"] = True
    hit_chance = 0.65 if battle_state["stage"] == 3 else 0.10
    import random
    if random.random() < hit_chance:
        battle_state["cannon_hit"] = True
        await query.message.reply_text("🎯 Cannon hit the enemy ship!")
    else:
        await query.message.reply_text("💨 Cannon missed!")
    await run_battle(query, context)

async def end_battle(query: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = query.from_user.id
    opponent_id = context.user_data["opponent_id"]
    user = users[user_id]
    opponent = users[opponent_id]
    battle_state = context.user_data["battle_state"]

    # Determine winner
    user_score = user["energy"] * 0.5
    opponent_score = opponent["energy"] * 0.5
    if battle_state["cannon_hit"]:
        user_score += 30
    if user["strategy"] and opponent["strategy"]:
        if opponent["strategy"] in STRATEGY_COUNTERS.get(user["strategy"], []):
            opponent_score += 50
            await query.message.reply_text(f"⚔️ {opponent['ship_name']}'s strategy ({opponent['strategy']}) countered yours ({user['strategy']})!")
        elif user["strategy"] in STRATEGY_COUNTERS.get(opponent["strategy"], []):
            user_score += 50
            await query.message.reply_text(f"⚔️ Your strategy ({user['strategy']}) countered {opponent['ship_name']}'s ({opponent['strategy']})!")

    winner = user_id if user_score > opponent_score else opponent_id
    import random
    if winner == user_id:
        user["wins"] += 1
        user["total_games"] += 1
        user["energy"] = min(100, user["energy"] + 10)
        user["gold"] += 3
        user["silver"] += 5
        if random.random() < 0.25:
            user["gems"] += 1
        await query.message.reply_text(
            f"🏆 Victory! You defeated {opponent['ship_name']}!\n"
            "+30 points, +3 gold, +5 silver, +10% energy" + (", +1 gem" if random.random() < 0.25 else "")
        )
    else:
        user["total_games"] += 1
        user["energy"] = max(0, user["energy"] - 30)
        user["gold"] = max(0, user["gold"] - 3)
        user["silver"] = max(0, user["silver"] - 5)
        if random.random() < 0.25:
            user["gems"] = max(0, user["gems"] - 1)
        await query.message.reply_text(
            f"💥 Defeat! {opponent['ship_name']} won!\n"
            "-10 points, -3 gold, -5 silver, -30% energy" + (", -1 gem" if random.random() < 0.25 else "")
        )

    update_leaderboard(user_id)
    if opponent_id != -1:
        update_leaderboard(opponent_id)
    context.user_data.pop("battle_state", None)
    context.user_data.pop("opponent_id", None)
    if opponent_id == -1:
        users.pop(opponent_id, None)
    await show_main_menu(query, context)

# Strategy menu
async def show_strategy_menu(query: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton(s, callback_data=f"strategy_{s}")] for s in STRATEGIES]
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text("🎯 Choose your attack strategy:", reply_markup=reply_markup)

async def set_strategy(query: Update, context: ContextTypes.DEFAULT_TYPE, strategy: str):
    user_id = query.from_user.id
    users[user_id]["strategy"] = strategy
    await query.message.reply_text(f"✅ Strategy set to: {strategy}")
    await show_game_menu(query, context)

# Cannons
async def check_cannons(query: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = query.from_user.id
    user = users[user_id]
    if user["cannons"] == 0:
        await query.message.reply_text("❌ No cannons left! Head to the shop to buy more.")
    else:
        await query.message.reply_text(f"☄️ You have {user['cannons']} cannons ready!")
    await show_game_menu(query, context)

# Shop menu
async def show_shop_menu(query: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("💎 Buy Gems", callback_data="shop_gems")],
        [InlineKeyboardButton("☄️ Buy Cannons", callback_data="shop_cannons")],
        [InlineKeyboardButton("🔄 Convert Gems", callback_data="shop_convert")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text("🛒 Shop Menu:", reply_markup=reply_markup)

async def show_gems_shop(query: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("25 Gems = 5 TRX", callback_data="buy_gems_25")],
        [InlineKeyboardButton("50 Gems = 8 TRX", callback_data="buy_gems_50")],
        [InlineKeyboardButton("100 Gems = 14 TRX", callback_data="buy_gems_100")],
        [InlineKeyboardButton("🔙 Back", callback_data="shop")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text(f"💎 Buy Gems (Send TRX to: {TRX_ADDRESS}):", reply_markup=reply_markup)

async def handle_gem_purchase(query: Update, context: ContextTypes.DEFAULT_TYPE, amount: str):
    context.user_data["state"] = "awaiting_payment_proof"
    context.user_data["gem_amount"] = int(amount)
    await query.message.reply_text("📸 Please send the payment receipt (image or text).")

async def forward_payment_proof(update: Update, context: ContextTypes.DEFAULT_TYPE, proof: str):
    user_id = update.effective_user.id
    gem_amount = context.user_data.get("gem_amount")
    if not gem_amount:
        await update.message.reply_text("❌ Error: No pending purchase.")
        return

    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"Payment proof from user {user_id} for {gem_amount} gems:\n{proof}",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Approve", callback_data=f"approve_{user_id}_{gem_amount}")],
            [InlineKeyboardButton("❌ Reject", callback_data=f"reject_{user_id}")]
        ])
    )
    await update.message.reply_text("✅ Proof sent to admin. Please wait for approval.")
    context.user_data.pop("state")
    context.user_data.pop("gem_amount")

async def handle_admin_response(query: Update, context: ContextTypes.DEFAULT_TYPE):
    data = query.data
    if data.startswith("approve_"):
        _, user_id, gem_amount = data.split("_")
        user_id = int(user_id)
        gem_amount = int(gem_amount)
        users[user_id]["gems"] += gem_amount
        await context.bot.send_message(user_id, f"✅ Payment approved! {gem_amount} gems added.")
    elif data.startswith("reject_"):
        _, user_id = data.split("_")
        user_id = int(user_id)
        await context.bot.send_message(user_id, "❌ Payment rejected by admin.")
    await query.message.delete()

async def buy_cannons(query: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = query.from_user.id
    user = users[user_id]
    if user["gems"] < 3:
        await query.message.reply_text("❌ Not enough gems! Need 3 gems per cannon.")
        return
    user["gems"] -= 3
    user["cannons"] += 1
    await query.message.reply_text("☄️ Cannon purchased successfully!")
    await show_shop_menu(query, context)

async def show_convert_menu(query: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("1 Gem = 2 Gold", callback_data="convert_1")],
        [InlineKeyboardButton("3 Gems = 6 Gold + 4 Silver", callback_data="convert_3")],
        [InlineKeyboardButton("10 Gems = 20 Gold + 15 Silver", callback_data="convert_10")],
        [InlineKeyboardButton("🔙 Back", callback_data="shop")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text("🔄 Convert Gems:", reply_markup=reply_markup)

async def handle_conversion(query: Update, context: ContextTypes.DEFAULT_TYPE, amount: str):
    user_id = query.from_user.id
    user = users[user_id]
    conversions = {
        "1": {"gems": 1, "gold": 2, "silver": 0},
        "3": {"gems": 3, "gold": 6, "silver": 4},
        "10": {"gems": 10, "gold": 20, "silver": 15}
    }
    conv = conversions[amount]
    if user["gems"] < conv["gems"]:
        await query.message.reply_text("❌ Not enough gems!")
        return
    user["gems"] -= conv["gems"]
    user["gold"] += conv["gold"]
    user["silver"] += conv["silver"]
    await query.message.reply_text(f"✅ Converted! +{conv['gold']} gold, +{conv['silver']} silver")
    await show_shop_menu(query, context)

# Leaderboard
async def show_leaderboard(query: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "🏆 Top Captains:\n\n"
    for i, entry in enumerate(leaderboard[:10], 1):
        text += f"{i}. {entry['ship_name']} - {entry['score']} points, {entry['win_rate']:.1f}% win rate\n"
    await query.message.reply_text(text or "No captains yet!")
    await show_main_menu(query, context)

# User search
async def start_user_search(query: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["state"] = "searching_user"
    await query.message.reply_text("🔍 Enter the ship name to search for a user:")

async def handle_user_search(update: Update, context: ContextTypes.DEFAULT_TYPE, ship_name: str):
    user_id = update.effective_user.id
    opponent_id = ships.get(ship_name)
    if not opponent_id or opponent_id == user_id:
        await update.message.reply_text("❌ Ship not found or invalid!")
        context.user_data.pop("state")
        return
    context.user_data["opponent_id"] = opponent_id
    await update.message.reply_text(
        f"⚔️ Found {ship_name}! Send battle request?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⚔️ Request Battle", callback_data=f"request_battle_{opponent_id}")]
        ])
    )
    context.user_data.pop("state")

async def handle_battle_request(query: Update, context: ContextTypes.DEFAULT_TYPE):
    data = query.data
    if data.startswith("request_battle_"):
        opponent_id = int(data.split("_")[2])
        await context.bot.send_message(
            opponent_id,
            f"⚔️ {users[query.from_user.id]['ship_name']} has challenged you to a friendly battle!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Accept", callback_data=f"accept_battle_{query.from_user.id}")]
            ])
        )
        await query.message.reply_text("✅ Battle request sent! Waiting for response.")

async def handle_battle_accept(query: Update, context: ContextTypes.DEFAULT_TYPE):
    data = query.data
    if data.startswith("accept_battle_"):
        opponent_id = int(data.split("_")[2])
        user_id = query.from_user.id
        context.user_data["opponent_id"] = opponent_id
        context.user_data["battle_state"] = {
            "stage": 0,
            "cannon_fired": False,
            "cannon_hit": False,
            "friendly": True
        }
        users[user_id]["cannons"] += 20
        users[opponent_id]["cannons"] += 20
        await query.message.reply_text("✅ Battle accepted! Starting friendly battle...")
        await run_battle(query, context)

# Ship info
async def show_ship_info(query: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = query.from_user.id
    user = users[user_id]
    win_rate = (user["wins"] / user["total_games"] * 100) if user["total_games"] > 0 else 0
    text = (
        f"🚢 Ship Info: {user['ship_name']}\n"
        f"💎 Gems: {user['gems']}\n"
        f"🥇 Gold: {user['gold']}\n"
        f"🥈 Silver: {user['silver']}\n"
        f"🏆 Win Rate: {win_rate:.1f}%\n"
        f"⚡️ Energy: {user['energy']}%"
    )
    await query.message.reply_text(text)
    await show_main_menu(query, context)

# Energy menu
async def show_energy_menu(query: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = query.from_user.id
    user = users[user_id]
    text = f"⚡️ Warriors' Energy: {user['energy']}%\n\n"
    if user["energy"] < 50:
        text += "⚠️ Your warriors are tired! Buy food to restore energy.\n"
    
    keyboard = [
        [InlineKeyboardButton("Biscuit (25% energy, 4 silver)", callback_data="buy_energy_biscuit")],
        [InlineKeyboardButton("Fish (35% energy, 1 gold + 1 silver)", callback_data="buy_energy_fish")],
        [InlineKeyboardButton("Fruit (30% energy, 1 gold)", callback_data="buy_energy_fruit")],
        [InlineKeyboardButton("Cheese (50% energy, 1 gold + 3 silver)", callback_data="buy_energy_cheese")],
        [InlineKeyboardButton("Water (20% energy, 3 silver)", callback_data="buy_energy_water")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text(text, reply_markup=reply_markup)

async def buy_energy_item(query: Update, context: ContextTypes.DEFAULT_TYPE, item: str):
    user_id = query.from_user.id
    user = users[user_id]
    now = datetime.utcnow()
    last_purchase = user["last_purchase"].get(item, datetime.min)

    if now - last_purchase < timedelta(hours=24):
        await query.message.reply_text("❌ You can only buy each item once every 24 hours!")
        return

    items = {
        "biscuit": {"energy": 25, "silver": 4, "gold": 0},
        "fish": {"energy": 35, "silver": 1, "gold": 1},
        "fruit": {"energy": 30, "silver": 0, "gold": 1},
        "cheese": {"energy": 50, "silver": 3, "gold": 1},
        "water": {"energy": 20, "silver": 3, "gold": 0}
    }
    cost = items[item]
    if user["gold"] < cost["gold"] or user["silver"] < cost["silver"]:
        await query.message.reply_text("❌ Not enough resources!")
        return

    user["gold"] -= cost["gold"]
    user["silver"] -= cost["silver"]
    user["energy"] = min(100, user["energy"] + cost["energy"])
    user["last_purchase"][item] = now
    await query.message.reply_text(f"✅ Purchased! +{cost['energy']}% energy")
    await show_energy_menu(query, context)

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
    logger.info("Webhook set: %s", WEBHOOK_URL)
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
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
application.add_handler(CallbackQueryHandler(button_handler, pattern="^(start_game|shop|leaderboard|search_users|ship_info|energy|sailing|strategy|cannons|shop_gems|shop_cannons|shop_convert|back_to_menu|fire_cannon|strategy_.*|buy_gems_.*|convert_.*|buy_energy_.*)$"))
application.add_handler(CallbackQueryHandler(handle_admin_response, pattern="^(approve_.*|reject_.*)$"))
application.add_handler(CallbackQueryHandler(handle_battle_request, pattern="^request_battle_.*$"))
application.add_handler(CallbackQueryHandler(handle_battle_accept, pattern="^accept_battle_.*$"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)
