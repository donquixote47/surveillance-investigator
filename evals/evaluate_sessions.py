#!/usr/bin/env python
"""Score the sessions of a dataset run with AgentCore Evaluations (data doc section 4.1) and merge the scores
into the run's results.

    uv run evals/evaluate_sessions.py evals/runs/<run_id>                     # every session, all evaluators
    uv run evals/evaluate_sessions.py evals/runs/<run_id> --sample 30          # stratified subset
    uv run evals/evaluate_sessions.py evals/runs/<run_id> --evaluators Builtin.TrajectoryInOrderMatch rubric
    uv run evals/evaluate_sessions.py evals/runs/<run_id> --only-missing       # finish an interrupted pass

Each session is evaluated with its ground truth from `evals/ground_truth.py` (built from the labels, never seen by
the agent): `Builtin.Correctness` against `expected_response` (trace level), `Builtin.GoalSuccessRate` against
the assertions (session level), `Builtin.TrajectoryInOrderMatch` / `AnyOrderMatch` against the expected tools
(programmatic, free), and the custom `surv_rationale_rubric` (Opus 5.5 judge, no ground truth). Raw results go
to `<run>/evaluations/<alert_id>.json`; the aggregate goes into `results.json["evaluations"]` and `results.md`.

Cost (pricing page 2026-11-05): built-in LLM evaluators $2.40 / $12.00 per M tokens in/out (model included);
custom evaluators $1.50 per 1,000 evaluations plus the judge model's tokens in this account. GoalSuccessRate reads
the whole session (about 23k tokens here), Correctness about 1k, the rubric about 12k on Opus. A full 167-session
pass is roughly $25.
"""

from __future__ import annotations

import argparse
import json
import logging
import random
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import boto3
import pandas as pd
from bedrock_agentcore.evaluation import EvaluationClient, ReferenceInputs

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evals"))
from ground_truth import reference_inputs  # noqa: E402
from metrics import render_markdown, summarize_evaluations  # noqa: E402
from run_dataset import rescore  # noqa: E402

REGION = "eu-west-2"
LOG_GROUP = "/aws/bedrock-agentcore/runtimes/surv_default_surv_investigator_l1-lrnjCN5vBp-DEFAULT"
RUBRIC_NAME = "surv_rationale_rubric"
DEFAULT_EVALUATORS = [
    "Builtin.Correctness",
    "Builtin.GoalSuccessRate",
    "Builtin.TrajectoryInOrderMatch",
    "Builtin.TrajectoryAnyOrderMatch",
    "rubric",
]
DEFAULT_DATASET = ROOT / "data" / "synthetic" / "seed7"
# Measured on the v4 judged pass (167 sessions): built-in judges 2.95 M in / 0.10 M out at $2.40 / $12.00 per M,
# the rubric 3.83 M in / 0.25 M out on Opus at $4 / $20 (assumed) plus $1.50 per 1,000 evaluations: about $28,
# $0.17 a session. Used only for the estimate printed before a pass starts.
JUDGE_COST_PER_SESSION_USD = 0.17

logging.basicConfig(level=logging.WARNING)
_print_lock = threading.Lock()


def rubric_id() -> str:
    c = boto3.client("bedrock-agentcore-control", region_name=REGION)
    token = None
    while True:
        kw: dict[str, Any] = {"maxResults": 50}
        if token:
            kw["nextToken"] = token
        r = c.list_evaluators(**kw)
        for e in r.get("evaluators", []):
            if e.get("evaluatorName") == RUBRIC_NAME:
                return e["evaluatorId"]
        token = r.get("nextToken")
        if not token:
            raise SystemExit(
                f"evaluator {RUBRIC_NAME} not found; run `uv run evals/evaluators.py create rationale_rubric`"
            )


def evaluate_one(
    client: EvaluationClient,
    alert_id: str,
    session_id: str,
    label: dict[str, Any],
    evaluator_ids: list[str],
    retries: int = 3,
) -> dict[str, Any]:
    ref = reference_inputs(label)
    ri = ReferenceInputs(
        expected_response=ref["expected_response"],
        assertions=ref["assertions"],
        expected_trajectory=ref["expected_trajectory"],
    )
    results: list[dict[str, Any]] = []
    errors: list[str] = []
    for ev in evaluator_ids:  # one evaluator per call, so a throttle on one does not void the others
        for attempt in range(retries + 1):
            try:
                results.extend(
                    client.run(evaluator_ids=[ev], session_id=session_id, log_group_name=LOG_GROUP, reference_inputs=ri)
                )
                break
            except Exception as exc:  # throttling, transient service errors
                msg = f"{type(exc).__name__}: {exc}"
                if attempt < retries and any(k in msg for k in ("Throttl", "TooMany", "ServiceUnavailable", "Timeout")):
                    time.sleep(10 * (attempt + 1))
                    continue
                errors.append(f"{ev}: {msg[:300]}")
                break
    return {
        "alert_id": alert_id,
        "session_id": session_id,
        "evaluated_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
        "reference_inputs": ref,
        "results": results,
        "errors": errors,
    }


