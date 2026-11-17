"""The Streamlit app renders, gates on login, and (when local analyst credentials exist) shows the queue and a case.
No Runtime invocation here: that costs money and 35 s; `scripts/invoke_runtime.py` covers it."""

from __future__ import annotations

import os
import sys
from datetime import date
from pathlib import Path

import pytest

UI = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(UI))

from surv_client import CONFIG_FILE, Config  # noqa: E402

pytestmark = pytest.mark.skipif(not CONFIG_FILE.exists(), reason="no local analyst configuration")


def _creds() -> dict[str, str]:
    out = {}
    for line in CONFIG_FILE.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def test_config_loads_without_passwords():
    cfg = Config.load()
    assert cfg.region == "eu-west-2"
    assert cfg.api_url.startswith("https://")
    assert "PASSWORD" not in str(cfg)


def test_login_screen_renders():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(UI / "analyst_app.py"), default_timeout=60)
    at.run()
    assert not at.exception, at.exception
    assert any("Log in" in str(m.value) for m in at.markdown) or at.text_input, "login form expected"
    assert at.button(key="FormSubmitter:login-Log in") or at.text_input[0].label == "Analyst"


@pytest.mark.skipif(
    not os.environ.get("SURV_UI_LIVE"), reason="set SURV_UI_LIVE=1 to log in against Cognito and the API"
)
def test_logged_in_queue_and_case():
    from streamlit.testing.v1 import AppTest

    c = _creds()
    at = AppTest.from_file(str(UI / "analyst_app.py"), default_timeout=120)
    at.run()
    at.text_input[0].set_value(c["SURV_L1_USER"])
    at.text_input[1].set_value(c["SURV_L1_PASSWORD"])
    at.button[0].click()
    at.run()
    assert not at.exception, at.exception
    assert any("level L1" in str(s.value) for s in at.success), "logged-in banner"
    # The screen opens on today, whose queue may be empty (a weekend, a day after the dataset ends). The queue
    # and the case are checked on a day of the evaluated set, picked the way an analyst picks it.
    day = at.sidebar.selectbox[0]
    assert day.value == date.today().isoformat(), "a login opens on today"

    def iso(shown: str) -> str:  # the options are shown as DD-MM-YYYY, the first one with " (today)"
        d, m, y = shown.split(" ")[0].split("-")
        return f"{y}-{m}-{d}"

    assert max(iso(o) for o in day.options) == date.today().isoformat(), "no day after today is offered"
    day.set_value("2026-10-06")
    at.run()
    assert not at.exception, at.exception
    assert at.dataframe, "queue table rendered"
    assert any("Detector:" in str(m.value) for m in at.markdown), "a case opened"
