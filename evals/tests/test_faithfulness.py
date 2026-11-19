"""Evidence faithfulness: numbers and categorical claims in a fact must appear in the tool outputs (data doc 4.2)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "evals"))

from faithfulness import (  # noqa: E402
    check_alert,
    check_categorical,
    check_fact,
    has_proposal_call,
    numbers_in,
    summarize,
)
from metrics import regression  # noqa: E402

GROUND = (
    '{"trader_id": "T-X1104-10", "desk": "PROP-EQ", "role": "PROP", "registered_mm_instruments": [], '
    '"typical_order_size": 500}\n'
    '{"order_types": ["LIMIT", "MARKET"], "max_resting_size_vs_depth": 15.7, "opposite_side_fill_qty": 1423, '
    '"ms_before_first_cancel": 360.5}\n'
    "NEW BUY LIMIT O-00019290 qty 38461 at 9994 at 12:50:39.339"
)
GROUND_MM = GROUND.replace(
    '"role": "PROP", "registered_mm_instruments": []', '"role": "MARKET_MAKER", "registered_mm_instruments": ["SYN.A"]'
)


def test_numbers_grounded_and_not():
    n, un = check_fact("38,461 shares at 15.7x depth, 1423 filled 360 ms before the cancel", GROUND, numbers_in(GROUND))
    assert n == 4 and un == []
    n, un = check_fact("a 40,000-share order at 15.7x depth", GROUND, numbers_in(GROUND))
    assert un == ["40,000"]


def test_categorical_positive_claims_must_be_in_the_tool_outputs():
    _c, un = check_categorical("role PROP on desk PROP-EQ, LIMIT and MARKET orders only", GROUND)
    assert _c == 4 and un == []
    _c, un = check_categorical("the trader is a MARKET_MAKER on the ETF-MM desk", GROUND)
    assert sorted(un) == ["ETF-MM", "MARKET_MAKER"]
    _c, un = check_categorical("a PEGGED order was re-priced three times", GROUND)
    assert un == ["PEGGED"]


def test_categorical_negated_claims_are_not_checked():
    _c, un = check_categorical("no PEGGED or ICEBERG orders; LIMIT only", GROUND)
    assert un == [] and _c == 1  # LIMIT is the only positive assertion
    _c, un = check_categorical("order types LIMIT only, not MARKET_MAKER quoting", GROUND)
    assert un == []


def test_registration_claim_matches_the_profile():
    # fact says not registered, profile list is empty: fine
    _c, un = check_categorical("role PROP, registered_mm_instruments empty", GROUND)
    assert un == []
    _c, un = check_categorical("not a registered market maker on SYN.A", GROUND)
    assert un == []
    # fact says registered, profile list is empty: caught
    _c, un = check_categorical("registered market maker on SYN.A quoting both sides", GROUND)
    assert un == ["registered"]
    # fact says not registered, profile says registered: caught
    _c, un = check_categorical("role MARKET_MAKER but no registration on SYN.A", GROUND_MM)
    assert "not registered" in un
    # fact says registered, profile agrees: fine
    _c, un = check_categorical("registered MARKET_MAKER on SYN.A", GROUND_MM)
    assert un == []


def _span(tool: str, result: str) -> dict:
    return {"name": f"mcp tools/call surv___{tool}", "attributes": {"gen_ai.tool.call.result": result}}


REPORT = {
    "evidence": [{"id": "E1", "source": "get_trader_profile", "fact": "role MARKET_MAKER, typical_order_size 3642"}]
}
EARLY = [_span("get_alert", '{"alert_id": "A-1", "trigger": "OPPOSITE_FILL_CANCEL"}')]
ALL_IN = [
    *EARLY,
    _span("get_trader_profile", '{"role": "MARKET_MAKER", "typical_order_size": 3642}'),
    _span("propose_disposition", '{"alert_id": "A-1", "status": "PROPOSED"}'),
]


class _Collector:
    """Returns one list of spans per call, the last one from then on: CloudWatch as the telemetry arrives."""

    def __init__(self, *arrivals: list[dict]):
        self.arrivals = list(arrivals)
        self.calls = 0

    def collect(self, **_kw) -> list[dict]:
        self.calls += 1
        return self.arrivals[min(self.calls, len(self.arrivals)) - 1]


def test_a_session_whose_spans_are_not_all_in_is_read_again():
    """2026-11-19: the check ran three minutes after a run ended, the last two sessions had half their spans, and
    twelve numbers and three roles the tools had returned were counted as unmatched (promotion rule: FAIL). The
    report goes out through `propose_disposition`, the last call; without its span the session is not all in."""
    assert has_proposal_call(ALL_IN) and not has_proposal_call(EARLY)
    naps: list[float] = []
    collector = _Collector(EARLY, EARLY, ALL_IN)
    res = check_alert("A-1", "session", REPORT, collector, wait_s=240, pause_s=20, sleep=naps.append)
    assert collector.calls == 3 and naps == [20, 20]
    assert res["complete"] and res["faithful"] and res["numbers_unmatched"] == 0 and res["categorical_unmatched"] == 0


def test_a_session_that_stays_incomplete_is_not_scored_and_the_verdict_waits():
    naps: list[float] = []
    collector = _Collector(EARLY)
    late = check_alert("A-2", "session", REPORT, collector, wait_s=40, pause_s=20, sleep=naps.append)
    assert naps == [20, 20] and collector.calls == 3
    assert not late["complete"] and not late["faithful"]
    assert late["numbers_unmatched"] == 1, "what the half-read session would have been charged with"

    done = check_alert("A-1", "session", REPORT, _Collector(ALL_IN), sleep=naps.append)
    summary = summarize([done, late], {})
    assert summary["n_incomplete"] == 1 and summary["incomplete"] == ["A-2"]
    assert summary["n_with_report"] == 1 and summary["numbers_unmatched"] == 0 and summary["number_rate"] == 1.0
    assert summary["offenders"] == []

    rows = [
        {
            "alert_id": "f1",
            "truth": "FALSE_POSITIVE",
            "injected_scenario": "F-MM-1",
            "expected_disposition": "CLOSE_FP",
            "proposed": "CLOSE_FP",
            "confidence": 0.7,
            "status": "ok",
        }
    ]
    from metrics import compute

    m = compute(rows)
    verdict = regression(m, {"run_id": "prev", "metrics": m}, current_faith=summary)["verdict"]
    assert verdict == "PASS (offline promotion rule, faithfulness pending)"
    summary["n_incomplete"] = 0
    assert (
        regression(m, {"run_id": "prev", "metrics": m}, current_faith=summary)["verdict"]
        == "PASS (offline promotion rule)"
    )


def test_a_session_without_a_report_does_not_wait():
    collector = _Collector(EARLY)
    res = check_alert(
        "A-3", "session", None, collector, sleep=lambda _s: (_ for _ in ()).throw(AssertionError("waited"))
    )
    assert collector.calls == 1 and res["complete"] and not res["faithful"]


def test_sessions_scored_before_the_field_existed_are_kept_as_scored():
    old = {
        "alert_id": "A-0",
        "has_report": True,
        "ground_chars": 10,
        "numbers_checked": 5,
        "numbers_unmatched": 1,
        "faithful": False,
        "facts": [],
    }
    summary = summarize([old], {})
    assert summary["n_incomplete"] == 0 and summary["numbers_checked"] == 5 and summary["numbers_unmatched"] == 1
