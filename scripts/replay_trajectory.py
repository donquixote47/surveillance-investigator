"""Re-run an investigation's tool calls and compare the results with what the agent saw: the audit record you can
re-execute.

    uv run scripts/replay_trajectory.py <session_id>                       # as l1.analyst, from the DEFAULT log group
    uv run scripts/replay_trajectory.py <session_id> --endpoint demo
    uv run scripts/replay_trajectory.py --run evals/runs/<run_id> --alerts A-261104-0010
    uv run scripts/replay_trajectory.py <session_id> --json out.json

What it does. The session's spans hold every `mcp tools/call <tool>` the agent made, with the arguments it sent and
the full result it received. This script replays the read-only calls, in order, through the same Gateway as the
same analyst role, and diffs each result against the recorded one. The tools are deterministic functions over the
firm's tables, so a clean replay means: the numbers in the report were produced from these inputs, and anyone with
the trace and the data can reproduce them. Only the model's narrative is not replayed; its variation is measured
separately (data doc 4.6, variance).

What it skips. `propose_disposition` and `draft_stor_narrative` write to the case and are not replayed; their
recorded inputs are shown. `recall_memory` is replayed but a difference is reported as "memory moved", not as a
mismatch: Memory legitimately changes as analysts record decisions.

Needs the analyst credentials file (`~/.config/surv-investigator/analyst-credentials.env`) and CloudWatch Logs read
permission on this machine. Each replayed call is a Gateway InvokeTool ($5 per million) and a Policy authorisation;
a replay of a ten-call investigation costs well under a cent.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from bedrock_agentcore.evaluation import CloudWatchAgentSpanCollector  # noqa: E402

from smoke_gateway import CREDS, access_token, gateway_url, load_env  # noqa: E402

REGION = "eu-west-2"
RUNTIME_ID = "surv_default_surv_investigator_l1-lrnjCN5vBp"
WRITES = ("propose_disposition", "draft_stor_narrative")
VOLATILE = ("recall_memory",)


def recorded_calls(session_id: str, log_group: str) -> list[dict[str, Any]]:
    """The tool calls of one session, in the order they were made, with arguments and results as the agent saw them."""
    collector = CloudWatchAgentSpanCollector(
        log_group_name=log_group, region=REGION, max_wait_seconds=60, poll_interval_seconds=2
    )
    end = datetime.now(UTC)
    spans = collector.collect(session_id=session_id, start_time=end - timedelta(days=30), end_time=end)
    calls = []
    for s in spans:
        name = str(s.get("name") or "")
        if not name.startswith("mcp tools/call"):
            continue
        a = s.get("attributes") or {}
        tool = name.split("mcp tools/call", 1)[1].strip().removeprefix("surv___")
        try:
            args = json.loads(a.get("gen_ai.tool.call.arguments") or "{}")
        except json.JSONDecodeError:
            args = {"_raw": a.get("gen_ai.tool.call.arguments")}
        calls.append(
            {
                "tool": tool,
                "args": args,
                "recorded": a.get("gen_ai.tool.call.result"),
                "start_ns": int(s.get("startTimeUnixNano", 0)),
                "duration_ms": int(s.get("durationNano", 0)) / 1e6,
            }
        )
    calls.sort(key=lambda c: c["start_ns"])
    return calls


REPR_TEXT_RE = re.compile(r"TextContent\(type='text', text='((?:[^'\\]|\\.)*)'")


def canonical(text: str | None) -> Any:
    """Parse a tool result for comparison. The span records the Python repr of the MCP result
    (`meta=None content=[TextContent(type='text', text='{...}')] ...`); the replay gets the text content directly.
    Both end up as the parsed JSON the tool returned."""
    if text is None:
        return None
    if isinstance(text, str) and text.startswith("meta="):
        m = REPR_TEXT_RE.search(text)
        if m:
            text = m.group(1).encode().decode("unicode_escape")
    try:
        return json.loads(text)
    except json.JSONDecodeError, TypeError, UnicodeDecodeError:
        return text


def diff(a: Any, b: Any, path: str = "") -> list[str]:
    """Paths where two JSON-like values differ, with both values shortened."""
    out: list[str] = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a:
                out.append(f"{path}/{k}: missing in recorded")
            elif k not in b:
                out.append(f"{path}/{k}: missing in replay")
            else:
                out += diff(a[k], b[k], f"{path}/{k}")
        return out
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append(f"{path}: {len(a)} items recorded, {len(b)} replayed")
        for i, (x, y) in enumerate(zip(a, b, strict=False)):
            out += diff(x, y, f"{path}[{i}]")
        return out
    if a != b:
        out.append(f"{path}: recorded {str(a)[:60]!r}, replayed {str(b)[:60]!r}")
    return out


async def replay(calls: list[dict[str, Any]], token: str, url: str) -> list[dict[str, Any]]:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamable_http_client
    from mcp.shared._httpx_utils import create_mcp_http_client

    # a fresh policy session: the replay is read-only, so no temporal rule needs this session's history
    http = create_mcp_http_client(
        headers={
            "Authorization": f"Bearer {token}",
            "x-amzn-bedrock-agentcore-policy-session-id": f"replay-{uuid.uuid4().hex}",
        }
    )
    results = []
    async with streamable_http_client(f"{url}/mcp", http_client=http) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            for c in calls:
                entry = {"tool": c["tool"], "args": c["args"], "status": None, "differences": []}
                if c["tool"] in WRITES:
                    entry["status"] = "not replayed (writes to the case)"
                    results.append(entry)
                    continue
                res = await session.call_tool(f"surv___{c['tool']}", c["args"])
                text = "".join(getattr(x, "text", "") for x in res.content)
                replayed = canonical(text) if text else (getattr(res, "structured_content", None) or {})
                recorded = canonical(c["recorded"])
                # the recorded result is the Gateway's text content; both sides are compared as parsed JSON
                if isinstance(recorded, dict) and "content" in recorded and isinstance(recorded["content"], list):
                    inner = "".join(x.get("text", "") for x in recorded["content"] if isinstance(x, dict))
                    recorded = canonical(inner) if inner else recorded
                d = diff(recorded, replayed)
                if res.is_error:
                    entry["status"] = "replay error"
                    entry["differences"] = [text[:200]]
                elif not d:
                    entry["status"] = "identical"
                elif c["tool"] in VOLATILE:
                    entry["status"] = "memory moved (expected)"
                    entry["differences"] = d[:10]
                else:
                    entry["status"] = "MISMATCH"
                    entry["differences"] = d[:20]
                results.append(entry)
    return results


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("session_ids", nargs="*")
    ap.add_argument("--run", type=Path, default=None, help="run dir: take session ids from its responses")
    ap.add_argument("--alerts", nargs="*", default=None, help="with --run: only these alerts")
    ap.add_argument("--endpoint", default="DEFAULT", help="Runtime endpoint whose log group holds the session")
    ap.add_argument("--user", choices=["L1", "L2"], default="L1")
    ap.add_argument("--json", type=Path, default=None)
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

    env = load_env(CREDS)
    token = access_token(env, args.user)
    url = gateway_url()
    log_group = f"/aws/bedrock-agentcore/runtimes/{RUNTIME_ID}-{args.endpoint}"
    all_out = []
    exit_code = 0
    for sid in ids:
        calls = recorded_calls(sid, log_group)
        if not calls:
            print(f"{sid}: no tool-call spans found in {log_group}")
            exit_code = 2
            continue
        results = asyncio.run(replay(calls, token, url))
        n_same = sum(1 for r in results if r["status"] == "identical")
        n_mis = sum(1 for r in results if r["status"] == "MISMATCH")
        n_skip = sum(1 for r in results if r["status"].startswith("not replayed"))
        n_mem = sum(1 for r in results if r["status"].startswith("memory"))
        verdict = "REPRODUCED" if n_mis == 0 else "NOT REPRODUCED"
        print(
            f"{sid}\n  {len(calls)} tool calls: {n_same} identical, {n_mem} memory moved, {n_skip} not replayed "
            f"(writes), {n_mis} mismatches -> {verdict}"
        )
        for r in results:
            mark = {"identical": "=", "MISMATCH": "!"}.get(
                r["status"], "~" if r["status"].startswith("memory") else "-"
            )
            print(f"  {mark} {r['tool']:28s} {r['status']}")
            for dline in r["differences"]:
                print(f"        {dline}")
        all_out.append({"session_id": sid, "verdict": verdict, "calls": results})
        if n_mis:
            exit_code = 1
    if args.json:
        args.json.write_text(json.dumps(all_out, indent=1, default=str))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
