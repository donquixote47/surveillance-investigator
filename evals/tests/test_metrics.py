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
        *_scenario("F-NEWS-1", 3, closed=3),
        _row("a1", "TRUE_ABUSE", "S-SPOOF-1", ESCALATE, ESCALATE),
    ]
    prev = {"run_id": "prev", "metrics": compute(prev_rows)}
    same = regression(compute(prev_rows), prev)
    assert same["verdict"].startswith("PASS")
    worse = [
        _row("f1", "FALSE_POSITIVE", "F-MM-1", CLOSE, CLOSE),
        *_scenario("F-NEWS-1", 3, closed=0),  # F-NEWS-1 falls from 3/3 to 0% close
        _row("a1", "TRUE_ABUSE", "S-SPOOF-1", ESCALATE, ESCALATE),
    ]
    r = regression(compute(worse), prev)
    assert r["verdict"] == "FAIL"
    assert r["deltas"]["raw_safe_close_rate"] == pytest.approx(-3 / 4, abs=1e-3)
    assert any("F-NEWS-1" in name and not ok for name, ok in r["checks"])
    assert regression(compute(worse), None)["previous"] is None


def _scenario(scen: str, n: int, closed: int) -> list[dict]:
    """A false-positive scenario of `n` alerts of which the agent proposed to close `closed`."""
    return [_row(f"{scen}-{i}", "FALSE_POSITIVE", scen, CLOSE, CLOSE if i < closed else ESCALATE) for i in range(n)]


def _third_check(prev_rows: list[dict], cur_rows: list[dict]) -> tuple[str, bool]:
    r = regression(compute(cur_rows), {"run_id": "prev", "metrics": compute(prev_rows)})
    return next(c for c in r["checks"] if c[0].startswith("no false-positive scenario regressed"))


@pytest.mark.parametrize(
    ("n", "closed_before", "counts"),
    [
        (6, 1, False),  # v2 -> v3, F-STOP-1: the first floor (2 alerts, a quarter) was written for this one
        (6, 2, False),  # v7 -> v8, F-STOP-1: one agent version, measured twice, PASS then FAIL under that floor
        (6, 4, False),
        (6, 5, True),
        (4, 3, False),  # F-NEWS-1 closes three of its four alerts in one run of nine by chance
        (4, 4, True),
        (3, 2, False),
        (3, 3, True),  # F-FAT-1, F-RISK-1
        (5, 4, True),  # four in five is "at least"
        (24, 19, False),
        (24, 20, True),
        (2, 2, False),  # two alerts are not a scenario the agent closes steadily, whatever their rate
    ],
)
def test_a_fall_to_zero_counts_only_for_a_scenario_the_previous_run_closed_steadily(n, closed_before, counts):
    """The third check of the promotion rule speaks for the scenarios the agent closes nearly always: the previous
    run closed at least 3 of the scenario's alerts and at least four in five of them. Below that, a fall to 0% on
    four to six alerts is what an unchanged agent does by chance, and the scenario is judged on the variance run."""
    name, ok = _third_check(_scenario("F-X-1", n, closed_before), _scenario("F-X-1", n, 0))
    assert ok is not counts
    if counts:
        assert name == "no false-positive scenario regressed to 0% close (F-X-1)"
    else:
        assert name == (
            "no false-positive scenario regressed to 0% close "
            f"(none; below the floor, read the variance run: F-X-1 ({closed_before}/{n} -> 0/{n}))"
        ), "a fall the check does not judge is still shown"


def test_the_third_check_sees_a_collapse_that_gains_elsewhere_hide():
    """What the check is for. A scenario of three alerts that stops closing costs 2 points of safe close rate, and
    a change that closes three more alerts somewhere else hides it from the second check."""
    prev_rows = [*_scenario("BACKGROUND", 30, closed=27), *_scenario("F-FAT-1", 3, closed=3)]
    cur_rows = [*_scenario("BACKGROUND", 30, closed=30), *_scenario("F-FAT-1", 3, closed=0)]
    r = regression(compute(cur_rows), {"run_id": "prev", "metrics": compute(prev_rows)})
    assert r["deltas"]["raw_safe_close_rate"] == 0
    checks = dict(r["checks"])
    assert checks["safe close rate not down by more than 2 points"] is True
    assert checks["no false-positive scenario regressed to 0% close (F-FAT-1)"] is False
    assert r["verdict"] == "FAIL"


def test_the_floor_is_out_of_reach_of_the_scenarios_the_agent_closes_now_and_then():
    """Why four in five, from the runs and not from a model. Alert by alert over the nine runs since v4 (five full
    runs and four variance runs, 2026-11-10 to 2026-11-19; data doc 4.6), F-STOP-1 is three alerts never proposed
    for closing in 45 investigations and three closed about one time in four, and F-NEWS-1 is two alerts never
    closed in 35 investigations and two that are. A run reaches the floor on such a scenario only if an alert that
    was never closed is closed. The floor of half that was proposed first is within F-STOP-1's reach: its three
    closable alerts in one run. (A test here first recomputed "1 comparison in 6" and "1 in 350" from a rate per
    scenario; the alerts of a scenario are not alike, and those figures were withdrawn on 2026-11-19.)"""
    from math import ceil

    from metrics import ZERO_FLOOR_N, ZERO_FLOOR_RATE

    ever_closed = {"F-STOP-1": (3, 6), "F-NEWS-1": (2, 4)}  # alerts ever proposed CLOSE_FP, alerts of the scenario

    def needed(n: int, floor_n: int, floor_rate: float) -> int:
        return max(floor_n, ceil(floor_rate * n - 1e-9))

    for scenario, (closable, n) in ever_closed.items():
        assert closable < needed(n, ZERO_FLOOR_N, ZERO_FLOOR_RATE), scenario
    assert ever_closed["F-STOP-1"][0] >= needed(6, 3, 0.5), "half is reachable by F-STOP-1"
    assert ever_closed["F-NEWS-1"][0] < needed(4, 3, 0.5), "and not by F-NEWS-1, whatever was written on 2026-11-18"


