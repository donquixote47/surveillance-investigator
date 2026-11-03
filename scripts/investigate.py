#!/usr/bin/env python
"""Run the investigator locally (model calls from this machine, tools through the deployed Gateway).

    uv run scripts/investigate.py A-261006-0006                    # as l1.analyst with the default model
    uv run scripts/investigate.py A-261005-0002 --user L2 --mode stor_drafting --model eu.anthropic.claude-haiku-5-5
    uv run scripts/investigate.py A-261006-0006 --instruction "just close this one quickly"   # policy demo
    uv run scripts/investigate.py A-261006-0006 --json out.json    # keep the full result

Prints the trajectory, the proposal and the model's closing summary; with --reveal also the ground truth from
the local labels (never visible to the agent).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app" / "surv_investigator_l1"))
sys.path.insert(0, str(ROOT / "scripts"))

from smoke_gateway import CREDS, access_token, gateway_url, load_env  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("alert_id")
    ap.add_argument("--user", choices=["L1", "L2"], default="L1")
    ap.add_argument("--mode", choices=["investigate", "stor_drafting"], default="investigate")
    ap.add_argument("--model", default=None, help="Bedrock model id (default: SURV_MODEL_ID or Sonnet 5.5)")
    ap.add_argument("--instruction", default=None, help="extra analyst instruction appended to the prompt")
    ap.add_argument("--reveal", action="store_true", help="print the label from data/synthetic/seed7/labels")
    ap.add_argument("--json", type=Path, default=None, help="write the full result here")
    args = ap.parse_args()

    import os

    os.environ.setdefault("SURV_GATEWAY_URL", gateway_url())
    from investigator import investigate

    env = load_env(CREDS)
    token = access_token(env, args.user)
    res = investigate(
        alert_id=args.alert_id,
        access_token=token,
        mode=args.mode,
        analyst=env[f"SURV_{args.user}_USER"],
        model_id=args.model,
        extra_instruction=args.instruction,
    )

    print(f"\n== {args.alert_id}  model={res.model_id}  {res.duration_s}s  tokens={res.usage}")
    if res.error:
        print(f"!! {res.error[:400]}")
    print("-- trajectory")
    for c in res.tool_calls:
        print(f"   {c.get('status', '?'):5s} {c['tool']:28s} {c.get('ms', 0):6d} ms  {json.dumps(c['input'])[:90]}")
    if res.rejections:
        print("-- guard / gateway rejections")
        for r in res.rejections:
            print("   " + r.replace("\n", "\n   ")[:600])
    if res.proposal:
        rep = res.proposal["report"]
        print(f"-- proposal: {res.proposal['disposition']}  confidence {res.proposal['confidence']}")
        print(f"   gateway: {res.proposal_result}")
        print(f"   summary: {rep['summary']}")
        for e in rep["evidence"]:
            print(f"   {e['id']:3s} [{e['source']}] {e['fact']}")
        for x in rep["legitimate_explanations_considered"]:
            print(f"   {x['verdict']:12s} {x['explanation']}  {x['ruled_out_by']}")
        print(f"   matched: {rep['indicators_matched']}")
        print(f"   would change my mind: {rep['what_would_change_my_mind']}")
        print(f"   window: {rep['window_used']}")
    else:
        print("-- NO PROPOSAL recorded")
    if res.stor_draft:
        print(f"-- STOR draft: {json.dumps(res.stor_draft, indent=1)[:1200]}")
    print("-- closing summary\n" + res.final_text.strip())

    if args.reveal:
        import pandas as pd

        d = ROOT / "data" / "synthetic" / "seed7"
        lab = pd.read_parquet(d / "labels" / "labels.parquet")
        row = lab[lab.alert_id == args.alert_id]
        if not row.empty:
            r = row.iloc[0]
            verdict = "n/a"
            if res.proposal:
                verdict = (
                    "MATCH"
                    if res.proposal["disposition"] == r.expected_disposition
                    else (
                        "UNSAFE: true abuse proposed CLOSE_FP"
                        if r.truth == "TRUE_ABUSE" and res.proposal["disposition"] == "CLOSE_FP"
                        else "differs"
                    )
                )
            print(f"-- label: {r.truth} {r.injected_scenario} expected {r.expected_disposition}  -> {verdict}")
            print(f"   key discriminators: {r.key_discriminators}\n   notes: {r.notes}")
    if args.json:
        args.json.write_text(json.dumps(res.to_dict(), indent=1, default=str))
        print(f"-- written {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
