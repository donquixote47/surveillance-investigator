"""The Gateway tools Lambda against a moto DynamoDB loaded through `ddb_items` from the seed7 dataset.

What this proves: the loader's keys and the Lambda's queries agree, every tool answers for a real alert, the
discriminators computed through DynamoDB equal the ones computed locally for the labels, and the two write paths
(agent proposes, human records) stay separate. Skipped when the dataset is absent.
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path

import boto3
import pandas as pd
import pytest

DATASET = Path(__file__).resolve().parents[3] / "data" / "synthetic" / "seed7"
pytestmark = pytest.mark.skipif(not DATASET.exists(), reason="seed7 dataset not built")

NS = 1_000_000_000
TABLE_ENV = {
    "ORDER_EVENTS_TABLE": "surv-order-events",
    "TRADES_TABLE": "surv-trades",
    "TRADERS_TABLE": "surv-traders",
    "MARKET_EVENTS_TABLE": "surv-market-events",
    "INSTRUMENT_STATS_TABLE": "surv-instrument-stats",
    "ALERTS_TABLE": "surv-alerts",
    "CASES_HISTORY_TABLE": "surv-cases-history",
    "CASES_TABLE": "surv-cases",
}


def _create_tables(ddb):
    from tools.ddb_items import KEY_SCHEMA

    gsis = {
        "order_events": [("by_date", "date", "sk")],
        "alerts": [("by_date", "date", "trigger_sk")],
        "cases": [("by_trader", "trader_id", "proposed_at")],
    }
    for stem, (pk, sk) in KEY_SCHEMA.items():
        name = f"surv-{stem.replace('_', '-')}"
        attrs = {pk: "S"}
        key_schema = [{"AttributeName": pk, "KeyType": "HASH"}]
        if sk:
            attrs[sk] = "S"
            key_schema.append({"AttributeName": sk, "KeyType": "RANGE"})
        kwargs = {}
        if stem in gsis:
            kwargs["GlobalSecondaryIndexes"] = []
            for iname, ipk, isk in gsis[stem]:
                attrs[ipk] = "S"
                attrs[isk] = "S"
                kwargs["GlobalSecondaryIndexes"].append(
                    {
                        "IndexName": iname,
                        "KeySchema": [
                            {"AttributeName": ipk, "KeyType": "HASH"},
                            {"AttributeName": isk, "KeyType": "RANGE"},
                        ],
                        "Projection": {"ProjectionType": "ALL"},
                    }
                )
        ddb.create_table(
            TableName=name,
            KeySchema=key_schema,
            AttributeDefinitions=[{"AttributeName": a, "AttributeType": t} for a, t in attrs.items()],
            BillingMode="PAY_PER_REQUEST",
            **kwargs,
        )


def _write(ddb, table_name: str, items) -> int:
    n = 0
    with ddb.Table(table_name).batch_writer() as bw:
        for it in items:
            bw.put_item(Item=it)
            n += 1
    return n


@pytest.fixture(scope="module")
def world():
    """moto DynamoDB with one true-abuse alert's neighbourhood loaded; yields (alert row, label row)."""
    from moto import mock_aws

    os.environ.update(TABLE_ENV)
    os.environ.setdefault("AWS_DEFAULT_REGION", "eu-west-2")
    os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
    os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
    with mock_aws():
        from tools import data_access as da
        from tools.ddb_items import items_for

        da._ddb = None  # the cached resource must be created inside the mock
        ddb = boto3.resource("dynamodb", region_name="eu-west-2")
        _create_tables(ddb)

        alerts = pd.read_parquet(DATASET / "alerts.parquet")
        labels = pd.read_parquet(DATASET / "labels" / "labels.parquet")
        truth = alerts.merge(labels, on="alert_id")
        alert = truth[truth["truth"] == "TRUE_ABUSE"].iloc[0]
        w0, w1 = int(alert["window_start"]), int(alert["window_end"])

        ev = pd.read_parquet(DATASET / "order_events.parquet")
        day = ev[ev["date"] == alert["date"]]
        keep = (day["trader_id"] == alert["trader_id"]) | (
            (day["ts"] >= w0 - 21 * 60 * NS) & (day["ts"] <= w1 + 60 * NS)
        )
        _write(ddb, "surv-order-events", items_for("order_events", day[keep]))
        for stem in ("traders", "market_events", "instrument_stats", "alerts", "cases_history"):
            _write(ddb, f"surv-{stem.replace('_', '-')}", items_for(stem, pd.read_parquet(DATASET / f"{stem}.parquet")))

        disc = pd.read_parquet(DATASET / "labels" / "discriminators.parquet")
        local = disc[disc["alert_id"] == alert["alert_id"]].iloc[0].to_dict()
        yield alert.to_dict(), local
        da._ddb = None


