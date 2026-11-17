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
    # The Lambda code reads AWS_REGION; the tables below are created in eu-west-2. A shell with another region
    # exported (AWS_REGION=eu-west-1 failed six tests here on 2026-11-16) must not decide where the code looks.
    saved = {k: os.environ.get(k) for k in ("AWS_REGION", "AWS_DEFAULT_REGION")}
    os.environ["AWS_REGION"] = os.environ["AWS_DEFAULT_REGION"] = "eu-west-2"
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
    for k, v in saved.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v


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

    # the per-order block comes through the Lambda with the times a report can quote, and every key it returns is
    # declared on the Gateway target's output schema (an undeclared key would be an undocumented contract)
    from tools.schema import TOOLS

    declared = next(t for t in TOOLS if t["name"] == "compute_discriminators")["outputSchema"]["properties"]
    assert set(out) <= set(declared), sorted(set(out) - set(declared))
    assert [o["order_id"] for o in out["large_orders"]] == out["large_order_ids"] and out["large_orders_omitted"] == 0
    entry_keys = set(declared["large_orders"]["items"]["properties"])
    for o in out["large_orders"]:
        assert set(o) <= entry_keys, sorted(set(o) - entry_keys)
        assert len(o["placed_time"]) == 12 and o["placed_time"][2] == ":"  # HH:MM:SS.mmm
        assert (o["opposite_trade_ts"] is None) == ("opposite_trade_time" not in o)
    json.dumps(out, allow_nan=False)


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


def _human(alert_id: str, route: str, body: dict | None, user: str, groups):
    from tools.lambda_handlers import human_path

    event = {
        "routeKey": route,
        "pathParameters": {"alert_id": alert_id},
        "body": json.dumps(body) if body is not None else None,
        "requestContext": {
            "authorizer": {"jwt": {"claims": {"cognito:username": user, "cognito:groups": groups}}},
            "http": {"method": route.split(" ")[0]},
        },
    }
    r = human_path.handler(event, context=None)
    return r["statusCode"], json.loads(r["body"])


def test_decision_is_not_overwritten_and_l2_supersedes_with_history(world):
    """Review 2026-11-16: a recorded decision could be silently overwritten and the agent could re-propose on a
    decided case. Now: a second record is refused (409); Level 2 may supersede with a note and the earlier decision
    stays in decision_history; a new proposal on a decided case is refused by the tools Lambda."""
    from tools import data_access as da

    alert_id = "A-261005-0005"
    report = {
        "summary": "s" * 20,
        "evidence": [{"id": "E1", "source": "compute_discriminators", "fact": "x 1.0"}],
        "legitimate_explanations_considered": [{"explanation": "market making", "verdict": "supported"}],
    }
    r = call(
        "propose_disposition",
        alert_id=alert_id,
        disposition="CLOSE_FP",
        confidence=0.8,
        report=report,
        provenance={"session_id": "sess-1", "analyst": "l1.analyst", "model_id": "m", "secret": "dropped"},
    )
    assert "error" not in r
    prov = json.loads(da.get_case(alert_id)["proposal_provenance"])
    assert prov == {"session_id": "sess-1", "analyst": "l1.analyst", "model_id": "m"}  # unknown keys dropped

    code, body = _human(
        alert_id,
        "POST /cases/{alert_id}/disposition",
        {"disposition": "ESCALATE", "note": "L2 view"},
        "l2.reviewer",
        ["L2"],
    )
    assert code == 200 and body["recorded_disposition"] == "ESCALATE" and body["override"] is True
    # L1 tries to record over it: refused, nothing changes
    code, body = _human(
        alert_id,
        "POST /cases/{alert_id}/disposition",
        {"disposition": "CLOSE_FP", "note": "fine"},
        "l1.analyst",
        ["L1"],
    )
    assert code == 409 and "not overwritten" in body["error"]
    assert da.get_case(alert_id)["recorded_disposition"] == "ESCALATE"
    # L1 with supersede: still refused (Level 2 only)
    code, body = _human(
        alert_id,
        "POST /cases/{alert_id}/disposition",
        {"disposition": "CLOSE_FP", "note": "fine", "supersede": True},
        "l1.analyst",
        ["L1"],
    )
    assert code == 403
    # L2 supersedes with a reason: accepted, the earlier decision kept
    code, body = _human(
        alert_id,
        "POST /cases/{alert_id}/disposition",
        {"disposition": "CLOSE_FP", "note": "on review, MM quoting", "supersede": True},
        "l2.reviewer",
        ["L2"],
    )
    assert code == 200
    case = da.get_case(alert_id)
    assert case["recorded_disposition"] == "CLOSE_FP"
    hist = case["decision_history"]
    assert (
        len(hist) == 1 and hist[0]["recorded_disposition"] == "ESCALATE" and hist[0]["superseded_by"] == "l2.reviewer"
    )
    # the agent cannot propose on a decided case
    r = call("propose_disposition", alert_id=alert_id, disposition="ESCALATE", confidence=0.7, report=report)
    assert "error" in r and "decided" in r["error"] and r["recorded_disposition"] == "CLOSE_FP"
    assert da.get_case(alert_id)["proposed_disposition"] == "CLOSE_FP"  # the earlier proposal stands


