"""The analyst's path. An HTTP API with a Cognito JWT authoriser in front; the agent has no route here.

  GET  /alerts?date=YYYY-MM-DD           queue for a day (alerts joined with their case state)
  GET  /cases/{alert_id}                  the agent's proposal and report, plus any recorded decision
  POST /cases/{alert_id}/disposition      body {disposition, note}; L1 may record CLOSE_FP or ESCALATE, only L2
                                          may record DRAFT_STOR; sets override = (recorded != proposed)
  POST /cases/{alert_id}/feedback         body {note}; appended to the case; later also written to Memory

Group membership comes from the JWT's cognito:groups claim, which API Gateway has already verified.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime

from boto3.dynamodb.conditions import Key

from tools import data_access as da
from tools import memory_access as mem

DISPOSITIONS = ("CLOSE_FP", "ESCALATE", "DRAFT_STOR")
L1_ALLOWED = ("CLOSE_FP", "ESCALATE")


def _resp(status: int, body: dict) -> dict:
    return {
        "statusCode": status,
        "headers": {"content-type": "application/json"},
        "body": json.dumps(da.from_ddb(body), default=str),
    }


def _claims(event: dict) -> tuple[str, list[str]]:
    jwt = (((event.get("requestContext") or {}).get("authorizer") or {}).get("jwt") or {}).get("claims") or {}
    user = jwt.get("cognito:username") or jwt.get("username") or jwt.get("sub") or "unknown"
    groups = jwt.get("cognito:groups") or []
    if isinstance(groups, str):
        groups = [g.strip() for g in groups.strip("[]").split(",") if g.strip()]
    return user, list(groups)


def handler(event: dict, context) -> dict:
    route = event.get("routeKey", "")
    params = event.get("pathParameters") or {}
    qs = event.get("queryStringParameters") or {}
    body = {}
    if event.get("body"):
        try:
            body = json.loads(event["body"])
        except json.JSONDecodeError:
            return _resp(400, {"error": "body must be JSON"})
    user, groups = _claims(event)

    if route == "GET /alerts":
        return list_alerts(qs.get("date"))
    if route == "GET /cases/{alert_id}":
        return get_case(params["alert_id"])
    if route == "POST /cases/{alert_id}/disposition":
        return record_disposition(params["alert_id"], body, user, groups)
    if route == "POST /cases/{alert_id}/feedback":
        return send_feedback(params["alert_id"], body, user, groups)
    return _resp(404, {"error": f"no route {route}"})


def list_alerts(date: str | None) -> dict:
    if not date:
        return _resp(400, {"error": "date=YYYY-MM-DD is required"})
    alerts = da.query_all(da.table("ALERTS_TABLE"), IndexName="by_date", KeyConditionExpression=Key("date").eq(date))
    cases = {}
    for a in alerts:
        c = da.get_case(a["alert_id"])
        if c:
            cases[a["alert_id"]] = {
                k: c.get(k)
                for k in (
                    "proposed_disposition",
                    "confidence",
                    "proposed_at",
                    "recorded_disposition",
                    "recorded_by",
                    "recorded_at",
                    "override",
                    "status",
                )
            }
    out = []
    for a in alerts:
        out.append(
            {
                **{
                    k: a.get(k)
                    for k in (
                        "alert_id",
                        "date",
                        "scenario",
                        "instrument",
                        "trader_id",
                        "trigger",
                        "trigger_summary",
                        "status",
                    )
                },
                "window_start_time": da.hhmmss(a["window_start"]),
                "window_end_time": da.hhmmss(a["window_end"]),
                "case": cases.get(a["alert_id"]),
            }
        )
    return _resp(200, {"date": date, "alerts": out, "count": len(out)})


def get_case(alert_id: str) -> dict:
    alert = da.get_alert(alert_id)
    if alert is None:
        return _resp(404, {"error": f"alert {alert_id!r} not found"})
    case = da.get_case(alert_id) or {}
    if isinstance(case.get("report"), str):
        try:
            case["report"] = json.loads(case["report"])
        except json.JSONDecodeError:
            pass
    return _resp(200, {"alert": alert, "case": case})


def record_disposition(alert_id: str, body: dict, user: str, groups: list[str]) -> dict:
    disp = str(body.get("disposition", "")).upper()
    note = str(body.get("note", "")).strip()
    if disp not in DISPOSITIONS:
        return _resp(400, {"error": f"disposition must be one of {DISPOSITIONS}"})
    if not note:
        return _resp(
            400,
            {
                "error": (
                    "a note with the analyst's reasoning is required "
                    "(record-keeping, Delegated Regulation (EU) 2016/957)"
                )
            },
        )
    is_l2 = "L2" in groups
    is_l1 = "L1" in groups or is_l2
    if not is_l1:
        return _resp(403, {"error": "not an analyst (groups L1 or L2 required)"})
    if disp not in L1_ALLOWED and not is_l2:
        return _resp(403, {"error": "only Level 2 may record DRAFT_STOR"})
    alert = da.get_alert(alert_id)
    if alert is None:
        return _resp(404, {"error": f"alert {alert_id!r} not found"})
    case = da.get_case(alert_id) or {}
    proposed = case.get("proposed_disposition")
    override = bool(proposed) and proposed != disp
    now = datetime.now(UTC).isoformat(timespec="seconds")
    status = {"CLOSE_FP": "CLOSED", "ESCALATE": "ESCALATED", "DRAFT_STOR": "ESCALATED"}[disp]
    da.table("CASES_TABLE").update_item(
        Key={"alert_id": alert_id},
        UpdateExpression=(
            "SET case_id = if_not_exists(case_id, :cid), trader_id = :t, #d = :dt, scenario = :s, "
            "recorded_disposition = :rd, recorded_by = :by, "
            "recorded_at = :at, analyst_note = :n, #ov = :ov, #st = :status"
        ),
        ExpressionAttributeNames={"#d": "date", "#ov": "override", "#st": "status"},
        ExpressionAttributeValues={
            ":cid": f"C-{alert_id}",
            ":t": alert["trader_id"],
            ":dt": alert["date"],
            ":s": alert["scenario"],
            ":rd": disp,
            ":by": user,
            ":at": now,
            ":n": note,
            ":ov": override,
            ":status": status,
        },
    )
    da.table("ALERTS_TABLE").update_item(
        Key={"alert_id": alert_id},
        UpdateExpression="SET #st = :s",
        ExpressionAttributeNames={"#st": "status"},
        ExpressionAttributeValues={":s": status},
    )
    # the decision becomes part of the trader's history for future investigations
    da.table("CASES_HISTORY_TABLE").put_item(
        Item={
            "trader_id": alert["trader_id"],
            "sk": f"{alert['date']}#{alert_id}",
            "alert_id": alert_id,
            "instrument": alert["instrument"],
            "date": alert["date"],
            "scenario": alert["scenario"],
            "proposed_disposition": proposed,
            "recorded_disposition": disp,
            "recorded_by": user,
            "analyst_note": note,
            "override": override,
        }
    )
    desk = (da.get_trader(alert["trader_id"]) or {}).get("desk")
    memory_written = _to_memory(lambda: mem.record_disposition(alert, case, disp, user, note, override, desk))
    return _resp(
        200,
        {
            "alert_id": alert_id,
            "memory_written": memory_written,
            "recorded_disposition": disp,
            "proposed_disposition": proposed,
            "override": override,
            "recorded_by": user,
            "recorded_at": now,
            "status": status,
        },
    )


def _to_memory(fn) -> bool:
    """Memory is a secondary store: a failure must not lose the DynamoDB record that was just written."""
    try:
        fn()
        return True
    except Exception as exc:  # logged, not raised
        print(f"memory write failed: {type(exc).__name__}: {exc}")
        return False


def send_feedback(alert_id: str, body: dict, user: str, groups: list[str]) -> dict:
    note = str(body.get("note", "")).strip()
    if not note:
        return _resp(400, {"error": "note is required"})
    if not ({"L1", "L2"} & set(groups)):
        return _resp(403, {"error": "not an analyst (groups L1 or L2 required)"})
    alert = da.get_alert(alert_id)
    if alert is None:
        return _resp(404, {"error": f"alert {alert_id!r} not found"})
    now = datetime.now(UTC).isoformat(timespec="seconds")
    entry = {"by": user, "at": now, "note": note}
    da.table("CASES_TABLE").update_item(
        Key={"alert_id": alert_id},
        UpdateExpression=(
            "SET case_id = if_not_exists(case_id, :cid), trader_id = :t, #d = :dt, "
            "feedback = list_append(if_not_exists(feedback, :empty), :f)"
        ),
        ExpressionAttributeNames={"#d": "date"},
        ExpressionAttributeValues={
            ":cid": f"C-{alert_id}",
            ":t": alert["trader_id"],
            ":dt": alert["date"],
            ":empty": [],
            ":f": [entry],
        },
    )
    desk = (da.get_trader(alert["trader_id"]) or {}).get("desk")
    memory_written = _to_memory(lambda: mem.record_feedback(alert, user, note, desk))
    return _resp(
        200,
        {
            "alert_id": alert_id,
            "memory_written": memory_written,
            "feedback": entry,
            "memory": "written to AgentCore Memory in Phase 4" if not os.environ.get("MEMORY_ID") else "queued",
        },
    )
