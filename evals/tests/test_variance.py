"""Run-to-run variance: per-alert stability, gate miss in any repetition, pseudo-run spread (operations doc 1.2)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "evals"))

from metrics import CLOSE, ESCALATE  # noqa: E402
from variance import compute_variance, render_variance  # noqa: E402


def _row(alert, truth, scen, expected, proposed, repeat, conf=0.7):
    return {
        "alert_id": alert,
        "truth": truth,
        "injected_scenario": scen,
        "expected_disposition": expected,
        "proposed": proposed,
        "confidence": conf,
        "status": "ok",
        "duration_s": 30.0,
        "wall_s": 32.0,
        "input_tokens": 10,
        "output_tokens": 3000,
        "n_tool_calls": 10,
        "repeat": repeat,
    }


def test_plain_rows_give_no_variance_section():
    rows = [_row("a1", "FALSE_POSITIVE", "BACKGROUND", CLOSE, CLOSE, None)]
    assert compute_variance(rows) is None


def test_stability_flips_and_pseudo_runs():
    rows = []
    # a1: stable close; a2: flips once in three; s1: true abuse, stable escalate; s2: true abuse, closed once (!)
    for k in range(3):
        rows.append(_row("a1", "FALSE_POSITIVE", "BACKGROUND", CLOSE, CLOSE, k, 0.9))
        rows.append(_row("a2", "FALSE_POSITIVE", "F-STOP-1", CLOSE, ESCALATE if k == 1 else CLOSE, k, 0.6 + k / 10))
        rows.append(_row("s1", "TRUE_ABUSE", "S-SPOOF-1", ESCALATE, ESCALATE, k))
        rows.append(_row("s2", "TRUE_ABUSE", "S-SPOOF-5", ESCALATE, CLOSE if k == 2 else ESCALATE, k))
    v = compute_variance(rows)
    assert v["n_alerts"] == 4 and v["repeats"] == 3 and v["n_investigations"] == 12
    assert v["stable_alerts"] == 2 and v["stable_rate"] == 0.5
    assert [a["alert_id"] for a in v["unstable"]] == ["a2", "s2"]
    assert v["gate_miss_any"] == ["s2"]
    assert v["per_scenario"]["F-STOP-1"]["flips"] == 1 and v["per_scenario"]["F-STOP-1"]["flip_rate"] == round(1 / 3, 3)
    assert v["per_scenario"]["BACKGROUND"]["flips"] == 0
    # pseudo-runs: k=0 and k=1 hold the gate (safe close 2/2 and 1/2), k=2 misses it (safe close is n/a on a miss)
    gates = [p["gate_holds"] for p in v["pseudo_runs"]]
    assert gates == [True, True, False]
    assert v["pseudo_runs"][0]["safe_close_rate"] == 1.0 and v["pseudo_runs"][1]["safe_close_rate"] == 0.5
    assert v["safe_close_spread"]["min"] == 0.5 and v["safe_close_spread"]["max"] == 1.0
    a2 = next(a for a in v["per_alert"] if a["alert_id"] == "a2")
    assert a2["sequence"] == [CLOSE, ESCALATE, CLOSE] and a2["confidence_min"] == 0.6 and a2["confidence_max"] == 0.8
    md = "\n".join(render_variance(v))
    assert "s2" in md and "2 of 4" in md


def test_incomplete_repetition_is_not_a_pseudo_run():
    rows = [
        _row("a1", "FALSE_POSITIVE", "BACKGROUND", CLOSE, CLOSE, 0),
        _row("a2", "FALSE_POSITIVE", "BACKGROUND", CLOSE, CLOSE, 0),
        _row("a1", "FALSE_POSITIVE", "BACKGROUND", CLOSE, CLOSE, 1),  # a2's second repetition is missing
    ]
    v = compute_variance(rows)
    assert [p["repeat"] for p in v["pseudo_runs"]] == [0]
    assert v["stable_alerts"] == 2
