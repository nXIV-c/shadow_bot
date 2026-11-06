"""Text of the bot's replies that depends on data (kept apart from Telegram so it can be tested)."""


def format_price(value):
    """12345.6 -> "$12,345.60". Falls back to the raw value if it is not a number."""
    try:
        return f"${float(value):,.2f}"
    except (ValueError, TypeError):
        return f"${value}"


def format_ledger(rows):
    """Format rows of ``(coin_name, price_usd, source, created_at)`` for /history."""
    lines = ["📓 **THE LEDGER (RECENT DROPS):**\n"]
    for coin_name, price_usd, _source, created_at in rows:
        lines.append(f"• **{coin_name}** | `{format_price(price_usd)}` | `{created_at}`")
    return "\n".join(lines) + "\n"
