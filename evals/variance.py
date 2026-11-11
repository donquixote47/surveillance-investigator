"""Run-to-run variance of the agent: the same alerts investigated several times with nothing changed.

`run_dataset.py --repeat N` saves one response per repetition (`responses/<alert_id>~r<k>.json`) and calls
`compute_variance` on the rows. Two readings come out:

- per alert: how many repetitions agreed on the disposition (5/5 = stable), the confidence range, and whether a
  true-abuse alert ever came out CLOSE_FP (a gate miss in any repetition is the finding that matters most);
- per pseudo-run: repetition k of every alert forms one run, so N repetitions give N safe close rates on the same
  alerts, and their spread is what a one- or two-point difference between two full runs has to be read against.

Nothing here is a model of the noise; it is the observed spread on the selected alerts.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from statistics import mean, pstdev
from typing import Any

from metrics import CLOSE, TRUE_ABUSE, compute


def compute_variance(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Rows carry `repeat` (0-based). Returns None when no row is a repetition."""
    reps = [r for r in rows if r.get("repeat") is not None]
    if not reps:
        return None
    by_alert: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in reps:
        by_alert[r["alert_id"]].append(r)

    per_alert = []
    for alert_id in sorted(by_alert):
        rs = sorted(by_alert[alert_id], key=lambda r: r["repeat"])
        props = [r["proposed"] or "none" for r in rs]
        c = Counter(props)
        top, top_n = c.most_common(1)[0]
        confs = [float(r["confidence"]) for r in rs if r.get("confidence") is not None]
        exp = rs[0]["expected_disposition"]
        per_alert.append(
            {
                "alert_id": alert_id,
                "scenario": rs[0]["injected_scenario"],
                "truth": rs[0]["truth"],
                "expected": exp,
                "n": len(rs),
                "dispositions": dict(c),
                "sequence": props,
                "modal": top,
                "stable": top_n == len(rs),
                "agreement_with_label": sum(1 for p in props if p == exp) / len(rs),
                "gate_miss_any": rs[0]["truth"] == TRUE_ABUSE and any(p == CLOSE for p in props),
                "confidence_min": min(confs) if confs else None,
                "confidence_max": max(confs) if confs else None,
                "duration_min_s": min(float(r["duration_s"]) for r in rs if r.get("duration_s") is not None),
                "duration_max_s": max(float(r["duration_s"]) for r in rs if r.get("duration_s") is not None),
            }
        )

    n_alerts = len(per_alert)
    unstable = [a for a in per_alert if not a["stable"]]
    by_scenario: dict[str, dict[str, int]] = defaultdict(lambda: {"alerts": 0, "unstable": 0, "flips": 0, "reps": 0})
    for a in per_alert:
        s = by_scenario[a["scenario"]]
        s["alerts"] += 1
        s["reps"] += a["n"]
        if not a["stable"]:
            s["unstable"] += 1
            s["flips"] += a["n"] - max(a["dispositions"].values())

    # pseudo-runs: repetition k of every alert
    k_max = max(r["repeat"] for r in reps) + 1
    pseudo = []
    for k in range(k_max):
        krows = [r for r in reps if r["repeat"] == k]
        if len(krows) != n_alerts:
            continue  # an incomplete repetition does not make a run
        m = compute(krows)
        pseudo.append(
            {
                "repeat": k,
                "safe_close_rate": m["safe_close_rate"],
                "agreement": m["agreement"],
                "escalation_precision": m["escalation_precision"],
                "gate_holds": m["gate"]["holds"],
            }
        )
    sc = [p["safe_close_rate"] for p in pseudo if p["safe_close_rate"] is not None]
    ag = [p["agreement"] for p in pseudo if p["agreement"] is not None]

    # the flip rate per repetition, by scenario, is what carries to the full set: for each unstable alert the share
    # of repetitions that left the modal disposition
    flip_rate = {s: round(v["flips"] / v["reps"], 3) if v["reps"] else 0.0 for s, v in sorted(by_scenario.items())}
    return {
        "n_alerts": n_alerts,
        "repeats": k_max,
        "n_investigations": len(reps),
        "stable_alerts": n_alerts - len(unstable),
        "stable_rate": round((n_alerts - len(unstable)) / n_alerts, 3) if n_alerts else None,
        "unstable": [
            {k: a[k] for k in ("alert_id", "scenario", "expected", "sequence", "confidence_min", "confidence_max")}
            for a in unstable
        ],
        "gate_miss_any": [a["alert_id"] for a in per_alert if a["gate_miss_any"]],
        "per_scenario": {s: {**v, "flip_rate": flip_rate[s]} for s, v in sorted(by_scenario.items())},
        "pseudo_runs": pseudo,
        "safe_close_spread": {
            "min": round(min(sc), 4) if sc else None,
            "max": round(max(sc), 4) if sc else None,
            "mean": round(mean(sc), 4) if sc else None,
            "stdev": round(pstdev(sc), 4) if len(sc) > 1 else None,
        },
        "agreement_spread": {
            "min": round(min(ag), 4) if ag else None,
            "max": round(max(ag), 4) if ag else None,
            "stdev": round(pstdev(ag), 4) if len(ag) > 1 else None,
        },
        "per_alert": per_alert,
    }