def test_group_claim_shapes():
    """The HTTP API JWT authorizer stringifies the groups array; every shape seen or plausible must parse."""
    from tools.lambda_handlers.human_path import _claims

    def groups(raw):
        return _claims({"requestContext": {"authorizer": {"jwt": {"claims": {"cognito:groups": raw}}}}})[1]

    assert groups(["L1", "L2"]) == ["L1", "L2"]
    assert groups("[L1 L2]") == ["L1", "L2"]
    assert groups("[L1]") == ["L1"]
    assert groups("L1,L2") == ["L1", "L2"]
    assert groups('["L2"]') == ["L2"]
    assert groups("") == []


def test_reproposal_before_a_decision_keeps_the_earlier_proposals_line(world):
    """A second investigation before anyone decided replaces the report; the earlier proposal's line (what, when,
    which session) stays on the case, and the provenance on the case is the current proposal's, never the last one's."""
    from tools import data_access as da

    alert_id = "A-261005-0004"
    report = {
        "summary": "s" * 20,
        "evidence": [{"id": "E1", "source": "compute_discriminators", "fact": "x 1.0"}],
        "legitimate_explanations_considered": [{"explanation": "market making", "verdict": "undetermined"}],
    }
    first = call(
        "propose_disposition",
        alert_id=alert_id,
        disposition="ESCALATE",
        confidence=0.65,
        report=report,
        provenance={"session_id": "sess-A"},
    )
    assert "error" not in first
    second = call("propose_disposition", alert_id=alert_id, disposition="CLOSE_FP", confidence=0.8, report=report)
    assert "error" not in second
    case = da.get_case(alert_id)
    assert case["proposed_disposition"] == "CLOSE_FP" and case["proposal_count"] == 2
    assert "proposal_provenance" not in case  # the second call carried none; the first one's must not linger
    (earlier,) = case["proposal_history"]
    assert earlier["disposition"] == "ESCALATE" and earlier["session_id"] == "sess-A"
    assert earlier["proposed_at"] == first["proposed_at"]


def test_a_lock_without_a_read_still_refuses_the_write(world, monkeypatch):
    """The read catches a decided case; the condition on the write catches a decision recorded between that read
    and the write. Simulated by hiding the decision from the read."""
    from tools import data_access as da
    from tools.lambda_handlers import gateway_tools as gt

    alert_id = "A-261005-0006"
    report = {
        "summary": "s" * 20,
        "evidence": [{"id": "E1", "source": "get_alert", "fact": "x 1.0"}],
        "legitimate_explanations_considered": [{"explanation": "market making", "verdict": "undetermined"}],
    }
    code, _ = _human(
        alert_id, "POST /cases/{alert_id}/disposition", {"disposition": "ESCALATE", "note": "n"}, "l1.analyst", "[L1]"
    )
    assert code == 200 and da.get_case(alert_id)["decision_lock"] is True
    real = da.get_case
    reads = {"n": 0}

    def first_read_sees_no_decision(a):
        reads["n"] += 1
        return {} if reads["n"] == 1 else real(a)

    monkeypatch.setattr(gt.da, "get_case", first_read_sees_no_decision)
    r = call("propose_disposition", alert_id=alert_id, disposition="CLOSE_FP", confidence=0.9, report=report)
    assert "error" in r and "decided" in r["error"]
    monkeypatch.undo()
    assert "proposed_disposition" not in (da.get_case(alert_id) or {})


