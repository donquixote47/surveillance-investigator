"""Hand-built tapes for compute_discriminators. Depth 1000, so a 'large' order is >= 3000."""

import math

import pandas as pd

from market_sim.types import ORDER_EVENT_COLUMNS
from tools.discriminators import compute_discriminators

S = 1_000_000_000
T0 = 1_700_000_000 * S


def row(ts, oid, trader, event, side, price, qty, remaining, otype="LIMIT", parent=None, bb=9_998, ba=10_002):
    return ("SYN.A", ts, oid, trader, event, side, price, qty, remaining, otype, parent, bb, ba)


def tape(rows) -> pd.DataFrame:
    df = pd.DataFrame.from_records(rows, columns=list(ORDER_EVENT_COLUMNS))
    df["date"] = "2026-10-05"
    return df


def alert(trader="X", start=T0 - 60 * S, end=T0 + 10 * S):
    return {
        "alert_id": "A-1",
        "trader_id": trader,
        "instrument": "SYN.A",
        "window_start": start,
        "window_end": end,
    }


def test_single_spoof_signature() -> None:
    rows = [
        row(T0, "S0", "X", "NEW", "SELL", 10_005, 8000, 8000, bb=9_998, ba=10_002),  # 3 ticks above the ask
        # market makers shift down one tick in reaction
        row(T0 + S, "Q1", "MM", "CANCEL", "BUY", 9_998, 300, 0, bb=9_998, ba=10_002),
        row(T0 + S + 1, "Q2", "MM", "NEW", "BUY", 9_997, 300, 300, bb=9_997, ba=10_001),
        row(T0 + 2 * S, "B1", "X", "NEW", "BUY", None, 600, 600, "MARKET", bb=9_997, ba=10_001),
        row(T0 + 2 * S, "B1", "X", "FILL", "BUY", 10_001, 600, 0, "MARKET", bb=9_997, ba=10_001),
        row(T0 + 2 * S + 300_000_000, "S0", "X", "CANCEL", "SELL", 10_005, 8000, 0, bb=9_997, ba=10_001),
        # price comes back
        row(T0 + 8 * S, "Q3", "MM", "NEW", "BUY", 9_998, 300, 300, bb=9_998, ba=10_002),
    ]
    all_ev = tape(rows)
    mine = all_ev[all_ev.trader_id == "X"]
    d = compute_discriminators(alert(), mine, 1000.0, all_events=all_ev)
    assert d.dominant_side == "SELL" and d.gross_submitted_dominant == 8000 and d.gross_submitted_other == 0
    assert d.distinct_price_levels == 1 and d.large_order_ids == ["S0"]
    assert d.distance_from_touch_ticks == 3.0
    assert d.cancel_ratio == 1.0 and d.cancel_symmetry == 0.0
    assert d.median_cancel_latency_ms == 2300.0
    assert d.same_side_fill_qty == 0 and d.opposite_side_fill_qty == 600
    assert d.opposite_side_fills[0]["ms_before_first_cancel"] == 300.0
    assert d.max_resting_size_vs_depth == 8.0
    assert d.price_move_ticks == 1.0  # mid fell from 10000 to 9999 before he bought: in the spoofer's favour
    assert d.post_cancel_move_ticks == -1.0 and d.reversion_ticks == 1.0  # and came back after the cancel
    assert d.repetitions_in_session == 1
    assert d.otr == 3.0  # NEW (spoof), NEW (market order), CANCEL over one execution
    assert d.market_wide_cancels_1s_before_first_cancel == 0


def test_two_sided_market_maker_signature() -> None:
    rows = []
    t = T0
    for k in range(6):
        rows.append(row(t, f"B{k}", "MM", "NEW", "BUY", 9_998, 500, 500))
        rows.append(row(t + 1, f"A{k}", "MM", "NEW", "SELL", 10_002, 500, 500))
        rows.append(row(t + 2 * S, f"B{k}", "MM", "CANCEL", "BUY", 9_998, 500, 0))
        rows.append(row(t + 2 * S + 1, f"A{k}", "MM", "CANCEL", "SELL", 10_002, 500, 0))
        t += 3 * S
    rows.append(row(T0 + 10 * S, "A3x", "MM", "NEW", "SELL", 10_002, 500, 500))
    rows.append(row(T0 + 10 * S + 5, "A3x", "MM", "FILL", "SELL", 10_002, 500, 0))
    d = compute_discriminators(alert("MM", T0 - S, T0 + 30 * S), tape(rows), 1000.0)
    assert d.cancel_symmetry == 1.0
    assert d.gross_submitted_dominant == d.gross_submitted_other == 3000 or d.gross_submitted_dominant == 3500
    assert d.max_resting_size_vs_depth <= 1.0
    assert d.large_order_ids == []
    assert d.repetitions_in_session == 0


def test_partial_fill_and_modify_reduction_are_visible() -> None:
    rows = [
        row(T0, "P1", "X", "NEW", "BUY", 9_998, 5000, 5000),
        row(T0 + 3 * S, "P1", "X", "PARTIAL_FILL", "BUY", 9_998, 1200, 3800),
        row(T0 + 5 * S, "H1", "X", "NEW", "SELL", 10_002, 100, 100),
        row(T0 + 6 * S, "H1", "X", "FILL", "SELL", 10_002, 100, 0),
        row(T0 + 7 * S, "P1", "X", "MODIFY", "BUY", 9_998, -2800, 1000),
    ]
    d = compute_discriminators(alert(), tape(rows), 1000.0)
    assert d.same_side_fill_qty == 1200 and d.opposite_side_fill_qty == 100
    assert d.modify_reduction_qty == 2800
    assert d.cancel_ratio == 2800 / 5100
    assert math.isnan(d.median_cancel_latency_ms)  # no CANCEL events, only a reduction
    assert any("MODIFY" in n for n in d.notes)


