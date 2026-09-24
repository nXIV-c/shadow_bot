# Shadow Syndicate Telegram Bot 🚀

An asynchronous Python Telegram bot for tracking real-time cryptocurrency rates, featuring built-in anti-spam protection and autonomous deployment on a Linux server.

## 🛠 Tech Stack
* **Language:** Python 3.11+
* **Framework:** `pyTelegramBotAPI` (`telebot`)
* **Database:** SQLite (for user tracking and rate limiting)
* **Infrastructure:** Linux (Ubuntu), `systemd` (24/7 auto-restart "reanimator")
* **Security:** Multi-stage flood/spam protection with a strike system, environment isolation via `.env`

## ✨ Core Features
* **Crypto Parser:** Fetches real-time market prices for key assets (BTC, ETH, SOL, BNB, TON, XRP, DOGE).
* **News Feeds:** Scrapes the latest crypto updates using `BeautifulSoup`.
* **Rate Limiter:** Built-in warning and blacklist system to prevent abuse and API overload.
* **Autonomous Operations:** Runs as a background system service with automatic recovery after server reboots or crashes.

## 🚀 Quick Start & Deployment

1. **Clone the repository:**
   ```bash
   git clone https://github.com/nXIV-c/shadow_bot.git
   cd shadow_bot