def _named_attributes(kwargs: dict) -> set[str]:
    """The top-level attribute names an UpdateItem request touches: set, removed, or tested in its condition."""
    import re

    names = kwargs.get("ExpressionAttributeNames") or {}
    text = " ".join(str(kwargs.get(k) or "") for k in ("UpdateExpression", "ConditionExpression"))
    out = set(kwargs["Key"])
    for tok in re.findall(r"[#:]?[A-Za-z_][A-Za-z0-9_]*", text):
        if tok.startswith(":") or tok in ("SET", "REMOVE", "ADD", "DELETE", "AND", "OR", "NOT"):
            continue
        if tok in ("if_not_exists", "list_append", "attribute_not_exists", "attribute_exists"):
            continue
        out.add(names[tok] if tok.startswith("#") else tok)
    return out


def test_the_agents_updates_name_only_the_attributes_its_role_allows(world, monkeypatch):
    """moto does not evaluate IAM, so this is the check that the tools Lambda's `dynamodb:Attributes` allow-list
    (infra/surv_firm/stack.py, from tools/case_fields.py) and the Lambda's own update expressions agree: every
    attribute the agent's two writes name is allowed, and none is the human path's. A new field written by the
    agent's path without being added to the list fails here instead of failing as AccessDenied after a deploy."""
    from tools import data_access as da
    from tools.case_fields import AGENT_WRITABLE, HUMAN_ONLY
    from tools.lambda_handlers import gateway_tools as gt

    assert not set(AGENT_WRITABLE) & set(HUMAN_ONLY)
    captured: list[dict] = []
    real_table = da.table

    class Spy:
        def __init__(self, tbl):
            self._tbl = tbl

        def update_item(self, **kwargs):
            captured.append(kwargs)
            return self._tbl.update_item(**kwargs)

        def __getattr__(self, name):
            return getattr(self._tbl, name)

    monkeypatch.setattr(gt.da, "table", lambda env: Spy(real_table(env)) if env == "CASES_TABLE" else real_table(env))
    alert_id = "A-261005-0007"
    report = {
        "summary": "s" * 20,
        "evidence": [{"id": "E1", "source": "get_alert", "fact": "x 1.0"}],
        "indicators_matched": ["high order-to-trade ratio (Annex II 4(f))"],
        "legitimate_explanations_considered": [{"explanation": "market making", "verdict": "undetermined"}],
    }
    for prov in ({"session_id": "s1"}, None, {"session_id": "s3"}):  # with, without (REMOVE) and with history
        r = call(
            "propose_disposition",
            alert_id=alert_id,
            disposition="DRAFT_STOR",
            confidence=0.8,
            report=report,
            **({"provenance": prov} if prov else {}),
        )
        assert "error" not in r
    assert "error" not in call("draft_stor_narrative", alert_id=alert_id)
    assert len(captured) == 4
    named = set().union(*(_named_attributes(k) for k in captured))
    assert named <= set(AGENT_WRITABLE), f"not in the role's allow-list: {sorted(named - set(AGENT_WRITABLE))}"
    assert not named & set(HUMAN_ONLY)
    assert {"proposal_history", "proposal_provenance", "decision_lock", "stor_draft"} <= named  # the parser sees them


