"""Replay one alert from a built dataset for a human sanity check: the trader's events in and around the
window, the discriminators, the baseline's view, and (only if --reveal) the label.

    uv run scripts/replay_alert.py data/synthetic/seed7 A-261005-0002
    uv run scripts/replay_alert.py data/synthetic/seed7 --random 3 --reveal
    uv run scripts/replay_alert.py data/synthetic/seed7 --scenario F-SPOOFLIKE-HARD-1 --reveal
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from detector.baseline import classify
from tools.discriminators import compute_discriminators

NS = 1_000_000_000


def hhmmss(ts: int) -> str:
    return pd.Timestamp(int(ts)).strftime("%H:%M:%S.%f")[:-3]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dataset")
    ap.add_argument("alert_id", nargs="?")
    ap.add_argument("--random", type=int, default=0, help="replay N random alerts")
    ap.add_argument("--scenario", help="pick alerts of this injected scenario (uses labels)")
    ap.add_argument("--reveal", action="store_true", help="print the ground-truth label at the end")
    ap.add_argument("--pad", type=float, default=15.0, help="seconds of context before/after the window")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    root = Path(args.dataset)
    alerts = pd.read_parquet(root / "alerts.parquet")
    labels = pd.read_parquet(root / "labels" / "labels.parquet")
    traders = pd.read_parquet(root / "traders.parquet").set_index("trader_id")
    stats = pd.read_parquet(root / "instrument_stats.parquet")
    market_events = pd.read_parquet(root / "market_events.parquet")
    oe = pd.read_parquet(root / "order_events.parquet")

    rng = np.random.default_rng(args.seed)
    if args.alert_id:
        ids = [args.alert_id]
    elif args.scenario:
        pool = labels[labels.injected_scenario == args.scenario].alert_id.tolist()
        ids = list(rng.choice(pool, size=min(max(1, args.random or 1), len(pool)), replace=False))
    else:
        ids = list(rng.choice(alerts.alert_id.tolist(), size=max(1, args.random), replace=False))

    pd.set_option("display.width", 220)
    for aid in ids:
        a = alerts[alerts.alert_id == aid].iloc[0].to_dict()
        day = oe[oe.date == a["date"]]
        mine = day[day.trader_id == a["trader_id"]]
        depth = float(stats[(stats.instrument == a["instrument"]) & (stats.date == a["date"])].avg_depth_top5.iloc[0])
        prof = traders.loc[a["trader_id"]].to_dict()
        w0, w1 = int(a["window_start"]), int(a["window_end"])
        print("=" * 110)
        print(
            f"{aid}  {a['date']}  {a['instrument']}  trader {a['trader_id']}  [{prof['role']}, desk {prof['desk']}, "
            f"MM on {prof['registered_mm_instruments']}, typical size {prof['typical_order_size']}, typical OTR {prof['typical_daily_otr']}]"
        )
        print(
            f"detector: {a['scenario']} via {a['trigger']}  window {hhmmss(w0)} .. {hhmmss(w1)}  (avg top-5 depth {depth:.0f})"
        )
        print(f"  {a['trigger_summary']}")
        risk = json.loads(prof["risk_limit_events"]) if isinstance(prof["risk_limit_events"], str) else []
        if risk:
            print(f"risk events: {[(hhmmss(e['ts']), e['reason']) for e in risk]}")
        me = market_events[
            (market_events.date == a["date"])
            & (market_events.ts >= w0 - int(args.pad * NS))
            & (market_events.ts <= w1 + int(args.pad * NS))
        ]
        if not me.empty:
            print(
                "market events in/near window: "
                + "; ".join(f"{hhmmss(r.ts)} {r.type} {r.description}" for r in me.itertuples())
            )
        ctx = mine[(mine.ts >= w0 - int(args.pad * NS)) & (mine.ts <= w1 + int(args.pad * NS))].copy()
        ctx["t"] = ctx.ts.map(hhmmss)
        ctx["in_window"] = np.where((ctx.ts >= w0) & (ctx.ts <= w1), "*", "")
        cols = [
            "t",
            "in_window",
            "event",
            "side",
            "price_ticks",
            "qty",
            "remaining_qty",
            "order_type",
            "parent_order_id",
            "best_bid",
            "best_ask",
        ]
        print(f"--- trader's events ({len(ctx)} rows; * = inside the alert window)")
        print(ctx[cols].to_string(index=False, max_rows=60))
        d = compute_discriminators(a, mine, depth, all_events=day).to_dict()
        print("--- discriminators")
        for k in (
            "dominant_side",
            "gross_submitted_dominant",
            "gross_submitted_other",
            "otr",
            "cancel_ratio",
            "median_cancel_latency_ms",
            "max_resting_size_vs_depth",
            "distance_from_touch_ticks",
            "distinct_price_levels",
            "same_side_fill_qty",
            "opposite_side_fill_qty",
            "modify_reduction_qty",
            "cancel_symmetry",
            "price_move_ticks",
            "reversion_ticks",
            "round_trip_ticks",
            "repetitions_in_session",
            "market_wide_cancels_1s_before_first_cancel",
            "order_types",
            "parent_order_ids",
            "notes",
        ):
            v = d[k]
            print(f"  {k:<44} {round(v, 3) if isinstance(v, float) else v}")
        b = classify(d, prof, me.to_dict("records") if not me.empty else [], a)
        print(f"--- threshold baseline: {b.disposition}  ({b.rule}: {b.reason})")
        if args.reveal:
            lab = labels[labels.alert_id == aid].iloc[0]
            print(f"--- LABEL: {lab.truth}  scenario {lab.injected_scenario}  expected {lab.expected_disposition}")
            print(f"    key discriminators: {lab.key_discriminators}")
            print(f"    {lab.notes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
