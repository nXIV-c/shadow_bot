# SHADOW // PLUG — crypto price Telegram bot

A small Telegram bot with a "syndicate" personality. Send it a ticker and it replies with the live price from Binance; ask for `/news` and it returns the latest crypto headlines from a public RSS feed. It has built-in flood protection and runs as a background service on a Linux server.

## Features

- **Live prices** for BTC, ETH, SOL, BNB, TON, XRP and DOGE (Binance public API, no API key needed).
- **`/news`** — the five latest headlines from the Cointelegraph RSS feed (junk such as digests and newsletter ads is filtered out).
- **`/history`** — the five most recent price lookups from the local SQLite log.
- **Anti-spam with strikes** — messages faster than one per 3 seconds earn a warning; three strikes in a row blacklist the user until an admin runs `/unban <user_id>` (or the bot restarts). Strikes expire after 5 minutes of good behaviour.
- **Runs unattended** — a `systemd` service restarts it after crashes and reboots.

## Tech stack

| Area | Technology |
|---|---|
| Language | Python 3.10+ |
| Telegram | `pyTelegramBotAPI` (synchronous, handles messages in threads) |
| Data | `requests`, `beautifulsoup4` + `lxml` (RSS), SQLite (`sqlite3`) |
| Config | environment variables / `.env` (`python-dotenv`) |
| Tests | `pytest` |

## Project layout

| File | Responsibility |
|---|---|
| `tg_bot.py` | Telegram handlers and wiring |
| `antispam.py` | Flood protection rules (pure logic, no Telegram — easy to test) |
| `parser.py` | Binance price lookup and RSS headline parsing |
| `database.py` | SQLite storage: users and price log (the log keeps the newest 1000 rows) |
| `formatting.py` | Text of replies that depends on data |
| `config.py` | Reads and validates settings |
| `tests/` | Unit tests |

## Setup

```bash
git clone https://github.com/nXIV-c/shadow_bot.git
cd shadow_bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # then edit .env
python tg_bot.py
```

### Configuration (`.env`)

| Variable | Required | Meaning |
|---|---|---|
| `BOT_TOKEN` | yes | Token from [@BotFather](https://t.me/BotFather). The bot refuses to start without it. |
| `ADMIN_IDS` | no | Comma-separated Telegram user IDs allowed to use `/unban`. |
| `TELEGRAM_API_URL` | no | Reverse proxy for the Telegram API (for example a Cloudflare Worker). Must contain `{0}` (token) and `{1}` (method), e.g. `https://my-worker.example.workers.dev/bot{0}/{1}`. |

The `.env` file is listed in `.gitignore` and must never be committed.

## Running as a service (systemd)

Example unit, `/etc/systemd/system/shadow_bot.service`. It runs the bot as a normal user instead of `root`:

```ini
[Unit]
Description=SHADOW // PLUG Telegram bot
After=network-online.target
Wants=network-online.target

[Service]
User=shadowbot
WorkingDirectory=/opt/shadow_bot
ExecStart=/opt/shadow_bot/venv/bin/python tg_bot.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now shadow_bot
journalctl -u shadow_bot -f      # follow the log
```

## Tests

```bash
pip install -r requirements-dev.txt
python -m pytest -q
```

The tests cover the anti-spam rules (with a fake clock), configuration checks, the database, price and news parsing (network replaced by fakes) and reply formatting.

## Security notes

- The token lives only in `.env` / the environment, never in the code.
- All SQL uses bound parameters. Ticker symbols are checked against a fixed allow-list before any request is made.
- `/unban` silently ignores everyone who is not in `ADMIN_IDS`.
- The anti-spam state is kept in memory, so blacklists reset when the bot restarts.
- The bot is public by design (anyone can ask for a price). It stores each user's Telegram ID and username for as long as the database file exists.

## Known limitations

- Binance may refuse requests from some countries; the bot then answers that it could not pull the numbers.
- The news feed belongs to a third party and can change or block requests at any time.
- Price logs are shared by all users (`/history` shows the last lookups of everyone, without names).
