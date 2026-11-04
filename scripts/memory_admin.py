#!/usr/bin/env python
"""Administer the investigator's Memory: ingest the procedures, list or delete records in a namespace.

    uv run scripts/memory_admin.py ingest-procedures            # one record per topic into /procedures/
    uv run scripts/memory_admin.py list /traders/T-X1016-03/notes/
    uv run scripts/memory_admin.py delete /traders/T-X1016-03/notes/ --kind feedback   # by metadata kind
    uv run scripts/memory_admin.py seed-history                 # cases_history -> /traders/<id>/notes/ (one record each)

Uses this machine's AWS credentials (admin); the Lambdas only ever read, or append through the human path.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import boto3

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

REGION = "eu-west-2"
MEMORY_NAME = "surv_default_investigator_memory"


def memory_id() -> str:
    c = boto3.client("bedrock-agentcore-control", region_name=REGION)
    for m in c.list_memories()["memories"]:
        if m["id"].startswith(MEMORY_NAME):
            return m["id"]
    raise SystemExit(f"no memory named {MEMORY_NAME}*")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("ingest-procedures")
    sub.add_parser("seed-history").add_argument("--dataset", default="data/synthetic/seed7")
    p_list = sub.add_parser("list")
    p_list.add_argument("namespace")
    p_del = sub.add_parser("delete")
    p_del.add_argument("namespace")
    p_del.add_argument("--kind", default=None, help="only records whose metadata.kind equals this")
    p_del.add_argument("--yes", action="store_true")
    args = ap.parse_args()

    import os

    os.environ["MEMORY_ID"] = memory_id()
    from tools import memory_access as mem

    c = mem.client()
    mid = mem.memory_id()

    if args.cmd == "ingest-procedures":
        from tools.procedures import PROCEDURES

        recs = [
            {
                "namespace": mem.PROCEDURES_NS,
                "text": f"[{topic}] {text}",
                "metadata": {"kind": "procedure", "topic": topic},
            }
            for topic, text in PROCEDURES.items()
        ]
        out = mem.write_records(recs)
        print(
            f"ingested {sum(1 for o in out if o['status'] == 'SUCCEEDED')}/{len(recs)} procedure records into {mem.PROCEDURES_NS}"
        )
        return 0

    if args.cmd == "seed-history":
        import pandas as pd

        hist = pd.read_parquet(ROOT / args.dataset / "cases_history.parquet")
        desks = pd.read_parquet(ROOT / args.dataset / "traders.parquet").set_index("trader_id")["desk"].to_dict()
        recs = []
        for r in hist.to_dict("records"):
            alert = {k: r[k] for k in ("alert_id", "date", "scenario", "instrument", "trader_id")}
            text = mem.disposition_text(
                alert,
                {"proposed_disposition": r["proposed_disposition"]},
                r["recorded_disposition"],
                r["recorded_by"],
                r["analyst_note"],
                bool(r["override"]),
            )
            meta = {
                "kind": "disposition",
                "alert_id": r["alert_id"],
                "trader_id": r["trader_id"],
                "instrument": r["instrument"],
                "date": r["date"],
                "recorded": r["recorded_disposition"],
                "proposed": r["proposed_disposition"],
                "override": str(bool(r["override"])).lower(),
                "recorded_by": r["recorded_by"],
                "seeded": "true",
            }
            recs += mem._fan_out(alert, desks.get(r["trader_id"]), text, meta)
        out = mem.write_records(recs)
        print(
            f"seeded {sum(1 for o in out if o['status'] == 'SUCCEEDED')}/{len(recs)} prior dispositions from cases_history"
        )
        return 0

    ns = args.namespace.rstrip("/")
    rows = []
    token = None
    while True:
        kw = {"memoryId": mid, "namespace": ns}
        if token:
            kw["nextToken"] = token
        resp = c.list_memory_records(**kw)
        rows += resp.get("memoryRecordSummaries", [])
        token = resp.get("nextToken")
        if not token:
            break
    if args.cmd == "list":
        print(f"{len(rows)} records in {ns}/")
        for r in rows:
            meta = {k: v.get("stringValue") for k, v in (r.get("metadata") or {}).items() if not k.startswith("x-amz-")}
            strat = (r.get("metadata") or {}).get("x-amz-agentcore-memory-strategyType", {}).get("stringValue")
            print(
                f"  {r['memoryRecordId'][:28]:28s} {str(r.get('createdAt'))[:19]} {'[extracted]' if strat and strat != 'NONE' else '[direct]   '} {meta.get('kind', ''):11s} {r['content']['text'][:110]}"
            )
        return 0
    if args.cmd == "delete":
        victims = [
            r
            for r in rows
            if not args.kind or (r.get("metadata") or {}).get("kind", {}).get("stringValue") == args.kind
        ]
        print(f"{len(victims)} record(s) to delete in {ns}/" + (f" with kind={args.kind}" if args.kind else ""))
        if not victims:
            return 0
        if not args.yes and input("delete them? [y/N] ").strip().lower() != "y":
            return 1
        for r in victims:
            c.delete_memory_record(memoryId=mid, memoryRecordId=r["memoryRecordId"])
        print("deleted")
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
