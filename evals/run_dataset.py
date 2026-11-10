#!/usr/bin/env python
"""Run the investigator over the labelled dataset and score it (data doc section 4.2).

    uv run evals/run_dataset.py --sample 6 --tag pilot                 # six alerts through the Runtime, as L1
    uv run evals/run_dataset.py --tag sonnet-v1 --notes "first full run"   # all 167 alerts
    uv run evals/run_dataset.py --scenario F-NEWS-1 S-SPOOF-2 --tag news  # a slice
    uv run evals/run_dataset.py --backend local --model eu.anthropic.claude-haiku-5-5 --sample 10 --tag haiku
    uv run evals/run_dataset.py --resume evals/runs/<run_id>          # finish a run that was cut short
    uv run evals/run_dataset.py --rescore evals/runs/<run_id>         # recompute results from saved responses
    uv run evals/run_dataset.py --dry-run                              # baselines only, no model calls

One Runtime session per alert (its id is also the Gateway policy session). The proposal is read back from the
`surv-cases` table, not from the model's text: a proposal counts only if `proposed_at` is after this run began.
Every response is written to `evals/runs/<run_id>/responses/<alert_id>.json` as it arrives, so a crash loses
nothing and `--resume` picks up where it stopped. Scores: `evals/metrics.py`. Labels never reach the agent.

Rate limits: the Gateway allows an analyst 60 requests/min and 3 proposals/min with a burst of 15-20
(design doc section 8). An investigation makes 10-12 Gateway calls in 30-40 s, so concurrency 2 sits around
3.4 proposals/min, just over the sustained rate and inside the burst for a full run; concurrency 3 will see
throttling. A throttled or errored alert is retried once after a pause.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

import boto3
import httpx
import pandas as pd
from boto3.dynamodb.types import TypeDeserializer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "evals"))
from metrics import CLOSE, ESCALATE, compute, regression, render_markdown, rows_from_labels  # noqa: E402
from smoke_gateway import CREDS, access_token, gateway_url, load_env  # noqa: E402

REGION = "eu-west-2"
ACCOUNT = "384308066035"
RUNTIME_NAME = "surv_default_surv_investigator_l1"
CASES_TABLE = "surv-cases"
RUNS_DIR = ROOT / "evals" / "runs"
DEFAULT_DATASET = ROOT / "data" / "synthetic" / "seed7"
TOKEN_TTL_S = 40 * 60  # Cognito access tokens live 60 min; a full run can take longer
RETRY_PAUSE_S = 90

_des = TypeDeserializer()


def now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class Tokens:
    """One analyst token, refreshed before Cognito's 60-minute expiry."""

    def __init__(self, env: dict[str, str], user: str):
        self.env, self.user = env, user
        self._tok, self._at = None, 0.0
        self._lock = threading.Lock()

    def get(self) -> str:
        with self._lock:
            if self._tok is None or time.time() - self._at > TOKEN_TTL_S:
                self._tok, self._at = access_token(self.env, self.user), time.time()
            return self._tok


class Cases:
    def __init__(self) -> None:
        self.c = boto3.client("dynamodb", region_name=REGION)

    def get(self, alert_id: str) -> dict[str, Any] | None:
        r = self.c.get_item(TableName=CASES_TABLE, Key={"alert_id": {"S": alert_id}}, ConsistentRead=True)
        item = r.get("Item")
        if not item:
            return None
        out = {k: _des.deserialize(v) for k, v in item.items()}
        if isinstance(out.get("report"), str):
            try:
                out["report"] = json.loads(out["report"])
            except json.JSONDecodeError:
                pass
        return out


def runtime_arn() -> str:
    c = boto3.client("bedrock-agentcore-control", region_name=REGION)
    for r in c.list_agent_runtimes()["agentRuntimes"]:
        if r["agentRuntimeName"] == RUNTIME_NAME:
            return r["agentRuntimeArn"]
    raise SystemExit(f"runtime {RUNTIME_NAME} not found in {REGION}")


