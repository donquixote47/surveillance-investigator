"""The analyst screen opens on today and offers no day after today (decision log 2026-11-18).

A queue holds what the detector has already raised. The firm's tables hold session days up to 2026-11-27 (seed8),
so the rule is the screen's: a day appears when it arrives.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

UI = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(UI))

from session_days import DATASET_DATES, offered_days  # noqa: E402


def test_the_screen_opens_on_today_and_offers_nothing_later():
    days = offered_days("2026-11-18")
    assert days[0] == "2026-11-18"
    assert max(days) == "2026-11-18"
    assert days == sorted(days, reverse=True), "newest first, the way a queue reads"
    # every session day up to today is there, once; the later ones are in the tables and not on the screen
    assert days[1:] == [d for d in DATASET_DATES if d < "2026-11-18"]
    assert len(days) == len(set(days))
    assert not {"2026-11-19", "2026-11-27"} & set(days)


def test_today_is_offered_even_when_it_is_not_a_session_day():
    saturday = offered_days("2026-11-21")
    assert saturday[0] == "2026-11-21" and saturday[1] == "2026-11-20"
    after_the_dataset = offered_days("2026-12-15")
    assert after_the_dataset == ["2026-12-15", *DATASET_DATES]
    before_the_dataset = offered_days("2026-01-05")
    assert before_the_dataset == ["2026-01-05"]


def test_by_default_today_is_the_clock_of_the_machine():
    assert offered_days()[0] == date.today().isoformat()


def test_the_app_takes_its_days_from_this_rule_and_starts_a_login_on_today():
    """The app's source has no day list and no fixed opening day of its own, and a login drops the day an earlier
    visit left in the tab or in its URL."""
    src = (UI / "analyst_app.py").read_text()
    assert "offered_days()" in src
    assert "DATASET_DATES" not in src and "DEFAULT_DATE" not in src
    login = src[src.index('if st.form_submit_button("Log in"') : src.index("login failed")]
    assert '"date"' in login and "d=None" in login