def test_news_cancel_storm_is_counted() -> None:
    rows = [row(T0, "P1", "X", "NEW", "BUY", 9_996, 4000, 4000)]
    for k in range(12):
        rows.append(row(T0 + 10 * S - 500_000_000 + k * 1000, f"N{k}", f"T{k}", "CANCEL", "BUY", 9_997, 100, 0))
    rows.append(row(T0 + 10 * S, "P1", "X", "CANCEL", "BUY", 9_996, 4000, 0))
    all_ev = tape(rows)
    d = compute_discriminators(alert(), all_ev[all_ev.trader_id == "X"], 1000.0, all_events=all_ev)
    assert d.market_wide_cancels_1s_before_first_cancel == 12
    assert d.opposite_side_fill_qty == 0 and d.otr == float("inf")
    assert d.to_dict()["otr"] == "inf"


def test_repetitions_counted_over_the_whole_session_not_the_window() -> None:
    rows = []
    for c in range(4):
        t = T0 + c * 120 * S
        rows.append(row(t, f"S{c}", "X", "NEW", "SELL", 10_005, 6000, 6000))
        rows.append(row(t + S, f"B{c}", "X", "NEW", "BUY", None, 300, 300, "MARKET"))
        rows.append(row(t + S, f"B{c}", "X", "FILL", "BUY", 10_002, 300, 0, "MARKET"))
        rows.append(row(t + S + 200_000_000, f"S{c}", "X", "CANCEL", "SELL", 10_005, 6000, 0))
    d = compute_discriminators(alert(start=T0 - 60 * S, end=T0 + 6 * S), tape(rows), 1000.0)
    assert d.repetitions_in_session == 4
    assert d.gross_submitted_dominant == 6000  # only the first cycle is inside the window


def test_adverse_move_has_no_reversion_even_if_price_keeps_falling() -> None:
    rows = [
        row(T0, "P1", "X", "NEW", "BUY", 9_990, 4000, 4000, bb=9_996, ba=9_998),  # mid 9997
        # the market moves against him before he trades (another participant's row carries the new BBO)
        row(T0 + 5 * S, "N1", "MM", "NEW", "SELL", 9_996, 100, 100, bb=9_994, ba=9_996),  # mid 9995
        row(T0 + 10 * S, "M1", "X", "NEW", "SELL", None, 500, 500, "MARKET", bb=9_994, ba=9_996),
        row(T0 + 10 * S, "M1", "X", "FILL", "SELL", 9_994, 500, 0, "MARKET", bb=9_994, ba=9_996),
        row(T0 + 11 * S, "P1", "X", "CANCEL", "BUY", 9_990, 4000, 0, bb=9_993, ba=9_995),
        row(T0 + 18 * S, "Q", "MM", "NEW", "BUY", 9_990, 100, 100, bb=9_991, ba=9_993),  # mid 9992: kept falling
    ]
    all_ev = tape(rows)
    d = compute_discriminators(alert(end=T0 + 15 * S), all_ev[all_ev.trader_id == "X"], 1000.0, all_events=all_ev)
    assert d.price_move_ticks == -2.0
    assert d.post_cancel_move_ticks == -3.0  # BUY-dominant orientation: - = price went down after the cancel
    assert d.reversion_ticks == 0.0  # nothing favourable happened, so nothing reverted
    assert math.isnan(d.round_trip_ticks)  # he only sold inside the window


def test_round_trip_is_signed_profit_in_ticks() -> None:
    rows = [
        row(T0, "B", "X", "NEW", "BUY", None, 300, 300, "MARKET"),
        row(T0, "B", "X", "FILL", "BUY", 10_004, 300, 0, "MARKET"),
        row(T0 + S, "P1", "X", "NEW", "BUY", 9_990, 4000, 4000),
        row(T0 + 9 * S, "M", "X", "NEW", "SELL", None, 300, 300, "MARKET"),
        row(T0 + 9 * S, "M", "X", "PARTIAL_FILL", "SELL", 9_998, 100, 200, "MARKET"),
        row(T0 + 9 * S, "M", "X", "FILL", "SELL", 9_996, 200, 0, "MARKET"),
        row(T0 + 10 * S, "P1", "X", "CANCEL", "BUY", 9_990, 4000, 0),
    ]
    d = compute_discriminators(alert(end=T0 + 12 * S), tape(rows), 1000.0)
    sell_vwap = (9_998 * 100 + 9_996 * 200) / 300
    assert d.round_trip_ticks == sell_vwap - 10_004  # about -7.3: he sold well below where he bought


def test_memory_namespaces_are_regex_safe():
    import re

    from tools import memory_access as mem

    pat = re.compile(r"^[a-zA-Z0-9/*][a-zA-Z0-9\-_/*]*$")
    for ns in (mem.trader_ns("T-X1016-03"), mem.instrument_ns("SYN.A"), mem.instrument_ns("BRK/B"), mem.PROCEDURES_NS):
        assert pat.match(ns.rstrip("/")), ns
    assert mem.instrument_ns("SYN.A") == "/instruments/SYN_A/notes/"


