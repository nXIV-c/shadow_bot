import os
import time
import telebot
from telebot import apihelper, BaseMiddleware
from telebot.handler_backends import CancelUpdate
from dotenv import load_dotenv

# Import custom modules
from database import init_db, add_user, get_last_prices
from parser import fetch_binance_api, scrape_crypto_news

# --- SYSTEM INITIALIZATION ---
load_dotenv()

# Custom Worker reverse proxy for Telegram API bypass
apihelper.API_URL = "https://royal-math-a6b6.n-xiv98.workers.dev/bot{0}/{1}"

TOKEN = os.getenv("BOT_TOKEN")
admin_ids_str = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = [int(user_id.strip()) for user_id in admin_ids_str.split(",") if user_id.strip()]
bot = telebot.TeleBot(TOKEN, use_class_middlewares=True)

init_db()

# --- MIDDLEWARE: ANTI-SPAM & STRIKES ---
class AntispamMiddleware(BaseMiddleware):
    def __init__(self, bot_instance):
        super().__init__()
        self.bot = bot_instance
        self.update_types = ['message']
        self.user_state = {}

        self.message_cooldown = 3.0       # Seconds between requests
        self.strike_reset_time = 300      # Strikes expire after 5 minutes
        self.max_strikes = 3

    def pre_process(self, message, data):
        user_id = message.from_user.id
        current_time = time.time()

        user = self.user_state.setdefault(user_id, {
            'last_msg_time': 0,
            'last_strike_time': 0,
            'strikes': 0,
            'banned': False
        })

        if user['banned']:
            return CancelUpdate()

        # Amnesty: reset strikes after a long period of good behavior
        if user['strikes'] > 0 and (current_time - user['last_strike_time'] > self.strike_reset_time):
            user['strikes'] = 0

        # Flood detection
        if current_time - user['last_msg_time'] < self.message_cooldown:
            user['strikes'] += 1
            user['last_strike_time'] = current_time
            user['last_msg_time'] = current_time

            if user['strikes'] >= self.max_strikes:
                user['banned'] = True
                self.bot.send_message(
                    user_id,
                    "💀 **BLACKLISTED.**\n\nYou made too much noise. You're cut off from the syndicate.",
                    parse_mode="Markdown"
                )
            else:
                self.bot.send_message(
                    user_id,
                    f"⚠️ **Watch your step.** You're moving too fast. Slow down.\n_Strike {user['strikes']}/{self.max_strikes}_", 
                    parse_mode="Markdown"
                )

            return CancelUpdate()

        user['last_msg_time'] = current_time

    def post_process(self, message, data, exception):
        pass

bot.setup_middleware(AntispamMiddleware(bot))

# --- SUPPORTED ASSETS ---
SUPPORTED_COINS = ["BTC", "ETH", "SOL", "BNB", "TON", "XRP", "DOGE"]

# --- COMMAND HANDLERS ---
@bot.message_handler(commands=['start', 'help'])
def handle_start(message):
    user_id = message.from_user.id
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
    bot.send_chat_action(message.chat.id, "typing")
    headlines = scrape_crypto_news()

    if not headlines:
        bot.reply_to(message, "Dead end. The informants are quiet right now.")
        return

    response = "👁️ WORD ON THE STREET:\n\n"
    for idx, title in enumerate(headlines, 1):
        response += f"{idx}. {title}\n\n"

    bot.reply_to(message, response)

@bot.message_handler(commands=['history', 'stats', 'ledger'])
def handle_stats(message):
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
    bot.reply_to(
        message,
        "You're digging too deep. Fall back before you get buried.",
        parse_mode="Markdown"
    )

@bot.message_handler(commands=['unban'])
def admin_unban(message):
    if message.from_user.id not in ADMIN_IDS:
        return

    try:
        target_id = int(message.text.split()[1])

        for middleware in bot.middlewares:
            if isinstance(middleware, AntispamMiddleware):
                if target_id in middleware.user_state:
                    middleware.user_state[target_id]['strikes'] = 0
                    middleware.user_state[target_id]['banned'] = False
                    bot.reply_to(message, f"✅ Access restored for `{target_id}`.", parse_mode="Markdown")
                else:
                    bot.reply_to(message, f"Target `{target_id}` not found in current memory cycle.", parse_mode="Markdown")
                return
    except (IndexError, ValueError):
        bot.reply_to(message, "Syntax: `/unban `", parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    if not message.text:
        bot.reply_to(message, "Watch your mouth. Only plaintext signals accepted.")
        return

    text = message.text.strip().upper()

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
        bot.infinity_polling(timeout=10, long_polling_timeout=5, skip_pending=True)
    except Exception as e:
        print(f"\n[!] SYSTEM FAILURE: {e}")
