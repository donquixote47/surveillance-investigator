"""The analyst's path. An HTTP API with a Cognito JWT authoriser in front; the agent has no route here.

  GET  /alerts?date=YYYY-MM-DD           queue for a day (alerts joined with their case state)
  GET  /cases/{alert_id}                  the agent's proposal and report, plus any recorded decision
  POST /cases/{alert_id}/disposition      body {disposition, note, supersede?}; L1 may record CLOSE_FP or ESCALATE,
                                          only L2 may record DRAFT_STOR; sets override = (recorded != proposed).
                                          A decision is recorded ONCE: a second record is refused (409). Only L2 may
                                          replace it, explicitly (`supersede: true`) and with a note; the earlier
                                          decision is kept on the case in `decision_history` (who, when, why).
  POST /cases/{alert_id}/feedback         body {note}; appended to the case; later also written to Memory

Group membership comes from the JWT's cognito:groups claim, which API Gateway has already verified.
"""

from __future__ import annotations

import json
import os
import re
from datetime import UTC, datetime

from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

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


def parse_groups(raw: object) -> list[str]:
    """The groups claim as a list, whatever shape it arrives in. The HTTP API's JWT authorizer hands claims to the
    Lambda as strings and does not document how it writes an array (the payload example shows string values only):
    a user in two groups has been reported as `[L1 L2]`, one group arrives as `[L1]`, and other front ends send a
    JSON array or a comma list. Splitting on commas alone read `[L1 L2]` as ONE group called "L1 L2", so a
    two-group analyst was refused as "not an analyst" (review 2026-11-16). Accept every shape."""
    if raw is None:
        return []
    if isinstance(raw, (list, tuple, set)):
        return [str(g).strip() for g in raw if str(g).strip()]
    text = str(raw).strip()
    if not text:
        return []
    if text.startswith("["):
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return [str(g).strip() for g in parsed if str(g).strip()]
        except json.JSONDecodeError:
            pass
    return [g for g in re.split(r"[\s,]+", text.strip("[]").replace('"', "").replace("'", "")) if g]


def _claims(event: dict) -> tuple[str, list[str]]:
    jwt = (((event.get("requestContext") or {}).get("authorizer") or {}).get("jwt") or {}).get("claims") or {}
    user = jwt.get("cognito:username") or jwt.get("username") or jwt.get("sub") or "unknown"
    return user, parse_groups(jwt.get("cognito:groups"))


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
    for key in ("report", "stor_draft", "proposal_provenance"):  # stored as JSON text
        if isinstance(case.get(key), str):
            try:
                case[key] = json.loads(case[key])
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

    # A decision is the firm's record: it is written once. Replacing it is a separate, explicit act (Level 2,
    # `supersede: true`, a note saying why) and the earlier decision stays on the case.
    earlier = case.get("recorded_disposition")
    supersede = body.get("supersede") is True
    if earlier and not supersede:
        return _resp(409, _already_decided(case))
    if earlier and not is_l2:
        return _resp(403, {"error": "only Level 2 may supersede a recorded decision"})

    names = {"#d": "date", "#ov": "override", "#st": "status"}
    values = {
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
        ":lock": True,
    }
    update = (
        "SET case_id = if_not_exists(case_id, :cid), trader_id = :t, #d = :dt, scenario = :s, "
        "recorded_disposition = :rd, recorded_by = :by, "
        "recorded_at = :at, analyst_note = :n, #ov = :ov, #st = :status, decision_lock = :lock"
    )
    if earlier:
        superseded = {
            "recorded_disposition": earlier,
            "recorded_by": case.get("recorded_by"),
            "recorded_at": case.get("recorded_at"),
            "analyst_note": case.get("analyst_note"),
            "override": bool(case.get("override")),
            "superseded_by": user,
            "superseded_at": now,
            "superseded_note": note,
        }
        update += ", decision_history = list_append(if_not_exists(decision_history, :empty), :h)"
        values.update({":empty": [], ":h": [superseded], ":prev_at": case.get("recorded_at")})
        # the decision being replaced must still be the one this request read (two reviewers at once)
        condition = "recorded_at = :prev_at"
    else:
        condition = "attribute_not_exists(recorded_disposition)"
    try:
        da.table("CASES_TABLE").update_item(
            Key={"alert_id": alert_id},
            UpdateExpression=update,
            ConditionExpression=condition,
            ExpressionAttributeNames=names,
            ExpressionAttributeValues=values,
        )
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") != "ConditionalCheckFailedException":
            raise
        # someone recorded between this request's read and its write: report what is on file now
        return _resp(409, _already_decided(da.get_case(alert_id) or {}))
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
            **({"supersedes": earlier} if earlier else {}),
        }
    )
    desk = (da.get_trader(alert["trader_id"]) or {}).get("desk")
    memory_written = _to_memory(
        lambda: mem.record_disposition(alert, case, disp, user, note, override, desk, supersedes=earlier)
    )
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
            "superseded": earlier,
        },
    )


def _already_decided(case: dict) -> dict:
    return {
        "error": (
            f"a decision is already recorded for this alert ({case.get('recorded_disposition')} by "
            f"{case.get('recorded_by')} at {case.get('recorded_at')}); it is not overwritten. Level 2 may supersede "
            "it explicitly (supersede: true) with a note; the earlier decision stays on the case."
        ),
        "recorded_disposition": case.get("recorded_disposition"),
        "recorded_by": case.get("recorded_by"),
        "recorded_at": case.get("recorded_at"),
    }


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
            "memory": "queued for extraction" if os.environ.get("MEMORY_ID") else "no Memory configured",
        },
    )
