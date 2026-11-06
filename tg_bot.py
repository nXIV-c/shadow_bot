import telebot
from telebot import apihelper, BaseMiddleware
from telebot.handler_backends import CancelUpdate

# Import custom modules
from antispam import AntiSpam, BAN, IGNORE, WARN
from config import load_settings
from database import init_db, add_user, get_last_prices
from formatting import format_ledger, format_price
from parser import fetch_binance_api, scrape_crypto_news

# --- SYSTEM INITIALIZATION ---
try:
    settings = load_settings()
except RuntimeError as exc:
    raise SystemExit(f"Configuration error: {exc}") from exc

# Optional reverse proxy for the Telegram API (for example a Cloudflare Worker).
if settings.telegram_api_url:
    apihelper.API_URL = settings.telegram_api_url

ADMIN_IDS = settings.admin_ids
bot = telebot.TeleBot(settings.bot_token, use_class_middlewares=True)

init_db()


# --- MIDDLEWARE: ANTI-SPAM & STRIKES ---
class AntispamMiddleware(BaseMiddleware):
    """Connects the AntiSpam rules to Telegram: drops flooding messages and warns the user."""

    def __init__(self, bot_instance, antispam=None):
        super().__init__()
        self.bot = bot_instance
        self.update_types = ['message']
        self.antispam = antispam or AntiSpam()

    def pre_process(self, message, data):
        verdict = self.antispam.check(message.from_user.id)

        if verdict.action == IGNORE:
            return CancelUpdate()

        if verdict.action == BAN:
            self.bot.send_message(
                message.from_user.id,
                "💀 **BLACKLISTED.**\n\nYou made too much noise. You're cut off from the syndicate.",
                parse_mode="Markdown"
            )
            return CancelUpdate()

        if verdict.action == WARN:
            self.bot.send_message(
                message.from_user.id,
                f"⚠️ **Watch your step.** You're moving too fast. Slow down.\n_Strike {verdict.strikes}/{self.antispam.max_strikes}_",
                parse_mode="Markdown"
            )
            return CancelUpdate()

    def post_process(self, message, data, exception):
        pass


antispam_middleware = AntispamMiddleware(bot)
bot.setup_middleware(antispam_middleware)

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

    bot.reply_to(message, format_ledger(records), parse_mode="Markdown")


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
    except (IndexError, ValueError):
        bot.reply_to(message, "Syntax: `/unban 123456789`", parse_mode="Markdown")
        return

    if antispam_middleware.antispam.unban(target_id):
        bot.reply_to(message, f"✅ Access restored for `{target_id}`.", parse_mode="Markdown")
    else:
        bot.reply_to(message, f"Target `{target_id}` not found in current memory cycle.", parse_mode="Markdown")


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
            formatted_price = f"{format_price(price)} USDT"

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
