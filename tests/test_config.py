import pytest

from config import load_settings, parse_admin_ids
import config


@pytest.fixture
def env(monkeypatch):
    for name in ("BOT_TOKEN", "ADMIN_IDS", "TELEGRAM_API_URL"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(config, "load_dotenv", lambda *args, **kwargs: None)
    return monkeypatch


def test_the_token_is_required(env):
    with pytest.raises(RuntimeError, match="BOT_TOKEN"):
        load_settings()


def test_a_blank_token_is_rejected(env):
    env.setenv("BOT_TOKEN", "   ")
    with pytest.raises(RuntimeError, match="BOT_TOKEN"):
        load_settings()


def test_defaults(env):
    env.setenv("BOT_TOKEN", "1:abc")
    settings = load_settings()
    assert settings.bot_token == "1:abc"
    assert settings.admin_ids == frozenset()
    assert settings.telegram_api_url is None


def test_admin_ids_are_parsed(env):
    env.setenv("BOT_TOKEN", "1:abc")
    env.setenv("ADMIN_IDS", "10, 20,,30")
    assert load_settings().admin_ids == frozenset({10, 20, 30})


def test_bad_admin_ids_are_an_error():
    with pytest.raises(RuntimeError, match="ADMIN_IDS"):
        parse_admin_ids("10, abc")


def test_the_api_proxy_needs_both_placeholders(env):
    env.setenv("BOT_TOKEN", "1:abc")
    env.setenv("TELEGRAM_API_URL", "https://example.workers.dev/bot{0}")
    with pytest.raises(RuntimeError, match="TELEGRAM_API_URL"):
        load_settings()


def test_the_api_proxy_without_the_token_placeholder_is_rejected(env):
    env.setenv("BOT_TOKEN", "1:abc")
    env.setenv("TELEGRAM_API_URL", "https://example.workers.dev/{1}")
    with pytest.raises(RuntimeError, match="TELEGRAM_API_URL"):
        load_settings()


def test_a_valid_api_proxy_is_accepted(env):
    env.setenv("BOT_TOKEN", "1:abc")
    env.setenv("TELEGRAM_API_URL", "https://example.workers.dev/bot{0}/{1}")
    assert load_settings().telegram_api_url == "https://example.workers.dev/bot{0}/{1}"
