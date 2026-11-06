#!/usr/bin/env python
"""Turn analyst overrides in `surv-cases` into labelled cases (data doc section 4.5.2).

    uv run evals/ingest_overrides.py              # scan the table, merge into labels/overrides.parquet, print them
    uv run evals/ingest_overrides.py --dry-run    # print only

An override is a case whose `recorded_disposition` differs from the agent's `proposed_disposition`. Each becomes
a row with truth = the analyst's decision (CLOSE_FP -> FALSE_POSITIVE, anything else -> TRUE_ABUSE),
expected_disposition = the recorded one, key_discriminators = the analyst's note, and the run it came from
(the eval run whose saved response carries the same `proposed_at`, or "ui" when the proposal came from the
analyst UI). The dataset's own labels are never modified: overrides live in `labels/overrides.parquet`, and
`evals/run_dataset.py` reports agreement on "alerts an analyst previously overrode" as its own line.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import boto3
import pandas as pd
from boto3.dynamodb.types import TypeDeserializer

ROOT = Path(__file__).resolve().parents[1]
REGION = "eu-west-2"
CASES_TABLE = "surv-cases"
RUNS_DIR = ROOT / "evals" / "runs"
_des = TypeDeserializer()


def scan_cases() -> list[dict[str, Any]]:
    c = boto3.client("dynamodb", region_name=REGION)
    items: list[dict[str, Any]] = []
    kw: dict[str, Any] = {"TableName": CASES_TABLE, "FilterExpression": "attribute_exists(recorded_disposition)"}
    while True:
        r = c.scan(**kw)
        items.extend({k: _des.deserialize(v) for k, v in it.items()} for it in r.get("Items", []))
        if "LastEvaluatedKey" not in r:
            return items
        kw["ExclusiveStartKey"] = r["LastEvaluatedKey"]


def source_run(alert_id: str, proposed_at: str | None) -> str:
    """The eval run whose saved response for this alert carries the same proposed_at; else 'ui'."""
    if not proposed_at:
        return "ui"
    for p in sorted(RUNS_DIR.glob(f"*/responses/{alert_id}.json")):
        try:
            d = json.loads(p.read_text())
        except json.JSONDecodeError:
            continue
        if str(((d.get("case_after") or {}).get("proposed_at")) or "") == str(proposed_at):
            return p.parents[1].name
    return "ui"


def override_rows(cases: list[dict[str, Any]], labels: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for c in cases:
        proposed, recorded = c.get("proposed_disposition"), c.get("recorded_disposition")
        if not recorded or not proposed or recorded == proposed:
            continue
        lab = labels.get(c["alert_id"], {})
        # an eval run re-proposes on alerts the analyst already recorded: the pairing is then recording-first
        recorded_first = bool(
            c.get("recorded_at") and c.get("proposed_at") and str(c["recorded_at"]) < str(c["proposed_at"])
        )
        rows.append(
            {
                "alert_id": c["alert_id"],
                "truth": "FALSE_POSITIVE" if recorded == "CLOSE_FP" else "TRUE_ABUSE",
                "expected_disposition": recorded,
                "proposed_disposition": proposed,
                "injected_scenario": lab.get("injected_scenario", "ANALYST"),
                "dataset_truth": lab.get("truth"),
                "dataset_expected": lab.get("expected_disposition"),
                "key_discriminators": json.dumps([c.get("analyst_note") or ""]),
                "recorded_by": c.get("recorded_by"),
                "recorded_at": c.get("recorded_at"),
                "proposed_at": c.get("proposed_at"),
                "source_run": "ui" if recorded_first else source_run(c["alert_id"], c.get("proposed_at")),
                "recorded_before_proposal": recorded_first,
                "ingested_at": datetime.now(UTC).isoformat(timespec="seconds"),
            }
        )
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dataset", type=Path, default=ROOT / "data" / "synthetic" / "seed7")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    labels = {r["alert_id"]: r for r in pd.read_parquet(args.dataset / "labels" / "labels.parquet").to_dict("records")}
    rows = override_rows(scan_cases(), labels)
    out = args.dataset / "labels" / "overrides.parquet"
    if out.exists():
        old = pd.read_parquet(out)
        merged = pd.concat([old, pd.DataFrame(rows)], ignore_index=True) if rows else old
        merged = merged.drop_duplicates(subset=["alert_id", "recorded_at"], keep="first")
    else:
        merged = pd.DataFrame(rows)
    for r in rows:
        agrees = "agrees with" if r["expected_disposition"] == r["dataset_expected"] else "DIFFERS from"
        print(
            f"{r['alert_id']} {r['injected_scenario']:18s} agent {r['proposed_disposition']:10s} -> analyst {r['expected_disposition']:10s} "
            f"by {r['recorded_by']} ({r['source_run']}{', recorded before this proposal' if r['recorded_before_proposal'] else ''}); "
            f"{agrees} the dataset label; note: {json.loads(r['key_discriminators'])[0][:90]}"
        )
    print(
        f"{len(rows)} override(s) in the table; {len(merged)} in {out.name}"
        + (" (dry run, not written)" if args.dry_run else "")
    )
    if not args.dry_run and len(merged):
        merged.to_parquet(out, index=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
