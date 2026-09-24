import sqlite3

DB_NAME = "bot_users.db"

def init_db():
    """Initialize the SQLite database and create required tables."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE,
        username TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS prices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        coin_name TEXT,
        price_usd REAL,
        source TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()

def add_user(user_id, username):
    """Store unique Telegram users in the database."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)",
        (user_id, username)
    )
    conn.commit()
    conn.close()

def save_price(coin_name, price_usd, source):
    """Log successfully fetched cryptocurrency price query."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO prices (coin_name, price_usd, source) VALUES (?, ?, ?)",
        (coin_name, price_usd, source)
    )
    conn.commit()
    conn.close()

def get_last_prices(limit=5):
    """Retrieve the most recent price logs from the database."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT coin_name, price_usd, source, created_at FROM prices ORDER BY id DESC LIMIT ?",
        (limit,)
    )
    rows = cursor.fetchall()
    conn.close()
    return rows
