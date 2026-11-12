"""Is the agent's `confidence` worth reading? Agreement with the label by proposed disposition and confidence band,
pooled over the runs given (default: the promoted run, the generalisation run and the variance run).

    uv run evals/calibration.py
    uv run evals/calibration.py evals/runs/<run_a> evals/runs/<run_b> ...

`confidence` is defined in the prompt as the agent's probability that a Level-2 reviewer would record the same
disposition after reading the tape. For an escalation the question that matters is whether the label escalates at
all (ESCALATE or DRAFT_STOR), so that column is shown beside exact agreement.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUNS = [
    ROOT / "evals/runs/20261110T1833-sonnet-v4",
    ROOT / "evals/runs/20261111T1326-seed8-generalisation",
    ROOT / "evals/runs/20261111T0950-variance-v4",
]
BANDS = [(0.0, 0.65, "< 0.65"), (0.65, 0.75, "0.65-0.74"), (0.75, 0.85, "0.75-0.84"), (0.85, 1.01, ">= 0.85")]


def band(c: float) -> str:
    for lo, hi, name in BANDS:
        if lo <= c < hi:
            return name
    return "?"


def main() -> int:
    runs = [Path(p) for p in sys.argv[1:]] or DEFAULT_RUNS
    frames = []
    for r in runs:
        df = pd.read_csv(r / "per_alert.csv")
        df["run"] = r.name
        frames.append(df)
    df = pd.concat(frames)
    df = df[df.proposed.notna() & df.confidence.notna()].copy()
    df["agree"] = df.proposed == df.expected_disposition
    df["label_escalates"] = df.expected_disposition != "CLOSE_FP"
    df["band"] = df.confidence.apply(band)
    order = [b[2] for b in BANDS]
    print(f"{len(df)} proposals from {len(runs)} runs: {', '.join(r.name for r in runs)}\n")

    e = df[df.proposed.isin(["ESCALATE", "DRAFT_STOR"])]
    g = (
        e.groupby("band")
        .agg(n=("agree", "size"), label_escalates=("label_escalates", "mean"), exact_agree=("agree", "mean"))
        .reindex([b for b in order if b in set(e.band)])
    )
    print("ESCALATE / DRAFT_STOR proposals, by confidence band")
    print("  band        n   label escalates   exact disposition agrees")
    for b, row in g.iterrows():
        print(f"  {b:10s} {int(row.n):3d}   {row.label_escalates:14.0%}   {row.exact_agree:22.0%}")

    c = df[df.proposed == "CLOSE_FP"]
    g = (
        c.groupby("band")
        .agg(n=("agree", "size"), label_closes=("agree", "mean"))
        .reindex([b for b in order if b in set(c.band)])
    )
    print("\nCLOSE_FP proposals, by confidence band")
    print("  band        n   label closes")
    for b, row in g.iterrows():
        print(f"  {b:10s} {int(row.n):3d}   {row.label_closes:12.0%}")

    print("\nESCALATE / DRAFT_STOR confidence by scenario (n, mean, min, max)")
    s = e.groupby("injected_scenario").confidence.agg(["count", "mean", "min", "max"]).sort_values("mean")
    for scen, row in s.iterrows():
        print(f"  {scen:20s} {int(row['count']):3d}   {row['mean']:.2f}   {row['min']:.2f}-{row['max']:.2f}")
    print("\nCLOSE_FP confidence by scenario (n, mean, min, max)")
    s = c.groupby("injected_scenario").confidence.agg(["count", "mean", "min", "max"]).sort_values("mean")
    for scen, row in s.iterrows():
        print(f"  {scen:20s} {int(row['count']):3d}   {row['mean']:.2f}   {row['min']:.2f}-{row['max']:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
