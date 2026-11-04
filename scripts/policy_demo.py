#!/usr/bin/env python
"""Demo steps 5 and 6: show the Gateway's Policy Engine refusing a shortcut, deterministically.

    uv run scripts/policy_demo.py                   # alert A-261005-0001 (a disposable background alert)
    uv run scripts/policy_demo.py --alert A-261005-0002 --user L1

Sequence, all in one policy session, as the analyst's own token:
  1. propose_disposition with no evidence in the session   -> DENIED (03a: no get_alert/order_events/discriminators)
  2. get_alert, get_order_events, compute_discriminators, get_trader_profile, get_market_events
  3. propose_disposition CLOSE_FP without the history       -> DENIED (04: CLOSE_FP needs get_trader_alert_history)
  4. get_trader_alert_history, then propose CLOSE_FP        -> ALLOWED
  5. a second propose_disposition for the same alert        -> DENIED (06: one proposal per alert per session)
  6. draft_stor_narrative as L1                             -> DENIED (07: L2 only)  [as L2: 05 needs a DRAFT_STOR proposal]
  7. a record_disposition tool                              -> does not exist on the Gateway (tools/list shows 11 tools)

The Gateway returns "Tool Execution Denied ... [Policy evaluation denied due to <policy>]" for a denial, so the
policy name is printed from the Gateway's own message. The test proposal is removed from surv-cases afterwards.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
import uuid
from pathlib import Path

import boto3

sys.path.insert(0, str(Path(__file__).resolve().parent))
from smoke_gateway import CREDS, access_token, gateway_url, load_env

REGION = "eu-west-2"
REPORT = {
    "summary": "policy demo: this report exists only to exercise the Gateway's temporal rules",
    "evidence": [{"id": "E1", "source": "compute_discriminators", "fact": "demo"}],
    "legitimate_explanations_considered": [{"explanation": "market making", "verdict": "supported"}],
}


def outcome(res_or_exc) -> str:
    if isinstance(res_or_exc, Exception):
        msg = str(res_or_exc)
        if "Policy evaluation denied due to" in msg:
            pol = msg.split("Policy evaluation denied due to", 1)[1].strip(" []")
            return f"DENIED by {pol.rsplit('-', 1)[0]}"
        return f"ERROR {type(res_or_exc).__name__}: {msg[:120]}"
    text = "".join(getattr(b, "text", "") for b in res_or_exc.content)
    if res_or_exc.is_error:
        return f"tool error: {text[:120]}"
    return "ALLOWED " + text[:90].replace("\n", " ")


async def run(alert_id: str, user: str) -> None:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamable_http_client
    from mcp.shared._httpx_utils import create_mcp_http_client

    env = load_env(CREDS)
    token = access_token(env, user)
    session = f"demo-{alert_id}-{uuid.uuid4().hex}"
    http = create_mcp_http_client(
        headers={"Authorization": f"Bearer {token}", "x-amzn-bedrock-agentcore-policy-session-id": session}
    )
    print(f"analyst {env[f'SURV_{user}_USER']} ({user})   policy session {session}\n")

    async def call(tool, args):
        try:
            return await s.call_tool(f"surv___{tool}", args)
        except Exception as exc:
            return exc

    async with streamable_http_client(f"{gateway_url()}/mcp", http_client=http) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            tools = sorted(t.name for t in (await s.list_tools()).tools)
            print(
                f"7. tools on the Gateway ({len(tools)}): record_disposition present? {'surv___record_disposition' in tools}\n"
            )

            print("1. propose_disposition before any evidence")
            print(
                "   ->",
                outcome(
                    await call(
                        "propose_disposition",
                        {"alert_id": alert_id, "disposition": "ESCALATE", "confidence": 0.5, "report": REPORT},
                    )
                ),
            )

            print("\n2. evidence tools")
            alert = json.loads(
                "".join(b.text for b in (await s.call_tool("surv___get_alert", {"alert_id": alert_id})).content)
            )
            for tool, args in (
                ("get_order_events", {"alert_id": alert_id, "pad_seconds": 2}),
                ("compute_discriminators", {"alert_id": alert_id}),
                ("get_trader_profile", {"trader_id": alert["trader_id"], "alert_id": alert_id}),
                (
                    "get_market_events",
                    {
                        "instrument": alert["instrument"],
                        "window_start": alert["window_start"],
                        "window_end": alert["window_end"],
                    },
                ),
            ):
                print(f"   {tool:26s} ->", outcome(await call(tool, args))[:40])
                await asyncio.sleep(1)
            await asyncio.sleep(6)  # response events are recorded shortly after each call completes

            print("\n3. propose CLOSE_FP without the trader's alert history")
            print(
                "   ->",
                outcome(
                    await call(
                        "propose_disposition",
                        {"alert_id": alert_id, "disposition": "CLOSE_FP", "confidence": 0.8, "report": REPORT},
                    )
                ),
            )

            print("\n4. get_trader_alert_history, then propose CLOSE_FP")
            print(
                "   history ->",
                outcome(
                    await call(
                        "get_trader_alert_history", {"trader_id": alert["trader_id"], "before_date": alert["date"]}
                    )
                )[:40],
            )
            await asyncio.sleep(6)
            print(
                "   propose ->",
                outcome(
                    await call(
                        "propose_disposition",
                        {"alert_id": alert_id, "disposition": "CLOSE_FP", "confidence": 0.8, "report": REPORT},
                    )
                ),
            )
            await asyncio.sleep(6)

            print("\n5. a second proposal for the same alert in the same session")
            print(
                "   ->",
                outcome(
                    await call(
                        "propose_disposition",
                        {"alert_id": alert_id, "disposition": "ESCALATE", "confidence": 0.5, "report": REPORT},
                    )
                ),
            )

            print(f"\n6. draft_stor_narrative as {user}")
            print("   ->", outcome(await call("draft_stor_narrative", {"alert_id": alert_id})))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--alert", default="A-261005-0001")
    ap.add_argument("--user", choices=["L1", "L2"], default="L1")
    ap.add_argument("--keep", action="store_true", help="keep the demo proposal in surv-cases")
    args = ap.parse_args()
    t0 = time.time()
    try:
        asyncio.run(run(args.alert, args.user))
    finally:
        if not args.keep:
            boto3.resource("dynamodb", region_name=REGION).Table("surv-cases").delete_item(Key={"alert_id": args.alert})
            print(f"\n(demo proposal on {args.alert} removed from surv-cases; {time.time() - t0:.0f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