def test_promotion_rule_checks_faithfulness_once_it_has_run():
    """The fourth check of the promotion rule (data doc 4.4) was written down and never coded: the verdict only
    said "faithfulness pending". It is a floor (99% of numbers traced to a tool output) and a maximum fall of half
    a point against the previous run; the history of the promoted runs (99.76, 99.91, 99.88, 99.90) passes."""
    rows = [
        _row("f1", "FALSE_POSITIVE", "F-MM-1", CLOSE, CLOSE),
        _row("a1", "TRUE_ABUSE", "S-SPOOF-1", ESCALATE, ESCALATE),
    ]
    m = compute(rows)
    prev = {"run_id": "prev", "metrics": m, "faithfulness": {"numbers_checked": 4221, "number_rate": 0.9991}}

    pending = regression(m, prev)
    assert pending["verdict"] == "PASS (offline promotion rule, faithfulness pending)" and len(pending["checks"]) == 3

    ok = regression(m, prev, current_faith={"numbers_checked": 4132, "number_rate": 0.9988})  # v2 -> v3
    assert ok["verdict"] == "PASS (offline promotion rule)" and len(ok["checks"]) == 4
    assert "99.88% of 4132 numbers, previous 99.91%" in ok["checks"][-1][0]

    below_floor = regression(m, prev, current_faith={"numbers_checked": 4000, "number_rate": 0.985})
    assert below_floor["verdict"] == "FAIL" and below_floor["checks"][-1][1] is False

    fell = regression(
        m,
        {**prev, "faithfulness": {"numbers_checked": 4000, "number_rate": 0.999}},
        current_faith={"numbers_checked": 4000, "number_rate": 0.992},  # above the floor, down 0.7 points
    )
    assert fell["verdict"] == "FAIL"

    invented_role = regression(
        m,
        prev,
        current_faith={
            "numbers_checked": 4096,
            "number_rate": 0.999,
            "categorical_checked": 615,
            "categorical_rate": 0.97,
        },
    )
    assert invented_role["verdict"] == "FAIL"

    first_checked = regression(
        m, {"run_id": "prev", "metrics": m}, current_faith={"numbers_checked": 10, "number_rate": 1.0}
    )
    assert first_checked["verdict"].startswith("PASS") and "previous run not checked" in first_checked["checks"][-1][0]


def test_alerts_decided_before_the_run_are_listed_and_not_scored(tmp_path):
    """A decided case takes no further proposal, so the harness does not investigate it; it is excluded from every
    number (the agent's and the baselines') and named in the results."""
    import json

    from run_dataset import DECIDED, finish, row_from

    labels = [
        {"alert_id": "f1", "truth": "FALSE_POSITIVE", "injected_scenario": "F-MM-1", "expected_disposition": CLOSE},
        {"alert_id": "f2", "truth": "FALSE_POSITIVE", "injected_scenario": "F-MM-1", "expected_disposition": CLOSE},
        {"alert_id": "a1", "truth": "TRUE_ABUSE", "injected_scenario": "S-SPOOF-1", "expected_disposition": ESCALATE},
    ]
    started = "2026-11-16T10:00:00"

    def investigated(lab, disposition):
        case = {"proposed_disposition": disposition, "confidence": 0.8, "proposed_at": "2026-11-16T10:00:30"}
        return row_from(lab, {"proposal": {"disposition": disposition}}, case, {"invoke_started_at": started})

    decided_case = {
        "proposed_disposition": ESCALATE,  # an old proposal on file must not be read as this run's
        "proposed_at": "2026-11-16T11:00:00",
        "recorded_disposition": CLOSE,
    }
    skipped = row_from(labels[1], {"skipped": DECIDED}, decided_case, {"skipped": DECIDED, "prior_recorded": True})
    assert skipped["status"] == DECIDED and skipped["proposed"] is None

    dataset = tmp_path / "ds"
    (dataset / "labels").mkdir(parents=True)
    pd.DataFrame(
        [
            {"alert_id": lab["alert_id"], "baseline_disposition": CLOSE if lab["truth"] != "TRUE_ABUSE" else ESCALATE}
            for lab in labels
        ]
    ).to_parquet(dataset / "labels" / "baseline.parquet")
    out = tmp_path / "run"
    out.mkdir()
    rows = [investigated(labels[0], CLOSE), skipped, investigated(labels[2], ESCALATE)]
    run = finish(out, {"run_id": "t", "dataset": "ds"}, rows, labels, dataset, compare=None)
    m = run["metrics"]
    assert m["n"] == 2 and m["excluded_decided"] == ["f2"] and m["n_false_positive"] == 1
    assert m["safe_close_rate"] == 1.0 and m["status_counts"] == {"ok": 2}
    assert run["baselines"]["escalate everything"]["n"] == 2
    assert "f2" in (out / "results.md").read_text() and "not investigated" in (out / "results.md").read_text()
    assert len(pd.read_csv(out / "per_alert.csv")) == 3  # the row is kept, with its status
    assert json.loads((out / "results.json").read_text())["metrics"]["excluded_decided"] == ["f2"]


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