def select(rows: list[dict[str, Any]], args: argparse.Namespace) -> list[dict[str, Any]]:
    sel = rows
    if args.alerts:
        want = set(args.alerts)
        sel = [r for r in sel if r["alert_id"] in want]
    if args.scenario:
        sel = [r for r in sel if r["injected_scenario"] in set(args.scenario)]
    if args.sample and args.sample < len(sel):
        rnd = random.Random(args.seed)
        by_s: dict[str, list[dict[str, Any]]] = {}
        for r in sel:
            by_s.setdefault(r["injected_scenario"], []).append(r)
        picked: list[dict[str, Any]] = []
        for s in sorted(by_s):
            if len(picked) < args.sample:
                picked.append(rnd.choice(by_s[s]))
        rest = [r for r in sel if r not in picked]
        rnd.shuffle(rest)
        sel = picked + rest[: max(0, args.sample - len(picked))]
    return sorted(sel, key=lambda r: r["alert_id"])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run_dir", type=Path)
    ap.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    ap.add_argument("--evaluators", nargs="*", default=DEFAULT_EVALUATORS, help="built-in ids, or 'rubric'")
    ap.add_argument("--alerts", nargs="*", default=None)
    ap.add_argument("--scenario", nargs="*", default=None)
    ap.add_argument("--sample", type=int, default=None)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--concurrency", type=int, default=3)
    ap.add_argument("--only-missing", action="store_true")
    ap.add_argument(
        "--summarize-only", action="store_true", help="no new calls; rebuild the aggregate from saved files"
    )
    ap.add_argument("--yes", action="store_true", help="start without the cost confirmation (scripted use)")
    args = ap.parse_args()

    run_dir: Path = args.run_dir
    results_path = run_dir / "results.json"
    run = json.loads(results_path.read_text())
    saved_ds = run.get("dataset")
    if saved_ds and saved_ds != args.dataset.name:  # a run is scored with the labels of the dataset it ran on
        print(f"note: run was made on dataset {saved_ds}; using its labels, not {args.dataset.name}")
        args.dataset = DEFAULT_DATASET.parent / saved_ds
    labels_list = pd.read_parquet(args.dataset / "labels" / "labels.parquet").to_dict("records")
    labels = {r["alert_id"]: r for r in labels_list}
    per_alert, _ = rescore(run_dir, labels_list)  # rows rebuilt from the saved responses, as run_dataset scores them
    out_dir = run_dir / "evaluations"
    out_dir.mkdir(exist_ok=True)

    if not args.summarize_only:
        evaluator_ids = [rubric_id() if e == "rubric" else e for e in args.evaluators]
        rows = [r for r in select(per_alert, args) if isinstance(r.get("session_id"), str)]
        if args.only_missing:
            rows = [r for r in rows if not (out_dir / f"{r['alert_id']}.json").exists()]
        print(
            f"evaluating {len(rows)} sessions of {run['run_id']} with {evaluator_ids} (concurrency {args.concurrency})"
        )
        # The judge is the one thing in this project that spends more than the investigation it looks at: about
        # $0.17 per session (GoalSuccessRate reads the whole session, the rubric runs on Opus) against $0.09 for the
        # investigation. It never runs on its own; it starts here, after this line, and only after a yes.
        est = len(rows) * JUDGE_COST_PER_SESSION_USD
        print(f"estimated judge cost: about ${est:.0f} ({len(rows)} sessions x ~${JUDGE_COST_PER_SESSION_USD:.2f})")
        if not args.yes:
            answer = input("start the judged pass? [y/N] ").strip().lower()
            if answer not in ("y", "yes"):
                print("not started")
                return 0
        client = EvaluationClient(region_name=REGION)
        t0 = time.time()
        with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
            futs = {
                pool.submit(
                    evaluate_one, client, r["alert_id"], r["session_id"], labels[r["alert_id"]], evaluator_ids
                ): r
                for r in rows
            }
            for i, fut in enumerate(as_completed(futs), 1):
                res = fut.result()
                (out_dir / f"{res['alert_id']}.json").write_text(json.dumps(res, indent=1, default=str))
                scores = {
                    (x.get("evaluatorName") or x.get("evaluatorId", "?")).replace("Builtin.", ""): x.get("value")
                    for x in res["results"]
                    if x.get("value") is not None
                }
                with _print_lock:
                    print(
                        f"[{i:3d}/{len(rows)}] {res['alert_id']} "
                        + "  ".join(f"{k}={v:g}" for k, v in scores.items())
                        + (f"  !! {len(res['errors'])} error(s): {res['errors'][0][:100]}" if res["errors"] else ""),
                        flush=True,
                    )
        print(f"done in {(time.time() - t0) / 60:.1f} min")

    saved = [json.loads(p.read_text()) for p in sorted(out_dir.glob("*.json"))]
    summary = summarize_evaluations(saved, {r["alert_id"]: r for r in per_alert})
    run["evaluations"] = summary
    results_path.write_text(json.dumps(run, indent=1, default=str))
    md = render_markdown(
        run,
        baselines=run.get("baselines"),
        reg=run.get("regression"),
        rows=per_alert,
        evaluations=summary,
    )
    (run_dir / "results.md").write_text(md)
    start = md.find("## AgentCore Evaluations")
    print(md[start:] if start >= 0 else md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
