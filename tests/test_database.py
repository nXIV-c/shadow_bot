import pytest

import database


@pytest.fixture
def db(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_NAME", str(tmp_path / "test.db"))
    database.init_db()
    return database


def test_prices_come_back_newest_first_with_all_columns(db):
    db.save_price("BTC", 100.0, "Binance API")
    db.save_price("ETH", 5.0, "Binance API")
    rows = db.get_last_prices(limit=5)
    assert [row[0] for row in rows] == ["ETH", "BTC"]
    assert rows[0][1] == 5.0
    assert rows[0][2] == "Binance API"
    assert len(rows[0]) == 4


def test_the_limit_is_respected(db):
    for i in range(10):
        db.save_price("BTC", float(i), "x")
    assert len(db.get_last_prices(limit=3)) == 3


def test_the_same_user_is_stored_once(db):
    db.add_user(1, "alice")
    db.add_user(1, "alice-renamed")
    import sqlite3

    conn = sqlite3.connect(db.DB_NAME)
    assert conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 1
    conn.close()


def test_old_prices_are_trimmed(db):
    for i in range(30):
        db.save_price("BTC", float(i), "x")
    db.trim_prices(keep=10)
    rows = db.get_last_prices(limit=100)
    assert len(rows) == 10
    assert rows[0][1] == 29.0  # the newest survived


def test_trimming_an_empty_table_is_fine(db):
    db.trim_prices(keep=10)
    assert db.get_last_prices() == []