def test_history_is_one_row_per_alert_and_never_the_alert_itself(world):
    """Review 2026-11-16: a recorded decision was listed twice (history table and case), and an investigation of
    alert X was shown X's own recorded decision (three alerts in every seed7 run, disclosed in results.md)."""
    alert, _ = world  # recorded ESCALATE by test_propose_then_human_records
    plain = call("get_trader_alert_history", trader_id=alert["trader_id"], before_date=alert["date"])
    mine = [r for r in plain["alerts"] if r["alert_id"] == alert["alert_id"]]
    assert len(mine) == 1 and mine[0]["recorded_disposition"] == "ESCALATE"  # once, not twice
    assert mine[0]["proposed_disposition"] == "DRAFT_STOR" and mine[0]["override"] is True  # the case row

    scoped = call("get_trader_alert_history", trader_id=alert["trader_id"], alert_id=alert["alert_id"])
    assert all(r["alert_id"] != alert["alert_id"] for r in scoped["alerts"])
    assert scoped["excluded_current_alert"] == 1 and scoped["before_date"] == alert["date"]
    assert scoped["count"] == plain["count"] - 1

    other = call("get_trader_alert_history", trader_id="T-MM-01", alert_id=alert["alert_id"])
    assert "not T-MM-01" in other["error"]


def test_market_events_for_an_alert_equal_the_explicit_lookup(world):
    alert, _ = world
    by_alert = call("get_market_events", alert_id=alert["alert_id"])
    explicit = call(
        "get_market_events",
        instrument=alert["instrument"],
        window_start=int(alert["window_start"]),
        window_end=int(alert["window_end"]),
    )
    assert by_alert["events"] == explicit["events"]
    assert by_alert["alert_id"] == alert["alert_id"] and by_alert["window_start"] == int(alert["window_start"])
    assert "pass alert_id" in call("get_market_events", instrument="SYN.A")["error"]
    assert "not found" in call("get_market_events", alert_id="A-000000-0000")["error"]


def test_memory_hides_only_the_decision_recorded_on_the_same_alert():
    """The agent must not be shown the answer to the alert it is investigating, and must be shown everything an
    analyst has taught it: feedback on this very alert (the analyst asks for the investigation again), and decisions
    and feedback on later alerts (a correction made yesterday reaches the backlog alert worked today)."""
    from tools.memory_access import visible_to

    alert = {"alert_id": "A-261009-0003", "date": "2026-10-09"}
    own = {"alert_id": "A-261009-0003", "date": "2026-10-09"}
    records = [
        {"text": "own recorded decision", "metadata": {**own, "kind": "disposition"}},
        {"text": "analyst feedback on this alert", "metadata": {**own, "kind": "feedback"}},
        {
            "text": "later decision, same desk",
            "metadata": {"alert_id": "A-261016-0003", "date": "2026-10-16", "kind": "disposition"},
        },
        {
            "text": "later feedback, same desk",
            "metadata": {"alert_id": "A-261016-0003", "date": "2026-10-16", "kind": "feedback"},
        },
        {
            "text": "earlier decision",
            "metadata": {"alert_id": "H-T-MM-01-02", "date": "2026-09-13", "kind": "disposition"},
        },
        {"text": "extracted fact, no metadata", "metadata": {}},
    ]
    kept, dropped = visible_to(records, alert)
    assert dropped == 1 and [r["text"] for r in kept] == [r["text"] for r in records[1:]]


def test_missing_depth_is_an_error_and_other_instruments_are_left_out(world, monkeypatch):
    from tools.lambda_handlers import gateway_tools as gt

    alert, _ = world
    rows = [{"instrument": "SYN.A", "n": 1}, {"instrument": "SYN.B", "n": 2}, {"n": 3}]
    assert gt._on_instrument(rows, {"instrument": "SYN.A"}) == [{"instrument": "SYN.A", "n": 1}]
    monkeypatch.setattr(gt.da, "instrument_stats", lambda instrument, date: None)
    out = call("compute_discriminators", alert_id=alert["alert_id"])
    assert "avg_depth_top5" in out["error"] and "max_resting_size_vs_depth" not in out


