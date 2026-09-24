import os
import time
import telebot
from telebot import apihelper
from dotenv import load_dotenv

# Import custom modules
from database import init_db, add_user, get_last_prices
from parser import fetch_binance_api, scrape_crypto_news

# --- SYSTEM INITIALIZATION ---
load_dotenv()

# Custom Worker reverse proxy for Telegram API bypass
apihelper.API_URL = "https://royal-math-a6b6.n-xiv98.workers.dev/bot{0}/{1}"

TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

init_db()

# --- STREET RULES & SECURITY (STRIKE SYSTEM) ---
USER_LAST_MSG_TIME = {}
USER_STRIKES = {}
BLACKLIST = set()

SPAM_THRESHOLD = 3.0  # seconds between requests to trigger a strike
MAX_STRIKES = 3

def check_security(user_id):
    """Returns 'BANNED', 'WARNING', or 'CLEAR'."""
    if user_id in BLACKLIST:
        return "BANNED"
        
    current_time = time.time()
    last_time = USER_LAST_MSG_TIME.get(user_id, 0)
    
    if current_time - last_time < SPAM_THRESHOLD:
        strikes = USER_STRIKES.get(user_id, 0) + 1
        USER_STRIKES[user_id] = strikes
        USER_LAST_MSG_TIME[user_id] = current_time
        
        if strikes >= MAX_STRIKES:
            BLACKLIST.add(user_id)
            return "BANNED"
        return "WARNING"
        
    USER_LAST_MSG_TIME[user_id] = current_time
    return "CLEAR"

def handle_violation(message, status):
    """Handles responses for rule breakers."""
    if status == "BANNED":
        bot.reply_to(message, "💀 **BLACKLISTED.**\n\nYou made too much noise. You're cut off from the syndicate.", parse_mode="Markdown")
    elif status == "WARNING":
        strikes = USER_STRIKES.get(message.from_user.id, 1)
        bot.reply_to(message, f"⚠️ **Watch your step.** You're moving too fast. Slow down.\n_Strike {strikes}/{MAX_STRIKES}_", parse_mode="Markdown")

# --- SUPPORTED ASSETS ---
SUPPORTED_COINS = ["BTC", "ETH", "SOL", "BNB", "TON", "XRP", "DOGE"]

# --- COMMAND HANDLERS ---

@bot.message_handler(commands=['start', 'help'])
def handle_start(message):
    user_id = message.from_user.id
    status = check_security(user_id)
    if status != "CLEAR":
        handle_violation(message, status)
        return

    username = message.from_user.username or "Unknown"
    add_user(user_id, username)
    
    welcome_msg = (
        "🏴 **SYNDICATE NETWORK ACCESSED**\n\n"
        "No names. No faces. We just track the money.\n"
        "You're in the shadow zone now. Keep it strictly business.\n\n"
        "**THE DIRECTIVES:**\n"
        "• `/news` - Word on the street (Latest Intel)\n"
        "• `/history` - Previous drops (Ledger)\n\n"
        "**AUTHORIZED ASSETS:**\n"
        f"`{', '.join(SUPPORTED_COINS)}`\n\n"
        "Drop a ticker to see the real-time cut."
    )
    bot.reply_to(message, welcome_msg, parse_mode="Markdown")

@bot.message_handler(commands=['news', 'intel'])
def handle_news(message):
    user_id = message.from_user.id
    status = check_security(user_id)
    if status != "CLEAR":
        handle_violation(message, status)
        return
        
    bot.send_chat_action(message.chat.id, "typing")
    
    headlines = scrape_crypto_news()
    
    if not headlines:
        bot.reply_to(message, "Dead end. The informants are quiet right now.")
        return
        
    response = "👁️ WORD ON THE STREET:\n\n"
    for idx, title in enumerate(headlines, 1):
        response += f"{idx}. {title}\n\n"
        
    # No Markdown mode here to prevent Telegram parsing exceptions on special chars in news titles
    bot.reply_to(message, response)

@bot.message_handler(commands=['history', 'stats'])
def handle_stats(message):
    user_id = message.from_user.id
    status = check_security(user_id)
    if status != "CLEAR":
        handle_violation(message, status)
        return
        
    records = get_last_prices(limit=5)
    
    if not records:
        bot.reply_to(message, "No records. The ledger is clean.", parse_mode="Markdown")
        return
        
    response = "📓 **THE LEDGER (RECENT DROPS):**\n\n"
    for row in records:
        coin = str(row[1])
        try:
            price = float(row[2])
            price_str = f"${price:,.2f}"
        except (ValueError, TypeError):
            price_str = f"${row[2]}"
            
        timestamp = str(row[-1])
        response += f"• **{coin}** | `{price_str}` | `{timestamp}`\n"
        
    bot.reply_to(message, response, parse_mode="Markdown")

@bot.message_handler(commands=['shadow'])
def handle_shadow(message):
    user_id = message.from_user.id
    status = check_security(user_id)
    if status != "CLEAR":
        handle_violation(message, status)
        return
        
    bot.reply_to(
        message, 
        "You're digging too deep. Fall back before you get buried.",
        parse_mode="Markdown"
    )

# --- TEXT MESSAGES HANDLER ---

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    user_id = message.from_user.id
    status = check_security(user_id)
    if status != "CLEAR":
        handle_violation(message, status)
        return
        
    # Edge case protection: ensure message contains actual text (not sticker/photo)
    if not message.text:
        bot.reply_to(message, "Watch your mouth. Only plaintext signals accepted.")
        return

    text = message.text.strip().upper()
    
    # Catch plain text keywords without slashes
    if text in ["NEWS", "INTEL"]:
        handle_news(message)
        return
    elif text in ["STATS", "HISTORY", "LEDGER"]:
        handle_stats(message)
        return
    elif text == "SHADOW":
        handle_shadow(message)
        return
        
    if text in SUPPORTED_COINS:
        bot.send_chat_action(message.chat.id, "typing")
        
        status_msg = bot.reply_to(message, f"Checking the stash for {text}...", parse_mode="Markdown")
        
        price = fetch_binance_api(text)
        
        if price:
            try:
                formatted_price = f"${float(price):,.2f} USDT"
            except (ValueError, TypeError):
                formatted_price = f"${price} USDT"

            final_msg = (
                f"💰 **{text} SECURED**\n\n"
                f"**Street Value:** `{formatted_price}`\n\n"
                f"_Logged and untraceable._"
            )
            bot.edit_message_text(chat_id=message.chat.id, message_id=status_msg.message_id, text=final_msg, parse_mode="Markdown")
        else:
            bot.edit_message_text(chat_id=message.chat.id, message_id=status_msg.message_id, text=f"Connection severed. Couldn't pull numbers for `{text}`.", parse_mode="Markdown")
    else:
        bot.reply_to(
            message, 
            "Watch your mouth. Invalid drop.\n"
            f"Stick to the authorized assets: `{', '.join(SUPPORTED_COINS)}`",
            parse_mode="Markdown"
        )

# --- ENGINE IGNITION ---

if __name__ == "__main__":
    print("=== SYNDICATE BOT RUNNING ===")
    print("[*] Strict security enforced.")
    print("[*] Awaiting signals...")
    
    try:
        bot.infinity_polling(timeout=10, long_polling_timeout=5)
    except Exception as e:
        print(f"\n[!] SYSTEM FAILURE: {e}")
