"""Report model rules, the guard's behaviour on propose_disposition, and alignment with the Gateway schema."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

APP = Path(__file__).resolve().parents[1]
SRC = APP.parents[1] / "src"
for p in (APP, SRC):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from investigator import PROPOSE, InvestigationGuard  # noqa: E402
from report import InvestigationReport  # noqa: E402

GOOD = {
    "alert_id": "A-261006-0006",
    "scenario": "SPOOFING",
    "summary": "A single 38,461-share bid, 15.7x top-5 depth, rested 2 ticks behind the touch for 2.9 s, during which the trader sold 1,423 shares; all 38,461 were cancelled 360 ms later and the mid reverted 1 tick.",
    "evidence": [
        {
            "id": "E1",
            "source": "compute_discriminators",
            "fact": "max_resting_size_vs_depth 15.70, distance_from_touch_ticks 2.0",
        },
        {
            "id": "E2",
            "source": "compute_discriminators",
            "fact": "opposite_side_fill_qty 1423, 360 ms before the first cancel",
        },
        {"id": "E3", "source": "get_trader_profile", "fact": "role PROP, registered_mm_instruments empty"},
        {"id": "E4", "source": "get_market_events", "fact": "no events within 60 s of the window"},
    ],
    "indicators_matched": [
        "orders with no intention to execute (Annex II 5(e))",
        "opposite-side execution before the cancel",
    ],
    "indicators_not_matched": ["several price levels on one side (layering)"],
    "legitimate_explanations_considered": [
        {"explanation": "market making", "ruled_out_by": ["E3"], "verdict": "ruled_out"},
        {"explanation": "reaction to a public event", "ruled_out_by": ["E4"], "verdict": "ruled_out"},
        {"explanation": "fat finger", "ruled_out_by": ["E2"], "verdict": "ruled_out"},
    ],
    "proposed_disposition": "ESCALATE",
    "confidence": 0.85,
    "what_would_change_my_mind": "A parent order or hedge instruction that explains the 38,461 bid.",
    "memory_used": [],
    "window_used": "12:49:41.863 to 12:50:49.339 (detector window); the trader's whole session was checked for repetitions (1 found).",
}


def test_good_report_validates():
    r = InvestigationReport.model_validate(GOOD)
    assert r.proposed_disposition == "ESCALATE"
    gw = r.for_gateway()
    assert "proposed_disposition" not in gw and "confidence" not in gw
    assert gw["evidence"][0]["source"] == "compute_discriminators"


def test_close_fp_needs_a_supported_explanation():
    bad = {**GOOD, "proposed_disposition": "CLOSE_FP"}
    with pytest.raises(ValueError, match="supported"):
        InvestigationReport.model_validate(bad)
    ok = {
        **GOOD,
        "proposed_disposition": "CLOSE_FP",
        "legitimate_explanations_considered": [
            {"explanation": "market making", "ruled_out_by": [], "verdict": "supported"}
        ],
    }
    assert InvestigationReport.model_validate(ok).proposed_disposition == "CLOSE_FP"


def test_escalate_with_supported_explanation_is_inconsistent():
    bad = {**GOOD, "legitimate_explanations_considered": [{"explanation": "market making", "verdict": "supported"}]}
    with pytest.raises(ValueError, match="inconsistent"):
        InvestigationReport.model_validate(bad)


def test_ruled_out_needs_evidence_and_known_ids():
    bad = {**GOOD, "legitimate_explanations_considered": [{"explanation": "market making", "verdict": "ruled_out"}]}
    with pytest.raises(ValueError, match="cites no evidence"):
        InvestigationReport.model_validate(bad)
    bad = {
        **GOOD,
        "legitimate_explanations_considered": [
            {"explanation": "market making", "ruled_out_by": ["E9"], "verdict": "ruled_out"}
        ],
    }
    with pytest.raises(ValueError, match="unknown evidence ids"):
        InvestigationReport.model_validate(bad)


def test_evidence_source_must_be_a_tool():
    bad = {
        **GOOD,
        "evidence": [*GOOD["evidence"][:2], {"id": "E3", "source": "my_intuition", "fact": "he looked guilty"}],
    }
    with pytest.raises(ValueError, match="source must be one of"):
        InvestigationReport.model_validate(bad)
    ok = {
        **GOOD,
        "evidence": [*GOOD["evidence"][:3], {"id": "E4", "source": "surv___get_market_events", "fact": "no events"}],
    }
    assert InvestigationReport.model_validate(ok).evidence[3].source == "get_market_events"


def test_report_fields_are_declared_on_the_gateway_schema():
    from tools.schema import TOOLS

    gw = next(t for t in TOOLS if t["name"] == "propose_disposition")["inputSchema"]["properties"]["report"][
        "properties"
    ]
    ours = InvestigationReport.model_json_schema()["properties"]
    missing = set(ours) - set(gw) - {"proposed_disposition", "confidence"}  # these two travel as separate tool inputs
    assert not missing, f"fields the agent sends that the Gateway schema does not declare: {sorted(missing)}"


class _Event:
    def __init__(self, name, inputs):
        self.tool_use = {"toolUseId": "t1", "name": name, "input": inputs}
        self.cancel_tool = False
        self.invocation_state = {}


def test_guard_rejects_bad_report_fills_tool_calls_and_blocks_second_proposal():
    g = InvestigationGuard(alert_id="A-261006-0006")
    for t in ("get_alert", "get_procedures", "compute_discriminators"):
        g.before_tool(_Event(f"surv___{t}", {"alert_id": "A-261006-0006"}))

    bad = _Event(
        PROPOSE,
        {"alert_id": "A-261006-0006", "disposition": "CLOSE_FP", "confidence": 0.9, "report": {"summary": "too short"}},
    )
    g.before_tool(bad)
    assert isinstance(bad.cancel_tool, str) and "report rejected" in bad.cancel_tool
    assert g.proposal is None and len(g.rejections) == 1

    report = {k: v for k, v in GOOD.items() if k not in ("proposed_disposition", "confidence")}
    good = _Event(
        PROPOSE, {"alert_id": "A-261006-0006", "disposition": "ESCALATE", "confidence": 0.85, "report": report}
    )
    g.before_tool(good)
    assert good.cancel_tool is False
    sent = good.tool_use["input"]["report"]
    assert sent["tool_calls"] == ["get_alert", "get_procedures", "compute_discriminators"]
    assert "proposed_disposition" not in sent
    assert g.proposal["disposition"] == "ESCALATE"

    wrong_alert = _Event(
        PROPOSE, {"alert_id": "A-000000-0001", "disposition": "ESCALATE", "confidence": 0.5, "report": report}
    )
    g2 = InvestigationGuard(alert_id="A-261006-0006")
    g2.before_tool(wrong_alert)
    assert "this investigation is for alert" in wrong_alert.cancel_tool

    second = _Event(
        PROPOSE, {"alert_id": "A-261006-0006", "disposition": "CLOSE_FP", "confidence": 0.5, "report": report}
    )
    g.before_tool(second)
    assert "already called" in second.cancel_tool


def test_guard_blocks_stor_draft_in_l1_mode():
    g = InvestigationGuard(alert_id="A-1", mode="investigate")
    ev = _Event("surv___draft_stor_narrative", {"alert_id": "A-1"})
    g.before_tool(ev)
    assert "Level-2" in ev.cancel_tool
    g2 = InvestigationGuard(alert_id="A-1", mode="stor_drafting")
    ev2 = _Event("surv___draft_stor_narrative", {"alert_id": "A-1"})
    g2.before_tool(ev2)
    assert ev2.cancel_tool is False
