"""Spoofing / layering detector, written to be noisy on purpose.

Two triggers, evaluated per (date, instrument, trader):

1. OPPOSITE_FILL_CANCEL. For each execution of the trader on side X at time tf, let Y be the other side.
   If the gross size of non-market orders the trader *submitted* on Y in the last W seconds is at least
   K times the instrument's average top-5 depth, the trader still has resting size R on Y at tf, and at
   least P percent of R is cancelled (or reduced by MODIFY) within C seconds after tf: alert.
2. LARGE_QUICK_CANCEL. A single non-market order of at least K2 times the average depth, of which at
   least P percent is cancelled or reduced within C2 seconds of placement: alert. No opposite fill needed
   (attempts count under MAR Art. 15).

What it does not look at, by design: the trader's role, whether cancels are two-sided, whether a
market event happened, whether the resting orders were partially executed, or what happened to the
price. Those are the analyst's job. Gross submitted size (not net resting) is the classic naive choice
that makes active market makers and algos light up.

One alert per trader and instrument per cooldown period; repeated cycles inside the cooldown are left to
the `repetitions_in_session` discriminator.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from market_sim.types import NS_PER_S, EventType, OrderType, Side

DETECTOR_VERSION = "spoof-naive-v1"

ALERT_COLUMNS = [
    "alert_id",
    "date",
    "scenario",
    "instrument",
    "trader_id",
    "trigger",
    "trigger_ts",
    "window_start",
    "window_end",
    "trigger_summary",
    "detector_version",
    "detector_params",
    "status",
]


@dataclass(frozen=True)
class DetectorParams:
    window_s: float = 60.0  # W
    k_depth: float = 3.25  # K: tuned so background market makers trip it a couple of times a day
    cancel_pct: float = 70.0  # P
    cancel_within_s: float = 5.0  # C
    large_quick_k: float = 6.0  # K2
    large_quick_within_s: float = 10.0  # C2
    cooldown_s: float = 900.0
    layering_min_levels: int = 3

    def to_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True)


def _fmt_ts(ts: int) -> str:
    return pd.Timestamp(int(ts)).strftime("%H:%M:%S.%f")[:-3]


class _TraderTape:
    """Per-trader numpy views used by both triggers."""

    def __init__(self, ev: pd.DataFrame) -> None:
        ev = ev.sort_values("ts", kind="stable")
        self.ev = ev
        ts = ev["ts"].to_numpy(dtype=np.int64)
        event = ev["event"].to_numpy()
        side = ev["side"].to_numpy()
        otype = ev["order_type"].to_numpy()
        qty = ev["qty"].to_numpy(dtype=np.int64)
        rem = ev["remaining_qty"].to_numpy(dtype=np.int64)
        price = ev["price_ticks"].to_numpy()
        oid = ev["order_id"].to_numpy()
        self.ts, self.event, self.side, self.qty, self.rem, self.price, self.oid, self.otype = (
            ts,
            event,
            side,
            qty,
            rem,
            price,
            oid,
            otype,
        )
        nonmkt = otype != str(OrderType.MARKET)
        self.by_side: dict[str, dict[str, np.ndarray]] = {}
        for s in (str(Side.BUY), str(Side.SELL)):
            m = side == s
            is_new = m & nonmkt & (event == str(EventType.NEW))
            is_cancel = m & nonmkt & (event == str(EventType.CANCEL))
            is_reduce = m & nonmkt & (event == str(EventType.MODIFY)) & (qty < 0)
            cancelled_qty = np.where(is_cancel, qty, np.where(is_reduce, -qty, 0))
            is_fill_nonmkt = m & nonmkt & np.isin(event, [str(EventType.FILL), str(EventType.PARTIAL_FILL)])
            delta = (
                np.where(is_new, qty, 0)
                - np.where(is_fill_nonmkt, qty, 0)
                - cancelled_qty
                + np.where(m & nonmkt & (event == str(EventType.MODIFY)) & (qty > 0), qty, 0)
            )
            resting_cum = np.cumsum(delta)
            self.by_side[s] = {
                "new_ts": ts[is_new],
                "new_qty_cum": np.concatenate([[0], np.cumsum(qty[is_new])]),
                "new_qty": qty[is_new],
                "new_price": price[is_new],
                "new_oid": oid[is_new],
                "cancel_ts": ts[is_cancel | is_reduce],
                "cancel_qty_cum": np.concatenate([[0], np.cumsum(cancelled_qty[is_cancel | is_reduce])]),
                "resting_cum": resting_cum,
            }
        self.fill_idx = np.flatnonzero(np.isin(event, [str(EventType.FILL), str(EventType.PARTIAL_FILL)]))
        # order lifecycle for level counting: non-market orders, open interval [ts_new, ts_closed)
        self.orders: dict[str, tuple[int, int, str, int]] = {}  # oid -> (ts_new, ts_closed, side, price)
        for i in np.flatnonzero(nonmkt & (event == str(EventType.NEW))):
            self.orders[oid[i]] = (
                int(ts[i]),
                np.iinfo(np.int64).max,
                side[i],
                int(price[i]) if price[i] is not None and not pd.isna(price[i]) else 0,
            )
        closed = np.flatnonzero(nonmkt & (rem == 0) & (event != str(EventType.NEW)))
        for i in closed:
            o = self.orders.get(oid[i])
            if o is not None and o[1] == np.iinfo(np.int64).max:
                self.orders[oid[i]] = (o[0], int(ts[i]), o[2], o[3])

    @staticmethod
    def _window_sum(ts_arr: np.ndarray, cum: np.ndarray, lo: int, hi: int) -> int:
        a = np.searchsorted(ts_arr, lo, side="left")
        b = np.searchsorted(ts_arr, hi, side="right")
        return int(cum[b] - cum[a])

    def gross_new(self, side: str, lo: int, hi: int) -> int:
        d = self.by_side[side]
        return self._window_sum(d["new_ts"], d["new_qty_cum"], lo, hi)

    def cancelled(self, side: str, lo: int, hi: int) -> int:
        d = self.by_side[side]
        return self._window_sum(d["cancel_ts"], d["cancel_qty_cum"], lo, hi)

    def resting_at(self, side: str, t: int) -> int:
        d = self.by_side[side]
        i = np.searchsorted(self.ts, t, side="right") - 1
        return int(d["resting_cum"][i]) if i >= 0 else 0

    def levels_at(self, side: str, t: int) -> int:
        return len({p for (t0, t1, s, p) in self.orders.values() if s == side and t0 <= t < t1})


def _candidates_for_trader(tape: _TraderTape, depth: float, p: DetectorParams) -> list[dict]:
    W = int(p.window_s * NS_PER_S)  # noqa: N806  (documented parameter names)
    C = int(p.cancel_within_s * NS_PER_S)  # noqa: N806
    C2 = int(p.large_quick_within_s * NS_PER_S)  # noqa: N806
    out: list[dict] = []

    # trigger 1
    for i in tape.fill_idx:
        tf = int(tape.ts[i])
        x = tape.side[i]
        y = str(Side.SELL) if x == str(Side.BUY) else str(Side.BUY)
        gross = tape.gross_new(y, tf - W, tf)
        if gross < p.k_depth * depth:
            continue
        resting = tape.resting_at(y, tf)
        if resting <= 0:
            continue
        cancelled = tape.cancelled(y, tf, tf + C)
        if cancelled < p.cancel_pct / 100.0 * resting:
            continue
        levels = tape.levels_at(y, tf)
        out.append(
            {
                "trigger": "OPPOSITE_FILL_CANCEL",
                "trigger_ts": tf,
                "window_start": tf - W,
                "window_end": tf + C,
                "levels": levels,
                "summary": (
                    f"gross {y} size {gross} submitted in {p.window_s:.0f}s >= {p.k_depth:g} x avg top-5 depth "
                    f"({depth:.0f}); "
                    f"{x} execution of {int(tape.qty[i])} at {_fmt_ts(tf)}; {cancelled} cancelled on {y} within "
                    f"{p.cancel_within_s:g}s against {resting} resting at the execution"
                ),
            }
        )

    # trigger 2
    for y in (str(Side.BUY), str(Side.SELL)):
        d = tape.by_side[y]
        big = np.flatnonzero(d["new_qty"] >= p.large_quick_k * depth)
        for j in big:
            t0 = int(d["new_ts"][j])
            q = int(d["new_qty"][j])
            cancelled = tape.cancelled(y, t0, t0 + C2)
            if cancelled >= p.cancel_pct / 100.0 * q:
                out.append(
                    {
                        "trigger": "LARGE_QUICK_CANCEL",
                        "trigger_ts": t0,
                        "window_start": t0 - 5 * NS_PER_S,
                        "window_end": t0 + C2,
                        "levels": tape.levels_at(y, t0 + 1),
                        "summary": (
                            f"single {y} order of {q} ({q / depth:.1f} x avg top-5 depth) placed at {_fmt_ts(t0)}; "
                            f"{cancelled} cancelled within {p.large_quick_within_s:g}s"
                        ),
                    }
                )
    out.sort(key=lambda c: c["trigger_ts"])
    return out


def detect(
    order_events: pd.DataFrame, instrument_stats: pd.DataFrame, params: DetectorParams | None = None
) -> pd.DataFrame:
    """Run the detector over a tape covering one or more dates. Returns the alerts table."""
    p = params or DetectorParams()
    depth_by = {(r.instrument, r.date): float(r.avg_depth_top5) for r in instrument_stats.itertuples()}
    rows: list[dict] = []
    cooldown = int(p.cooldown_s * NS_PER_S)
    for (date, instrument, trader_id), ev in order_events.groupby(["date", "instrument", "trader_id"], sort=True):
        depth = depth_by.get((instrument, date))
        if not depth or depth <= 0:
            continue
        tape = _TraderTape(ev)
        if len(tape.fill_idx) == 0 and not any(
            len(np.flatnonzero(tape.by_side[s]["new_qty"] >= p.large_quick_k * depth)) for s in tape.by_side
        ):
            continue
        accepted: list[dict] = []
        for c in _candidates_for_trader(tape, depth, p):
            if accepted:
                last = accepted[-1]
                if c["window_start"] <= last["window_end"]:
                    # same episode: take the union of the windows, keep the stronger trigger, join the summaries
                    last["window_start"] = min(last["window_start"], c["window_start"])
                    last["window_end"] = max(last["window_end"], c["window_end"])
                    last["levels"] = max(last["levels"], c["levels"])
                    if c["trigger"] == "OPPOSITE_FILL_CANCEL" and last["trigger"] != "OPPOSITE_FILL_CANCEL":
                        last["trigger"] = c["trigger"]
                        last["summary"] = c["summary"] + " | also: " + last["summary"]
                    elif c["trigger_ts"] != last.get("last_merged_ts") and last["summary"].count(" | also: ") < 2:
                        # one line per distinct moment, at most three lines: partial fills of one order are one moment
                        last["summary"] = last["summary"] + " | also: " + c["summary"]
                    last["last_merged_ts"] = c["trigger_ts"]
                    continue
                if c["trigger_ts"] - last["trigger_ts"] < cooldown:
                    continue
            accepted.append(dict(c))
        for c in accepted:
            rows.append(
                {
                    "date": date,
                    "scenario": "LAYERING" if c["levels"] >= p.layering_min_levels else "SPOOFING",
                    "instrument": instrument,
                    "trader_id": trader_id,
                    "trigger": c["trigger"],
                    "trigger_ts": int(c["trigger_ts"]),
                    "window_start": int(c["window_start"]),
                    "window_end": int(c["window_end"]),
                    "trigger_summary": c["summary"],
                    "detector_version": DETECTOR_VERSION,
                    "detector_params": p.to_json(),
                    "status": "OPEN",
                }
            )
    alerts = pd.DataFrame(rows, columns=[c for c in ALERT_COLUMNS if c != "alert_id"])
    alerts = alerts.sort_values(["date", "trigger_ts"], kind="stable").reset_index(drop=True)
    ids = []
    seq: dict[str, int] = {}
    for d in alerts["date"]:
        seq[d] = seq.get(d, 0) + 1
        ids.append(f"A-{d[2:4]}{d[5:7]}{d[8:10]}-{seq[d]:04d}")
    alerts.insert(0, "alert_id", ids)
    return alerts[ALERT_COLUMNS]