def test_same_side_fills_are_split_around_the_opposite_trade() -> None:
    """F-ICE-1 / F-PARTIAL-1: the resting order trades first, then the trader goes the other way (genuine);
    S-SPOOF-5: nothing trades on the resting order until after the trader's opposite trade (caught in the book)."""
    genuine = [
        row(T0, "B0", "X", "NEW", "BUY", 9_998, 8000, 8000),
        row(T0 + 2 * S, "B0", "X", "PARTIAL_FILL", "BUY", 9_998, 1500, 6500),
        row(T0 + 4 * S, "B0", "X", "PARTIAL_FILL", "BUY", 9_998, 1500, 5000),
        row(T0 + 6 * S, "S1", "X", "NEW", "SELL", None, 400, 400, "MARKET"),
        row(T0 + 6 * S, "S1", "X", "FILL", "SELL", 10_002, 400, 0, "MARKET"),
        row(T0 + 7 * S, "B0", "X", "PARTIAL_FILL", "BUY", 9_998, 500, 4500),
        row(T0 + 8 * S, "B0", "X", "CANCEL", "BUY", 9_998, 4500, 0),
    ]
    d = compute_discriminators(alert(), tape(genuine), 1000.0)
    assert d.same_side_fill_qty == 3500
    assert d.same_side_fill_qty_before_opposite_trade == 3000 and d.same_side_fill_qty_after_opposite_trade == 500
    assert d.same_side_fill_share == 0.4375
    assert any("before any opposite-side execution" in n for n in d.notes)

    caught = [
        row(T0, "B0", "X", "NEW", "BUY", 9_996, 8000, 8000),
        row(T0 + 2 * S, "S1", "X", "NEW", "SELL", None, 400, 400, "MARKET"),
        row(T0 + 2 * S, "S1", "X", "FILL", "SELL", 10_002, 400, 0, "MARKET"),
        row(T0 + 2 * S + 200_000_000, "B0", "X", "PARTIAL_FILL", "BUY", 9_996, 1500, 6500),  # sweep hits him
        row(T0 + 2 * S + 600_000_000, "B0", "X", "CANCEL", "BUY", 9_996, 6500, 0),
    ]
    d = compute_discriminators(alert(), tape(caught), 1000.0)
    assert d.same_side_fill_qty_before_opposite_trade == 0 and d.same_side_fill_qty_after_opposite_trade == 1500
    assert any("only after the opposite-side execution" in n for n in d.notes)

    no_opposite = [
        row(T0, "B0", "X", "NEW", "BUY", 9_998, 8000, 8000),
        row(T0 + 2 * S, "B0", "X", "PARTIAL_FILL", "BUY", 9_998, 1000, 7000),
        row(T0 + 3 * S, "B0", "X", "CANCEL", "BUY", 9_998, 7000, 0),
    ]
    d = compute_discriminators(alert(), tape(no_opposite), 1000.0)
    assert d.same_side_fill_qty_before_opposite_trade == 1000 and d.same_side_fill_qty_after_opposite_trade == 0


# ----------------------------------------------------------------------------------------------
# frozen sets: the numbers the evaluation runs were scored on do not move
# ----------------------------------------------------------------------------------------------

import json  # noqa: E402
from pathlib import Path  # noqa: E402

import pytest  # noqa: E402

DATA = Path(__file__).resolve().parents[3] / "data" / "synthetic"


@pytest.mark.parametrize("dataset", ["seed7", "seed8", "seed9"])
def test_frozen_datasets_reproduce_their_committed_discriminators(dataset: str) -> None:
    """seed7 and seed8 are the regression and generalisation sets; `labels/discriminators.parquet` in each is what
    `compute_discriminators` returned when the dataset was built and what every evaluation run's tool results
    contained. A change to this module may ADD fields; it may not change the value of a field those runs saw, on
    any of the 267 alerts. (Added 2026-11-16 with the per-order block for large orders. seed9, the focused set of
    2026-11-17, is held the same way from the day it was built: 48 more alerts.)"""
    root = DATA / dataset
    if not (root / "labels" / "discriminators.parquet").exists():
        pytest.skip(f"{dataset} not built")
    events = pd.read_parquet(root / "order_events.parquet")
    alerts = pd.read_parquet(root / "alerts.parquet")
    stats = pd.read_parquet(root / "instrument_stats.parquet")
    depth = {(r.instrument, r.date): float(r.avg_depth_top5) for r in stats.itertuples()}
    committed = pd.read_parquet(root / "labels" / "discriminators.parquet").set_index("alert_id")
    by_date = {d: g for d, g in events.groupby("date")}
    mismatches = []
    for a in alerts.to_dict("records"):
        day = by_date[a["date"]]
        got = compute_discriminators(
            a, day[day.trader_id == a["trader_id"]], depth[(a["instrument"], a["date"])], all_events=day
        ).to_dict()
        # the same flattening scripts/build_dataset.py applies before writing the parquet
        row = {k: (json.dumps(v) if isinstance(v, (list, dict)) else v) for k, v in got.items()}
        row["otr"] = float("inf") if got["otr"] == "inf" else got["otr"]
        for field, old in committed.loc[a["alert_id"]].to_dict().items():
            new = row[field]
            if isinstance(old, float) and math.isnan(old):
                same = new is None or (isinstance(new, float) and math.isnan(new))
            else:
                same = old == new
            if not same:
                mismatches.append((a["alert_id"], field, old, new))
    assert not mismatches, f"{len(mismatches)} values changed on {dataset}; first: {mismatches[:5]}"
    assert len(committed) == len(alerts)


