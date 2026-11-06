#!/usr/bin/env python
"""Create, update, show and delete the project's custom evaluators from the JSON files in `evals/evaluators/`.

    uv run evals/evaluators.py list
    uv run evals/evaluators.py create rationale_rubric
    uv run evals/evaluators.py update rationale_rubric       # after editing the instructions or the scale
    uv run evals/evaluators.py show rationale_rubric
    uv run evals/evaluators.py delete rationale_rubric --yes

Why boto3 and not `agentcore add evaluator`: the CLI fixes the judge's inference config to temperature 0 and
maxTokens 4096, and Claude 5.5 rejects `temperature` (agentcore-gotchas). The file keeps the full
`evaluatorConfig` the API takes; the resource is tagged like everything else in the project.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import boto3

REGION = "eu-west-2"
HERE = Path(__file__).resolve().parent / "evaluators"
TAGS = {"Project": "agentcore-surveillance-investigator", "auto-delete": "no"}


def cp():
    return boto3.client("bedrock-agentcore-control", region_name=REGION)


def spec(name: str) -> dict:
    return json.loads((HERE / f"{name}.json").read_text())


def find(client, evaluator_name: str) -> dict | None:
    token = None
    while True:
        kw = {"maxResults": 50}
        if token:
            kw["nextToken"] = token
        r = client.list_evaluators(**kw)
        for e in r.get("evaluators", []) or r.get("evaluatorSummaries", []):
            if e.get("evaluatorName") == evaluator_name:
                return e
        token = r.get("nextToken")
        if not token:
            return None


def wait_ready(client, evaluator_id: str, timeout_s: int = 300) -> dict:
    t0 = time.time()
    while True:
        e = client.get_evaluator(evaluatorId=evaluator_id)
        status = e.get("status")
        if status == "ACTIVE":
            return e
        if status and status.endswith("FAILED"):
            raise SystemExit(
                f"evaluator {evaluator_id}: {status} {e.get('failureReason') or e.get('statusReason') or ''}"
            )
        if time.time() - t0 > timeout_s:
            raise SystemExit(f"evaluator {evaluator_id} still {status} after {timeout_s}s")
        time.sleep(3)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action", choices=["list", "create", "update", "show", "delete"])
    ap.add_argument("name", nargs="?", help="file stem under evals/evaluators/")
    ap.add_argument("--yes", action="store_true")
    args = ap.parse_args()
    client = cp()

    if args.action == "list":
        token = None
        while True:
            kw = {"maxResults": 50}
            if token:
                kw["nextToken"] = token
            r = client.list_evaluators(**kw)
            for e in r.get("evaluators", []) or r.get("evaluatorSummaries", []):
                if not str(e.get("evaluatorArn", "")).startswith("arn:aws:bedrock-agentcore:::"):
                    print(
                        f"{e.get('evaluatorId'):40s} {e.get('level', ''):8s} {e.get('status', ''):10s} {e.get('evaluatorName')}"
                    )
            token = r.get("nextToken")
            if not token:
                break
        return 0

    if not args.name:
        raise SystemExit("name is required")
    s = spec(args.name)
    existing = find(client, s["name"])

    if args.action == "show":
        if not existing:
            print("not created")
            return 0
        print(json.dumps(client.get_evaluator(evaluatorId=existing["evaluatorId"]), indent=1, default=str))
        return 0

    if args.action == "create":
        if existing:
            print(f"already exists: {existing['evaluatorId']} ({existing.get('status')})")
            return 0
        r = client.create_evaluator(
            evaluatorName=s["name"],
            level=s["level"],
            description=s.get("description", ""),
            evaluatorConfig=s["evaluatorConfig"],
            tags=TAGS,
        )
        e = wait_ready(client, r["evaluatorId"])
        print(f"created {r['evaluatorId']} {e.get('status')}\n{r['evaluatorArn']}")
        return 0

    if args.action == "update":
        if not existing:
            raise SystemExit("not created yet; use create")
        client.update_evaluator(
            evaluatorId=existing["evaluatorId"],
            description=s.get("description", ""),
            evaluatorConfig=s["evaluatorConfig"],
        )
        e = wait_ready(client, existing["evaluatorId"])
        print(f"updated {existing['evaluatorId']} {e.get('status')}")
        return 0

    if args.action == "delete":
        if not existing:
            print("nothing to delete")
            return 0
        if not args.yes:
            raise SystemExit(f"would delete {existing['evaluatorId']}; pass --yes")
        client.delete_evaluator(evaluatorId=existing["evaluatorId"])
        print(f"deleted {existing['evaluatorId']}")
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
