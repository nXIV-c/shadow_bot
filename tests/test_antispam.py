from antispam import BAN, IGNORE, OK, WARN, AntiSpam


class Clock:
    """A clock the test moves by hand."""

    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now

    def wait(self, seconds):
        self.now += seconds


def make(**kwargs):
    clock = Clock()
    return AntiSpam(clock=clock, **kwargs), clock


def test_the_first_message_is_always_fine():
    spam, _ = make()
    assert spam.check(1).action == OK


def test_a_message_after_the_cooldown_is_fine():
    spam, clock = make(cooldown=3)
    spam.check(1)
    clock.wait(3)
    assert spam.check(1).action == OK


def test_a_fast_message_gets_a_warning_with_a_strike():
    spam, clock = make(cooldown=3)
    spam.check(1)
    clock.wait(1)
    verdict = spam.check(1)
    assert (verdict.action, verdict.strikes) == (WARN, 1)


def test_the_third_fast_message_blacklists_the_user():
    spam, clock = make(cooldown=3, max_strikes=3)
    spam.check(1)
    actions = []
    for _ in range(3):
        clock.wait(1)
        actions.append(spam.check(1).action)
    assert actions == [WARN, WARN, BAN]


def test_a_blacklisted_user_is_ignored_even_after_waiting():
    spam, clock = make(cooldown=3, max_strikes=1)
    spam.check(1)
    clock.wait(1)
    assert spam.check(1).action == BAN
    clock.wait(3600)
    assert spam.check(1).action == IGNORE


def test_users_are_counted_separately():
    spam, clock = make(cooldown=3, max_strikes=1)
    spam.check(1)
    spam.check(2)
    clock.wait(1)
    assert spam.check(1).action == BAN
    assert spam.check(3).action == OK


def test_strikes_expire_after_good_behaviour():
    spam, clock = make(cooldown=3, strike_reset=300, max_strikes=3)
    spam.check(1)
    clock.wait(1)
    assert spam.check(1).strikes == 1
    clock.wait(301)
    assert spam.check(1).action == OK
    clock.wait(1)
    assert spam.check(1).strikes == 1  # counting started again from zero


def test_unban_restores_access():
    spam, clock = make(cooldown=3, max_strikes=1)
    spam.check(1)
    clock.wait(1)
    spam.check(1)
    assert spam.unban(1) is True
    clock.wait(10)
    assert spam.check(1).action == OK


def test_unban_of_an_unknown_user_reports_false():
    spam, _ = make()
    assert spam.unban(42) is False


def test_idle_users_are_forgotten_but_bans_are_kept(monkeypatch):
    import antispam

    monkeypatch.setattr(antispam, "_PRUNE_ABOVE", 5)
    spam, clock = make(cooldown=3, strike_reset=300, max_strikes=1)
    spam.check(999)
    clock.wait(1)
    spam.check(999)  # user 999 is now blacklisted
    for user_id in range(10):
        spam.check(user_id)
    clock.wait(1000)
    spam.check(12345)  # triggers the cleanup
    assert len(spam._users) < 11
    assert spam.check(999).action == IGNORE