# ----------------------------------------------------------------------------------------------
# large_orders: each large order measured on its own (2026-11-16)
# ----------------------------------------------------------------------------------------------

SPOOF = [  # the tape of test_single_spoof_signature: one large order and nothing else in the window
    row(T0, "S0", "X", "NEW", "SELL", 10_005, 8000, 8000, bb=9_998, ba=10_002),
    row(T0 + S, "Q1", "MM", "CANCEL", "BUY", 9_998, 300, 0, bb=9_998, ba=10_002),
    row(T0 + S + 1, "Q2", "MM", "NEW", "BUY", 9_997, 300, 300, bb=9_997, ba=10_001),
    row(T0 + 2 * S, "B1", "X", "NEW", "BUY", None, 600, 600, "MARKET", bb=9_997, ba=10_001),
    row(T0 + 2 * S, "B1", "X", "FILL", "BUY", 10_001, 600, 0, "MARKET", bb=9_997, ba=10_001),
    row(T0 + 2 * S + 300_000_000, "S0", "X", "CANCEL", "SELL", 10_005, 8000, 0, bb=9_997, ba=10_001),
    row(T0 + 8 * S, "Q3", "MM", "NEW", "BUY", 9_998, 300, 300, bb=9_998, ba=10_002),
]
QUOTING = [  # a market maker's minute before it: two-sided quotes, one fill on each, both pulled
    row(T0 - 40 * S, "QB", "X", "NEW", "BUY", 9_998, 1200, 1200),
    row(T0 - 40 * S + 5, "QS", "X", "NEW", "SELL", 10_002, 1200, 1200),
    row(T0 - 30 * S, "QS", "X", "PARTIAL_FILL", "SELL", 10_002, 500, 700),  # a client lifts his ask quote
    row(T0 - 25 * S, "QB", "X", "PARTIAL_FILL", "BUY", 9_998, 400, 800),  # a client hits his bid quote
    row(T0 - 20 * S, "QB", "X", "CANCEL", "BUY", 9_998, 800, 0),
    row(T0 - 20 * S + 5, "QS", "X", "CANCEL", "SELL", 10_002, 700, 0),
]


def _run(rows, **kw):
    all_ev = tape(rows)
    return compute_discriminators(alert(), all_ev[all_ev.trader_id == "X"], 1000.0, all_events=all_ev, **kw)


def test_a_lone_large_order_reads_the_same_at_both_levels() -> None:
    """When the window holds nothing but the large order, its own entry repeats the window-level numbers and no
    remark is added: this is every large-order alert of the frozen datasets, so the block adds no new signal there."""
    d = _run(SPOOF)
    (e,) = d.large_orders
    assert d.large_orders_omitted == 0 and e["order_id"] == "S0" and e["side"] == "SELL" and e["order_type"] == "LIMIT"
    assert e["qty"] == 8000 and e["size_vs_depth"] == 8.0 and e["distance_from_touch_ticks"] == 3.0
    assert e["other_side_resting_vs_depth"] == 0.0  # one-sided
    assert e["executed_qty_before_opposite_trade"] == 0 and e["executed_qty_after_opposite_trade"] == 0
    assert e["cancelled_qty"] == 8000 and e["reduced_qty"] == 0 and e["open_qty_at_window_end"] == 0
    assert e["final_state"] == "CANCELLED"
    assert e["opposite_trade_qty"] == 600 and e["opposite_trade_ts"] == T0 + 2 * S
    assert (
        e["ms_from_opposite_trade_to_first_withdrawal"] == 300.0
        and e["ms_from_placement_to_first_withdrawal"] == 2300.0
    )
    assert e["price_move_ticks"] == d.price_move_ticks == 1.0
    assert e["reversion_ticks"] == d.reversion_ticks == 1.0
    assert not any("large_orders" in n for n in d.notes)


def test_a_market_maker_who_spoofs_is_described_by_the_orders_own_entry() -> None:
    """S-SPOOF-6 in miniature. The quoting earlier in the window moves every window-level number: the first
    opposite-side execution is a fill on his bid quote 25 s before the large order existed, so the window-level
    price move is 0 and the 500 executed on his ask quote read as "the resting order was trading". The large
    order's own entry says what happened to IT, and a remark, first in `notes`, says which is which."""
    d = _run(QUOTING + SPOOF)
    assert d.dominant_side == "SELL" and d.large_order_ids == ["S0"]
    # window level: diluted by the quoting
    assert d.price_move_ticks == 0.0 and d.reversion_ticks == 0.0
    assert d.same_side_fill_qty_before_opposite_trade == 500
    assert d.distance_from_touch_ticks < 3.0 and d.cancel_symmetry > 0.1
    # the order itself
    (e,) = d.large_orders
    assert e["order_id"] == "S0" and e["distance_from_touch_ticks"] == 3.0 and e["size_vs_depth"] == 8.0
    assert e["executed_qty_before_opposite_trade"] == 0 and e["executed_share_before_opposite_trade"] == 0.0
    assert e["other_side_resting_vs_depth"] == 0.0  # his quotes were pulled before it was placed
    assert e["opposite_trade_qty"] == 600  # the market order, not the 400 on his bid quote 25 s earlier
    assert e["ms_from_opposite_trade_to_first_withdrawal"] == 300.0
    assert e["price_move_ticks"] == 1.0 and e["reversion_ticks"] == 1.0
    # the remark comes first, names the order and splits the same-side executions
    assert d.notes[0].startswith("large order S0 (SELL, 8.0 x depth) was placed after 2 other order(s)")
    assert (
        "of the 500 executed on his resting SELL orders in the window, 0 were on the large order(s) and 500 on other"
        in d.notes[0]
    )
    assert "round trip" in d.notes[0]  # the window round trip is one of the numbers that mix his orders
    assert d.notes[0].endswith("large_orders describes each large order alone")
    assert any("the resting order was trading" in n for n in d.notes[1:])  # the existing remark is still there