# ----------------------------------------------------------------------------------------------
# an evidence lookup answers with the alert's id, and only when it answered for that alert (2026-11-17)
# ----------------------------------------------------------------------------------------------


def test_every_evidence_tool_returns_the_alert_id_when_it_answered_for_the_alert(world):
    """Policies 03a, 03b and 04 allow a proposal only after each of these tools RETURNED the alert's id. So every
    one of them must return it for a lookup that named the alert, and the profile and history tools must return
    it only for the alert's own trader."""
    from tools.lambda_handlers.gateway_tools import EVIDENCE_TOOLS

    alert, _ = world
    aid, tid = alert["alert_id"], alert["trader_id"]
    inputs = {
        "get_alert": {"alert_id": aid},
        "get_order_events": {"alert_id": aid},
        "compute_discriminators": {"alert_id": aid},
        "get_trader_profile": {"alert_id": aid, "trader_id": tid},
        "get_market_events": {"alert_id": aid},
        "get_trader_alert_history": {"alert_id": aid, "trader_id": tid},
    }
    assert set(inputs) == set(EVIDENCE_TOOLS)
    for tool, args in inputs.items():
        out = call(tool, **args)
        assert "error" not in out and out["alert_id"] == aid, tool

    # without the alert the profile, the market events and the history still answer, and name no alert:
    # a lookup that was not made for the alert is not evidence for it
    assert "alert_id" not in call("get_trader_profile", trader_id=tid)
    assert "alert_id" not in call("get_trader_alert_history", trader_id=tid)
    explicit = call(
        "get_market_events",
        instrument=alert["instrument"],
        window_start=int(alert["window_start"]),
        window_end=int(alert["window_end"]),
    )
    assert "error" not in explicit and "alert_id" not in explicit


def test_a_failed_evidence_lookup_never_names_the_alert(world, monkeypatch):
    """The gap this closes: a tool that RETURNS {"error": ...} has returned successfully as far as the Gateway
    knows, so the response is recorded and used to satisfy "look before you propose". With the policies matching
    on output.alert_id, the guarantee is that an answer which is an error carries no alert id."""
    from tools.lambda_handlers import gateway_tools

    alert, _ = world
    aid, tid = alert["alert_id"], alert["trader_id"]
    other = "T-MM-01" if tid != "T-MM-01" else "T-MM-02"
    failures = [
        ("get_alert", {"alert_id": "A-000000-0000"}),
        ("get_order_events", {"alert_id": "A-000000-0000"}),
        ("compute_discriminators", {"alert_id": "A-000000-0000"}),
        ("get_trader_profile", {"alert_id": aid, "trader_id": "T-NOBODY"}),  # the trader does not exist
        ("get_trader_profile", {"alert_id": aid, "trader_id": other}),  # a real trader, not this alert's
        ("get_trader_profile", {"alert_id": "A-000000-0000", "trader_id": tid}),  # the alert does not exist
        ("get_market_events", {"alert_id": "A-000000-0000"}),
        ("get_market_events", {}),  # neither the alert nor a window
        ("get_trader_alert_history", {"alert_id": aid, "trader_id": other}),
        ("get_trader_alert_history", {"alert_id": "A-000000-0000", "trader_id": tid}),
    ]
    for tool, args in failures:
        out = call(tool, **args)
        assert "error" in out and "alert_id" not in out, (tool, args, out)

    # and the rule holds for a tool that builds its answer before it fails: the dispatcher strips the id
    monkeypatch.setitem(gateway_tools.TOOL_IMPL, "get_alert", lambda ev: {"alert_id": ev["alert_id"], "error": "boom"})
    out = call("get_alert", alert_id=aid)
    assert out == {"error": "boom"}

    # other tools keep what they return: the refusal on a decided case names the alert it refused
    monkeypatch.setitem(
        gateway_tools.TOOL_IMPL, "propose_disposition", lambda ev: {"alert_id": ev["alert_id"], "error": "decided"}
    )
    out = call("propose_disposition", alert_id=aid, disposition="ESCALATE", confidence=0.5, report={})
    assert out["alert_id"] == aid
