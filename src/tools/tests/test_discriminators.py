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
