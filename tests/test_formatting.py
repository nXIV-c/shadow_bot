from formatting import format_ledger, format_price


def test_prices_get_a_currency_sign_and_separators():
    assert format_price(1234567.891) == "$1,234,567.89"


def test_a_value_that_is_not_a_number_is_shown_as_is():
    assert format_price("n/a") == "$n/a"


def test_the_ledger_shows_coin_then_price_then_time():
    rows = [("BTC", 66000.5, "Binance API", "2026-11-03 10:00:00")]
    text = format_ledger(rows)
    assert "• **BTC** | `$66,000.50` | `2026-11-03 10:00:00`" in text
    assert "Binance API" not in text  # the source is not part of the line