def call(tool: str, **inputs):
    from tools.lambda_handlers import gateway_tools

    return gateway_tools.handler({"__tool__": tool, **inputs}, context=None)


def test_unknown_tool_and_missing_input(world):
    assert "unknown tool" in call("nope")["error"]
    assert "missing required" in call("get_alert")["error"]


def test_get_alert(world):
    alert, _ = world
    out = call("get_alert", alert_id=alert["alert_id"])
    assert out["alert_id"] == alert["alert_id"]
    assert out["trader_id"] == alert["trader_id"]
    assert out["window_seconds"] == pytest.approx((alert["window_end"] - alert["window_start"]) / NS)
    assert out["window_start_time"].count(":") == 2
    assert "not found" in call("get_alert", alert_id="A-000000-0000")["error"]


def test_get_order_events_pagination(world):
    alert, _ = world
    first = call("get_order_events", alert_id=alert["alert_id"], pad_seconds=5)
    assert first["event_count"] >= 1
    assert all(e["event"] for e in first["events"])
    seen = first["event_count"]
    token = first.get("next_token")
    while token:
        page = call("get_order_events", alert_id=alert["alert_id"], pad_seconds=5, next_token=token)
        seen += page["event_count"]
        token = page.get("next_token")
    assert seen == first["total_in_range"]
    ts = [e["ts"] for e in first["events"]]
    assert ts == sorted(ts)


def test_reconstruct_book(world):
    alert, _ = world
    out = call("reconstruct_book", alert_id=alert["alert_id"], levels=5)
    assert out["bids"] and out["asks"], "a lit book twenty minutes into a session has both sides"
    assert out["bids"][0]["price_ticks"] < out["asks"][0]["price_ticks"]
    assert out["spread_ticks"] >= 1
    assert all(b["total_qty"] >= b["trader_qty"] for b in out["bids"] + out["asks"])
    assert out["bbo_path"], "the BBO path through the alert window must not be empty"


def test_compute_discriminators_matches_local_labels(world):
    """The Lambda reads DynamoDB and sees only one minute of other traders' context; the label side read the
    whole parquet day. Every scalar discriminator must still agree."""
    alert, local = world
    out = call("compute_discriminators", alert_id=alert["alert_id"])
    assert "error" not in out, out
    assert out["evidence_id"] == f"DISC-{alert['alert_id']}"
    scalar_keys = [
        "dominant_side",
        "gross_submitted_dominant",
        "gross_submitted_other",
        "cancel_ratio",
        "median_cancel_latency_ms",
        "max_resting_size_vs_depth",
        "distance_from_touch_ticks",
        "distinct_price_levels",
        "same_side_fill_qty",
        "opposite_side_fill_qty",
        "modify_reduction_qty",
        "cancel_symmetry",
        "price_move_ticks",
        "post_cancel_move_ticks",
        "reversion_ticks",
        "round_trip_ticks",
        "repetitions_in_session",
        "market_wide_cancels_1s_before_first_cancel",
    ]
    for k in scalar_keys:
        a, b = out[k], local[k]
        if isinstance(b, float) and math.isnan(b):
            assert a is None, (k, a)
        elif isinstance(b, float):
            assert a == pytest.approx(b, rel=1e-9, abs=1e-9), (k, a, b)
        else:
            assert a == b, (k, a, b)
    assert out["otr"] == (None if local["otr"] == float("inf") else pytest.approx(local["otr"]))
    assert sorted(out["large_order_ids"]) == sorted(json.loads(local["large_order_ids"]))
    assert len(out["opposite_side_fills"]) == len(json.loads(local["opposite_side_fills"]))
    assert all("time" in f for f in out["opposite_side_fills"])


def test_profile_history_market_stats_procedures(world):
    alert, _ = world
    prof = call("get_trader_profile", trader_id=alert["trader_id"], alert_id=alert["alert_id"])
    assert prof["trader_id"] == alert["trader_id"]
    assert isinstance(prof["registered_mm_instruments"], list)
    assert prof["typical_order_size"] > 0
    assert "not found" in call("get_trader_profile", trader_id="T-NOBODY")["error"]

    hist = call("get_trader_alert_history", trader_id=alert["trader_id"], before_date=alert["date"], lookback_days=90)
    assert hist["count"] == len(hist["alerts"])

    mkt = call(
        "get_market_events",
        instrument=alert["instrument"],
        window_start=alert["window_start"],
        window_end=alert["window_end"],
        pad_seconds=3600,
    )
    assert isinstance(mkt["events"], list)
    for e in mkt["events"]:
        assert e["instrument"] in ("*", alert["instrument"])

    stats = call("get_instrument_stats", instrument=alert["instrument"], date=alert["date"])
    assert stats["avg_depth_top5"] > 0 and stats["adv"] > 0

    proc = call("get_procedures", topic="closure_standard")
    assert "closure" in proc["text"].lower() or "close" in proc["text"].lower()


