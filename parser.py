import requests
from bs4 import BeautifulSoup
from database import save_price


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


def scrape_crypto_news():
    """Scrape top crypto news using RSS feed (reliable & fast)."""
    url = "https://cointelegraph.com/rss"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/115.0.0.0 Safari/537.36"
        )
    }

    ignore_keywords = [
        "here's what happened in crypto today",
        "subscribe to",
        "weekly digest",
    ]

    try:
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "xml")
        headlines = []

        for item in soup.find_all("item"):
            title = item.find("title")
            if title:
                clean_title = title.text.strip()
                is_trash = any(
                    kw in clean_title.lower() for kw in ignore_keywords
                )

                if not is_trash and clean_title not in headlines:
                    headlines.append(clean_title)

            if len(headlines) == 5:
                break

        return headlines

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