def test_a_working_order_and_a_caught_spoof_differ_on_their_own_executions() -> None:
    working = [  # F-PARTIAL-1: executed before he traded the other way, then cut by MODIFY, later completed
        row(T0, "B0", "X", "NEW", "BUY", 9_999, 5000, 5000),
        row(T0 + 2 * S, "B0", "X", "PARTIAL_FILL", "BUY", 9_999, 1200, 3800),
        row(T0 + 4 * S, "S1", "X", "NEW", "SELL", None, 300, 300, "MARKET"),
        row(T0 + 4 * S, "S1", "X", "FILL", "SELL", 9_998, 300, 0, "MARKET"),
        row(T0 + 5 * S, "B0", "X", "MODIFY", "BUY", 9_999, -2800, 1000),
        row(T0 + 40 * S, "B0", "X", "FILL", "BUY", 9_999, 1000, 0),  # after the window: the residual completes
    ]
    (e,) = _run(working).large_orders
    assert e["distance_from_touch_ticks"] == -1.0  # improving the touch: placed to trade
    assert e["executed_qty_before_opposite_trade"] == 1200 and e["executed_share_before_opposite_trade"] == 0.24
    assert e["reduced_qty"] == 2800 and e["cancelled_qty"] == 0 and e["open_qty_at_window_end"] == 1000
    assert e["ms_from_opposite_trade_to_first_withdrawal"] == 1000.0  # the reduction is the removal
    assert e["reversion_ticks"] is None  # read after a CANCEL only, as at window level
    assert e["final_state"] == "FILLED"

    caught = [  # S-SPOOF-5: a third party hits the spoof 200 ms after his own trade, the rest is pulled
        row(T0, "B0", "X", "NEW", "BUY", 9_996, 8000, 8000),
        row(T0 + 2 * S, "S1", "X", "NEW", "SELL", None, 400, 400, "MARKET"),
        row(T0 + 2 * S, "S1", "X", "FILL", "SELL", 10_002, 400, 0, "MARKET"),
        row(T0 + 2 * S + 200_000_000, "B0", "X", "PARTIAL_FILL", "BUY", 9_996, 1500, 6500),
        row(T0 + 2 * S + 600_000_000, "B0", "X", "CANCEL", "BUY", 9_996, 6500, 0),
    ]
    (e,) = _run(caught).large_orders
    assert e["executed_qty_before_opposite_trade"] == 0 and e["executed_qty_after_opposite_trade"] == 1500
    assert e["cancelled_qty"] == 6500 and e["ms_from_opposite_trade_to_first_withdrawal"] == 600.0
    assert e["final_state"] == "CANCELLED"


def test_no_opposite_trade_while_the_order_rested_gives_nulls_not_numbers() -> None:
    fat = [  # F-FAT-1: entered by mistake, pulled in a second; he buys nothing and sells nothing meanwhile
        row(T0, "B0", "X", "NEW", "BUY", 9_997, 9000, 9000),
        row(T0 + S, "B0", "X", "CANCEL", "BUY", 9_997, 9000, 0),
        # an opposite-side execution AFTER the order was gone is not "before that order was removed"
        row(T0 + 2 * S, "S1", "X", "NEW", "SELL", None, 300, 300, "MARKET"),
        row(T0 + 2 * S, "S1", "X", "FILL", "SELL", 9_998, 300, 0, "MARKET"),
    ]
    d = _run(fat)
    (e,) = d.large_orders
    assert d.opposite_side_fill_qty == 300  # the window-level total counts it
    assert e["opposite_trade_qty"] == 0 and e["opposite_trade_ts"] is None
    assert (
        e["ms_from_opposite_trade_to_first_withdrawal"] is None and e["ms_from_placement_to_first_withdrawal"] == 1000.0
    )
    assert e["price_move_ticks"] is None and e["reversion_ticks"] is None


