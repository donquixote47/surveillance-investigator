#!/usr/bin/env python
"""Validate statements in policies/ against the deployed Policy Engine and print the service's findings.

    uv run scripts/validate_policies.py                 # all files
    uv run scripts/validate_policies.py policies/06-one-proposal-per-alert.dw

Each statement is created on the engine with FAIL_ON_ANY_FINDINGS under a `probe_` name, its status and reasons
are printed, and it is deleted again, so the engine ends as it started. The engine must already be attached to
the Gateway (the Cedar schema comes from the Gateway's tool manifest). Note: adding a temporal policy, even a
probe, invalidates the engine's open policy sessions (devguide, "Session invalidation").
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import boto3

REGION = "eu-west-2"
ENGINE_NAME = "surv_default_investigator_pe"


def wait(fn, done, timeout_s=120, every=3):
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        r = fn()
        if done(r):
            return r
        time.sleep(every)
    raise TimeoutError("timed out")


def main() -> int:
    files = [Path(a) for a in sys.argv[1:]] or sorted(Path("policies").glob("*"))
    c = boto3.client("bedrock-agentcore-control", region_name=REGION)
    engines = [e for e in c.list_policy_engines()["policyEngines"] if e["name"] == ENGINE_NAME]
    if not engines:
        print(f"no policy engine named {ENGINE_NAME}; deploy it first (agentcore deploy)")
        return 1
    pe = engines[0]["policyEngineId"]
    print("engine", pe, flush=True)
    ok = 0
    for f in files:
        stmt = f.read_text()
        name = "probe_" + f.stem.replace("-", "_")[:30]
        try:
            r = c.create_policy(
                policyEngineId=pe,
                name=name,
                validationMode="FAIL_ON_ANY_FINDINGS",
                definition={"policy": {"statement": stmt}},
            )
            pid = r["policyId"]
            g = wait(lambda pid=pid: c.get_policy(policyEngineId=pe, policyId=pid), lambda x: x["status"] != "CREATING")
            print(f"\n== {f.name}: {g['status']}", flush=True)
            for s in g.get("statusReasons") or []:
                print("   " + s.replace("\n", "\n   ")[:1800])
            ok += g["status"] == "ACTIVE"
            try:
                c.delete_policy(policyEngineId=pe, policyId=pid)
            except Exception as exc:  # leave a trace, the next run will find it under probe_
                print(f"   (delete failed: {str(exc)[:200]})")
        except Exception as exc:
            print(f"\n== {f.name}: REJECTED\n   {str(exc)[:1800]}", flush=True)
    print(f"\n{ok}/{len(files)} statements valid with FAIL_ON_ANY_FINDINGS")
    leftovers = [p for p in c.list_policies(policyEngineId=pe).get("policies", []) if p["name"].startswith("probe_")]
    for p in leftovers:
        c.delete_policy(policyEngineId=pe, policyId=p["policyId"])
    if leftovers:
        print(f"removed {len(leftovers)} leftover probe policies")
    return 0


if __name__ == "__main__":
    sys.exit(main())
