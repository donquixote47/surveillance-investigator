"""DynamoDB access for the tool Lambdas. Table names come from environment variables set by the CDK stack.

Key design (see design doc section 3):
  order_events   pk = "<trader_id>#<date>", sk = "<ts:019d>#<seq:06d>"; GSI by_date: date, sk
  trades         pk = date, sk = "<ts:019d>#<trade_id>"
  traders        pk = trader_id
  market_events  pk = date, sk = "<ts:019d>#<type>"
  instrument_stats pk = instrument, sk = date
  alerts         pk = alert_id; GSI by_date: date, trigger_sk
  cases_history  pk = trader_id, sk = "<date>#<alert_id>"
  cases          pk = alert_id; GSI by_trader: trader_id, proposed_at
"""

from __future__ import annotations

import base64
import json
import os
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import boto3
from boto3.dynamodb.conditions import Key

NS_PER_S = 1_000_000_000

_ddb = None


def ddb():
    global _ddb
    if _ddb is None:
        _ddb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "eu-west-2"))
    return _ddb


def table(env_name: str):
    return ddb().Table(os.environ[env_name])


def sk_ts(ts: int, suffix: str | int = "") -> str:
    s = f"{int(ts):019d}"
    if suffix != "":
        s += f"#{suffix:06d}" if isinstance(suffix, int) else f"#{suffix}"
    return s


def hhmmss(ts: int) -> str:
    """ns since epoch -> HH:MM:SS.mmm on the venue clock (the simulator wrote naive timestamps as UTC)."""
    return datetime.fromtimestamp(int(ts) / NS_PER_S, tz=UTC).strftime("%H:%M:%S.%f")[:-3]


def date_of(ts: int) -> str:
    return datetime.fromtimestamp(int(ts) / NS_PER_S, tz=UTC).strftime("%Y-%m-%d")


def to_ddb(value: Any) -> Any:
    """Make a Python value storable: floats -> Decimal, NaN/None dropped by caller, nested handled."""
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            return None
        return Decimal(str(value))
    if isinstance(value, dict):
        return {k: to_ddb(v) for k, v in value.items() if v is not None}
    if isinstance(value, list):
        return [to_ddb(v) for v in value]
    return value


def from_ddb(value: Any) -> Any:
    """Decimal -> int or float for JSON output."""
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    if isinstance(value, dict):
        return {k: from_ddb(v) for k, v in value.items()}
    if isinstance(value, list):
        return [from_ddb(v) for v in value]
    return value


def encode_token(key: dict | None) -> str | None:
    if not key:
        return None
    return base64.urlsafe_b64encode(json.dumps(from_ddb(key)).encode()).decode()


def decode_token(token: str | None) -> dict | None:
    if not token:
        return None
    return json.loads(base64.urlsafe_b64decode(token.encode()).decode())


def query_all(tbl, **kwargs) -> list[dict]:
    """Query and follow pagination until exhausted."""
    items: list[dict] = []
    resp = tbl.query(**kwargs)
    items.extend(resp.get("Items", []))
    while "LastEvaluatedKey" in resp:
        resp = tbl.query(ExclusiveStartKey=resp["LastEvaluatedKey"], **kwargs)
        items.extend(resp.get("Items", []))
    return [from_ddb(i) for i in items]


# ----- typed accessors -----


def get_alert(alert_id: str) -> dict | None:
    item = table("ALERTS_TABLE").get_item(Key={"alert_id": alert_id}).get("Item")
    return from_ddb(item) if item else None


def trader_day_events(trader_id: str, date: str, ts_from: int | None = None, ts_to: int | None = None) -> list[dict]:
    pk = f"{trader_id}#{date}"
    cond = Key("pk").eq(pk)
    if ts_from is not None and ts_to is not None:
        cond = cond & Key("sk").between(sk_ts(ts_from), sk_ts(ts_to, "zzzzzz"))
    return query_all(table("ORDER_EVENTS_TABLE"), KeyConditionExpression=cond)


def day_events(date: str, ts_from: int, ts_to: int) -> list[dict]:
    cond = Key("date").eq(date) & Key("sk").between(sk_ts(ts_from), sk_ts(ts_to, "zzzzzz"))
    return query_all(table("ORDER_EVENTS_TABLE"), IndexName="by_date", KeyConditionExpression=cond)


def get_trader(trader_id: str) -> dict | None:
    item = table("TRADERS_TABLE").get_item(Key={"trader_id": trader_id}).get("Item")
    return from_ddb(item) if item else None


def market_events(date: str, ts_from: int, ts_to: int) -> list[dict]:
    cond = Key("date").eq(date) & Key("sk").between(sk_ts(ts_from), sk_ts(ts_to, "zzzz"))
    return query_all(table("MARKET_EVENTS_TABLE"), KeyConditionExpression=cond)


def instrument_stats(instrument: str, date: str) -> dict | None:
    item = table("INSTRUMENT_STATS_TABLE").get_item(Key={"instrument": instrument, "date": date}).get("Item")
    return from_ddb(item) if item else None


def history(trader_id: str, before_date: str, after_date: str) -> list[dict]:
    cond = Key("trader_id").eq(trader_id) & Key("sk").between(f"{after_date}#", f"{before_date}#zzzz")
    return query_all(table("CASES_HISTORY_TABLE"), KeyConditionExpression=cond, ScanIndexForward=False)


def recorded_cases_for_trader(trader_id: str) -> list[dict]:
    return query_all(
        table("CASES_TABLE"),
        IndexName="by_trader",
        KeyConditionExpression=Key("trader_id").eq(trader_id),
        ScanIndexForward=False,
    )


def get_case(alert_id: str) -> dict | None:
    item = table("CASES_TABLE").get_item(Key={"alert_id": alert_id}).get("Item")
    return from_ddb(item) if item else None
