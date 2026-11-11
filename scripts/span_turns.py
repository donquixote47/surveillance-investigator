"""Per-turn timing of one or more Runtime sessions from their CloudWatch spans: model turns with their output
tokens, tool calls, and the share of wall time in the model. The number the operations doc's section 4 was built
from, as a command.

    uv run scripts/span_turns.py <session_id> [<session_id> ...] [--endpoint DEFAULT|demo] [--lookback-h 6]
    uv run scripts/span_turns.py --run evals/runs/<run_id> --alerts A-261006-0006      # session ids from a run

Reads the `spans` stream of the Runtime log group; needs CloudWatch Logs read permission on this machine.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import boto3

REGION = "eu-west-2"
RUNTIME_ID = "surv_default_surv_investigator_l1-lrnjCN5vBp"


def spans_for(session_id: str, log_group: str, lookback_s: int) -> list[dict[str, Any]]:
    logs = boto3.client("logs", region_name=REGION)
    now = int(time.time() * 1000)
    out: list[dict[str, Any]] = []
    token = None
    while True:
        kw: dict[str, Any] = {
            "logGroupName": log_group,
            "logStreamNames": ["spans"],
            "startTime": now - lookback_s * 1000,
            "endTime": now + 60_000,
            "filterPattern": f'"{session_id}"',
            "limit": 1000,
        }
        if token:
            kw["nextToken"] = token
        resp = logs.filter_log_events(**kw)
        for ev in resp.get("events", []):
            try:
                d = json.loads(ev["message"])
            except json.JSONDecodeError:
                continue
            if (d.get("attributes") or {}).get("session.id") == session_id:
                out.append(d)
        token = resp.get("nextToken")
        if not token:
            break
    out.sort(key=lambda d: int(d.get("startTimeUnixNano", 0)))
    return out


def summarize(session_id: str, spans: list[dict[str, Any]]) -> dict[str, Any]:
    turns = []
    tools = []
    # a model turn is two nested spans: Strands' `chat` (the cycle; carries the cache token attributes) and its
    # child `chat <model id>` (the Bedrock request; carries the token counts). Count the child, read the cache
    # numbers off its parent.
    by_id = {d.get("spanId"): d for d in spans}
    for d in spans:
        a = d.get("attributes") or {}
        name = d.get("name", "")
        dur = int(d.get("durationNano", 0)) / 1e9
        if name.startswith("chat "):
            parent = (by_id.get(d.get("parentSpanId")) or {}).get("attributes") or {}
            turns.append(
                {
                    "start": int(d.get("startTimeUnixNano", 0)) / 1e9,
                    "s": round(dur, 1),
                    "out": a.get("gen_ai.usage.output_tokens"),
                    "in": a.get("gen_ai.usage.input_tokens"),
                    "cache_read": parent.get("gen_ai.usage.cache_read_input_tokens"),
                }
            )
        elif a.get("gen_ai.tool.name") and name.startswith("execute_tool"):
            tools.append(
                {"start": int(d.get("startTimeUnixNano", 0)) / 1e9, "s": round(dur, 2), "tool": a["gen_ai.tool.name"]}
            )
    t0 = min([t["start"] for t in turns] + [t["start"] for t in tools], default=0)
    for t in turns + tools:
        t["at"] = round(t["start"] - t0, 1)
        t.pop("start")
    model_s = sum(t["s"] for t in turns)
    tool_s = sum(t["s"] for t in tools)
    return {
        "session_id": session_id,
        "n_spans": len(spans),
        "model_turns": turns,
        "tools": tools,
        "model_s": round(model_s, 1),
        "tool_s": round(tool_s, 1),
        "model_share": round(model_s / (model_s + tool_s), 2) if model_s + tool_s else None,
        "longest_turn_s": max((t["s"] for t in turns), default=None),
        "output_tokens": sum(int(t["out"] or 0) for t in turns),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("session_ids", nargs="*")
    ap.add_argument("--run", type=Path, default=None, help="run dir: take session ids from its responses")
    ap.add_argument("--alerts", nargs="*", default=None, help="with --run: only these alerts")
    ap.add_argument("--endpoint", default="DEFAULT")
    ap.add_argument("--lookback-h", type=float, default=6)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    ids = list(args.session_ids)
    if args.run:
        for f in sorted((args.run / "responses").glob("*.json")):
            alert_id = f.stem.split("~")[0]
            if args.alerts and alert_id not in args.alerts:
                continue
            d = json.loads(f.read_text())
            sid = (d.get("response") or {}).get("session_id") or (d.get("meta") or {}).get("session_id")
            if sid:
                ids.append(sid)
    if not ids:
        ap.error("no session ids")
    log_group = f"/aws/bedrock-agentcore/runtimes/{RUNTIME_ID}-{args.endpoint}"
    for sid in ids:
        s = summarize(sid, spans_for(sid, log_group, int(args.lookback_h * 3600)))
        if args.json:
            print(json.dumps(s))
            continue
        print(
            f"{sid}  spans={s['n_spans']}  model {s['model_s']} s / tools {s['tool_s']} s  (model {s['model_share']})  out {s['output_tokens']}"
        )
        for t in s["model_turns"]:
            print(f"   +{t['at']:5.1f}s  model turn {t['s']:5.1f} s   out {t['out']}  cache_read {t['cache_read']}")
        for t in s["tools"]:
            print(f"   +{t['at']:5.1f}s  tool {t['tool']:28s} {t['s']:5.2f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