def test_iceberg_entry_carries_the_parents_that_tell_two_clients_apart() -> None:
    ice = [
        row(T0, "I0", "X", "NEW", "BUY", 9_999, 8000, 8000, "ICEBERG", parent="P-A"),
        row(T0 + S, "I0", "X", "PARTIAL_FILL", "BUY", 9_999, 2000, 6000, "ICEBERG", parent="P-A"),
        row(T0 + 3 * S, "S1", "X", "NEW", "SELL", 10_002, 400, 400, parent="P-B"),
        row(T0 + 4 * S, "S1", "X", "FILL", "SELL", 10_002, 400, 0, parent="P-B"),
        row(T0 + 7 * S, "I0", "X", "CANCEL", "BUY", 9_999, 6000, 0, "ICEBERG", parent="P-A"),
    ]
    (e,) = _run(ice).large_orders
    assert e["order_type"] == "ICEBERG" and e["parent_order_id"] == "P-A"
    assert e["opposite_trade_parent_order_ids"] == ["P-B"]  # another client's order, not one round trip
    assert e["executed_share_before_opposite_trade"] == 0.25
    assert e["other_side_resting_vs_depth"] == 0.4  # the 400 he had on the other side while it rested


def test_cap_keeps_the_largest_and_counts_the_rest_and_lists_either_side() -> None:
    sizes = [5000, 9000, 4000, 9500, 7000]
    many = []
    for k, q in enumerate(sizes):
        many.append(row(T0 + k * S, f"S{k}", "X", "NEW", "SELL", 10_005, q, q))
    many.append(row(T0 + 9 * S, "B9", "X", "NEW", "BUY", 9_995, 3500, 3500))  # a large order on the other side
    d = _run(many)
    assert d.dominant_side == "SELL" and "B9" not in d.large_order_ids and len(d.large_order_ids) == 5
    assert [e["order_id"] for e in d.large_orders] == ["S1", "S3", "S4"]  # the three largest, in placement order
    assert d.large_orders_omitted == 3  # S0, S2 and the BUY order
    one_each = [many[1], many[-1]]
    d = _run(one_each)
    assert [(e["order_id"], e["side"]) for e in d.large_orders] == [("S1", "SELL"), ("B9", "BUY")]
    assert d.large_order_ids == ["S1"] and d.large_orders_omitted == 0


def test_block_is_json_safe_and_needs_the_market_tape_for_prices() -> None:
    import json

    for rows in (SPOOF, QUOTING + SPOOF):
        json.dumps(_run(rows).to_dict(), allow_nan=False)
    all_ev = tape(SPOOF)
    d = compute_discriminators(alert(), all_ev[all_ev.trader_id == "X"], 1000.0)  # no market tape
    (e,) = d.large_orders
    # the trader's own rows cannot show where the market was: null, not a number read off his own order
    assert e["price_move_ticks"] is None and e["reversion_ticks"] is None
    assert e["ms_from_opposite_trade_to_first_withdrawal"] == 300.0  # timings need only his own rows
    assert (
        compute_discriminators(alert(), tape([row(T0, "Q", "X", "NEW", "BUY", 9_998, 500, 500)]), 1000.0).large_orders
        == []
    )


@pytest.mark.parametrize("dataset", ["seed7", "seed8"])
def test_on_the_frozen_datasets_the_block_restates_what_the_window_already_said(dataset: str) -> None:
    """The evaluation runs were scored on these alerts. There the block must add no new signal: it lists exactly the
    orders `large_order_ids` already named, none is left out, no remark is added, and where a window holds one
    large order its own price move, reversion and distance are the window-level ones."""
    root = DATA / dataset
    if not (root / "order_events.parquet").exists():
        pytest.skip(f"{dataset} not built")
    events = pd.read_parquet(root / "order_events.parquet")
    alerts = pd.read_parquet(root / "alerts.parquet")
    stats = pd.read_parquet(root / "instrument_stats.parquet")
    depth = {(r.instrument, r.date): float(r.avg_depth_top5) for r in stats.itertuples()}
    by_date = {d: g for d, g in events.groupby("date")}
    entries = 0
    for a in alerts.to_dict("records"):
        day = by_date[a["date"]]
        mine = day[day.trader_id == a["trader_id"]]
        d = compute_discriminators(a, mine, depth[(a["instrument"], a["date"])], all_events=day).to_dict()
        assert sorted(e["order_id"] for e in d["large_orders"]) == sorted(d["large_order_ids"]), a["alert_id"]
        assert d["large_orders_omitted"] == 0 and not any("large_orders" in n for n in d["notes"]), a["alert_id"]
        entries += len(d["large_orders"])
        if len(d["large_orders"]) == 1:
            (e,) = d["large_orders"]
            for k in ("price_move_ticks", "reversion_ticks", "distance_from_touch_ticks"):
                assert e[k] == d[k], (a["alert_id"], k, e[k], d[k])
            assert e["opposite_trade_qty"] == d["opposite_side_fill_qty"], a["alert_id"]
        # the Lambda passes other traders' rows only from 60 s before the window to 15 s after it
        cut = day[(day.ts >= a["window_start"] - 60 * S) & (day.ts <= a["window_end"] + 15 * S)]
        again = compute_discriminators(a, mine, depth[(a["instrument"], a["date"])], all_events=cut).to_dict()
        assert again["large_orders"] == d["large_orders"], a["alert_id"]
    assert entries == {"seed7": 43, "seed8": 39}[dataset]


# ---- defects an adversarial review found in the first version of the block (2026-11-16), each pinned here ----

MS = 1_000_000


