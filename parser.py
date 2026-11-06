import requests
from bs4 import BeautifulSoup
from database import save_price

NEWS_FEED_URL = "https://cointelegraph.com/rss"
NEWS_LIMIT = 5
# Kept from the first version: some news sites refuse unknown clients. If the feed
# still works with an honest name (e.g. "shadow-bot/1.1"), prefer that.
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/115.0.0.0 Safari/537.36"
)
_IGNORE_KEYWORDS = (
    "here's what happened in crypto today",
    "subscribe to",
    "weekly digest",
)


def fetch_binance_api(coin_symbol):
    """Fetch real-time price from Binance API."""
    symbol = f"{coin_symbol.upper()}USDT"
    url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"

    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()

        if "price" in data:
            price = float(data["price"])
            save_price(coin_symbol.upper(), price, "Binance API")
            return price
    except Exception as e:
        print(f"[!] API Error: {e}")
    return None


def parse_headlines(feed_xml, limit=NEWS_LIMIT):
    """Return up to ``limit`` clean, unique headlines from an RSS document."""
    soup = BeautifulSoup(feed_xml, "xml")
    headlines = []

    for item in soup.find_all("item"):
        title = item.find("title")
        if title:
            clean_title = title.text.strip()
            # News sites write "Here\u2019s" with a curly apostrophe; compare with a straight one.
            plain_title = clean_title.lower().replace("\u2019", "'")
            is_trash = any(kw in plain_title for kw in _IGNORE_KEYWORDS)

            if clean_title and not is_trash and clean_title not in headlines:
                headlines.append(clean_title)

        if len(headlines) == limit:
            break

    return headlines


def scrape_crypto_news():
    """Fetch top crypto news from the public RSS feed (reliable and fast)."""
    try:
        response = requests.get(NEWS_FEED_URL, headers={"User-Agent": _USER_AGENT}, timeout=5)
        response.raise_for_status()
        return parse_headlines(response.text)
    except Exception as e:
        print(f"[!] Scraping Error: {e}")
        return []


if __name__ == "__main__":
    print("=== CRYPTO DATA ENGINE ===")
    coin = input("Enter ticker (e.g. BTC): ")
    price = fetch_binance_api(coin)

    if price:
        print(f"[*] Fetched {coin.upper()} Price: ${price:,.2f} (Saved to DB)")

    print("\n=== LATEST CRYPTO NEWS (SCRAPED) ===")
    news = scrape_crypto_news()
    for idx, title in enumerate(news, 1):
        print(f"{idx}. {title}")
