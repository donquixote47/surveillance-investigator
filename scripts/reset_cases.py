"""Put case rows back to "no proposal yet", the state an alert has when it arrives from the detector.

Evaluation runs invoke the agent on every alert and leave `proposed_*` on every case row, which is not what a
queue looks like in use. This script clears the agent's proposal fields so the analyst can run the investigation
live. It never touches a case with a recorded disposition (that is the analyst's record and the history Memory
relies on) unless `--include-recorded` is given, and it never touches Memory at all.

    uv run scripts/reset_cases.py                                   # dry run: what would be cleared, by day
    uv run scripts/reset_cases.py --dates 2026-11-02 2026-11-03      # only these session days
    uv run scripts/reset_cases.py --from 2026-11-01                  # every day from this date on
    uv run scripts/reset_cases.py --alerts A-261006-0006             # named alerts
    uv run scripts/reset_cases.py --from 2026-11-01 --apply          # do it

What "cleared" means: `proposed_disposition`, `confidence`, `report`, `proposed_at`, `proposal_count`,
`proposal_history` and `proposal_provenance` are removed and `status` goes back to OPEN. `case_id`, `trader_id`,
`date`, `scenario` stay (a case row with no proposal is what the human path returns for an untouched alert anyway).
`--include-recorded --apply` also removes `recorded_*`, `analyst_note`, `override`, `feedback`, `decision_history`
and the `decision_lock` (so the alert can be investigated again), sets the alert's own status back to OPEN, and
prints the Memory namespaces that then hold stale records so you can delete them with
`scripts/memory_admin.py delete`; it does not delete them for you. This is the only way to reopen a decided alert
in the demo; a firm's reopen is a Level-2 procedure step and is not built.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

import boto3

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from tools.case_fields import PROPOSAL_FIELDS, RECORD_FIELDS

REGION = "eu-west-2"
TABLE = "surv-cases"
ALERTS_TABLE = "surv-alerts"


def scan_cases(table) -> list[dict]:
    rows: list[dict] = []
    kw: dict = {}
    while True:
        page = table.scan(**kw)
        rows.extend(page.get("Items", []))
        if "LastEvaluatedKey" not in page:
            return rows
        kw["ExclusiveStartKey"] = page["LastEvaluatedKey"]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dates", nargs="*", default=None, help="session days YYYY-MM-DD")
    ap.add_argument("--from", dest="from_date", default=None, help="every session day >= this date")
    ap.add_argument("--to", dest="to_date", default=None, help="every session day <= this date")
    ap.add_argument("--alerts", nargs="*", default=None, help="alert ids")
    ap.add_argument("--include-recorded", action="store_true", help="also clear the analyst's record (rare)")
    ap.add_argument("--apply", action="store_true", help="write; without it the script only reports")
    ap.add_argument("--region", default=REGION)
    args = ap.parse_args()

    table = boto3.resource("dynamodb", region_name=args.region).Table(TABLE)
    alerts = boto3.resource("dynamodb", region_name=args.region).Table(ALERTS_TABLE)
    rows = scan_cases(table)
    sel = rows
    if args.alerts:
        want = set(args.alerts)
        sel = [r for r in sel if r["alert_id"] in want]
    if args.dates:
        sel = [r for r in sel if r.get("date") in set(args.dates)]
    if args.from_date:
        sel = [r for r in sel if (r.get("date") or "") >= args.from_date]
    if args.to_date:
        sel = [r for r in sel if (r.get("date") or "") <= args.to_date]
    with_proposal = [
        r for r in sel if r.get("proposed_disposition") or (args.include_recorded and r.get("recorded_disposition"))
    ]
    recorded = [r for r in with_proposal if r.get("recorded_disposition")]
    targets = (
        with_proposal if args.include_recorded else [r for r in with_proposal if not r.get("recorded_disposition")]
    )

    by_day = Counter(r.get("date") for r in targets)
    print(f"{len(rows)} case rows in {TABLE}; {len(sel)} in the selection; {len(with_proposal)} carry a proposal")
    print(f"{len(recorded)} of those are recorded by an analyst: {'INCLUDED' if args.include_recorded else 'kept'}")
    for d, n in sorted(by_day.items()):
        print(f"  {d}: {n} to clear")
    print(f"{len(targets)} case rows would be reset" + ("" if args.apply else " (dry run; add --apply)"))
    if not args.apply or not targets:
        return 0

    fields = PROPOSAL_FIELDS + (RECORD_FIELDS if args.include_recorded else ())
    done = 0
    for r in targets:  # one UpdateItem each; a few hundred rows, no need for batching
        table.update_item(
            Key={"alert_id": r["alert_id"]},
            UpdateExpression="REMOVE " + ", ".join(f"#f{i}" for i in range(len(fields))) + " SET #st = :open",
            ExpressionAttributeNames={**{f"#f{i}": f for i, f in enumerate(fields)}, "#st": "status"},
            ExpressionAttributeValues={":open": "OPEN"},
        )
        if args.include_recorded and r.get("recorded_disposition"):
            # the human path also wrote the decision's status on the alert; an OPEN case on a CLOSED alert would
            # make the agent's guard stop at get_alert
            alerts.update_item(
                Key={"alert_id": r["alert_id"]},
                UpdateExpression="SET #st = :open",
                ExpressionAttributeNames={"#st": "status"},
                ExpressionAttributeValues={":open": "OPEN"},
            )
        done += 1
    print(f"reset {done} case rows")
    if args.include_recorded and recorded:
        print("Memory namespaces that now hold records of cleared dispositions (delete by hand if wanted):")
        for r in recorded:
            print(f"  /traders/{r['trader_id']}/notes/   (alert {r['alert_id']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