def test_a_marketable_limit_on_the_other_side_is_an_execution_not_resting_quantity() -> None:
    """A spoofer may take the other side with a marketable LIMIT instead of a MARKET order. It executes on entry
    and never rests; counting it as the trader's resting quantity on the other side would present the execution
    that is feature (b) as evidence that the large order was one leg of two-sided quoting."""
    rows = [
        row(T0 - 5 * S, "Q0", "MM", "NEW", "BUY", 9_998, 300, 300),
        row(T0, "S0", "X", "NEW", "SELL", 10_005, 8000, 8000),
        row(T0 + 2 * S, "B1", "X", "NEW", "BUY", 10_002, 600, 600),
        row(T0 + 2 * S, "B1", "X", "FILL", "BUY", 10_002, 600, 0),
        row(T0 + 2 * S + 300 * MS, "S0", "X", "CANCEL", "SELL", 10_005, 8000, 0),
    ]
    (e,) = _run(rows).large_orders
    assert e["other_side_resting_vs_depth"] == 0.0 and e["opposite_trade_qty"] == 600
    partly = [*rows[:3], row(T0 + 2 * S, "B1", "X", "PARTIAL_FILL", "BUY", 10_002, 400, 200), rows[4]]
    (e,) = _run(partly).large_orders
    assert e["other_side_resting_vs_depth"] == 0.2  # what actually rested


def test_the_order_of_events_in_one_nanosecond_is_the_tape_order() -> None:
    lead = row(T0 - 5 * S, "Q0", "MM", "NEW", "BUY", 9_998, 300, 300)
    buy = [
        row(T0 + 3 * S, "B1", "X", "NEW", "BUY", None, 600, 600, "MARKET"),
        row(T0 + 3 * S, "B1", "X", "FILL", "BUY", 10_002, 600, 0, "MARKET"),
    ]
    # he pulls the order and THEN trades the other way, in the same nanosecond: not "before that order was removed"
    cancel_first = [
        lead,
        row(T0, "S0", "X", "NEW", "SELL", 10_005, 8000, 8000),
        row(T0 + 3 * S, "S0", "X", "CANCEL", "SELL", 10_005, 8000, 0),
        *buy,
    ]
    (e,) = _run(cancel_first).large_orders
    assert e["opposite_trade_qty"] == 0 and e["opposite_trade_ts"] is None
    assert e["ms_from_opposite_trade_to_first_withdrawal"] is None and e["price_move_ticks"] is None
    # the same rows the other way round: the trade came first, and the cancel 0 ms after it
    trade_first = [lead, cancel_first[1], *buy, cancel_first[2]]
    (e,) = _run(trade_first).large_orders
    assert e["opposite_trade_qty"] == 600 and e["ms_from_opposite_trade_to_first_withdrawal"] == 0.0
    # an execution recorded before the placement, in the placement's nanosecond, is not "while it rested"
    before = [
        lead,
        row(T0, "B1", "X", "NEW", "BUY", None, 600, 600, "MARKET"),
        row(T0, "B1", "X", "FILL", "BUY", 10_002, 600, 0, "MARKET"),
        row(T0, "S0", "X", "NEW", "SELL", 10_005, 8000, 8000),
        row(T0 + 3 * S, "S0", "X", "CANCEL", "SELL", 10_005, 8000, 0),
    ]
    (e,) = _run(before).large_orders
    assert e["opposite_trade_qty"] == 0


def test_a_token_reduction_does_not_end_the_order_or_hide_later_opposite_trades() -> None:
    rows = [
        row(T0, "S0", "X", "NEW", "SELL", 10_005, 8000, 8000),
        row(T0 + 2 * S, "B1", "X", "NEW", "BUY", None, 100, 100, "MARKET"),
        row(T0 + 2 * S, "B1", "X", "FILL", "BUY", 10_002, 100, 0, "MARKET"),
        row(T0 + 2 * S + MS, "S0", "X", "MODIFY", "SELL", 10_005, -100, 7900),  # 100 of 8,000, one ms later
        row(T0 + 3 * S, "B2", "X", "NEW", "BUY", None, 900, 900, "MARKET"),
        row(T0 + 3 * S, "B2", "X", "FILL", "BUY", 10_002, 900, 0, "MARKET"),
        row(T0 + 9 * S, "S0", "X", "CANCEL", "SELL", 10_005, 7900, 0),
    ]
    d = _run(rows)
    (e,) = d.large_orders
    assert e["opposite_trade_qty"] == d.opposite_side_fill_qty == 1000  # all of it happened while the order rested
    assert e["ms_from_opposite_trade_to_first_withdrawal"] == 1.0  # the first withdrawal, and it was 100 shares:
    assert e["reduced_qty"] == 100 and e["cancelled_qty"] == 7900 and e["final_state"] == "CANCELLED"


