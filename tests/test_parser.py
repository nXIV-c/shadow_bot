import pytest

import database
import parser as shadow_parser

FEED = """<?xml version="1.0"?>
<rss><channel>
<item><title>  Bitcoin hits a new high  </title></item>
<item><title>Here's what happened in crypto today</title></item>
<item><title>Bitcoin hits a new high</title></item>
<item><title>Subscribe to our newsletter</title></item>
<item><title>Ether upgrade ships</title></item>
<item><title></title></item>
<item><title>Solana outage explained</title></item>
</channel></rss>
"""


def test_headlines_are_cleaned_and_deduplicated():
    assert shadow_parser.parse_headlines(FEED) == [
        "Bitcoin hits a new high",
        "Ether upgrade ships",
        "Solana outage explained",
    ]


def test_trash_headlines_are_skipped_whatever_the_case():
    feed = "<rss><channel><item><title>WEEKLY DIGEST #5</title></item></channel></rss>"
    assert shadow_parser.parse_headlines(feed) == []


def test_trash_with_a_curly_apostrophe_is_skipped_too():
    feed = "<rss><channel><item><title>Here\u2019s what happened in crypto today</title></item></channel></rss>"
    assert shadow_parser.parse_headlines(feed) == []


def test_the_number_of_headlines_is_limited():
    items = "".join(f"<item><title>News {i}</title></item>" for i in range(20))
    assert len(shadow_parser.parse_headlines(f"<rss><channel>{items}</channel></rss>")) == 5
    assert len(shadow_parser.parse_headlines(f"<rss><channel>{items}</channel></rss>", limit=2)) == 2


class FakeResponse:
    def __init__(self, payload=None, error=None, text=""):
        self._payload, self._error, self.text = payload, error, text

    def raise_for_status(self):
        if self._error:
            raise self._error

    def json(self):
        return self._payload


@pytest.fixture
def db(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_NAME", str(tmp_path / "test.db"))
    database.init_db()
    return database


def test_a_price_is_returned_and_logged(db, monkeypatch):
    monkeypatch.setattr(shadow_parser.requests, "get", lambda *a, **k: FakeResponse({"price": "65000.10"}))
    assert shadow_parser.fetch_binance_api("btc") == 65000.10
    assert db.get_last_prices(1)[0][:3] == ("BTC", 65000.10, "Binance API")


def test_a_network_error_gives_none_and_logs_nothing(db, monkeypatch):
    def boom(*args, **kwargs):
        raise OSError("network down")

    monkeypatch.setattr(shadow_parser.requests, "get", boom)
    assert shadow_parser.fetch_binance_api("BTC") is None
    assert db.get_last_prices() == []


def test_a_reply_without_a_price_gives_none(db, monkeypatch):
    monkeypatch.setattr(shadow_parser.requests, "get", lambda *a, **k: FakeResponse({"code": -1121}))
    assert shadow_parser.fetch_binance_api("BTC") is None
    assert db.get_last_prices() == []


def test_news_failures_give_an_empty_list(monkeypatch):
    def boom(*args, **kwargs):
        raise OSError("network down")

    monkeypatch.setattr(shadow_parser.requests, "get", boom)
    assert shadow_parser.scrape_crypto_news() == []


def test_news_are_parsed_from_the_feed(monkeypatch):
    monkeypatch.setattr(shadow_parser.requests, "get", lambda *a, **k: FakeResponse(text=FEED))
    assert shadow_parser.scrape_crypto_news()[0] == "Bitcoin hits a new high"
