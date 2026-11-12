#!/usr/bin/env python
"""Invoke the deployed Runtime the way the analyst UI will: HTTPS to the Runtime's invocation URL with the
analyst's Cognito access token as a bearer, one session id per investigation.

    uv run scripts/invoke_runtime.py A-261006-0006                 # as L1
    uv run scripts/invoke_runtime.py A-261005-0002 --user L2 --mode stor_drafting
    uv run scripts/invoke_runtime.py A-261006-0006 --json out.json

With CUSTOM_JWT inbound auth the call is a plain HTTPS POST (no SigV4), so the UI does not need AWS credentials:
POST https://bedrock-agentcore.<region>.amazonaws.com/runtimes/<url-encoded runtime ARN>/invocations?qualifier=DEFAULT
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import uuid
from pathlib import Path
from urllib.parse import quote

import boto3
import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent))
from smoke_gateway import CREDS, access_token, load_env

REGION = "eu-west-2"
RUNTIME_NAME = "surv_default_surv_investigator_l1"


def runtime_arn() -> str:
    c = boto3.client("bedrock-agentcore-control", region_name=REGION)
    for r in c.list_agent_runtimes()["agentRuntimes"]:
        if r["agentRuntimeName"] == RUNTIME_NAME:
            return r["agentRuntimeArn"]
    raise SystemExit(f"runtime {RUNTIME_NAME} not found in {REGION}")


def invoke(
    alert_id: str, user: str, mode: str, instruction: str | None, session_id: str | None, qualifier: str = "DEFAULT"
) -> tuple[dict, str, float]:
    env = load_env(CREDS)
    token = access_token(env, user)
    arn = runtime_arn()
    url = f"https://bedrock-agentcore.{REGION}.amazonaws.com/runtimes/{quote(arn, safe='')}/invocations"
    session_id = session_id or f"surv-{alert_id}-{uuid.uuid4().hex}"  # must be 33+ characters
    payload = {"alert_id": alert_id, "mode": mode}
    if instruction:
        payload["instruction"] = instruction
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Amzn-Bedrock-AgentCore-Runtime-Session-Id": session_id,
    }
    t0 = time.time()
    with httpx.Client(timeout=httpx.Timeout(600.0, connect=30.0)) as client:
        r = client.post(url, params={"qualifier": qualifier}, headers=headers, json=payload)
    elapsed = time.time() - t0
    if r.status_code != 200:
        raise SystemExit(f"HTTP {r.status_code} after {elapsed:.1f}s: {r.text[:800]}")
    return r.json(), session_id, elapsed


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("alert_id")
    ap.add_argument("--user", choices=["L1", "L2"], default="L1")
    ap.add_argument(
        "--mode",
        choices=["investigate", "stor_drafting", "draft_stor"],
        default="investigate",
        help="draft_stor: the L2 second step; pass --session-id of the run that proposed DRAFT_STOR",
    )
    ap.add_argument("--instruction", default=None)
    ap.add_argument("--session-id", default=None)
    ap.add_argument("--qualifier", default="DEFAULT")
    ap.add_argument("--json", type=Path, default=None)
    args = ap.parse_args()
    out, session_id, elapsed = invoke(
        args.alert_id, args.user, args.mode, args.instruction, args.session_id, args.qualifier
    )
    print(
        f"== {args.alert_id} via Runtime  session={session_id}  {elapsed:.1f}s wall  agent={out.get('duration_s')}s  model={out.get('model_id')}"
    )
    if out.get("error"):
        print(f"!! {out['error']}")
    for c in out.get("tool_calls", []):
        print(f"   {c.get('status', '?'):5s} {c['tool']:28s} {c.get('ms', 0):6d} ms")
    p = out.get("proposal")
    if p:
        print(
            f"-- proposal: {p['disposition']}  confidence {p['confidence']}  analyst={out.get('analyst')} groups={out.get('groups')}"
        )
        print(f"   gateway: {out.get('proposal_result')}")
        print(f"   summary: {p['report']['summary']}")
    for r in out.get("rejections", []):
        print("-- rejection: " + r[:300].replace("\n", " "))
    if out.get("stor_draft"):
        print("-- STOR draft fields: " + ", ".join(out["stor_draft"].get("stor_fields", {}).keys()))
    print("-- closing summary\n" + (out.get("final_text") or "").strip()[:1500])
    print(f"-- usage: {out.get('usage')}")
    if args.json:
        args.json.write_text(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
