"""Scoring rules from data doc section 4.2, checked on hand-built rows and on the committed dataset's baseline."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "evals"))

from metrics import CLOSE, DRAFT_STOR, ESCALATE, compute, regression, render_markdown, rows_from_labels  # noqa: E402

DATASET = ROOT / "data" / "synthetic" / "seed7"


def _row(alert, truth, scen, expected, proposed, conf=0.7, **kw):
    r = {
        "alert_id": alert,
        "truth": truth,
        "injected_scenario": scen,
        "expected_disposition": expected,
        "proposed": proposed,
        "confidence": conf if proposed else None,
        "status": "ok" if proposed else "no_proposal",
        "duration_s": 30.0,
        "wall_s": 32.0,
        "input_tokens": 40000,
        "output_tokens": 3000,
        "n_tool_calls": 10,
    }
    r.update(kw)
    return r


def test_gate_and_safe_close_rate():
    rows = [
        _row("a1", "TRUE_ABUSE", "S-SPOOF-1", ESCALATE, ESCALATE),
        _row("a2", "TRUE_ABUSE", "S-SPOOF-2", DRAFT_STOR, ESCALATE),  # under-call: safe, but an override
        _row("f1", "FALSE_POSITIVE", "F-MM-1", CLOSE, CLOSE),
        _row("f2", "FALSE_POSITIVE", "F-MM-1", CLOSE, ESCALATE),  # safe miss
        _row("f3", "FALSE_POSITIVE", "F-NEWS-1", CLOSE, None),  # nothing recorded
    ]
    m = compute(rows, model_id="eu.anthropic.claude-sonnet-5-5")
    assert m["gate"]["holds"] and m["gate"]["missed"] == []
    assert m["safe_close_rate"] == pytest.approx(1 / 3)
    assert m["escalation_precision"] == pytest.approx(2 / 3)
    assert m["strong_call_precision"] is None
    assert m["agreement"] == pytest.approx(2 / 5)
    assert m["override_rate"] == pytest.approx(3 / 5)
    assert m["direction_agreement"] == pytest.approx(3 / 5)  # a1, a2, f1; f3 has no direction
    assert m["status_counts"] == {"ok": 4, "no_proposal": 1}
    assert m["per_scenario"]["F-MM-1"]["close_rate"] == 0.5
    assert m["tokens"]["estimated_cost_usd"] == pytest.approx((5 * 40000 * 2 + 5 * 3000 * 10) / 1e6, abs=0.01)


def test_gate_failure_hides_safe_close_rate():
    rows = [
        _row("a1", "TRUE_ABUSE", "S-SPOOF-5", ESCALATE, CLOSE),
        _row("f1", "FALSE_POSITIVE", "F-MM-1", CLOSE, CLOSE),
    ]
    m = compute(rows)
    assert m["gate"] == {"holds": False, "missed": ["a1"], "unproposed_true_abuse": []}
    assert m["safe_close_rate"] is None and m["raw_safe_close_rate"] == 1.0
    assert m["true_abuse_recall"] == 0.0
    md = render_markdown({"run_id": "t", "metrics": m})
    assert "FAILED" in md and "n/a (gate failed: 1 missed" in md


def test_regression_rule():
    prev_rows = [
        _row("f1", "FALSE_POSITIVE", "F-MM-1", CLOSE, CLOSE),
        _row("f2", "FALSE_POSITIVE", "F-NEWS-1", CLOSE, CLOSE),
        _row("a1", "TRUE_ABUSE", "S-SPOOF-1", ESCALATE, ESCALATE),
    ]
    prev = {"run_id": "prev", "metrics": compute(prev_rows)}
    same = regression(compute(prev_rows), prev)
    assert same["verdict"].startswith("PASS")
    worse = [
        _row("f1", "FALSE_POSITIVE", "F-MM-1", CLOSE, CLOSE),
        _row("f2", "FALSE_POSITIVE", "F-NEWS-1", CLOSE, ESCALATE),  # F-NEWS-1 falls to 0% close
        _row("a1", "TRUE_ABUSE", "S-SPOOF-1", ESCALATE, ESCALATE),
    ]
    r = regression(compute(worse), prev)
    assert r["verdict"] == "FAIL"
    assert r["deltas"]["raw_safe_close_rate"] == pytest.approx(-0.5)
    assert any("F-NEWS-1" in name and not ok for name, ok in r["checks"])
    assert regression(compute(worse), None)["previous"] is None


@pytest.mark.skipif(not (DATASET / "labels" / "baseline.parquet").exists(), reason="dataset not built")
def test_threshold_baseline_matches_phase1_report():
    """Phase 1 recorded: raw safe close 96%, gate failed on 6 of 7 S-SPOOF-5 alerts (build plan, Phase 1)."""
    labels = pd.read_parquet(DATASET / "labels" / "labels.parquet").to_dict("records")
    base = pd.read_parquet(DATASET / "labels" / "baseline.parquet")
    m = compute(rows_from_labels(labels, dict(zip(base["alert_id"], base["baseline_disposition"], strict=True))))
    assert m["n"] == 167 and m["n_true_abuse"] == 28
    assert not m["gate"]["holds"]
    assert len(m["gate"]["missed"]) == 6
    assert all(a in m["per_scenario"]["S-SPOOF-5"]["missed"] for a in m["gate"]["missed"])
    assert m["raw_safe_close_rate"] == pytest.approx(0.96, abs=0.01)
    escalate_all = compute(rows_from_labels(labels, dict.fromkeys(base["alert_id"], ESCALATE)))
    assert escalate_all["gate"]["holds"] and escalate_all["safe_close_rate"] == 0.0
