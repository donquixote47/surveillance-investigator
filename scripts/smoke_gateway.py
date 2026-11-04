#!/usr/bin/env python
"""Smoke test the deployed Gateway as an analyst would reach it: Cognito login, MCP over streamable HTTP,
list tools, call a few.

    uv run scripts/smoke_gateway.py                       # as l1.analyst, alert A-261006-0006
    uv run scripts/smoke_gateway.py --user L2 --alert A-261005-0001 --tools get_alert get_trader_profile

Credentials come from ~/.config/surv-investigator/analyst-credentials.env (written once after the first deploy,
mode 600, outside the repo). The Gateway URL is read from the deployed Gateway named `surv-default-surv-investigator`.

The token sent is the Cognito *access* token: the Gateway's `allowedClients` check reads the `client_id` claim,
which Cognito puts in access tokens (the id token carries the client id in `aud` instead).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

import boto3

REGION = "eu-west-2"
CREDS = Path.home() / ".config" / "surv-investigator" / "analyst-credentials.env"
GATEWAY_NAME = "surv-default-surv-investigator"


def load_env(path: Path) -> dict[str, str]:
    out = {}
    for line in path.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def access_token(env: dict[str, str], level: str) -> str:
    idp = boto3.client("cognito-idp", region_name=REGION)
    r = idp.initiate_auth(
        ClientId=env["SURV_CLIENT_ID"],
        AuthFlow="USER_PASSWORD_AUTH",
        AuthParameters={"USERNAME": env[f"SURV_{level}_USER"], "PASSWORD": env[f"SURV_{level}_PASSWORD"]},
    )
    return r["AuthenticationResult"]["AccessToken"]


def gateway_url() -> str:
    c = boto3.client("bedrock-agentcore-control", region_name=REGION)
    for g in c.list_gateways()["items"]:
        if g["name"] == GATEWAY_NAME:
            return c.get_gateway(gatewayIdentifier=g["gatewayId"])["gatewayUrl"]
    raise SystemExit(f"no gateway named {GATEWAY_NAME} in {REGION}")


async def run(url: str, token: str, alert_id: str, tools: list[str], verbose: bool) -> int:
    # mcp 2.x: headers go on a pre-built httpx client, the transport yields (read, write)
    import uuid

    from mcp import ClientSession
    from mcp.client.streamable_http import streamable_http_client
    from mcp.shared._httpx_utils import create_mcp_http_client

    # every Gateway call names a policy session; temporal policies look at this session's history only
    http = create_mcp_http_client(
        headers={
            "Authorization": f"Bearer {token}",
            "x-amzn-bedrock-agentcore-policy-session-id": f"smoke-{uuid.uuid4().hex}",
        }
    )
    failures = 0
    async with streamable_http_client(f"{url}/mcp", http_client=http) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            listed = await session.list_tools()
            names = sorted(t.name for t in listed.tools)
            print(f"tools/list -> {len(names)} tools")
            for n in names:
                print(f"   {n}")
            inputs = {
                "get_alert": {"alert_id": alert_id},
                "compute_discriminators": {"alert_id": alert_id},
                "get_procedures": {"topic": "closure_standard"},
                "get_order_events": {"alert_id": alert_id, "pad_seconds": 2},
                "reconstruct_book": {"alert_id": alert_id, "levels": 3},
            }
            alert = None
            for tool in tools:
                args = dict(inputs.get(tool, {}))
                if tool in ("get_trader_profile", "get_trader_alert_history") and alert:
                    args = {
                        "trader_id": alert["trader_id"],
                        **({"alert_id": alert_id} if tool == "get_trader_profile" else {}),
                    }
                if tool == "get_instrument_stats" and alert:
                    args = {"instrument": alert["instrument"], "date": alert["date"]}
                if tool == "get_market_events" and alert:
                    args = {
                        "instrument": alert["instrument"],
                        "window_start": alert["window_start"],
                        "window_end": alert["window_end"],
                    }
                t0 = time.time()
                res = await session.call_tool(f"surv___{tool}", args)
                ms = (time.time() - t0) * 1000
                text = "".join(getattr(c, "text", "") for c in res.content)
                try:
                    body = json.loads(text) if text else (getattr(res, "structured_content", None) or {})
                except json.JSONDecodeError:
                    body = {"raw": text[:300]}
                ok = not res.is_error and "error" not in body
                failures += 0 if ok else 1
                print(
                    f"{'ok ' if ok else 'ERR'} surv___{tool} {ms:6.0f} ms  keys={list(body)[:8] if isinstance(body, dict) else type(body).__name__}"
                )
                if tool == "get_alert" and ok:
                    alert = body
                if verbose or not ok:
                    print(json.dumps(body, indent=1)[:1500])
    return failures


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--user", choices=["L1", "L2"], default="L1")
    ap.add_argument("--alert", default="A-261006-0006")
    ap.add_argument(
        "--tools",
        nargs="*",
        default=["get_alert", "compute_discriminators", "get_trader_profile", "get_instrument_stats", "get_procedures"],
    )
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()
    env = load_env(CREDS) if CREDS.exists() else dict(os.environ)
    token = access_token(env, args.user)
    url = gateway_url()
    print(f"gateway {url}\nuser    {env[f'SURV_{args.user}_USER']}")
    failures = asyncio.run(run(url, token, args.alert, args.tools, args.verbose))
    print("all calls ok" if failures == 0 else f"{failures} call(s) failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