class RuntimeBackend:
    name = "runtime"

    def __init__(self, tokens: Tokens, mode: str, memory: bool = True, bundle: str | None = None):
        self.tokens, self.mode, self.memory = tokens, mode, memory
        self.baggage = None
        if (
            bundle
        ):  # "<bundleId>:<versionId>" -> the W3C baggage header the Runtime reads (configuration-bundles-runtime)
            bid, vid = bundle.split(":", 1)
            arn = f"arn:aws:bedrock-agentcore:{REGION}:{ACCOUNT}:configuration-bundle/{bid}"
            self.baggage = f"aws.agentcore.configbundle_arn={arn},aws.agentcore.configbundle_version={vid}"
        self.url = (
            f"https://bedrock-agentcore.{REGION}.amazonaws.com/runtimes/{quote(runtime_arn(), safe='')}/invocations"
        )
        self.client = httpx.Client(timeout=httpx.Timeout(900.0, connect=30.0))

    def investigate(self, alert_id: str, session_id: str) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.tokens.get()}",
            "Content-Type": "application/json",
            "X-Amzn-Bedrock-AgentCore-Runtime-Session-Id": session_id,
        }
        if self.baggage:
            headers["baggage"] = self.baggage
        r = self.client.post(
            self.url,
            params={"qualifier": "DEFAULT"},
            headers=headers,
            json={"alert_id": alert_id, "mode": self.mode, "memory": self.memory},
        )
        if r.status_code != 200:
            return {"alert_id": alert_id, "error": f"HTTP {r.status_code}: {r.text[:600]}", "session_id": session_id}
        out = r.json()
        out.setdefault("session_id", session_id)
        return out


class LocalBackend:
    """Model calls from this machine, tools through the deployed Gateway: cheap iteration without a Runtime
    deploy, and the only way to run a model the Runtime is not configured with."""

    name = "local"

    def __init__(self, tokens: Tokens, mode: str, model_id: str | None, analyst: str, memory: bool = True):
        os.environ.setdefault("SURV_GATEWAY_URL", gateway_url())
        sys.path.insert(0, str(ROOT / "app" / "surv_investigator_l1"))
        from investigator import investigate

        self._investigate, self.tokens, self.mode, self.model_id, self.analyst, self.memory = (
            investigate,
            tokens,
            mode,
            model_id,
            analyst,
            memory,
        )

    def investigate(self, alert_id: str, session_id: str) -> dict[str, Any]:
        res = self._investigate(
            alert_id=alert_id,
            access_token=self.tokens.get(),
            mode=self.mode,
            analyst=self.analyst,
            model_id=self.model_id,
            session_id=session_id,
            memory=self.memory,
        )
        return res.to_dict()


def load_labels(dataset: Path) -> list[dict[str, Any]]:
    df = pd.read_parquet(dataset / "labels" / "labels.parquet")
    return df.to_dict("records")


def load_baseline(dataset: Path) -> dict[str, str]:
    df = pd.read_parquet(dataset / "labels" / "baseline.parquet")
    return dict(zip(df["alert_id"], df["baseline_disposition"], strict=True))


def select_alerts(labels: list[dict[str, Any]], args: argparse.Namespace) -> list[dict[str, Any]]:
    sel = labels
    if args.alerts:
        want = set(args.alerts)
        sel = [lab for lab in sel if lab["alert_id"] in want]
        missing = want - {lab["alert_id"] for lab in sel}
        if missing:
            raise SystemExit(f"unknown alert ids: {sorted(missing)}")
    if args.scenario:
        sel = [lab for lab in sel if lab["injected_scenario"] in set(args.scenario)]
    if args.sample:
        rnd = random.Random(args.seed)
        # stratified: every scenario present gets at least one alert when the sample allows it
        by_s: dict[str, list[dict[str, Any]]] = {}
        for lab in sel:
            by_s.setdefault(lab["injected_scenario"], []).append(lab)
        picked: list[dict[str, Any]] = []
        for s in sorted(by_s):
            if len(picked) < args.sample:
                picked.append(rnd.choice(by_s[s]))
        rest = [lab for lab in sel if lab not in picked]
        rnd.shuffle(rest)
        sel = sorted(picked + rest[: max(0, args.sample - len(picked))], key=lambda x: x["alert_id"])
    return sel


