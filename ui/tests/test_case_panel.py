"""The case panel, driven with a fake human-path API: no Cognito, no Runtime, no AWS.

What it pins (decision log 2026-11-16): an undecided case offers the investigation and the record form and shows
where the proposal on file came from; a decided case offers neither; Level 2 gets a supersede form that needs an
explicit confirmation and then records with `supersede=True`; Level 1 is told only Level 2 can.
"""

from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest

UI = str(Path(__file__).resolve().parents[1])


def _panel(ui_dir: str, level: str, decided: bool, record_calls: list):
    import os
    import sys
    import types

    # the app reads its endpoints at import; none of them is called here
    for k, v in {
        "SURV_USER_POOL_ID": "eu-west-2_test",
        "SURV_CLIENT_ID": "client",
        "SURV_API_URL": "https://api.example.invalid",
        "SURV_RUNTIME_ARN": "arn:aws:bedrock-agentcore:eu-west-2:000000000000:runtime/test",
        "SURV_RUNTIME_LOG_GROUP": "/aws/bedrock-agentcore/runtimes/test-DEFAULT",
    }.items():
        os.environ.setdefault(k, v)
    sys.path.insert(0, ui_dir)
    import streamlit as st

    sys.modules.pop("analyst_app", None)
    import analyst_app  # main() runs at import and renders the login screen

    case = {
        "proposed_disposition": "ESCALATE",
        "confidence": 0.7,
        "proposed_at": "2026-11-16T10:00:00+00:00",
        "report": {"summary": "s", "evidence": [], "legitimate_explanations_considered": []},
        "proposal_provenance": {
            "session_id": "surv-A-1-abc",
            "analyst": "l1.analyst",
            "model_id": "eu.anthropic.claude-sonnet-5-5",
            "analyst_instruction": "look for a parent order",
        },
        "proposal_history": [
            {"disposition": "CLOSE_FP", "proposed_at": "2026-11-15T09:00:00+00:00", "session_id": "s0"}
        ],
    }
    if decided:
        case.update(
            recorded_disposition="ESCALATE",
            recorded_by="l1.analyst",
            recorded_at="2026-11-16T10:05:00+00:00",
            analyst_note="one-sided",
            decision_history=[
                {
                    "recorded_disposition": "CLOSE_FP",
                    "recorded_by": "l1.analyst",
                    "recorded_at": "2026-11-16T10:01:00+00:00",
                    "analyst_note": "mm",
                    "superseded_by": "l2.reviewer",
                    "superseded_at": "2026-11-16T10:05:00+00:00",
                    "superseded_note": "not a quote",
                }
            ],
        )

    class Api:
        def case(self, alert_id):
            alert = {
                "instrument": "SYN.A",
                "trader_id": "T-1",
                "scenario": "SPOOFING",
                "trigger": "OPPOSITE_FILL_CANCEL",
                "trigger_summary": "x",
            }
            return {"alert": alert, "case": case}

        def record(self, alert_id, disposition, note, supersede=False):
            record_calls.append((alert_id, disposition, note, supersede))
            return {"recorded_disposition": disposition, "superseded": "ESCALATE", "override": False}

        def feedback(self, alert_id, note):
            return {}

    st.session_state["alert_id"] = "A-1"
    sess = types.SimpleNamespace(level=level, username="u", groups=[level])
    analyst_app.case_panel(analyst_app.config(), sess, Api())


def _run(level: str, decided: bool):
    calls: list = []
    at = AppTest.from_function(_panel, args=(UI, level, decided, calls), default_timeout=60)
    at.run()
    assert not at.exception, at.exception
    text = " ".join(str(x.value) for x in [*at.markdown, *at.caption, *at.info, *at.warning, *at.success])
    return at, text, [b.label for b in at.button], calls


def test_undecided_case_offers_investigation_and_record_and_shows_provenance():
    _at, text, buttons, _ = _run("L1", decided=False)
    assert "Investigate again" in buttons and "Record disposition" in buttons
    assert "investigated by l1.analyst" in text and "look for a parent order" in text and "surv-A-1-abc" in text
    assert "Earlier proposals on this alert" in text


def test_decided_case_offers_neither_to_level_1():
    _at, text, buttons, _ = _run("L1", decided=True)
    assert not any("Investigate" in b for b in buttons)
    assert "Record disposition" not in buttons and "Supersede the decision" not in buttons
    assert "This alert is decided" in text and "Only Level 2 can supersede" in text
    assert "Superseded: **CLOSE_FP**" in text  # the decision that was replaced stays visible


def test_level_2_supersedes_only_with_the_confirmation_ticked():
    at, _text, buttons, calls = _run("L2", decided=True)
    assert "Supersede the decision" in buttons and not any("Investigate" in b for b in buttons)
    at.text_area[0].set_value("on review this was quoting")
    next(b for b in at.button if b.label == "Supersede the decision").click()
    at.run()
    assert not at.exception, at.exception
    assert calls == [] and any("tick the box" in str(e.value) for e in at.error)
    at.checkbox[0].check()
    at.text_area[0].set_value("on review this was quoting")
    next(b for b in at.button if b.label == "Supersede the decision").click()
    at.run()
    assert not at.exception, at.exception
    assert calls == [("A-1", "CLOSE_FP", "on review this was quoting", True)]
