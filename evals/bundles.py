#!/usr/bin/env python
"""AgentCore configuration bundles for the investigator (data doc 4.5.3 and 4.3): a bundle is a versioned,
immutable snapshot of `system_prompt`, `model_id` and `effort`, keyed by the Runtime ARN. The agent reads it per
request from the W3C `baggage` header (`investigator.bundle_config`); the harness sends that header with
`--bundle <bundleId>:<versionId>`; a Gateway A/B test sends it on its own.

    uv run evals/bundles.py create v1-current                       # the prompt the code runs today, Sonnet 5.5
    uv run evals/bundles.py create v2-rec --prompt-file evals/recommendations/<id>.recommended-prompt.txt
    uv run evals/bundles.py create opus --model eu.anthropic.claude-opus-5-5      # the model arm: prompt unchanged
    uv run evals/bundles.py list
    uv run evals/bundles.py show <bundleId> <versionId>
    uv run evals/bundles.py delete <bundleId> --yes

Bundle names are prefixed `surv_` (the API allows letters, digits and underscores only). Every bundle is tagged like the rest of the project.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

import boto3

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app" / "surv_investigator_l1"))
REGION = "eu-west-2"
RUNTIME_ARN = "arn:aws:bedrock-agentcore:eu-west-2:384308066035:runtime/surv_default_surv_investigator_l1-lrnjCN5vBp"
DEFAULT_MODEL = "eu.anthropic.claude-sonnet-5-5"
TAGS = {"Project": "agentcore-surveillance-investigator", "auto-delete": "no"}
REGISTRY = ROOT / "evals" / "bundles.json"  # local record of what was created, for the docs and the harness


def cp():
    return boto3.client("bedrock-agentcore-control", region_name=REGION)


def registry() -> dict:
    return json.loads(REGISTRY.read_text()) if REGISTRY.exists() else {}


def create(name: str, prompt_file: Path | None, model: str, effort: str, description: str) -> dict:
    if prompt_file:
        text = prompt_file.read_text()
        prompt_source = str(prompt_file.relative_to(ROOT)) if prompt_file.is_relative_to(ROOT) else str(prompt_file)
    else:
        from prompt import system_prompt

        text = system_prompt("investigate")
        prompt_source = "app/surv_investigator_l1/prompt.py system_prompt('investigate') at creation time"
    full = "surv_" + re.sub(r"[^a-zA-Z0-9_]", "_", name)  # API pattern [a-zA-Z][a-zA-Z0-9_]{0,99}
    r = cp().create_configuration_bundle(
        clientToken=str(uuid.uuid4()),
        bundleName=full,
        description=description or f"{full}: model {model}, effort {effort}, prompt from {prompt_source}",
        components={RUNTIME_ARN: {"configuration": {"system_prompt": text, "model_id": model, "effort": effort}}},
        commitMessage=f"created by evals/bundles.py on {datetime.now(UTC).isoformat(timespec='seconds')}",
        tags=TAGS,
    )
    rec = {
        "bundle_name": full,
        "bundle_id": r["bundleId"],
        "bundle_arn": r["bundleArn"],
        "version_id": r["versionId"],
        "model_id": model,
        "effort": effort,
        "prompt_source": prompt_source,
        "prompt_chars": len(text),
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "baggage": f"{r['bundleId']}:{r['versionId']}",
    }
    reg = registry()
    reg[name] = rec
    REGISTRY.write_text(json.dumps(reg, indent=1))
    print(json.dumps(rec, indent=1))
    return rec


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action", choices=["create", "list", "show", "delete"])
    ap.add_argument("name", nargs="?")
    ap.add_argument("version", nargs="?")
    ap.add_argument("--prompt-file", type=Path, default=None)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--effort", default="medium", choices=["low", "medium", "high"])
    ap.add_argument("--description", default="")
    ap.add_argument("--yes", action="store_true")
    args = ap.parse_args()
    c = cp()
    if args.action == "list":
        for b in c.list_configuration_bundles(maxResults=50).get("bundles", []):
            print(f"{b.get('bundleId'):45s} {b.get('bundleName'):30s} {b.get('createdAt')}")
        reg = registry()
        if reg:
            print("\nlocal registry (evals/bundles.json):")
            for k, v in reg.items():
                print(
                    f"  {k:14s} {v['baggage']}  model={v['model_id']} effort={v['effort']}  {v['prompt_source'][:60]}"
                )
        return 0
    if not args.name:
        raise SystemExit("name is required")
    if args.action == "create":
        if args.name in registry():
            raise SystemExit(f"{args.name} already in evals/bundles.json: {registry()[args.name]['baggage']}")
        create(args.name, args.prompt_file, args.model, args.effort, args.description)
        return 0
    if args.action == "show":
        bid = registry().get(args.name, {}).get("bundle_id", args.name)
        vid = args.version or registry().get(args.name, {}).get("version_id")
        r = c.get_configuration_bundle_version(bundleId=bid, versionId=vid)
        comp = r["components"].get(RUNTIME_ARN, {}).get("configuration", {})
        print(
            json.dumps(
                {k: v for k, v in r.items() if k not in ("components", "ResponseMetadata")}, indent=1, default=str
            )
        )
        print(json.dumps({k: (v if k != "system_prompt" else f"<{len(v)} chars>") for k, v in comp.items()}, indent=1))
        return 0
    if args.action == "delete":
        bid = registry().get(args.name, {}).get("bundle_id", args.name)
        if not args.yes:
            raise SystemExit(f"would delete bundle {bid}; pass --yes")
        c.delete_configuration_bundle(bundleId=bid)
        reg = registry()
        reg.pop(args.name, None)
        REGISTRY.write_text(json.dumps(reg, indent=1))
        print(f"deleted {bid}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