def row_from(
    lab: dict[str, Any], resp: dict[str, Any] | None, case: dict[str, Any] | None, meta: dict[str, Any]
) -> dict[str, Any]:
    """Join label + Runtime response + what the agent wrote to `cases`. The table is authoritative for the
    disposition; the response supplies trajectory, usage and the model's own view, which must agree."""
    started = meta.get("invoke_started_at") or ""
    fresh = bool(case and case.get("proposed_at") and str(case["proposed_at"]) >= started[:19])
    proposed = str(case["proposed_disposition"]) if fresh and case and case.get("proposed_disposition") else None
    conf = float(case["confidence"]) if fresh and case and case.get("confidence") is not None else None
    report = (case or {}).get("report") if fresh else None
    resp = resp or {}
    model_view = (resp.get("proposal") or {}).get("disposition")
    if resp.get("error"):
        status = "error"
    elif proposed is None:
        status = "no_proposal"
    else:
        status = "ok"
    usage = resp.get("usage") or {}
    calls = resp.get("tool_calls") or []
    return {
        "alert_id": lab["alert_id"],
        "truth": lab["truth"],
        "injected_scenario": lab["injected_scenario"],
        "expected_disposition": lab["expected_disposition"],
        "trader_role": lab.get("trader_role"),
        "proposed": proposed,
        "confidence": conf,
        "status": status,
        "error": (resp.get("error") or "")[:400] or None,
        "model_view": model_view,
        "model_view_agrees": (model_view == proposed) if proposed else None,
        "stale_proposal_in_cases": bool(case and case.get("proposed_at") and not fresh),
        "prior_recorded": meta.get("prior_recorded"),
        "summary": (report or {}).get("summary") if isinstance(report, dict) else None,
        "memory_used": len((report or {}).get("memory_used") or []) if isinstance(report, dict) else 0,
        "duration_s": resp.get("duration_s"),
        "wall_s": meta.get("wall_s"),
        "input_tokens": usage.get("input_tokens"),
        "output_tokens": usage.get("output_tokens"),
        "cache_read_tokens": usage.get("cache_read_tokens", 0),
        "cache_write_tokens": usage.get("cache_write_tokens", 0),
        "model_calls": usage.get("model_calls"),
        "n_tool_calls": len(calls),
        "tools": [c.get("tool") for c in calls],
        "n_rejections": len(resp.get("rejections") or []),
        "session_id": resp.get("session_id") or meta.get("session_id"),
        "attempt": meta.get("attempt"),
        "model_id": resp.get("model_id"),
        "bundle": resp.get("bundle"),
    }


def transient(resp: dict[str, Any]) -> bool:
    """Errors worth one retry after a pause: throttling anywhere in the chain (the Gateway's 429 surfaces as the
    Runtime's 500, which the invocation endpoint reports as HTTP 424), 5xx, timeouts, closed MCP connections."""
    e = (resp.get("error") or "").lower()
    return any(
        k in e
        for k in (
            "throttl",
            "rate",
            "too many",
            "429",
            "http 424",
            "http 5",
            "error (5",
            "timeout",
            "timed out",
            "service unavailable",
            "connection to the mcp server was closed",
            "connection reset",
            "readerror",
            "remoteprotocolerror",
        )
    )