def _pct(x: float | None) -> str:
    return "n/a" if x is None else f"{100 * x:.1f}%"


def render_variance(v: dict[str, Any]) -> list[str]:
    lines = [
        "## Run-to-run variance",
        "",
        f"{v['n_alerts']} alerts, each investigated {v['repeats']} times with nothing changed "
        f"({v['n_investigations']} investigations). An alert is *stable* when every repetition proposed the same "
        f"disposition.",
        "",
        "| measure | value |",
        "|---|---|",
        f"| stable alerts | {v['stable_alerts']} of {v['n_alerts']} ({_pct(v['stable_rate'])}) |",
        f"| true-abuse alerts proposed CLOSE_FP in any repetition | "
        f"{', '.join(v['gate_miss_any']) if v['gate_miss_any'] else '**none**'} |",
        f"| safe close rate across the {len(v['pseudo_runs'])} pseudo-runs | "
        f"{_pct(v['safe_close_spread']['min'])} to {_pct(v['safe_close_spread']['max'])} "
        f"(mean {_pct(v['safe_close_spread']['mean'])}, sd "
        f"{'n/a' if v['safe_close_spread']['stdev'] is None else f'{100 * v["safe_close_spread"]["stdev"]:.1f} pts'}) |",
        f"| agreement with the label across pseudo-runs | {_pct(v['agreement_spread']['min'])} to "
        f"{_pct(v['agreement_spread']['max'])} |",
        "",
        "| pseudo-run | gate | safe close | agreement | escalation precision |",
        "|---|---|---|---|---|",
    ]
    for p in v["pseudo_runs"]:
        lines.append(
            f"| repeat {p['repeat']} | {'holds' if p['gate_holds'] else 'MISS'} | {_pct(p['safe_close_rate'])} | "
            f"{_pct(p['agreement'])} | {_pct(p['escalation_precision'])} |"
        )
    lines += ["", "| scenario | alerts | unstable | flips / repetitions | flip rate |", "|---|---|---|---|---|"]
    for s, d in v["per_scenario"].items():
        lines.append(f"| {s} | {d['alerts']} | {d['unstable']} | {d['flips']} / {d['reps']} | {_pct(d['flip_rate'])} |")
    if v["unstable"]:
        lines += [
            "",
            "## Unstable alerts",
            "",
            "| alert | scenario | expected | sequence | confidence |",
            "|---|---|---|---|---|",
        ]
        for a in v["unstable"]:
            lines.append(
                f"| {a['alert_id']} | {a['scenario']} | {a['expected']} | {' , '.join(a['sequence'])} | "
                f"{a['confidence_min']} to {a['confidence_max']} |"
            )
    lines.append("")
    return lines
