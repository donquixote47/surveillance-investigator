"""Build a labelled synthetic dataset: N session days of simulated market with injected scenarios, run the
noisy detector, attribute labels, compute discriminators and the threshold baseline, write parquet + manifest.

    uv run scripts/build_dataset.py --seed 9 --sessions 20 --start-date 2026-12-01      # a new dataset, latest catalogue
    uv run scripts/build_dataset.py --seed 7 --sessions 20 --catalogue 1                # rebuild seed7 as it was built

The scenario mix is sampled from a versioned catalogue (`market_sim.scenarios.CATALOGUE_LATEST`); a dataset can be
rebuilt identically only from the catalogue it was built from. seed7 and seed8 are catalogue 1 (their manifests
predate the field). The script refuses to write over an existing dataset with a different catalogue.

Labels and injections are written under <out>/labels/ and must never be loaded by anything the agent can call.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from detector.baseline import classify
from detector.labels import attribute, coverage, missed_injections
from detector.rule import DETECTOR_VERSION, DetectorParams, detect
from market_sim.config import SimConfig
from market_sim.run import MixConfig, run_session
from market_sim.scenarios import CATALOGUE_LATEST
from market_sim.types import Disposition, Truth
from tools.discriminators import compute_discriminators

GENERATOR_VERSION = "market-sim-0.1"


def business_days(start: str, n: int) -> list[str]:
    return [d.strftime("%Y-%m-%d") for d in pd.bdate_range(start, periods=n)]


def consolidate_traders(frames: list[pd.DataFrame], order_events: pd.DataFrame) -> pd.DataFrame:
    """One row per trader. Background traders get their typical size and OTR from the tape; scenario
    traders keep the profile values their scenario assigned (their tape *is* the scenario)."""
    traders = pd.concat(frames, ignore_index=True)
    risk = traders.groupby("trader_id")["risk_limit_events"].apply(
        lambda s: json.dumps([e for x in s for e in json.loads(x)])
    )
    traders = traders.drop_duplicates("trader_id", keep="first").set_index("trader_id")
    traders["risk_limit_events"] = risk
    bg = ~traders.index.str.startswith("T-X")
    oe = order_events[order_events.trader_id.isin(traders.index[bg])]
    size = oe[oe.event == "NEW"].groupby("trader_id")["qty"].median()
    per_day = oe.groupby(["trader_id", "date"]).apply(
        lambda g: (
            (g.event.isin(["NEW", "MODIFY", "CANCEL"]).sum()) / max(1, g.event.isin(["FILL", "PARTIAL_FILL"]).sum())
        ),
        include_groups=False,
    )
    otr = per_day.groupby("trader_id").median()
    traders.loc[size.index, "typical_order_size"] = size.astype(int)
    traders.loc[otr.index, "typical_daily_otr"] = otr.round(1)
    return traders.reset_index()


def benign_history(traders: pd.DataFrame, first_date: str) -> pd.DataFrame:
    """A few prior dispositions for background desks, so Memory and get_trader_alert_history have texture."""
    base = pd.Timestamp(first_date)
    rows = []
    notes = {
        "MARKET_MAKER": "registered market maker; two-sided quotes re-priced on fair value moves; no opposite-side benefit",
        "ALGO": "pegged execution algo; children of a client parent order; cancels are re-pegs",
    }
    for r in traders.itertuples():
        if r.role in notes and not r.trader_id.startswith("T-X"):
            for k in range(2):
                when = base - pd.Timedelta(days=12 + 10 * k)
                rows.append(
                    {
                        "alert_id": f"H-{r.trader_id}-{k + 1:02d}",
                        "trader_id": r.trader_id,
                        "instrument": "SYN.A",
                        "date": when.strftime("%Y-%m-%d"),
                        "scenario": "SPOOFING",
                        "proposed_disposition": "CLOSE_FP",
                        "recorded_disposition": "CLOSE_FP",
                        "recorded_by": "L1-analyst-01",
                        "analyst_note": notes[r.role],
                        "override": False,
                    }
                )
    return pd.DataFrame(rows)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--sessions", type=int, default=20)
    ap.add_argument("--start-date", default="2026-10-05")
    ap.add_argument("--out", default=None, help="default data/synthetic/seed<seed>")
    ap.add_argument("--true-per-session", type=float, default=1.3)
    ap.add_argument("--false-per-session", type=float, default=4.0)
    ap.add_argument("--k-depth", type=float, default=DetectorParams().k_depth)
    ap.add_argument(
        "--catalogue",
        type=int,
        default=CATALOGUE_LATEST,
        choices=range(1, CATALOGUE_LATEST + 1),
        help=f"scenario catalogue version to sample the mix from (default: the latest, {CATALOGUE_LATEST}; "
        "seed7 and seed8 were built from 1)",
    )
    args = ap.parse_args()

    out = Path(args.out or f"data/synthetic/seed{args.seed}")
    existing = out / "manifest.json"
    if existing.exists():
        built_from = int(json.loads(existing.read_text()).get("catalogue", 1))  # manifests before the field: 1
        if built_from != args.catalogue:
            raise SystemExit(
                f"{out} was built from scenario catalogue {built_from}; this run would sample from catalogue "
                f"{args.catalogue} and write a different dataset over it. Pass --catalogue {built_from} to rebuild "
                "it as it was, or --out for a new dataset."
            )
    (out / "labels").mkdir(parents=True, exist_ok=True)
    cfg = SimConfig()
    mix = MixConfig(
        true_per_session=args.true_per_session, false_per_session=args.false_per_session, catalogue=args.catalogue
    )
    params = DetectorParams(k_depth=args.k_depth)
    dates = business_days(args.start_date, args.sessions)

    t0 = time.time()
    parts: dict[str, list[pd.DataFrame]] = {
        k: []
        for k in (
            "order_events",
            "trades",
            "traders",
            "market_events",
            "instrument_stats",
            "injections",
            "cases_history",
        )
    }
    for i, date in enumerate(dates):
        tab = run_session(cfg, seed=args.seed * 1000 + i, date=date, mix=mix)
        for k in parts:
            parts[k].append(getattr(tab, k))
        print(f"  {date}: {len(tab.order_events):>7,} events, {len(tab.injections)} injections", flush=True)
    sim_s = time.time() - t0

    order_events = pd.concat(parts["order_events"], ignore_index=True)
    trades = pd.concat(parts["trades"], ignore_index=True)
    market_events = pd.concat(parts["market_events"], ignore_index=True)
    stats = pd.concat(parts["instrument_stats"], ignore_index=True)
    injections = pd.concat(parts["injections"], ignore_index=True)
    traders = consolidate_traders(parts["traders"], order_events)
    history = pd.concat([*parts["cases_history"], benign_history(traders, dates[0])], ignore_index=True)

    t1 = time.time()
    alerts = detect(order_events, stats, params)
    labels = attribute(alerts, injections, traders, params.window_s, params.cancel_within_s)
    det_s = time.time() - t1
    missed = missed_injections(alerts, injections, params.window_s, params.cancel_within_s)
    cov = coverage(injections, labels)

    # discriminators + baseline for every alert (the baseline is a foil for the agent; its outputs live with the labels)
    t2 = time.time()
    depth_by = {(r.instrument, r.date): float(r.avg_depth_top5) for r in stats.itertuples()}
    prof_by = traders.set_index("trader_id").to_dict("index")
    ev_by_date = {d: g for d, g in order_events.groupby("date")}
    me_by_date = {d: g.to_dict("records") for d, g in market_events.groupby("date")}
    disc_rows, base_rows = [], []
    for a in alerts.to_dict("records"):
        day = ev_by_date[a["date"]]
        d = compute_discriminators(
            a, day[day.trader_id == a["trader_id"]], depth_by[(a["instrument"], a["date"])], all_events=day
        )
        dd = d.to_dict()
        row = {k: (json.dumps(v) if isinstance(v, (list, dict)) else v) for k, v in dd.items()}
        row["otr"] = float("inf") if dd["otr"] == "inf" else dd["otr"]  # keep the column numeric in parquet
        disc_rows.append(row)
        b = classify(dd, prof_by[a["trader_id"]], me_by_date.get(a["date"], []), a)
        base_rows.append(
            {
                "alert_id": a["alert_id"],
                "baseline_disposition": b.disposition,
                "baseline_rule": b.rule,
                "baseline_reason": b.reason,
            }
        )
    discriminators = pd.DataFrame(disc_rows)
    baseline = pd.DataFrame(base_rows)
    disc_s = time.time() - t2

    # --- baseline metrics against the labels ---
    j = baseline.merge(labels[["alert_id", "truth", "expected_disposition", "injected_scenario"]], on="alert_id")
    true_mask = j.truth == str(Truth.TRUE_ABUSE)
    fp_mask = ~true_mask
    missed_true = int((true_mask & (j.baseline_disposition == str(Disposition.CLOSE_FP))).sum())
    safe_close = float((fp_mask & (j.baseline_disposition == str(Disposition.CLOSE_FP))).sum() / max(1, fp_mask.sum()))
    per_scen = (
        j.assign(closed=j.baseline_disposition == str(Disposition.CLOSE_FP))
        .groupby("injected_scenario")["closed"]
        .agg(["mean", "size"])
    )
    gate_fail = j[true_mask & (j.baseline_disposition == str(Disposition.CLOSE_FP))][
        ["alert_id", "injected_scenario", "baseline_rule"]
    ]

    # --- write ---
    for name, df in {
        "order_events": order_events,
        "trades": trades,
        "traders": traders,
        "market_events": market_events,
        "instrument_stats": stats,
        "alerts": alerts,
        "cases_history": history,
    }.items():
        df.to_parquet(out / f"{name}.parquet", index=False)
    labels.to_parquet(out / "labels" / "labels.parquet", index=False)
    injections.to_parquet(out / "labels" / "injections.parquet", index=False)
    discriminators.to_parquet(out / "labels" / "discriminators.parquet", index=False)
    baseline.to_parquet(out / "labels" / "baseline.parquet", index=False)

    n_true = int((labels.truth == str(Truth.TRUE_ABUSE)).sum())
    manifest = {
        "seed": args.seed,
        "sessions": args.sessions,
        "dates": dates,
        "generator_version": GENERATOR_VERSION,
        "catalogue": args.catalogue,
        "detector_version": DETECTOR_VERSION,
        "detector_params": json.loads(params.to_json()),
        "mix": {"true_per_session": mix.true_per_session, "false_per_session": mix.false_per_session},
        "sim_config": cfg.model_dump(),
        "counts": {
            "order_events": len(order_events),
            "trades": len(trades),
            "traders": len(traders),
            "alerts": len(alerts),
            "true_abuse": n_true,
            "false_positive": int(len(labels) - n_true),
            "background_alerts": int((labels.injected_scenario == "BACKGROUND").sum()),
            "injections": len(injections),
            "missed_injections": len(missed),
        },
        "detector": {
            "recall_on_true_injections": 1.0
            if (missed.truth == str(Truth.TRUE_ABUSE)).sum() == 0
            else float(
                1
                - (missed.truth == str(Truth.TRUE_ABUSE)).sum()
                / max(1, (injections.truth == str(Truth.TRUE_ABUSE)).sum())
            ),
            "precision": float(n_true / max(1, len(labels))),
        },
        "baseline": {
            "missed_true": missed_true,
            "safe_close_rate": None if missed_true else round(safe_close, 3),
            "safe_close_rate_raw": round(safe_close, 3),
        },
        "timing_s": {
            "simulate": round(sim_s, 1),
            "detect": round(det_s, 1),
            "discriminators": round(disc_s, 1),
        },
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2))

    # --- report ---
    lines = [
        f"# Dataset {out.name}",
        "",
        f"seed {args.seed}, {args.sessions} sessions {dates[0]}..{dates[-1]}, generator {GENERATOR_VERSION} (scenario catalogue {args.catalogue}), detector {DETECTOR_VERSION} {params.to_json()}",
        "",
        f"- order events: {len(order_events):,}; trades: {len(trades):,}; traders: {len(traders)}",
        f"- alerts: {len(alerts)} ({n_true} TRUE_ABUSE = {n_true / max(1, len(alerts)):.0%}; {manifest['counts']['background_alerts']} background)",
        f"- detector recall on injected abuse: {manifest['detector']['recall_on_true_injections']:.0%}; precision: {manifest['detector']['precision']:.0%}",
        f"- missed injections: {len(missed)}" + ("" if missed.empty else "\n\n" + missed.to_string(index=False)),
        "",
        "## Coverage per scenario (injected vs alerts attributed)",
        "",
        cov.to_string(),
        "",
        "## Threshold baseline (no LLM)",
        "",
        f"- gate: {missed_true} TRUE_ABUSE alerts proposed CLOSE_FP"
        + ("" if not missed_true else " -> GATE FAILED; safe close rate reported as n/a"),
        f"- safe close rate: {'n/a (gate failed)' if missed_true else f'{safe_close:.0%}'} (raw {safe_close:.0%})",
        "",
        "Share proposed CLOSE_FP per scenario:",
        "",
        per_scen.rename(columns={"mean": "close_fp_share", "size": "alerts"}).to_string(),
        "",
        ("Gate failures:\n\n" + gate_fail.to_string(index=False) + "\n") if not gate_fail.empty else "",
        f"timing: simulate {sim_s:.1f}s, detect {det_s:.1f}s, discriminators+baseline {disc_s:.1f}s",
    ]
    report = "\n".join(lines)
    (out / "report.md").write_text(report)
    print(report)
    return 0 if missed.empty or (missed.truth != str(Truth.TRUE_ABUSE)).all() else 1


if __name__ == "__main__":
    raise SystemExit(main())