def test_remark_splits_executions_on_the_large_orders_own_side_and_sees_quotes_resting_from_before_the_window() -> None:
    # the large SELL order is on the NON-dominant side and did execute: the remark must not say "0 on the large order"
    rows = [row(T0 - 40 * S + k, f"QB{k}", "X", "NEW", "BUY", 9_998, 1200, 1200) for k in range(4)]
    rows += [
        row(T0 - 39 * S, "QS", "X", "NEW", "SELL", 10_002, 1200, 1200),
        row(T0 - 30 * S, "QB0", "X", "PARTIAL_FILL", "BUY", 9_998, 400, 800),
        row(T0 - 29 * S, "QS", "X", "PARTIAL_FILL", "SELL", 10_002, 300, 900),
        row(T0, "S0", "X", "NEW", "SELL", 10_003, 3000, 3000),
        row(T0 + S, "S0", "X", "PARTIAL_FILL", "SELL", 10_003, 700, 2300),
        row(T0 + 2 * S, "B1", "X", "NEW", "BUY", None, 600, 600, "MARKET"),
        row(T0 + 2 * S, "B1", "X", "FILL", "BUY", 10_002, 600, 0, "MARKET"),
        row(T0 + 2 * S + 300 * MS, "S0", "X", "CANCEL", "SELL", 10_003, 2300, 0),
    ]
    d = _run(rows)
    assert d.dominant_side == "BUY" and d.large_order_ids == []
    assert "of the 1000 executed on his resting SELL orders in the window, 700 were on the large order(s)" in d.notes[0]

    # his quotes were placed before the window opened and are still resting when the large order goes in
    late_window = alert(start=T0 - 5 * S, end=T0 + 10 * S)
    resting = [
        row(T0 - 30 * S, "QB", "X", "NEW", "BUY", 9_998, 1200, 1200),
        row(T0 - 30 * S + 5, "QS", "X", "NEW", "SELL", 10_002, 1200, 1200),
        row(T0, "S0", "X", "NEW", "SELL", 10_005, 8000, 8000),
        row(T0 + S, "QS", "X", "PARTIAL_FILL", "SELL", 10_002, 500, 700),
        row(T0 + 2 * S, "B1", "X", "NEW", "BUY", None, 600, 600, "MARKET"),
        row(T0 + 2 * S, "B1", "X", "FILL", "BUY", 10_002, 600, 0, "MARKET"),
        row(T0 + 2 * S + 300 * MS, "S0", "X", "CANCEL", "SELL", 10_005, 8000, 0),
    ]
    ev = tape(resting)
    d = compute_discriminators(late_window, ev[ev.trader_id == "X"], 1000.0, all_events=ev)
    assert d.notes[0].startswith("large order S0 (SELL, 8.0 x depth) was placed after 2 other order(s)")
    assert d.large_orders[0]["other_side_resting_vs_depth"] == 1.2  # and the entry shows it was not one-sided


def test_missing_touch_gives_null_and_a_size_increase_is_counted_in_the_size() -> None:
    blind = [
        row(T0, "S0", "X", "NEW", "SELL", 10_005, 8000, 8000, bb=None, ba=None),
        row(T0 + 2 * S, "S0", "X", "CANCEL", "SELL", 10_005, 8000, 0, bb=None, ba=None),
    ]
    (e,) = _run(blind).large_orders  # raised a TypeError before: the touch columns are objects when all are missing
    assert e["distance_from_touch_ticks"] is None and e["price_move_ticks"] is None

    grown = [
        row(T0, "B0", "X", "NEW", "BUY", 9_999, 3000, 3000),
        row(T0 + S, "B0", "X", "MODIFY", "BUY", 9_999, 6000, 9000),
        row(T0 + 2 * S, "B0", "X", "PARTIAL_FILL", "BUY", 9_999, 4000, 5000),
        row(T0 + 3 * S, "S1", "X", "NEW", "SELL", None, 300, 300, "MARKET"),
        row(T0 + 3 * S, "S1", "X", "FILL", "SELL", 9_998, 300, 0, "MARKET"),
        row(T0 + 4 * S, "B0", "X", "CANCEL", "BUY", 9_999, 5000, 0),
    ]
    (e,) = _run(grown).large_orders
    assert e["qty"] == 9000 and e["size_vs_depth"] == 9.0
    assert e["executed_share_before_opposite_trade"] == 0.4444  # 4,000 of 9,000, not 4,000 of the 3,000 at entry


def test_only_the_other_side_while_the_order_rested_counts_and_an_open_order_is_reported_open() -> None:
    """Three mutations of `_large_orders` survived the first test set (found by the review's mutation run): taking
    an execution on ANY side as the opposite trade, measuring the other side's resting quantity to the window end
    instead of to the order's end, and reporting an order still open as cancelled."""
    rows = [
        row(T0 - 5 * S, "Q0", "MM", "NEW", "BUY", 9_998, 300, 300),
        row(T0, "S0", "X", "NEW", "SELL", 10_005, 8000, 8000),
        row(T0 + S, "QS", "X", "NEW", "SELL", 10_002, 500, 500),  # another order of his on the SAME side...
        row(T0 + 2 * S, "QS", "X", "FILL", "SELL", 10_002, 500, 0),  # ...executes while the large order rests
        row(T0 + 3 * S, "S0", "X", "CANCEL", "SELL", 10_005, 8000, 0),
        row(T0 + 5 * S, "QB", "X", "NEW", "BUY", 9_998, 1500, 1500),  # a bid placed AFTER the large order was gone
    ]
    (e,) = _run(rows).large_orders
    assert e["opposite_trade_qty"] == 0 and e["opposite_trade_ts"] is None  # a same-side fill is not an opposite trade
    assert e["other_side_resting_vs_depth"] == 0.0  # the later bid did not rest beside the large order
    assert e["final_state"] == "CANCELLED" and e["open_qty_at_window_end"] == 0

    still_open = [row(T0, "S0", "X", "NEW", "SELL", 10_005, 8000, 8000)]
    (e,) = _run(still_open).large_orders
    assert e["final_state"] == "OPEN" and e["open_qty_at_window_end"] == 8000 and e["cancelled_qty"] == 0
    assert e["ms_from_placement_to_first_withdrawal"] is None
