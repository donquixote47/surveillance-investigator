"""Turn the synthetic dataset's parquet rows into DynamoDB items with the keys `data_access.py` queries by.

Pure functions, no AWS calls: `scripts/load_dynamodb.py` feeds the results to batch writers and the tests feed
them to moto. Keeping key construction in one place is what makes "the Lambda reads what the loader wrote"
testable without an account.

Key design (design doc section 3):
  order_events     pk = "<trader_id>#<date>", sk = "<ts:019d>#<seq:06d>", attribute date for GSI by_date
  trades           pk = date, sk = "<ts:019d>#<trade_id>"
  traders          pk = trader_id
  market_events    pk = date, sk = "<ts:019d>#<type>"
  instrument_stats pk = instrument, sk = date
  alerts           pk = alert_id, attribute trigger_sk = "<trigger_ts:019d>#<alert_id>" for GSI by_date
  cases_history    pk = trader_id, sk = "<date>#<alert_id>"

`seq` is the row's position within its day after a stable sort by ts, so two events with the same nanosecond
keep the order the simulator emitted them in, both in the trader partition and in the by_date index.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pandas as pd

from tools.data_access import sk_ts, to_ddb

TABLE_ENV = {
    "order_events": "ORDER_EVENTS_TABLE",
    "trades": "TRADES_TABLE",
    "traders": "TRADERS_TABLE",
    "market_events": "MARKET_EVENTS_TABLE",
    "instrument_stats": "INSTRUMENT_STATS_TABLE",
    "alerts": "ALERTS_TABLE",
    "cases_history": "CASES_HISTORY_TABLE",
}
"""dataset file stem -> environment variable the Lambdas read the table name from."""

KEY_SCHEMA: dict[str, tuple[str, str | None]] = {
    "order_events": ("pk", "sk"),
    "trades": ("date", "sk"),
    "traders": ("trader_id", None),
    "market_events": ("date", "sk"),
    "instrument_stats": ("instrument", "date"),
    "alerts": ("alert_id", None),
    "cases_history": ("trader_id", "sk"),
    "cases": ("alert_id", None),
}
"""table -> (partition key, sort key). Mirrors infra/surv_firm/stack.py; the tests assert they agree."""


def _clean(row: dict[str, Any]) -> dict[str, Any]:
    """Drop NaN/None (DynamoDB has no NaN and empty attributes waste bytes), convert floats to Decimal."""
    out = {}
    for k, v in row.items():
        if v is None:
            continue
        if isinstance(v, float) and v != v:
            continue
        if hasattr(v, "item") and not isinstance(v, str | bytes):  # numpy scalar -> python
            v = v.item()
        if isinstance(v, bool):
            out[k] = v
            continue
        out[k] = to_ddb(v)
    return out


def order_event_items(df: pd.DataFrame) -> Iterator[dict]:
    df = df.sort_values(["date", "ts"], kind="stable")
    seq = df.groupby("date", sort=False).cumcount()
    for row, s in zip(df.to_dict("records"), seq.to_numpy(), strict=True):
        item = _clean(row)
        item["pk"] = f"{row['trader_id']}#{row['date']}"
        item["sk"] = sk_ts(row["ts"], int(s))
        yield item


def trade_items(df: pd.DataFrame) -> Iterator[dict]:
    for row in df.to_dict("records"):
        item = _clean(row)
        item["sk"] = sk_ts(row["ts"], row["trade_id"])
        yield item


def trader_items(df: pd.DataFrame) -> Iterator[dict]:
    for row in df.to_dict("records"):
        yield _clean(row)  # registered_mm_instruments and risk_limit_events stay JSON strings


def market_event_items(df: pd.DataFrame) -> Iterator[dict]:
    for row in df.to_dict("records"):
        item = _clean(row)
        item["sk"] = sk_ts(row["ts"], row["type"])
        yield item


def instrument_stats_items(df: pd.DataFrame) -> Iterator[dict]:
    for row in df.to_dict("records"):
        yield _clean(row)


def alert_items(df: pd.DataFrame) -> Iterator[dict]:
    for row in df.to_dict("records"):
        item = _clean(row)
        item["trigger_sk"] = sk_ts(row["trigger_ts"], row["alert_id"])
        yield item


def cases_history_items(df: pd.DataFrame) -> Iterator[dict]:
    for row in df.to_dict("records"):
        item = _clean(row)
        item["sk"] = f"{row['date']}#{row['alert_id']}"
        yield item


BUILDERS = {
    "order_events": order_event_items,
    "trades": trade_items,
    "traders": trader_items,
    "market_events": market_event_items,
    "instrument_stats": instrument_stats_items,
    "alerts": alert_items,
    "cases_history": cases_history_items,
}


def items_for(table: str, df: pd.DataFrame) -> Iterator[dict]:
    return BUILDERS[table](df)
