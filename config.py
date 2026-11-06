"""Settings read from environment variables (and an optional .env file)."""
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    bot_token: str
    admin_ids: frozenset[int]
    telegram_api_url: str | None  # optional reverse proxy, must contain {0} and {1}


def parse_admin_ids(raw: str) -> frozenset[int]:
    """Turn "123, 456" into {123, 456}. Anything that is not a number is an error."""
    ids = set()
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            ids.add(int(part))
        except ValueError:
            raise RuntimeError(f"ADMIN_IDS must contain numbers separated by commas, got {part!r}.") from None
    return frozenset(ids)


def load_settings() -> Settings:
    """Read the configuration. Raises RuntimeError with a human-readable message."""
    load_dotenv()

    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("BOT_TOKEN is not set. Create a .env file (see .env.example) and put the token there.")

    api_url = os.getenv("TELEGRAM_API_URL", "").strip() or None
    if api_url is not None and ("{0}" not in api_url or "{1}" not in api_url):
        raise RuntimeError("TELEGRAM_API_URL must contain the {0} and {1} placeholders (token and method).")

    return Settings(
        bot_token=token,
        admin_ids=parse_admin_ids(os.getenv("ADMIN_IDS", "")),
        telegram_api_url=api_url,
    )
