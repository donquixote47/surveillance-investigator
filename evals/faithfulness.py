#!/usr/bin/env python
"""Evidence faithfulness (data doc section 4.2): every number the agent wrote in `report.evidence[].fact` must
appear in a tool result of the same session. Programmatic, no judge.

    uv run evals/faithfulness.py evals/runs/<run_id>                 # all alerts of the run
    uv run evals/faithfulness.py evals/runs/<run_id> --alerts A-261006-0006
    uv run evals/faithfulness.py evals/runs/<run_id> --summarize-only

Tool results are read from the session's `mcp tools/call <tool>` spans (`gen_ai.tool.call.result`, full text,
not truncated [verified 2026-11-05: 38 KB order-event pages intact]). The arguments of `propose_disposition`
are excluded, since they are the report itself. A number counts as grounded when it appears verbatim in a tool
result (commas and units stripped) or when a tool-result number rounds to it at the precision the report used
(7.94 -> "7.9x"). Times (`15:09:20.881`) are matched as strings. Integers up to 12 are skipped (levels, ticks,
counts that would match anywhere). What is left is listed per alert for a human to read: a derived ratio the
agent computed is a weak fact, an invented number is a defect.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from bedrock_agentcore.evaluation import CloudWatchAgentSpanCollector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evals"))
from metrics import regression, render_markdown  # noqa: E402

REGION = "eu-west-2"
LOG_GROUP = "/aws/bedrock-agentcore/runtimes/surv_default_surv_investigator_l1-lrnjCN5vBp-DEFAULT"
logging.basicConfig(level=logging.WARNING)
_lock = threading.Lock()

TIME_RE = re.compile(r"\b\d{1,2}:\d{2}:\d{2}(?:\.\d{1,9})?\b")
NUM_RE = re.compile(r"(?<![\w.])[-+]?\d{1,3}(?:,\d{3})+(?:\.\d+)?(?![\d.])|(?<![\w.])[-+]?\d+(?:\.\d+)?(?![\d.]\d)")
SMALL_INT_SKIP = 12


def tool_text(spans: list[dict[str, Any]]) -> str:
    parts = []
    for s in spans:
        name = str(s.get("name") or "")
        if not name.startswith("mcp tools/call"):
            continue
        a = s.get("attributes") or {}
        res = a.get("gen_ai.tool.call.result")
        if res:
            parts.append(str(res))
        if "propose_disposition" not in name and "draft_stor" not in name and a.get("gen_ai.tool.call.arguments"):
            parts.append(str(a["gen_ai.tool.call.arguments"]))
    return "\n".join(parts)


def numbers_in(text: str) -> list[float]:
    out = []
    for m in NUM_RE.finditer(TIME_RE.sub(" ", text)):  # times out first, so 15:09:20.881 is not three numbers
        try:
            out.append(float(m.group(0).replace(",", "")))
        except ValueError:
            pass
    return out


def fact_tokens(fact: str) -> list[tuple[str, float | None, int]]:
    """(token, value, decimals) for every number-like token in a fact; times carry value None."""
    toks: list[tuple[str, float | None, int]] = []
    for m in TIME_RE.finditer(fact):
        toks.append((m.group(0), None, 0))
    stripped = TIME_RE.sub(" ", fact)
    for m in NUM_RE.finditer(stripped):
        raw = m.group(0)
        clean = raw.replace(",", "")
        try:
            v = float(clean)
        except ValueError:
            continue
        dec = len(clean.split(".")[1]) if "." in clean else 0
        if dec == 0 and abs(v) <= SMALL_INT_SKIP:
            continue
        toks.append((raw, v, dec))
    return toks


def check_fact(fact: str, ground: str, ground_nums: list[float]) -> tuple[int, list[str]]:
    """Return (numbers checked, unmatched tokens)."""
    ground_flat = ground.replace(",", "")
    unmatched = []
    toks = fact_tokens(fact)
    for raw, v, dec in toks:
        if v is None:  # time string: verbatim, or the same time with more decimals in the tool text
            if raw in ground or re.search(re.escape(raw) + r"\d*", ground):
                continue
            unmatched.append(raw)
            continue
        clean = raw.replace(",", "")
        if clean.lstrip("+") in ground_flat:
            continue
        pct = v / 100 if dec == 0 else None  # "96%" written where the tool said 0.96
        if any(round(g, dec) == round(v, dec) or (pct is not None and abs(g - pct) < 1e-9) for g in ground_nums):
            continue
        unmatched.append(raw)
    return len(toks), unmatched


def check_alert(
    alert_id: str, session_id: str, report: dict[str, Any] | None, collector: CloudWatchAgentSpanCollector
) -> dict[str, Any]:
    end = datetime.now(UTC)
    spans = collector.collect(session_id=session_id, start_time=end - timedelta(days=14), end_time=end)
    ground = tool_text(spans)
    ground_nums = numbers_in(ground)
    facts = []
    n_checked = 0
    n_unmatched = 0
    for e in (report or {}).get("evidence") or []:
        fact = str(e.get("fact") or "")
        n, un = check_fact(fact, ground, ground_nums)
        n_checked += n
        n_unmatched += len(un)
        facts.append({"id": e.get("id"), "source": e.get("source"), "fact": fact, "numbers": n, "unmatched": un})
    return {
        "alert_id": alert_id,
        "session_id": session_id,
        "n_spans": len(spans),
        "ground_chars": len(ground),
        "has_report": bool(report),
        "numbers_checked": n_checked,
        "numbers_unmatched": n_unmatched,
        "faithful": bool(report) and n_unmatched == 0 and len(ground) > 0,
        "facts": facts,
    }


def summarize(saved: list[dict[str, Any]], rows_by_alert: dict[str, dict[str, Any]]) -> dict[str, Any]:
    with_report = [s for s in saved if s["has_report"] and s["ground_chars"] > 0]
    n_num = sum(s["numbers_checked"] for s in with_report)
    n_un = sum(s["numbers_unmatched"] for s in with_report)
    offenders = []
    for s in with_report:
        for f in s["facts"]:
            if f["unmatched"]:
                r = rows_by_alert.get(s["alert_id"], {})
                offenders.append(
                    {
                        "alert_id": s["alert_id"],
                        "scenario": r.get("injected_scenario"),
                        "proposed": r.get("proposed"),
                        "source": f["source"],
                        "unmatched": f["unmatched"],
                        "fact": f["fact"][:220],
                    }
                )
    return {
        "n_sessions": len(saved),
        "n_with_report": len(with_report),
        "n_no_spans": sum(1 for s in saved if s["ground_chars"] == 0),
        "alerts_faithful": sum(1 for s in with_report if s["faithful"]),
        "alert_rate": round(sum(1 for s in with_report if s["faithful"]) / len(with_report), 4)
        if with_report
        else None,
        "numbers_checked": n_num,
        "numbers_unmatched": n_un,
        "number_rate": round((n_num - n_un) / n_num, 4) if n_num else None,
        "offenders": offenders,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run_dir", type=Path)
    ap.add_argument("--alerts", nargs="*", default=None)
    ap.add_argument("--concurrency", type=int, default=3)
    ap.add_argument("--only-missing", action="store_true")
    ap.add_argument("--summarize-only", action="store_true")
    args = ap.parse_args()
    run_dir: Path = args.run_dir
    out_dir = run_dir / "faithfulness"
    out_dir.mkdir(exist_ok=True)
    run = json.loads((run_dir / "results.json").read_text())
    sys.path.insert(0, str(ROOT / "evals"))
    from run_dataset import load_labels, previous_run, rescore

    labels = load_labels(ROOT / "data" / "synthetic" / run["dataset"])
    rows, _ = rescore(run_dir, labels)
    rows_by_alert = {r["alert_id"]: r for r in rows}

    if not args.summarize_only:
        todo = []
        for p in sorted((run_dir / "responses").glob("*.json")):
            if args.alerts and p.stem not in set(args.alerts):
                continue
            if args.only_missing and (out_dir / p.name).exists():
                continue
            d = json.loads(p.read_text())
            sid = (d.get("response") or {}).get("session_id") or (d.get("meta") or {}).get("session_id")
            report = (
                ((d.get("case_after") or {}).get("report")) if rows_by_alert.get(p.stem, {}).get("proposed") else None
            )
            if isinstance(report, str):
                report = json.loads(report)
            todo.append((p.stem, sid, report))
        print(f"checking {len(todo)} sessions of {run['run_id']}")
        collector = CloudWatchAgentSpanCollector(
            log_group_name=LOG_GROUP, region=REGION, max_wait_seconds=60, poll_interval_seconds=2
        )
        t0 = time.time()
        with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
            futs = {pool.submit(check_alert, a, s, r, collector): a for a, s, r in todo}
            for i, fut in enumerate(as_completed(futs), 1):
                res = fut.result()
                (out_dir / f"{res['alert_id']}.json").write_text(json.dumps(res, indent=1))
                with _lock:
                    flag = (
                        "ok "
                        if res["faithful"]
                        else ("NO SPANS" if res["ground_chars"] == 0 else f"{res['numbers_unmatched']} unmatched")
                    )
                    print(
                        f"[{i:3d}/{len(todo)}] {res['alert_id']} {res['numbers_checked']:3d} numbers  {flag}",
                        flush=True,
                    )
        print(f"done in {(time.time() - t0) / 60:.1f} min")

    saved = [json.loads(p.read_text()) for p in sorted(out_dir.glob("*.json"))]
    summary = summarize(saved, rows_by_alert)
    run["faithfulness"] = summary
    prev = previous_run(run_dir, None)
    run["regression"] = regression(run["metrics"], prev, current_faith=summary)
    (run_dir / "results.json").write_text(json.dumps(run, indent=1, default=str))
    md = render_markdown(
        run,
        baselines=run.get("baselines"),
        reg=run.get("regression"),
        rows=rows,
        evaluations=run.get("evaluations"),
        faithfulness=summary,
    )
    (run_dir / "results.md").write_text(md)
    start = md.find("## Evidence faithfulness")
    print(md[start : start + 6000] if start >= 0 else "no section")
    return 0


if __name__ == "__main__":
    sys.exit(main())