def run_one(
    lab: dict[str, Any], backend: Any, cases: Cases, run_id: str, out_dir: Path, retries: int
) -> tuple[dict[str, Any], dict[str, Any]]:
    alert_id = lab["alert_id"]
    before = cases.get(alert_id)
    meta: dict[str, Any] = {"prior_recorded": bool(before and before.get("recorded_disposition"))}
    resp: dict[str, Any] = {}
    for attempt in range(1, retries + 2):
        session_id = f"surv-eval-{run_id}-{alert_id}-{uuid.uuid4().hex[:8]}"
        meta.update(session_id=session_id, attempt=attempt, invoke_started_at=now_iso())
        t0 = time.time()
        try:
            resp = backend.investigate(alert_id, session_id)
        except Exception as exc:  # network/client failure: keep going, score it as an error
            resp = {"alert_id": alert_id, "error": f"{type(exc).__name__}: {exc}", "session_id": session_id}
        meta["wall_s"] = round(time.time() - t0, 1)
        if not (resp.get("error") and transient(resp) and attempt <= retries):
            break
        time.sleep(RETRY_PAUSE_S)
    after = cases.get(alert_id)
    row = row_from(lab, resp, after, meta)
    (out_dir / "responses").mkdir(parents=True, exist_ok=True)
    (out_dir / "responses" / f"{alert_id}.json").write_text(
        json.dumps(
            {"meta": meta, "label_hidden_from_agent": True, "response": resp, "case_after": after},
            indent=1,
            default=str,
        )
    )
    return row, resp


