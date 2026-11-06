"""Threshold re-tuning report (data doc section 4.5.4): grid-search the detector's K, P and C on the labelled
dataset and report precision at 100% recall on injected abuse, old parameters vs the best found.

    uv run python -m detector.tune                       # seed7, default grid, prints the report
    uv run python -m detector.tune --out evals/runs/tune-seed7.md

The result is applied only to the next dataset build (`build_dataset.py --k-depth ...`), never to the alerts the
agent was evaluated on: changing the alert population under a finished run would make its numbers incomparable.

What "better" means here: fewer alerts for the analysts to read (detector precision up) while every injected
TRUE_ABUSE scenario still raises at least one alert (recall 1.0 on injections). Background market-maker alerts
are the detector's own noise and count against precision; injected FALSE_POSITIVE scenarios also count against
it, since those are false positives by construction.
"""

from __future__ import annotations

import argparse
import itertools
import sys
import time
from dataclasses import replace
from pathlib import Path

import pandas as pd

from detector.labels import attribute, missed_injections
from detector.rule import DetectorParams, detect
from market_sim.types import Truth

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASET = ROOT / "data" / "synthetic" / "seed7"

GRID = {
    "k_depth": [2.5, 3.25, 4.0, 5.0, 6.0],
    "cancel_pct": [60.0, 70.0, 80.0, 90.0],
    "cancel_within_s": [2.0, 5.0, 10.0],
}


def score(
    order_events: pd.DataFrame, stats: pd.DataFrame, injections: pd.DataFrame, traders: pd.DataFrame, p: DetectorParams
) -> dict:
    alerts = detect(order_events, stats, p)
    labels = attribute(alerts, injections, traders, p.window_s, p.cancel_within_s)
    missed = missed_injections(alerts, injections, p.window_s, p.cancel_within_s)
    missed_true = int((missed["truth"] == str(Truth.TRUE_ABUSE)).sum()) if len(missed) else 0
    n_inj_true = int((injections["truth"] == str(Truth.TRUE_ABUSE)).sum())
    n = len(labels)
    n_true = int((labels["truth"] == str(Truth.TRUE_ABUSE)).sum())
    n_bg = int((labels["injected_scenario"] == "BACKGROUND").sum())
    return {
        "k_depth": p.k_depth,
        "cancel_pct": p.cancel_pct,
        "cancel_within_s": p.cancel_within_s,
        "alerts": n,
        "true_abuse_alerts": n_true,
        "false_positive_alerts": n - n_true,
        "background_alerts": n_bg,
        "precision": round(n_true / n, 4) if n else 0.0,
        "injection_recall": round((n_inj_true - missed_true) / n_inj_true, 4) if n_inj_true else None,
        "missed_true_injections": missed_true,
    }


def run(dataset: Path, grid: dict[str, list] = GRID) -> tuple[pd.DataFrame, dict, dict]:
    order_events = pd.read_parquet(dataset / "order_events.parquet")
    stats = pd.read_parquet(dataset / "instrument_stats.parquet")
    injections = pd.read_parquet(dataset / "labels" / "injections.parquet")
    traders = pd.read_parquet(dataset / "traders.parquet")
    base = DetectorParams()
    rows = []
    for k, pct, c in itertools.product(grid["k_depth"], grid["cancel_pct"], grid["cancel_within_s"]):
        p = replace(base, k_depth=k, cancel_pct=pct, cancel_within_s=c)
        rows.append(score(order_events, stats, injections, traders, p))
    df = pd.DataFrame(rows)
    old = next(
        r
        for r in rows
        if r["k_depth"] == base.k_depth
        and r["cancel_pct"] == base.cancel_pct
        and r["cancel_within_s"] == base.cancel_within_s
    )
    full = df[df["injection_recall"] >= 1.0]
    best = full.sort_values(["precision", "alerts"], ascending=[False, True]).iloc[0].to_dict() if len(full) else old
    return df, old, best


def render(df: pd.DataFrame, old: dict, best: dict, dataset: Path, elapsed_s: float) -> str:
    L = [f"# Detector threshold re-tuning on `{dataset.name}`", ""]
    L.append(
        f"Grid of {len(df)} parameter sets over K (size vs depth), P (cancel percent) and C (cancel window), "
        f"W fixed at {DetectorParams().window_s:g} s; {elapsed_s:.0f} s. Recall is on injected TRUE_ABUSE scenarios "
        f"and must be 1.0; precision is TRUE_ABUSE alerts over all alerts."
    )
    L.append("")
    L.append("| | K | P | C | alerts | TRUE_ABUSE | false positives | background | precision | injection recall |")
    L.append("|---|---|---|---|---|---|---|---|---|---|")
    for name, r in (("current (used for the evaluated dataset)", old), ("best at 100% recall", best)):
        L.append(
            f"| {name} | {r['k_depth']:g} | {r['cancel_pct']:g} | {r['cancel_within_s']:g} | {r['alerts']} | {r['true_abuse_alerts']} "
            f"| {r['false_positive_alerts']} | {r['background_alerts']} | {100 * r['precision']:.1f}% | {r['injection_recall']} |"
        )
    L.append("")
    sweep = df[(df["cancel_pct"] == old["cancel_pct"]) & (df["cancel_within_s"] == old["cancel_within_s"])].sort_values(
        "k_depth"
    )
    L.append(f"K alone (P={old['cancel_pct']:g}, C={old['cancel_within_s']:g}):")
    L.append("")
    L.append("| K | alerts | precision | injection recall | missed true injections |")
    L.append("|---|---|---|---|---|")
    for r in sweep.itertuples():
        L.append(
            f"| {r.k_depth:g} | {r.alerts} | {100 * r.precision:.1f}% | {r.injection_recall} | {r.missed_true_injections} |"
        )
    L.append("")
    frontier = df[df["injection_recall"] >= 1.0].sort_values(["precision", "alerts"], ascending=[False, True]).head(8)
    L.append("Top parameter sets that keep recall at 1.0:")
    L.append("")
    L.append("| K | P | C | alerts | precision |")
    L.append("|---|---|---|---|---|")
    for r in frontier.itertuples():
        L.append(
            f"| {r.k_depth:g} | {r.cancel_pct:g} | {r.cancel_within_s:g} | {r.alerts} | {100 * r.precision:.1f}% |"
        )
    L.append("")
    L.append(
        "Applies to the next dataset build only (`scripts/build_dataset.py --k-depth ...`); the evaluated dataset keeps its "
        "parameters so that run-to-run comparisons stay on the same 167 alerts."
    )
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    t0 = time.time()
    df, old, best = run(args.dataset)
    md = render(df, old, best, args.dataset, time.time() - t0)
    print(md)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(md)
        df.to_csv(args.out.with_suffix(".csv"), index=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