def test_propose_then_human_records(world):
    alert, _ = world
    from tools import data_access as da
    from tools.lambda_handlers import human_path

    report = {
        "summary": "test",
        "evidence": [{"id": "E1", "source": "compute_discriminators", "fact": "x"}],
        "legitimate_explanations_considered": [{"explanation": "hedge", "verdict": "ruled_out"}],
    }
    bad = call("propose_disposition", alert_id=alert["alert_id"], disposition="CLOSE", confidence=0.5, report=report)
    assert "disposition must be one of" in bad["error"]
    bad = call("propose_disposition", alert_id=alert["alert_id"], disposition="ESCALATE", confidence=1.5, report=report)
    assert "between 0 and 1" in bad["error"]

    # STOR draft before any proposal
    assert "call propose_disposition first" in call("draft_stor_narrative", alert_id=alert["alert_id"])["error"]

    ok = call("propose_disposition", alert_id=alert["alert_id"], disposition="ESCALATE", confidence=0.8, report=report)
    assert ok["status"].startswith("PROPOSED")
    case = da.get_case(alert["alert_id"])
    assert case["proposed_disposition"] == "ESCALATE" and case["proposal_count"] == 1
    assert "recorded_disposition" not in case, "the agent's path must never set a recorded disposition"

    # STOR draft needs a DRAFT_STOR proposal
    assert "needs a DRAFT_STOR proposal" in call("draft_stor_narrative", alert_id=alert["alert_id"])["error"]
    call("propose_disposition", alert_id=alert["alert_id"], disposition="DRAFT_STOR", confidence=0.9, report=report)
    stor = call("draft_stor_narrative", alert_id=alert["alert_id"])
    assert stor["stor_fields"]["instrument"] == alert["instrument"]
    assert stor["status"].startswith("DRAFT: not filed")
    assert da.get_case(alert["alert_id"])["proposal_count"] == 2

    def http(route: str, groups: list[str], body: dict | None = None, user: str = "tester") -> tuple[int, dict]:
        event = {
            "routeKey": route,
            "pathParameters": {"alert_id": alert["alert_id"]},
            "queryStringParameters": {"date": alert["date"]},
            "body": json.dumps(body) if body is not None else None,
            "requestContext": {"authorizer": {"jwt": {"claims": {"cognito:username": user, "cognito:groups": groups}}}},
        }
        r = human_path.handler(event, context=None)
        return r["statusCode"], json.loads(r["body"])

    status, body = http("GET /cases/{alert_id}", ["L1"])
    assert status == 200 and body["case"]["proposed_disposition"] == "DRAFT_STOR"
    assert body["alert"]["alert_id"] == alert["alert_id"]

    status, body = http("POST /cases/{alert_id}/disposition", ["L1"], {"disposition": "DRAFT_STOR", "note": "n"})
    assert status == 403, body
    status, body = http("POST /cases/{alert_id}/disposition", ["L2"], {"disposition": "DRAFT_STOR"})
    assert status == 400 and "note" in body["error"]
    status, body = http(
        "POST /cases/{alert_id}/disposition", ["L1"], {"disposition": "ESCALATE", "note": "looks real"}, "l1.analyst"
    )
    assert status == 200, body
    case = da.get_case(alert["alert_id"])
    assert case["recorded_disposition"] == "ESCALATE" and case["recorded_by"] == "l1.analyst"
    assert case["override"] is True, "recorded != proposed must be flagged as an override"

    status, body = http("POST /cases/{alert_id}/feedback", ["L1"], {"note": "good evidence list"})
    assert status == 200, body
    assert len(da.get_case(alert["alert_id"])["feedback"]) == 1

    status, body = http("GET /alerts", ["L1"])
    assert status == 200
    mine = [a for a in body["alerts"] if a["alert_id"] == alert["alert_id"]]
    assert mine and mine[0]["case"]["recorded_disposition"] == "ESCALATE"
    assert mine[0]["status"] == "ESCALATED"