def rescore(out_dir: Path, labels: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    run = json.loads((out_dir / "run.json").read_text())
    by_id = {lab["alert_id"]: lab for lab in labels}
    rows = []
    for f in sorted((out_dir / "responses").glob("*.json")):
        d = json.loads(f.read_text())
        lab = by_id.get(f.stem)
        if lab is None:
            continue
        rows.append(row_from(lab, d.get("response"), d.get("case_after"), d.get("meta") or {}))
    return rows, run


ARM_MARKERS = ("pilot", "nomem", "opus", "slice", "bundle")  # runs that are arms or trials, not the promoted line


def previous_run(out_dir: Path, explicit: Path | None) -> dict[str, Any] | None:
    """The run to regress against: `--compare` if given; else the one recorded in this run's results.json (so the
    judge and faithfulness passes keep the comparison the scorer chose); else the latest mainline run by start
    time, skipping arms and pilots and this run itself."""
    if explicit:
        return json.loads((explicit / "results.json").read_text())
    own = out_dir / "results.json"
    if own.exists():
        prev_id = (json.loads(own.read_text()).get("regression") or {}).get("previous")
        if prev_id and (RUNS_DIR / prev_id / "results.json").exists():
            return json.loads((RUNS_DIR / prev_id / "results.json").read_text())
    cands = []
    for p in RUNS_DIR.glob("*/results.json"):
        if p.parent.resolve() == out_dir.resolve() or any(m in p.parent.name for m in ARM_MARKERS):
            continue
        d = json.loads(p.read_text())
        cands.append((d.get("started_at") or "", d))
    cands.sort(key=lambda t: t[0])
    return cands[-1][1] if cands else None


def finish(
    out_dir: Path,
    run: dict[str, Any],
    rows: list[dict[str, Any]],
    labels_all: list[dict[str, Any]],
    dataset: Path,
    compare: Path | None,
) -> dict[str, Any]:
    ids = {r["alert_id"] for r in rows}
    labels = [lab for lab in labels_all if lab["alert_id"] in ids]
    model_id = run.get("model_id") or next((r["model_id"] for r in rows if r.get("model_id")), None)
    run["model_id"] = model_id
    m = compute(rows, model_id=model_id)
    base = load_baseline(dataset)
    baselines = {
        "threshold baseline (detector rules)": compute(rows_from_labels(labels, base)),
        "escalate everything": compute(rows_from_labels(labels, {lab["alert_id"]: ESCALATE for lab in labels})),
        "close everything (the gate at work)": compute(
            rows_from_labels(labels, {lab["alert_id"]: CLOSE for lab in labels})
        ),
    }
    prev = previous_run(out_dir, compare)
    # keep what the judge and faithfulness passes already wrote for this run
    existing = json.loads((out_dir / "results.json").read_text()) if (out_dir / "results.json").exists() else {}
    for k in ("evaluations", "faithfulness", "finished_at", "elapsed_min"):
        if existing.get(k) is not None and run.get(k) is None:
            run[k] = existing[k]
    reg = regression(m, prev, current_faith=run.get("faithfulness"))
    run.update(metrics=m, baselines=baselines, regression=reg, finished_at=run.get("finished_at") or now_iso())
    if run.get("started_at") and not run.get("elapsed_min"):
        t0 = datetime.fromisoformat(run["started_at"])
        run["elapsed_min"] = round((datetime.fromisoformat(run["finished_at"]) - t0).total_seconds() / 60, 1)
    (out_dir / "results.json").write_text(json.dumps(run, indent=1, default=str))
    (out_dir / "results.md").write_text(
        render_markdown(
            run,
            baselines=baselines,
            reg=reg,
            rows=rows,
            evaluations=run.get("evaluations"),
            faithfulness=run.get("faithfulness"),
        )
    )
    pd.DataFrame(rows).to_csv(out_dir / "per_alert.csv", index=False)
    return run


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    ap.add_argument("--backend", choices=["runtime", "local"], default="runtime")
    ap.add_argument(
        "--model", default=None, help="model id for --backend local (the Runtime uses its own SURV_MODEL_ID)"
    )
    ap.add_argument("--user", choices=["L1", "L2"], default="L1")
    ap.add_argument("--mode", choices=["investigate", "stor_drafting"], default="investigate")
    ap.add_argument("--no-memory", action="store_true", help="hide recall_memory from the agent (data doc 4.5.1 arm)")
    ap.add_argument(
        "--bundle", default=None, help="configuration bundle '<bundleId>:<versionId>' or a name from evals/bundles.json"
    )
    ap.add_argument("--concurrency", type=int, default=2)
    ap.add_argument("--retries", type=int, default=1, help="retries per alert on throttling or 5xx")
    ap.add_argument("--alerts", nargs="*", default=None)
    ap.add_argument("--scenario", nargs="*", default=None)
    ap.add_argument("--sample", type=int, default=None, help="stratified sample of this many alerts")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--tag", default="run")
    ap.add_argument("--notes", default="")
    ap.add_argument("--compare", type=Path, default=None, help="previous run dir for the regression report")
    ap.add_argument("--resume", type=Path, default=None, help="existing run dir: skip alerts with a saved response")
    ap.add_argument(
        "--retry-errors", action="store_true", help="with --resume: also re-run alerts whose saved response is an error"
    )
    ap.add_argument("--rescore", type=Path, default=None, help="recompute results from a run's saved responses")
    ap.add_argument("--dry-run", action="store_true", help="baselines on the selection only, no invocations")
    args = ap.parse_args()

    labels_all = load_labels(args.dataset)
    if args.rescore:
        args.rescore = args.rescore.resolve()
        rows, run = rescore(args.rescore, labels_all)
        run = finish(args.rescore, run, rows, labels_all, args.dataset, args.compare)
        print((args.rescore / "results.md").read_text())
        return 0

    selection = select_alerts(labels_all, args)
    if args.dry_run:
        base = load_baseline(args.dataset)
        m = compute(rows_from_labels(selection, base))
        print(
            json.dumps(
                {k: m[k] for k in ("n", "gate", "safe_close_rate", "raw_safe_close_rate", "agreement")}, indent=1
            )
        )
        return 0

    if args.resume:
        out_dir = args.resume.resolve()
        run = json.loads((out_dir / "run.json").read_text())
        run_id = run["run_id"]
        done = set()
        for p in (out_dir / "responses").glob("*.json"):
            if args.retry_errors and (json.loads(p.read_text()).get("response") or {}).get("error"):
                continue  # re-run it; the new response overwrites the errored one
            done.add(p.stem)
        selection = [lab for lab in selection if lab["alert_id"] not in done]
        print(f"resuming {run_id}: {len(done)} saved, {len(selection)} to go")
    else:
        run_id = f"{datetime.now(UTC).strftime('%Y%m%dT%H%M')}-{args.tag}"
        out_dir = RUNS_DIR / run_id
        out_dir.mkdir(parents=True, exist_ok=False)
        manifest = (
            json.loads((args.dataset / "manifest.json").read_text())
            if (args.dataset / "manifest.json").exists()
            else {}
        )
        run = {
            "run_id": run_id,
            "dataset": args.dataset.name,
            "dataset_manifest": {
                k: manifest.get(k) for k in ("seed", "generator_version", "detector_version", "sessions")
            },
            "backend": args.backend,
            "model_id": args.model if args.backend == "local" else None,
            "user": args.user,
            "mode": args.mode,
            "memory": not args.no_memory,
            "bundle": args.bundle,
            "concurrency": args.concurrency,
            "selection": {"alerts": args.alerts, "scenario": args.scenario, "sample": args.sample, "seed": args.seed},
            "n_selected": len(selection),
            "notes": args.notes,
            "started_at": now_iso(),
        }
        (out_dir / "run.json").write_text(json.dumps(run, indent=1))

    env = load_env(CREDS)
    tokens = Tokens(env, args.user)
    bundle = args.bundle
    if bundle and ":" not in bundle:  # a name from the local registry
        reg_path = ROOT / "evals" / "bundles.json"
        reg = json.loads(reg_path.read_text()) if reg_path.exists() else {}
        if bundle not in reg:
            raise SystemExit(f"unknown bundle name {bundle}; known: {sorted(reg)}")
        bundle = reg[bundle]["baggage"]
        run["bundle"] = f"{args.bundle} ({bundle})"
        (out_dir / "run.json").write_text(json.dumps(run, indent=1))
    if args.backend == "runtime":
        backend: Any = RuntimeBackend(tokens, args.mode, memory=not args.no_memory, bundle=bundle)
    else:
        if bundle:
            raise SystemExit("--bundle needs --backend runtime (the bundle is resolved by the Runtime app)")
        backend = LocalBackend(tokens, args.mode, args.model, env[f"SURV_{args.user}_USER"], memory=not args.no_memory)
    cases = Cases()

    print(
        f"run {run_id}: {len(selection)} alerts, backend={args.backend}, user={args.user}, concurrency={args.concurrency}"
    )
    print(f"outputs: {out_dir}")
    t_run = time.time()
    rows: list[dict[str, Any]] = []
    progress = (out_dir / "progress.jsonl").open("a")
    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        futs = {pool.submit(run_one, lab, backend, cases, run_id, out_dir, args.retries): lab for lab in selection}
        for i, fut in enumerate(as_completed(futs), 1):
            row, _ = fut.result()
            rows.append(row)
            progress.write(json.dumps(row, default=str) + "\n")
            progress.flush()
            mark = (
                "ok "
                if row["proposed"] == row["expected_disposition"]
                else (
                    "MISS"
                    if row["truth"] == "TRUE_ABUSE" and row["proposed"] == CLOSE
                    else "..."
                    if row["proposed"]
                    else "NONE"
                )
            )
            print(
                f"[{i:3d}/{len(selection)}] {row['alert_id']} {row['injected_scenario']:20s} expected {row['expected_disposition']:10s} "
                f"-> {row['proposed'] or '-':10s} {row['confidence'] if row['confidence'] is not None else '':<5} {mark} "
                f"{row['wall_s']:6.1f}s  {(row['input_tokens'] or 0):6d} in  {row['status']}"
                + (f"  !! {row['error'][:120]}" if row["error"] else ""),
                flush=True,
            )
    progress.close()
    print(f"invocations done in {(time.time() - t_run) / 60:.1f} min")

    if args.resume:  # score everything saved, not only this leg
        rows, _ = rescore(out_dir, labels_all)
    run = finish(out_dir, run, rows, labels_all, args.dataset, args.compare)
    print((out_dir / "results.md").read_text())
    return 0


if __name__ == "__main__":
    sys.exit(main())
