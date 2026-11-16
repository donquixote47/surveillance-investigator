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
LARGE_ORDERS_CAP = 3  # entries listed in `large_orders`; the frozen datasets have at most 2 per alert


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
    # One entry per single order of at least 3 x depth placed in the window, either side, each measured ON THAT
    # ORDER ALONE (see `_large_orders`). Everything above is aggregated by side over the window, which describes
    # the large order only when the trader did nothing else in the window: a market maker who quotes for a minute
    # and then places one order of ten times the depth gets side-level numbers that describe his quoting.
    large_orders: list[dict] = field(default_factory=list)
    large_orders_omitted: int = 0  # large orders in the window not listed above (cap LARGE_ORDERS_CAP)

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

    large_orders, large_omitted, large_remark = _large_orders(
        te, w0, w1, depth, large_multiple, ref_events if all_events is not None else None
    )
    if large_remark:
        notes.insert(0, large_remark)  # first, so the remarks after it are read as window-level

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
        large_orders=large_orders,
        large_orders_omitted=large_omitted,
    )


def _clean(x: float | None) -> float | None:
    """A JSON-safe number: None for NaN/inf, and 0.0 rather than -0.0."""
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return None
    return float(x) + 0.0


def _large_orders(
    te: pd.DataFrame,
    w0: int,
    w1: int,
    depth: float,
    large_multiple: float,
    ref_events: pd.DataFrame | None,
) -> tuple[list[dict], int, str | None]:
    """Per-order facts for every single large order of the trader in the window.

    Listed: non-market orders whose NEW row has qty >= large_multiple x depth and lies inside the window, on EITHER
    side (`large_order_ids` stays dominant-side only), at most LARGE_ORDERS_CAP of them (the largest; the rest are
    counted), in placement order. Each entry is measured on the order's own rows, and the ORDER OF EVENTS is the
    order of rows on the tape (`te` is in tape order), never a comparison of timestamps alone: two events in the
    same nanosecond happened in the order the venue recorded them.

      rested    from the order's NEW row to its first row with nothing left open, if that is inside the window;
                else to the window end
      OPP       the trader's executions on the OTHER side (any order type) while the order rested:
                "an opposite-side execution before that order was removed" (feature (b) of the firm's standard)
      first withdrawal
                the first CANCEL or MODIFY size reduction of the order after the first of those executions (or its
                first one at all, when the trader never traded the other way while it rested). A reduction that
                leaves the order working is a withdrawal of part of it, not its removal: `cancelled_qty`,
                `reduced_qty`, `open_qty_at_window_end` and `final_state` say which.

    Price numbers use the same mid helper, the same sampling points and the same sign as the window-level
    `price_move_ticks` / `reversion_ticks`, anchored on this order's placement and its own cancel, so on a window
    that holds nothing but one large order the two levels return the same numbers. Anything that cannot be
    measured is None, never a default. Also returns a remark for `notes` when the window-level numbers mix the
    large order with other orders of the trader.
    """
    te = te.reset_index(drop=True)  # row position = tape order
    nonmkt = te[te["order_type"] != str(OrderType.MARKET)]
    new = nonmkt[
        (nonmkt["event"] == str(EventType.NEW))
        & (nonmkt["qty"] >= large_multiple * depth)
        & (nonmkt["ts"] >= w0)
        & (nonmkt["ts"] <= w1)
    ]
    if new.empty:
        return [], 0, None
    candidates = list(new.itertuples())  # Index = position on the tape
    listed = sorted(candidates, key=lambda r: (-int(r.qty), r.Index))[:LARGE_ORDERS_CAP]
    listed.sort(key=lambda r: r.Index)
    omitted = len(candidates) - len(listed)

    fills = te[te["event"].isin(FILL_EVENTS)]
    in_window = te["ts"] <= w1
    entries: list[dict] = []
    for n in listed:
        oid, side, placed, p_new = str(n.order_id), str(n.side), int(n.ts), n.Index
        other = str(Side.SELL) if side == str(Side.BUY) else str(Side.BUY)
        sign = 1.0 if side == str(Side.BUY) else -1.0
        rows = te[(te["order_id"] == n.order_id) & (te.index >= p_new)]
        in_win = rows[rows["ts"] <= w1]
        gone = in_win[(in_win.index > p_new) & (in_win["remaining_qty"] == 0)]
        p_gone = gone.index[0] if not gone.empty else None

        # the trader's executions on the other side while this order rested
        opp = fills[(fills["side"] == other) & (fills.index > p_new) & in_window[fills.index]]
        if p_gone is not None:
            opp = opp[opp.index < p_gone]
        p_opp = opp.index[0] if not opp.empty else None
        t_opp = int(opp["ts"].iloc[0]) if p_opp is not None else None

        own_fills = in_win[in_win["event"].isin(FILL_EVENTS)]
        executed = int(own_fills["qty"].sum())
        before = executed if p_opp is None else int(own_fills[own_fills.index < p_opp]["qty"].sum())

        cancels = in_win[in_win["event"] == str(EventType.CANCEL)]
        reductions = in_win[(in_win["event"] == str(EventType.MODIFY)) & (in_win["qty"] < 0)]
        increases = in_win[(in_win["event"] == str(EventType.MODIFY)) & (in_win["qty"] > 0)]
        withdrawals = pd.concat([cancels, reductions]).sort_index()
        if p_opp is not None:
            withdrawals = withdrawals[withdrawals.index > p_opp]
        t_wd = int(withdrawals["ts"].iloc[0]) if not withdrawals.empty else None
        qty = int(n.qty) + int(increases["qty"].sum())  # the largest size the order was given inside the window

        # The trader's own RESTING quantity on the other side while this order rested: 0 = the order was one-sided.
        # The level is read at the end of each timestamp, so an order that executes on entry (a marketable limit,
        # which is how a spoofer may take the other side) is not counted as having rested.
        os_rows = nonmkt[nonmkt["side"] == other]
        other_side_peak = 0.0
        if len(os_rows):
            delta = np.where(
                os_rows["event"] == str(EventType.NEW),
                os_rows["qty"],
                np.where(os_rows["event"] == str(EventType.MODIFY), os_rows["qty"], -os_rows["qty"]),
            )
            level = np.cumsum(delta)
            pos = os_rows.index.to_numpy()
            os_ts = os_rows["ts"].to_numpy()
            settled = np.r_[os_ts[1:] != os_ts[:-1], True]  # the last row of each timestamp
            end = p_gone if p_gone is not None else (te.index[in_window][-1] + 1 if in_window.any() else p_new)
            earlier_rows = settled & (pos < p_new)
            at_placement = float(level[earlier_rows][-1]) if earlier_rows.any() else 0.0
            during = level[settled & (pos > p_new) & (pos < end)]
            other_side_peak = max([0.0, at_placement, *[float(x) for x in during]])

        touch = n.best_bid if side == str(Side.BUY) else n.best_ask
        if pd.isna(touch) or pd.isna(n.price_ticks):
            distance = None
        else:
            distance = (float(touch) - float(n.price_ticks)) * sign  # BUY: bid - price; SELL: price - ask

        price_move = reversion = None
        if ref_events is not None and t_opp is not None:
            m0 = _mid_at(ref_events, placed, "before")
            m1 = _mid_at(ref_events, t_opp - 1, "before")
            if m0 is not None and m1 is not None:
                price_move = (m1 - m0) * sign
                if not cancels.empty:  # like the window-level field: a reversion is read after a CANCEL only
                    m2 = _mid_at(ref_events, int(cancels["ts"].max()) + 10 * NS_PER_S, "before")
                    if m2 is not None:
                        reversion = max(0.0, -(m2 - m1) * sign) if price_move > 0 else 0.0

        last = rows.iloc[-1]  # the order's last row of the session: the one fact here that looks past the window
        if int(last["remaining_qty"]) > 0:
            final_state = "OPEN"
        elif str(last["event"]) in FILL_EVENTS:
            final_state = "FILLED"
        else:
            final_state = "CANCELLED"

        entries.append(
            {
                "order_id": oid,
                "side": side,
                "order_type": str(n.order_type),
                "parent_order_id": None if pd.isna(n.parent_order_id) else str(n.parent_order_id),
                "placed_ts": placed,
                "price_ticks": None if pd.isna(n.price_ticks) else _clean(float(n.price_ticks)),
                "qty": qty,
                "size_vs_depth": round(qty / depth, 2),
                "distance_from_touch_ticks": _clean(distance),
                "other_side_resting_vs_depth": round(other_side_peak / depth, 2),
                "executed_qty_before_opposite_trade": before,
                "executed_qty_after_opposite_trade": executed - before,
                "executed_share_before_opposite_trade": round(before / qty, 4) if qty else 0.0,
                "cancelled_qty": int(cancels["qty"].sum()),
                "reduced_qty": int(-reductions["qty"].sum()),
                "open_qty_at_window_end": int(in_win["remaining_qty"].iloc[-1]),
                "final_state": final_state,
                "opposite_trade_ts": t_opp,
                "opposite_trade_qty": int(opp["qty"].sum()),
                "opposite_trade_parent_order_ids": sorted({str(p) for p in opp["parent_order_id"].dropna().unique()})[
                    :3
                ],
                "ms_from_placement_to_first_withdrawal": None
                if t_wd is None
                else round((t_wd - placed) / NS_PER_MS, 1),
                "ms_from_opposite_trade_to_first_withdrawal": None
                if t_wd is None or t_opp is None
                else round((t_wd - t_opp) / NS_PER_MS, 1),
                "price_move_ticks": _clean(price_move),
                "reversion_ticks": _clean(reversion),
            }
        )

    # The remark: only when other orders of the trader were ACTIVE IN THE WINDOW BEFORE the first large order (a
    # row of theirs between the window start and its placement, or still resting when it was placed), which is
    # when the side-level numbers stop describing it (S-SPOOF-6). A window that opens with the large order and
    # nothing else of his resting (every large-order alert of the frozen datasets) gets no remark, so its `notes`
    # do not change.
    first = candidates[0]
    large_ids = {r.order_id for r in candidates}
    not_large = ~te["order_id"].isin(large_ids)
    before_first = te[(te.index < first.Index) & not_large]
    active = set(before_first[before_first["ts"] >= w0]["order_id"])
    resting = (
        before_first[before_first["order_type"] != str(OrderType.MARKET)]
        .groupby("order_id", sort=False)["remaining_qty"]
        .last()
    )
    active |= set(resting[resting > 0].index)
    if not active:
        return entries, omitted, None
    fside = str(first.side)
    side_fills = fills[
        (fills["ts"] >= w0)
        & in_window[fills.index]
        & (fills["side"] == fside)
        & (fills["order_type"] != str(OrderType.MARKET))
    ]
    total = int(side_fills["qty"].sum())
    on_large = int(side_fills[side_fills["order_id"].isin(large_ids)]["qty"].sum())
    remark = (
        f"large order {first.order_id} ({fside}, {round(int(first.qty) / depth, 1)} x depth) was placed after "
        f"{len(active)} other order(s) of the trader had been active in the window: the window-level numbers "
        "(price move, reversion, round trip, distance from the touch, cancel latency, cancel symmetry, same-side "
        "and opposite-side executions) describe all his orders in the window together"
    )
    if total > 0:
        remark += (
            f"; of the {total} executed on his resting {fside} orders in the window, {on_large} were on the large "
            f"order(s) and {total - on_large} on other orders"
        )
    remark += ". large_orders describes each large order alone"
    return entries, omitted, remark


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
