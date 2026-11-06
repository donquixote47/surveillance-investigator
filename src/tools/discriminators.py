"""compute_discriminators: the numbers an analyst looks at, computed deterministically from the tape.

The LLM never computes these; it reads them. Every value is reproducible from the order_events rows
for the trader and the window, plus the instrument's average depth. Vocabulary follows Delegated
Regulation (EU) 2016/522 Annex II (orders away from the touch, no intention to execute, order-to-trade
ratio) so the agent's report can cite the indicators directly.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from market_sim.types import NS_PER_MS, NS_PER_S, EventType, OrderType, Side

FILL_EVENTS = (str(EventType.FILL), str(EventType.PARTIAL_FILL))


@dataclass
class Discriminators:
    alert_id: str
    trader_id: str
    instrument: str
    window_start: int
    window_end: int
    window_seconds: float
    dominant_side: str  # side with the larger gross submitted size in the window
    gross_submitted_dominant: int
    gross_submitted_other: int
    otr: float  # (NEW + MODIFY + CANCEL) / executions in the window; inf when no executions
    cancel_ratio: float  # cancelled or reduced qty / submitted qty (non-market)
    median_cancel_latency_ms: float  # placement -> cancel, dominant side
    max_resting_size_vs_depth: float  # peak open qty on the dominant side / avg top-5 depth
    distance_from_touch_ticks: float  # size-weighted, at placement, dominant side; negative = improving
    distinct_price_levels: int  # distinct prices of dominant-side orders placed in the window
    large_order_ids: list[str]  # dominant-side orders >= 3 x depth
    same_side_fill_qty: int  # executions on the dominant side's own orders (genuine intent)
    # the same executions split around the trader's first opposite-side execution: fills BEFORE it show an order
    # that was working (iceberg slices, partial fills); fills only AFTER it are a third party catching a spoof in
    # the book (S-SPOOF-5). With no opposite-side execution, everything counts as "before".
    same_side_fill_qty_before_opposite_trade: int
    same_side_fill_qty_after_opposite_trade: int
    same_side_fill_share: float  # same_side_fill_qty / gross submitted on the dominant side; 0 when nothing submitted
    opposite_side_fill_qty: int
    opposite_side_fills: list[dict]  # ts, price_ticks, qty, ms_before_first_cancel
    modify_reduction_qty: int
    cancel_symmetry: float  # 1 = cancels equal on both sides, 0 = one-sided
    price_move_ticks: (
        float  # mid at first dominant-side cancel vs mid at first large placement, + = as a spoofer would want
    )
    # mid 10 s after the last cancel vs mid before the opposite execution, oriented like price_move:
    # + = kept going the spoofer's way, - = came back
    post_cancel_move_ticks: float
    # how much of a favourable pre-trade move was undone after the cancel; 0 when there was none
    reversion_ticks: float
    # VWAP of the trader's SELL executions minus VWAP of his BUY executions inside the window, all order types;
    # + = sold above where he bought (a spoofer's round trip, or a market maker's spread), - = a loss (stop-out)
    round_trip_ticks: float
    repetitions_in_session: int  # large placement -> opposite fill -> cancel cycles over the whole session
    market_wide_cancels_1s_before_first_cancel: int  # OTHER traders with a cancel in the second before ours
    order_types: dict[str, int]
    parent_order_ids: list[str]
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = self.__dict__.copy()
        for k, v in d.items():
            if isinstance(v, float) and (math.isinf(v) or math.isnan(v)):
                d[k] = None if math.isnan(v) else "inf"
        return d


def _mid(row) -> float | None:
    bb, ba = row["best_bid"], row["best_ask"]
    if pd.isna(bb) or pd.isna(ba):
        return None
    return (float(bb) + float(ba)) / 2


def _mid_at(ev: pd.DataFrame, t: int, direction: str = "before") -> float | None:
    """Mid from the BBO recorded on the nearest event row at or before (or after) t."""
    if ev.empty:
        return None
    ts = ev["ts"].to_numpy()
    if direction == "before":
        i = int(np.searchsorted(ts, t, side="right")) - 1
        if i < 0:
            return None
    else:
        i = int(np.searchsorted(ts, t, side="left"))
        if i >= len(ts):
            i = len(ts) - 1
    return _mid(ev.iloc[i])


def compute_discriminators(
    alert: dict,
    trader_events: pd.DataFrame,
    avg_depth_top5: float,
    all_events: pd.DataFrame | None = None,
    large_multiple: float = 3.0,
) -> Discriminators:
    """`trader_events`: all rows for the alert's trader, instrument and date (the whole session, so
    repetitions can be counted). `all_events`: all traders' rows for the same date (optional; used for
    the market-wide cancel count and a better mid after the window)."""
    w0, w1 = int(alert["window_start"]), int(alert["window_end"])
    depth = max(1.0, float(avg_depth_top5))
    te = trader_events.sort_values("ts", kind="stable").reset_index(drop=True)
    win = te[(te["ts"] >= w0) & (te["ts"] <= w1)]
    nonmkt = win[win["order_type"] != str(OrderType.MARKET)]
    notes: list[str] = []

    new = nonmkt[nonmkt["event"] == str(EventType.NEW)]
    gross = new.groupby("side")["qty"].sum()
    g_buy, g_sell = int(gross.get(str(Side.BUY), 0)), int(gross.get(str(Side.SELL), 0))
    if g_buy == 0 and g_sell == 0:
        notes.append("no non-market orders submitted in the window")
    dom = str(Side.BUY) if g_buy >= g_sell else str(Side.SELL)
    other = str(Side.SELL) if dom == str(Side.BUY) else str(Side.BUY)

    # OTR and cancel ratio over the whole window
    n_msgs = int(win["event"].isin([str(EventType.NEW), str(EventType.MODIFY), str(EventType.CANCEL)]).sum())
    n_exec = int(win["event"].isin(FILL_EVENTS).sum())
    otr = float(n_msgs) / n_exec if n_exec else float("inf")
    cancelled = nonmkt[nonmkt["event"] == str(EventType.CANCEL)]["qty"].sum()
    reductions = -nonmkt[(nonmkt["event"] == str(EventType.MODIFY)) & (nonmkt["qty"] < 0)]["qty"].sum()
    submitted = new["qty"].sum()
    cancel_ratio = float(cancelled + reductions) / float(submitted) if submitted else 0.0

    # dominant-side detail
    dnew = new[new["side"] == dom]
    dcancel = nonmkt[(nonmkt["side"] == dom) & (nonmkt["event"] == str(EventType.CANCEL))]
    placed_ts = dict(zip(dnew["order_id"], dnew["ts"], strict=False))
    latencies = [
        (int(r.ts) - int(placed_ts[r.order_id])) / NS_PER_MS for r in dcancel.itertuples() if r.order_id in placed_ts
    ]
    median_latency = float(np.median(latencies)) if latencies else float("nan")

    # distance from the same-side touch at placement (BUY: bid - price; SELL: price - ask); negative = improving
    if not dnew.empty:
        if dom == str(Side.BUY):
            dist = dnew["best_bid"].astype(float) - dnew["price_ticks"].astype(float)
        else:
            dist = dnew["price_ticks"].astype(float) - dnew["best_ask"].astype(float)
        w = dnew["qty"].astype(float)
        ok = dist.notna()
        distance = float((dist[ok] * w[ok]).sum() / w[ok].sum()) if w[ok].sum() else float("nan")
        levels = int(dnew["price_ticks"].nunique())
    else:
        distance, levels = float("nan"), 0

    # peak resting size on the dominant side inside the window, from the whole-session series so that
    # orders placed before the window are counted
    sess_nonmkt = te[te["order_type"] != str(OrderType.MARKET)]
    dside = sess_nonmkt[sess_nonmkt["side"] == dom]
    delta = np.where(
        dside["event"] == str(EventType.NEW),
        dside["qty"],
        np.where(
            dside["event"].isin(FILL_EVENTS),
            -dside["qty"],
            np.where(dside["event"] == str(EventType.CANCEL), -dside["qty"], dside["qty"]),  # MODIFY delta is signed
        ),
    )
    resting = np.cumsum(delta)
    in_win = (dside["ts"].to_numpy() >= w0) & (dside["ts"].to_numpy() <= w1)
    before = resting[dside["ts"].to_numpy() < w0]
    peak_candidates = list(resting[in_win]) + ([before[-1]] if len(before) else [])
    peak = float(max(peak_candidates)) if peak_candidates else 0.0
    max_resting_vs_depth = max(0.0, peak) / depth

    large_ids = [str(r.order_id) for r in dnew.itertuples() if r.qty >= large_multiple * depth]

    same_rows = nonmkt[(nonmkt["side"] == dom) & nonmkt["event"].isin(FILL_EVENTS)]
    same_fill = int(same_rows["qty"].sum())
    opp_rows = win[(win["side"] == other) & win["event"].isin(FILL_EVENTS)]
    opp_fill = int(opp_rows["qty"].sum())
    first_opp_ts = int(opp_rows["ts"].min()) if not opp_rows.empty else None
    same_before = same_fill if first_opp_ts is None else int(same_rows[same_rows["ts"] < first_opp_ts]["qty"].sum())
    same_after = same_fill - same_before
    gross_dom = g_buy if dom == str(Side.BUY) else g_sell
    same_share = round(same_fill / gross_dom, 4) if gross_dom else 0.0
    if same_before > 0:
        notes.append(
            f"{same_before} executed on the trader's own {dom} orders before any opposite-side execution: "
            "the resting order was trading"
        )
    elif same_after > 0:
        notes.append(
            f"{same_after} executed on the trader's own {dom} orders only after the opposite-side execution: "
            "consistent with a third party hitting a resting order before it was pulled"
        )
    first_cancel_ts = int(dcancel["ts"].min()) if not dcancel.empty else None
    opp_fills = [
        {
            "ts": int(r.ts),
            "price_ticks": None if pd.isna(r.price_ticks) else float(r.price_ticks),
            "qty": int(r.qty),
            "ms_before_first_cancel": None if first_cancel_ts is None else (first_cancel_ts - int(r.ts)) / NS_PER_MS,
        }
        for r in opp_rows.itertuples()
    ]

    cb = int(nonmkt[(nonmkt["side"] == str(Side.BUY)) & (nonmkt["event"] == str(EventType.CANCEL))]["qty"].sum())
    ca = int(nonmkt[(nonmkt["side"] == str(Side.SELL)) & (nonmkt["event"] == str(EventType.CANCEL))]["qty"].sum())
    symmetry = 1.0 - abs(cb - ca) / (cb + ca) if (cb + ca) else 0.0

    # price move: mid just before the trader's first opposite-side execution vs mid at the first large
    # placement, signed so that + means "moved the way a spoofer on the dominant side would want".
    # post-cancel move: mid 10 s after the last dominant-side cancel vs the same pre-execution mid, same
    # orientation (+ = kept going the spoofer's way, - = came back). Measuring from the pre-execution mid, not
    # from the cancel, keeps the trader's own market order's impact out of the number.
    # reversion: the part of a *favourable* pre-trade move that was undone afterwards. A spoof snaps back when
    # the fake order disappears; a trader selling into a falling market has nothing to revert, so it is 0.
    direction = -1.0 if dom == str(Side.SELL) else 1.0  # big asks would push the price down
    ref_events = all_events.sort_values("ts", kind="stable") if all_events is not None else te
    first_large_ts = (
        int(dnew[dnew["qty"] >= large_multiple * depth]["ts"].min())
        if large_ids
        else (int(dnew["ts"].min()) if not dnew.empty else None)
    )
    price_move = float("nan")
    post_cancel_move = float("nan")
    reversion = float("nan")
    if first_large_ts is not None:
        m0 = _mid_at(ref_events, first_large_ts, "before")
        m1 = None
        if not opp_rows.empty:
            m1 = _mid_at(ref_events, int(opp_rows["ts"].min()) - 1, "before")
            if m0 is not None and m1 is not None:
                price_move = (m1 - m0) * direction
        if first_cancel_ts is not None:
            last_cancel_ts = int(dcancel["ts"].max())
            base = m1 if m1 is not None else _mid_at(ref_events, last_cancel_ts, "before")
            m2 = _mid_at(ref_events, last_cancel_ts + 10 * NS_PER_S, "before")
            if base is not None and m2 is not None:
                post_cancel_move = (m2 - base) * direction
                if not math.isnan(price_move):
                    reversion = max(0.0, -post_cancel_move) if price_move > 0 else 0.0

    fills_all = win[win["event"].isin(FILL_EVENTS)]
    round_trip = float("nan")
    buys = fills_all[fills_all["side"] == str(Side.BUY)]
    sells = fills_all[fills_all["side"] == str(Side.SELL)]
    if not buys.empty and not sells.empty and buys["price_ticks"].notna().all() and sells["price_ticks"].notna().all():
        vb = float((buys["price_ticks"].astype(float) * buys["qty"]).sum() / buys["qty"].sum())
        vs = float((sells["price_ticks"].astype(float) * sells["qty"]).sum() / sells["qty"].sum())
        round_trip = vs - vb

    repetitions = _count_cycles(te, dom, other, depth, large_multiple)

    mw = 0
    if all_events is not None and first_cancel_ts is not None:
        o = all_events[
            (all_events["trader_id"] != alert["trader_id"])
            & (all_events["event"] == str(EventType.CANCEL))
            & (all_events["ts"] >= first_cancel_ts - NS_PER_S)
            & (all_events["ts"] < first_cancel_ts)
        ]
        mw = int(o["trader_id"].nunique())  # distinct traders: a re-quoting market maker is 1, a news storm is many

    order_types = {str(k): int(v) for k, v in new["order_type"].value_counts().items()}
    parents = sorted({str(p) for p in win["parent_order_id"].dropna().unique()})

    if same_fill > 0 and dom in (str(Side.BUY), str(Side.SELL)):
        notes.append(f"{same_fill} executed on the dominant-side orders themselves")
    if reductions > 0:
        notes.append(f"{int(reductions)} removed through MODIFY size reductions rather than cancels")

    return Discriminators(
        alert_id=str(alert["alert_id"]),
        trader_id=str(alert["trader_id"]),
        instrument=str(alert["instrument"]),
        window_start=w0,
        window_end=w1,
        window_seconds=(w1 - w0) / NS_PER_S,
        dominant_side=dom,
        gross_submitted_dominant=int(max(g_buy, g_sell)),
        gross_submitted_other=int(min(g_buy, g_sell)),
        otr=otr,
        cancel_ratio=cancel_ratio,
        median_cancel_latency_ms=median_latency,
        max_resting_size_vs_depth=max_resting_vs_depth,
        distance_from_touch_ticks=distance,
        distinct_price_levels=levels,
        large_order_ids=large_ids,
        same_side_fill_qty=same_fill,
        same_side_fill_qty_before_opposite_trade=same_before,
        same_side_fill_qty_after_opposite_trade=same_after,
        same_side_fill_share=same_share,
        opposite_side_fill_qty=opp_fill,
        opposite_side_fills=opp_fills,
        modify_reduction_qty=int(reductions),
        cancel_symmetry=symmetry,
        price_move_ticks=price_move,
        post_cancel_move_ticks=post_cancel_move,
        reversion_ticks=reversion,
        round_trip_ticks=round_trip,
        repetitions_in_session=repetitions,
        market_wide_cancels_1s_before_first_cancel=mw,
        order_types=order_types,
        parent_order_ids=parents,
        notes=notes,
    )


def _count_cycles(
    te: pd.DataFrame,
    dom: str,
    other: str,
    depth: float,
    large_multiple: float,
    within_s: float = 5.0,
    gap_s: float = 30.0,
) -> int:
    """Count clusters of 'cancel of a large dominant-side order within `within_s` after an opposite-side
    execution' over the whole session, merging cancels closer than `gap_s` into one cycle."""
    nonmkt = te[te["order_type"] != str(OrderType.MARKET)]
    big_ids = set(
        nonmkt[
            (nonmkt["event"] == str(EventType.NEW))
            & (nonmkt["side"] == dom)
            & (nonmkt["qty"] >= large_multiple * depth)
        ]["order_id"]
    )
    if not big_ids:
        return 0
    cancels = nonmkt[(nonmkt["event"] == str(EventType.CANCEL)) & (nonmkt["order_id"].isin(big_ids))]["ts"].to_numpy()
    opp = te[(te["side"] == other) & te["event"].isin(FILL_EVENTS)]["ts"].to_numpy()
    if len(cancels) == 0 or len(opp) == 0:
        return 0
    cycles = 0
    last = -(10**18)
    for tc in np.sort(cancels):
        j = int(np.searchsorted(opp, tc, side="right")) - 1
        if j >= 0 and tc - opp[j] <= within_s * NS_PER_S and tc - last > gap_s * NS_PER_S:
            cycles += 1
            last = tc
    return cycles
