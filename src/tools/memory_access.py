"""AgentCore Memory for the investigator (design doc section 7).

One Memory resource, id in MEMORY_ID. Namespaces:
  /traders/<trader_id>/notes/        one record per recorded disposition and per piece of analyst feedback
  /instruments/<instrument>/notes/   instrument facts (written by hand with scripts/memory_admin.py)
  /procedures/                       the firm's procedures, one record per topic

Records are written directly with BatchCreateMemoryRecords (deterministic, immediate, no extraction delay): the
human path is a system of record, so the fact it stores must be exactly what the analyst recorded. The free-text
feedback is ALSO sent as a conversational event so the SEMANTIC strategy extracts from it asynchronously (the
"does it learn" story: extracted facts land in the same per-trader namespace with a strategy id set).

Retrieval is one semantic query per namespace (RetrieveMemoryRecords); the Gateway tool `recall_memory` wraps it.
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime
from typing import Any

import boto3

_client = None


def client():
    global _client
    if _client is None:
        _client = boto3.client("bedrock-agentcore", region_name=os.environ.get("AWS_REGION", "eu-west-2"))
    return _client


def memory_id() -> str | None:
    return os.environ.get("MEMORY_ID") or os.environ.get("MEMORY_INVESTIGATOR_MEMORY_ID")


def ns_segment(value: str) -> str:
    """Namespaces accept only [a-zA-Z0-9-_/*]; a symbol like SYN.A becomes SYN_A (observed 2026-11-04)."""
    return "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in value)


def trader_ns(trader_id: str) -> str:
    return f"/traders/{ns_segment(trader_id)}/notes/"


def instrument_ns(instrument: str) -> str:
    return f"/instruments/{ns_segment(instrument)}/notes/"


def desk_ns(desk: str) -> str:
    """Scenario traders are one per day, so a correction only carries to tomorrow through the desk."""
    return f"/desks/{ns_segment(desk)}/notes/"


PROCEDURES_NS = "/procedures/"


def _meta(d: dict[str, Any]) -> dict[str, dict[str, str]]:
    return {k: {"stringValue": str(v)} for k, v in d.items() if v not in (None, "")}


def write_records(records: list[dict[str, Any]]) -> list[dict]:
    """records: [{namespace, text, metadata}] -> MemoryRecordOutput list. No-op when MEMORY_ID is unset."""
    mid = memory_id()
    if not mid or not records:
        return []
    now = datetime.now(UTC)
    out = []
    for i in range(0, len(records), 100):
        batch = [
            {
                "requestIdentifier": f"{uuid.uuid4().hex}",
                "namespaces": [r["namespace"]],
                "content": {"text": r["text"]},
                "timestamp": r.get("timestamp") or now,
                "metadata": _meta(r.get("metadata") or {}),
            }
            for r in records[i : i + 100]
        ]
        resp = client().batch_create_memory_records(memoryId=mid, records=batch)
        out += resp.get("successfulRecords", []) + resp.get("failedRecords", [])
    return out


def disposition_text(alert: dict, case: dict, disposition: str, user: str, note: str, override: bool) -> str:
    """One sentence an analyst would write in a handover, with the facts a later investigation needs."""
    proposed = case.get("proposed_disposition")
    agent_part = f"the agent had proposed {proposed}" if proposed else "no agent proposal was on file"
    ov = " (OVERRIDE of the agent)" if override else ""
    return (
        f"On {alert['date']} alert {alert['alert_id']} ({alert['scenario']} on {alert['instrument']}, trader "
        f"{alert['trader_id']}) was recorded {disposition}{ov} by {user}; {agent_part}. Analyst note: {note}"
    )


def _fan_out(alert: dict, desk: str | None, text: str, metadata: dict[str, Any]) -> list[dict[str, Any]]:
    """The same fact under the trader and, when known, the trader's desk."""
    recs = [{"namespace": trader_ns(alert["trader_id"]), "text": text, "metadata": metadata}]
    if desk:
        recs.append(
            {"namespace": desk_ns(desk), "text": f"[desk {desk}] {text}", "metadata": {**metadata, "desk": desk}}
        )
    return recs


def record_disposition(
    alert: dict, case: dict, disposition: str, user: str, note: str, override: bool, desk: str | None = None
) -> None:
    write_records(
        _fan_out(
            alert,
            desk,
            disposition_text(alert, case, disposition, user, note, override),
            {
                "kind": "disposition",
                "alert_id": alert["alert_id"],
                "trader_id": alert["trader_id"],
                "instrument": alert["instrument"],
                "date": alert["date"],
                "recorded": disposition,
                "proposed": case.get("proposed_disposition"),
                "override": "true" if override else "false",
                "recorded_by": user,
            },
        )
    )


def record_feedback(alert: dict, user: str, note: str, desk: str | None = None) -> None:
    """Direct records for the agent's next recall, plus a conversational event for the SEMANTIC strategy."""
    write_records(
        _fan_out(
            alert,
            desk,
            (
                f"Analyst feedback from {user} on alert {alert['alert_id']} "
                f"({alert['trader_id']}, {alert['instrument']}, {alert['date']}): {note}"
            ),
            {
                "kind": "feedback",
                "alert_id": alert["alert_id"],
                "trader_id": alert["trader_id"],
                "instrument": alert["instrument"],
                "date": alert["date"],
                "recorded_by": user,
            },
        )
    )
    mid = memory_id()
    if not mid:
        return
    client().create_event(
        memoryId=mid,
        actorId=alert["trader_id"],  # the strategy's namespace is /traders/{actorId}/notes/
        sessionId=f"feedback-{alert['alert_id']}",
        eventTimestamp=datetime.now(UTC),
        payload=[
            {
                "conversational": {
                    "role": "USER",
                    "content": {
                        "text": (
                            f"Analyst {user} on alert {alert['alert_id']} about trader "
                            f"{alert['trader_id']} ({alert['instrument']}): {note}"
                        )
                    },
                }
            }
        ],
        metadata=_meta({"kind": "feedback", "alert_id": alert["alert_id"], "recorded_by": user}),
    )


def recall(namespace: str, query: str, top_k: int = 5) -> list[dict]:
    mid = memory_id()
    if not mid:
        return []
    # RetrieveMemoryRecords validates `namespace` against [a-zA-Z0-9/*][a-zA-Z0-9-_/*]*... which rejects the
    # trailing slash that BatchCreateMemoryRecords accepts (and the docs recommend). Observed 2026-11-04.
    resp = client().retrieve_memory_records(
        memoryId=mid,
        namespace=namespace.rstrip("/"),
        searchCriteria={"searchQuery": query[:1000], "topK": max(1, min(top_k, 20))},
    )
    out = []
    for r in resp.get("memoryRecordSummaries", []):
        meta = {
            k: (v.get("stringValue") or v.get("dateTimeValue") or v.get("numberValue"))
            for k, v in (r.get("metadata") or {}).items()
            if not k.startswith("x-amz-")
        }
        strategy = (r.get("metadata") or {}).get("x-amz-agentcore-memory-strategyType", {}).get("stringValue")
        out.append(
            {
                "text": r["content"]["text"],
                "score": round(float(r.get("score", 0)), 3),
                "source": "extracted by the semantic strategy"
                if strategy and strategy != "NONE"
                else "recorded by the human path",
                "metadata": {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in meta.items()},
                "record_id": r["memoryRecordId"],
            }
        )
    return out
