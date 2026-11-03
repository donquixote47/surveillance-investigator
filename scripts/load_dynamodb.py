#!/usr/bin/env python
"""Load a synthetic dataset (data/synthetic/<seed>/*.parquet) into the SurvFirm DynamoDB tables.

    uv run scripts/load_dynamodb.py data/synthetic/seed7                 # everything (about 1.96M items)
    uv run scripts/load_dynamodb.py data/synthetic/seed7 --tables alerts traders --dry-run
    uv run scripts/load_dynamodb.py data/synthetic/seed7 --dates 2026-10-05 2026-10-06

Table names come from the SurvFirm stack outputs (read with CloudFormation), or from the *_TABLE environment
variables if they are set. The `labels/` folder is never loaded: the agent must not be able to read answers.

Writes go through `batch_writer` (25 items a request, automatic retry of unprocessed items) in a thread pool.
Items are shuffled first: the `by_date` index has `date` as its partition key, so writing one day at a time puts
every in-flight write on one index partition (1,000 WCU/s) and the whole load crawls at about 600 items/s.
Shuffled, the writes spread over the 20 day partitions and the table's 4,000 WCU/s on-demand ceiling applies.
"""

from __future__ import annotations

import argparse
import os
import random
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import boto3
import pandas as pd
from botocore.config import Config

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tools.ddb_items import TABLE_ENV, items_for

REGION = "eu-west-2"
STACK = "SurvFirm"


def table_names(region: str) -> dict[str, str]:
    """dataset stem -> table name. Environment first, then the stack's outputs."""
    names = {}
    missing = [k for k, env in TABLE_ENV.items() if not os.environ.get(env)]
    if missing:
        cfn = boto3.client("cloudformation", region_name=region)
        stack = cfn.describe_stacks(StackName=STACK)["Stacks"][0]
        # CloudFormation output keys are alphanumeric: CDK drops the underscores from the CfnOutput ids
        outputs = {o["OutputKey"].replace("_", ""): o["OutputValue"] for o in stack.get("Outputs", [])}
        for k, env in TABLE_ENV.items():
            names[k] = os.environ.get(env) or outputs[env.replace("_", "")]
    else:
        names = {k: os.environ[env] for k, env in TABLE_ENV.items()}
    return names


_local = threading.local()


def _table(table_name: str, region: str):
    """One boto3 session and resource per thread: the default session is not safe for concurrent client creation.
    Adaptive retries keep throttled batches inside botocore instead of surfacing them as exceptions."""
    if not hasattr(_local, "ddb"):
        cfg = Config(retries={"mode": "adaptive", "max_attempts": 12}, max_pool_connections=4)
        _local.ddb = boto3.session.Session().resource("dynamodb", region_name=region, config=cfg)
    return _local.ddb.Table(table_name)


def write_chunk(table_name: str, items: list[dict], region: str) -> int:
    tbl = _table(table_name, region)
    with tbl.batch_writer() as bw:
        for it in items:
            bw.put_item(Item=it)
    return len(items)


def chunks(seq: list, n: int):
    for i in range(0, len(seq), n):
        yield seq[i : i + n]


def load_table(stem: str, df: pd.DataFrame, table_name: str, region: str, threads: int, dry_run: bool) -> int:
    t0 = time.time()
    items = list(items_for(stem, df))
    random.Random(0).shuffle(items)  # spread writes over partitions; see the module docstring
    if dry_run:
        print(f"  {stem:17s} -> {table_name:24s} {len(items):>9,d} items (dry run)")
        return len(items)
    done = 0
    with ThreadPoolExecutor(max_workers=threads) as ex:
        futures = [ex.submit(write_chunk, table_name, c, region) for c in chunks(items, 2_000)]
        for f in as_completed(futures):
            done += f.result()
            if done % 50_000 < 2_000 or done == len(items):
                rate = done / max(time.time() - t0, 1e-6)
                print(f"  {stem:17s} {done:>9,d}/{len(items):,d}  {rate:,.0f} items/s", flush=True)
    print(f"  {stem:17s} -> {table_name:24s} {len(items):>9,d} items in {time.time() - t0:,.0f}s")
    return len(items)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dataset", type=Path, help="data/synthetic/<seed> directory")
    ap.add_argument("--tables", nargs="*", default=list(TABLE_ENV), choices=list(TABLE_ENV))
    ap.add_argument("--dates", nargs="*", help="only these YYYY-MM-DD sessions (tables with a date column)")
    ap.add_argument("--threads", type=int, default=8)
    ap.add_argument("--region", default=REGION)
    ap.add_argument("--dry-run", action="store_true", help="build items and count them, write nothing")
    args = ap.parse_args()

    if (args.dataset / "labels").exists():
        print("note: labels/ is present and will NOT be loaded (ground truth stays local)")
    names = table_names(args.region)
    total = 0
    for stem in args.tables:
        path = args.dataset / f"{stem}.parquet"
        if not path.exists():
            print(f"  {stem:17s} skipped: {path} not found")
            continue
        df = pd.read_parquet(path)
        if args.dates and "date" in df.columns:
            df = df[df["date"].isin(args.dates)]
        total += load_table(stem, df, names[stem], args.region, args.threads, args.dry_run)
    print(f"total {total:,d} items{' (dry run)' if args.dry_run else ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
