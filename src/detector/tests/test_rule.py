"""Hand-built tapes for the detector. Depth is 1000 everywhere, so K x depth = 3250."""

import pandas as pd

from detector.rule import DetectorParams, detect
from market_sim.types import ORDER_EVENT_COLUMNS

S = 1_000_000_000
T0 = 1_700_000_000 * S
DATE = "2026-10-05"


def row(ts, oid, trader, event, side, price, qty, remaining, otype="LIMIT", parent=None, bb=9_998, ba=10_002):
    return ("SYN.A", ts, oid, trader, event, side, price, qty, remaining, otype, parent, bb, ba)


def tape(rows) -> pd.DataFrame:
    df = pd.DataFrame.from_records(rows, columns=list(ORDER_EVENT_COLUMNS))
    df["date"] = DATE
    return df


STATS = pd.DataFrame([{"instrument": "SYN.A", "date": DATE, "avg_depth_top5": 1000.0}])


def spoof_rows(trader="X", t=T0, size=8000, levels=1):
    rows = []
    per = size // levels
    for k in range(levels):
        rows.append(row(t + k, f"S{k}", trader, "NEW", "SELL", 10_004 + k, per, per))
    rows.append(row(t + 2 * S, "B1", trader, "NEW", "BUY", None, 500, 500, "MARKET"))
    rows.append(row(t + 2 * S, "B1", trader, "FILL", "BUY", 10_002, 500, 0, "MARKET"))
    for k in range(levels):
        rows.append(row(t + 2 * S + 300_000_000 + k, f"S{k}", trader, "CANCEL", "SELL", 10_004 + k, per, 0))
    return rows


def test_spoof_triggers_opposite_fill_cancel_with_window_around_the_fill() -> None:
    alerts = detect(tape(spoof_rows()), STATS)
    assert len(alerts) == 1
    a = alerts.iloc[0]
    assert a.trigger == "OPPOSITE_FILL_CANCEL" and a.scenario == "SPOOFING"
    tf = T0 + 2 * S
    # 8000 >= 6 x depth also trips LARGE_QUICK_CANCEL at T0; the two candidates merge into one alert
    # whose window is the union: [tf - 60 s, T0 + 10 s]
    assert a.window_start == tf - 60 * S and a.window_end == T0 + 10 * S
    assert a.alert_id.startswith("A-261005-")
    assert "gross SELL size 8000" in a.trigger_summary


def test_layering_classified_by_distinct_levels() -> None:
    alerts = detect(tape(spoof_rows(size=9000, levels=3)), STATS)
    assert len(alerts) == 1 and alerts.iloc[0].scenario == "LAYERING"


def test_small_gross_or_slow_cancel_does_not_trigger() -> None:
    small = detect(tape(spoof_rows(size=2000)), STATS)
    assert small.empty
    rows = spoof_rows()
    rows[-1] = row(T0 + 2 * S + 9 * S, "S0", "X", "CANCEL", "SELL", 10_004, 8000, 0)  # 9 s later, outside C
    slow = detect(tape(rows), STATS)
    assert slow.empty


def test_large_quick_cancel_needs_no_opposite_fill() -> None:
    rows = [
        row(T0, "F1", "X", "NEW", "BUY", 9_990, 7000, 7000),
        row(T0 + int(1.4 * S), "F1", "X", "CANCEL", "BUY", 9_990, 7000, 0),
    ]
    alerts = detect(tape(rows), STATS)
    assert len(alerts) == 1 and alerts.iloc[0].trigger == "LARGE_QUICK_CANCEL"
    # a reduction below P% does not count
    rows[1] = row(T0 + S, "F1", "X", "MODIFY", "BUY", 9_990, -3000, 4000)
    assert detect(tape(rows), STATS).empty


def test_market_orders_do_not_count_as_resting_size() -> None:
    rows = [
        row(T0, "M1", "X", "NEW", "SELL", None, 8000, 8000, "MARKET"),
        row(T0, "M1", "X", "FILL", "SELL", 9_998, 8000, 0, "MARKET"),
        row(T0 + S, "B1", "X", "NEW", "BUY", None, 500, 500, "MARKET"),
        row(T0 + S, "B1", "X", "FILL", "BUY", 10_002, 500, 0, "MARKET"),
    ]
    assert detect(tape(rows), STATS).empty


def test_overlapping_candidates_merge_and_cooldown_separates_episodes() -> None:
    first = spoof_rows(t=T0, size=8000)  # also qualifies for LARGE_QUICK (>= 6 x depth): must merge into one alert
    second = spoof_rows(t=T0 + 20 * 60 * S, size=8000)  # 20 minutes later, past the 15-minute cooldown
    third = spoof_rows(t=T0 + 22 * 60 * S, size=8000)  # inside the cooldown of the second: suppressed
    for i, r in enumerate(second):
        second[i] = (*r[:2], r[2] + "b", *r[3:])
    for i, r in enumerate(third):
        third[i] = (*r[:2], r[2] + "c", *r[3:])
    alerts = detect(tape(first + second + third), STATS, DetectorParams())
    assert len(alerts) == 2
    assert list(alerts.trigger) == ["OPPOSITE_FILL_CANCEL", "OPPOSITE_FILL_CANCEL"]
    assert "also:" in alerts.iloc[0].trigger_summary


def test_params_are_recorded_on_every_alert() -> None:
    alerts = detect(tape(spoof_rows()), STATS, DetectorParams(k_depth=2.0))
    assert '"k_depth": 2.0' in alerts.iloc[0].detector_params
    assert alerts.iloc[0].detector_version == "spoof-naive-v1"
