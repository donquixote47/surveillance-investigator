#!/usr/bin/env python
"""Side-by-side comparison of two dataset runs on the alerts they share: the paired view the memory on/off arm
(data doc 4.5.1) and the model arm (4.3) need, which the per-run regression report does not give.

    uv run evals/compare_runs.py evals/runs/<A> evals/runs/<B> [--label-a "memory on" --label-b "memory off"]
    uv run evals/compare_runs.py ... --out evals/runs/compare-<name>.md

Prints the headline metrics of both, the paired disposition changes (which alerts moved, in which direction),
the per-scenario agreement of both, and the cost/latency columns.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evals"))
from metrics import compute  # noqa: E402
from run_dataset import load_labels, rescore  # noqa: E402


def _pct(x: float | None) -> str:
    return "n/a" if x is None else f"{100 * x:.1f}%"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run_a", type=Path)
    ap.add_argument("run_b", type=Path)
    ap.add_argument("--label-a", default=None)
    ap.add_argument("--label-b", default=None)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    labels = load_labels(ROOT / "data" / "synthetic" / "seed7")
    rows_a, run_a = rescore(args.run_a.resolve(), labels)
    rows_b, run_b = rescore(args.run_b.resolve(), labels)
    la = args.label_a or run_a["run_id"]
    lb = args.label_b or run_b["run_id"]
    by_a = {r["alert_id"]: r for r in rows_a}
    by_b = {r["alert_id"]: r for r in rows_b}
    shared = sorted(set(by_a) & set(by_b))
    ra = [by_a[a] for a in shared]
    rb = [by_b[a] for a in shared]
    ma = compute(ra, model_id=run_a.get("model_id") or next((r["model_id"] for r in ra if r.get("model_id")), None))
    mb = compute(rb, model_id=run_b.get("model_id") or next((r["model_id"] for r in rb if r.get("model_id")), None))

    lines = [f"# {la} vs {lb}", "", f"{len(shared)} shared alerts (A has {len(rows_a)}, B has {len(rows_b)}).", ""]
    lines.append(f"| metric | {la} | {lb} |")
    lines.append("|---|---|---|")
    g = lambda m: "holds" if m["gate"]["holds"] else f"FAILED ({len(m['gate']['missed'])})"  # noqa: E731
    lines.append(f"| gate | {g(ma)} | {g(mb)} |")
    lines.append(f"| safe close rate | {_pct(ma['raw_safe_close_rate'])} | {_pct(mb['raw_safe_close_rate'])} |")
    lines.append(f"| escalation precision | {_pct(ma['escalation_precision'])} | {_pct(mb['escalation_precision'])} |")
    lines.append(
        f"| agreement / override rate | {_pct(ma['agreement'])} / {_pct(ma['override_rate'])} | {_pct(mb['agreement'])} / {_pct(mb['override_rate'])} |"
    )
    lines.append(f"| proposals | {ma['proposed_counts']} | {mb['proposed_counts']} |")
    lines.append(f"| run status | {ma['status_counts']} | {mb['status_counts']} |")
    mem_a = sum(1 for r in ra if r.get("memory_used"))
    mem_b = sum(1 for r in rb if r.get("memory_used"))
    rec_a = sum(1 for r in ra if any(str(t).endswith("recall_memory") for t in (r.get("tools") or [])))
    rec_b = sum(1 for r in rb if any(str(t).endswith("recall_memory") for t in (r.get("tools") or [])))
    lines.append(f"| recall_memory called / reports citing memory_used | {rec_a} / {mem_a} | {rec_b} / {mem_b} |")
    lines.append(
        f"| agent p50 / p95 | {ma['latency']['agent_p50_s']} s / {ma['latency']['agent_p95_s']} s | {mb['latency']['agent_p50_s']} s / {mb['latency']['agent_p95_s']} s |"
    )
    lines.append(
        f"| tokens in / out per alert (mean) | {ma['tokens']['input_mean']} / {ma['tokens']['output_mean']} | {mb['tokens']['input_mean']} / {mb['tokens']['output_mean']} |"
    )
    lines.append(
        f"| tool calls per alert (mean) | {ma['tokens']['tool_calls_mean']} | {mb['tokens']['tool_calls_mean']} |"
    )
    lines.append(
        f"| estimated model cost (assumed prices) | ${ma['tokens']['estimated_cost_usd']} | ${mb['tokens']['estimated_cost_usd']} |"
    )
    lines.append(
        f"| mean confidence | {round(sum(float(r['confidence']) for r in ra if r.get('confidence') is not None) / max(1, sum(1 for r in ra if r.get('confidence') is not None)), 3)} | {round(sum(float(r['confidence']) for r in rb if r.get('confidence') is not None) / max(1, sum(1 for r in rb if r.get('confidence') is not None)), 3)} |"
    )
    lines.append("")
    moved = [(a, by_a[a], by_b[a]) for a in shared if by_a[a]["proposed"] != by_b[a]["proposed"]]
    pairs = Counter((x["proposed"] or "NONE", y["proposed"] or "NONE") for _, x, y in moved)
    lines.append(f"## Paired changes ({len(moved)} of {len(shared)} alerts proposed differently)")
    lines.append("")
    if pairs:
        lines.append(f"| {la} -> {lb} | n |")
        lines.append("|---|---|")
        for (x, y), n in pairs.most_common():
            lines.append(f"| {x} -> {y} | {n} |")
        lines.append("")
        lines.append("| alert | scenario | expected | " + la + " | " + lb + " | who is right |")
        lines.append("|---|---|---|---|---|---|")
        for a, x, y in sorted(moved, key=lambda t: (t[1]["truth"] != "TRUE_ABUSE", t[1]["injected_scenario"], t[0])):
            who = (
                "A"
                if x["proposed"] == x["expected_disposition"]
                else ("B" if y["proposed"] == y["expected_disposition"] else "neither")
            )
            lines.append(
                f"| {a} | {x['injected_scenario']} | {x['expected_disposition']} | {x['proposed'] or '-'} ({x.get('confidence') or '-'}) | {y['proposed'] or '-'} ({y.get('confidence') or '-'}) | {who} |"
            )
        lines.append("")
    lines.append("## Per scenario (agreement with the label)")
    lines.append("")
    lines.append(f"| scenario | truth | n | {la} | {lb} |")
    lines.append("|---|---|---|---|---|")
    by_s: dict[str, list[str]] = defaultdict(list)
    for a in shared:
        by_s[by_a[a]["injected_scenario"]].append(a)
    for s_, ids in sorted(by_s.items(), key=lambda kv: (by_a[kv[1][0]]["truth"] != "TRUE_ABUSE", kv[0])):
        ok_a = sum(1 for a in ids if by_a[a]["proposed"] == by_a[a]["expected_disposition"])
        ok_b = sum(1 for a in ids if by_b[a]["proposed"] == by_b[a]["expected_disposition"])
        lines.append(f"| {s_} | {by_a[ids[0]]['truth']} | {len(ids)} | {ok_a}/{len(ids)} | {ok_b}/{len(ids)} |")
    md = "\n".join(lines)
    print(md)
    if args.out:
        args.out.write_text(md)
        args.out.with_suffix(".json").write_text(
            json.dumps(
                {
                    "a": run_a["run_id"],
                    "b": run_b["run_id"],
                    "shared": len(shared),
                    "metrics_a": ma,
                    "metrics_b": mb,
                    "moved": [(a, x["proposed"], y["proposed"]) for a, x, y in moved],
                },
                indent=1,
                default=str,
            )
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
