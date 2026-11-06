"""Flood protection with strikes. Pure logic: no Telegram, so it is easy to test."""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Callable

OK = "ok"  # let the message through
WARN = "warn"  # too fast: drop the message and warn the user
BAN = "ban"  # last strike: drop the message and blacklist the user
IGNORE = "ignore"  # user is already blacklisted: drop silently

_PRUNE_ABOVE = 1000  # forget idle users once more than this many are stored


@dataclass(frozen=True)
class Verdict:
    action: str
    strikes: int


class AntiSpam:
    """Counts messages that arrive faster than ``cooldown`` seconds apart.

    ``max_strikes`` fast messages in a row blacklist the user (until ``unban``
    or a restart). Strikes expire after ``strike_reset`` seconds of good behaviour.
    """

    def __init__(
        self,
        cooldown: float = 3.0,
        strike_reset: float = 300.0,
        max_strikes: int = 3,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.cooldown = cooldown
        self.strike_reset = strike_reset
        self.max_strikes = max_strikes
        self._clock = clock
        self._users: dict[int, dict] = {}
        self._lock = threading.Lock()  # the bot handles messages in several threads

    def check(self, user_id: int) -> Verdict:
        now = self._clock()
        with self._lock:
            self._prune(now)
            user = self._users.setdefault(
                user_id, {"last_msg": None, "last_strike": 0.0, "strikes": 0, "banned": False}
            )

            if user["banned"]:
                return Verdict(IGNORE, user["strikes"])

            # Amnesty: strikes expire after a long period of good behaviour.
            if user["strikes"] and now - user["last_strike"] > self.strike_reset:
                user["strikes"] = 0

            too_fast = user["last_msg"] is not None and now - user["last_msg"] < self.cooldown
            user["last_msg"] = now
            if not too_fast:
                return Verdict(OK, user["strikes"])

            user["strikes"] += 1
            user["last_strike"] = now
            if user["strikes"] >= self.max_strikes:
                user["banned"] = True
                return Verdict(BAN, user["strikes"])
            return Verdict(WARN, user["strikes"])

    def unban(self, user_id: int) -> bool:
        """Lift a blacklist. False if the user is not known (e.g. after a restart)."""
        with self._lock:
            user = self._users.get(user_id)
            if user is None:
                return False
            user["strikes"] = 0
            user["banned"] = False
            return True

    def _prune(self, now: float) -> None:
        """Forget users who have been quiet for a while, so memory cannot grow forever."""
        if len(self._users) < _PRUNE_ABOVE:
            return
        stale = [
            uid
            for uid, user in self._users.items()
            if not user["banned"] and user["last_msg"] is not None and now - user["last_msg"] > self.strike_reset
        ]
        for uid in stale:
            del self._users[uid]
