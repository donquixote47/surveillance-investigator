"""An evaluation run gives each worker its own analyst (2026-11-18).

The Gateway allows each analyst 3 proposals a minute. Two workers under one analyst ask for nearly four, so the
proposals of a run sat on that limit: 79 of 169 invocations of run v6 met a 429. The limit is right for one analyst
working one alert at a time; what was wrong is one analyst doing two analysts' work.
"""

from __future__ import annotations

import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "evals"))

import run_dataset  # noqa: E402
from run_dataset import Tokens, analysts_of  # noqa: E402

ENV = {
    "SURV_L1_USER": "l1.analyst",
    "SURV_L1_PASSWORD": "x",
    "SURV_L1B_USER": "l1.analyst2",
    "SURV_L1B_PASSWORD": "x",
    "SURV_L1C_USER": "l1.nopassword",
    "SURV_L2_USER": "l2.reviewer",
    "SURV_L2_PASSWORD": "x",
    "SURV_CLIENT_ID": "c",
}


def _tokens_seen_by(tokens: Tokens, workers: int) -> list[tuple[str, str]]:
    """Each thread asks twice; returns (first, second) per thread, in thread order."""
    seen: list[tuple[str, str]] = [("", "")] * workers
    turn = threading.Semaphore(1)  # one thread at a time takes its analyst, so the order is the thread order

    def work(i: int) -> None:
        with turn:
            first = tokens.get()
        seen[i] = (first, tokens.get())

    threads = [threading.Thread(target=work, args=(i,)) for i in range(workers)]
    for t in threads:
        t.start()
        t.join()
    return seen


def test_the_analysts_of_a_level_are_read_from_the_credentials_file():
    assert analysts_of(ENV, "L1") == ["L1", "L1B"], "an analyst without a password is not usable"
    assert analysts_of(ENV, "L2") == ["L2"]
    assert analysts_of({}, "L1") == []


def test_each_worker_thread_keeps_its_own_analyst(monkeypatch):
    logins: list[str] = []

    def fake_login(env, user):
        logins.append(user)
        return f"token-of-{user}"

    monkeypatch.setattr(run_dataset, "access_token", fake_login)
    seen = _tokens_seen_by(Tokens(ENV, ["L1", "L1B"]), workers=2)
    assert seen == [("token-of-L1", "token-of-L1"), ("token-of-L1B", "token-of-L1B")]
    assert logins == ["L1", "L1B"], "one login per analyst; the second call of a thread reuses its token"

    # more workers than analysts: the analysts are shared round-robin, which is when proposals get throttled
    seen = _tokens_seen_by(Tokens(ENV, ["L1", "L1B"]), workers=3)
    assert [first for first, _ in seen] == ["token-of-L1", "token-of-L1B", "token-of-L1"]


def test_one_analyst_is_still_accepted(monkeypatch):
    monkeypatch.setattr(run_dataset, "access_token", lambda env, user: f"token-of-{user}")
    tokens = Tokens(ENV, "L2")
    assert tokens.user == "L2" and tokens.users == ["L2"]
    assert {first for first, _ in _tokens_seen_by(tokens, workers=2)} == {"token-of-L2"}
