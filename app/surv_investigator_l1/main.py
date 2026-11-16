"""AgentCore Runtime entrypoint for the Level-1 investigator (HTTP protocol).

Payload: {"alert_id": "A-261006-0006", "mode": "investigate" | "stor_drafting" | "draft_stor",
          "instruction": "optional free text",
          "memory": true | false (default true; false hides `recall_memory` for the Memory on/off evaluation arm)}
`draft_stor` is the Level-2 second step on the session that proposed DRAFT_STOR: it only drafts the narrative.
Headers: Authorization: Bearer <analyst's Cognito access token>  (allowlisted on the Runtime; forwarded to the Gateway)

Returns the InvestigationResult as JSON: the proposal and its report, the Gateway's answer, the tool trajectory
with timings, any rejections the guard issued, token usage and the model's closing summary.
"""

from __future__ import annotations

import base64
import json
import logging
import os

from bedrock_agentcore.runtime import BedrockAgentCoreApp, RequestContext
from investigator import investigate

app = BedrockAgentCoreApp()
log = app.logger if hasattr(app, "logger") else logging.getLogger("surv.main")

MODES = ("investigate", "stor_drafting", "draft_stor")
L2_MODES = ("stor_drafting", "draft_stor")


def _bearer(context: RequestContext | None) -> str | None:
    headers = (getattr(context, "request_headers", None) or {}) if context is not None else {}
    for k, v in headers.items():
        if k.lower() == "authorization" and v.lower().startswith("bearer "):
            return v.split(" ", 1)[1].strip()
    if os.environ.get("LOCAL_DEV") == "1":  # `agentcore dev` without a UI in front: a token from .env.local
        return os.environ.get("SURV_LOCAL_TOKEN")
    return None


def _flag(value: object, default: bool = True) -> bool:
    """A JSON boolean, or the strings a hand-written payload carries: bool("false") is True."""
    if value is None:
        return default
    if isinstance(value, str):
        return value.strip().lower() not in ("false", "0", "off", "no", "")
    return bool(value)


def _claims(token: str) -> dict:
    """Unverified read of the JWT body for trace attributes only. The Runtime and the Gateway verify the signature."""
    try:
        part = token.split(".")[1]
        part += "=" * (-len(part) % 4)
        return json.loads(base64.urlsafe_b64decode(part))
    except Exception:
        return {}


@app.entrypoint
def invoke(payload: dict, context: RequestContext):
    if not isinstance(payload, dict):
        return {"error": "payload must be a JSON object"}
    alert_id = str(payload.get("alert_id") or "").strip()
    if not alert_id:
        return {"error": "alert_id is required"}
    mode = str(payload.get("mode") or "investigate")
    if mode not in MODES:
        return {"error": f"mode must be one of {MODES}"}
    token = _bearer(context)
    if not token:
        return {"error": "no analyst token: send Authorization: Bearer <Cognito access token>"}
    claims = _claims(token)
    groups = claims.get("cognito:groups") or []
    if isinstance(groups, str):  # a token body carries the array; tolerate a provider that sends one name
        groups = [g for g in groups.replace(",", " ").strip("[]").split() if g]
    if mode in L2_MODES and "L2" not in groups:
        return {"error": f"{mode} mode needs a Level-2 analyst (cognito:groups must include L2)"}
    if mode == "draft_stor" and not getattr(context, "session_id", None):
        # policy 05 admits the drafting tool only after a DRAFT_STOR proposal in the same policy session, and the
        # policy session is the Runtime session: the caller has to come back on the session that proposed
        return {"error": "draft_stor needs the Runtime session id of the investigation that proposed DRAFT_STOR"}
    analyst = claims.get("username") or claims.get("sub")
    log.info(
        "investigate alert=%s mode=%s analyst=%s session=%s",
        alert_id,
        mode,
        analyst,
        getattr(context, "session_id", None),
    )
    result = investigate(
        alert_id=alert_id,
        access_token=token,
        mode=mode,
        analyst=analyst,
        session_id=getattr(context, "session_id", None),
        extra_instruction=(payload.get("instruction") or None),
        memory=_flag(payload.get("memory"), True),
    )
    out = result.to_dict()
    out["analyst"] = analyst
    out["groups"] = groups
    return out


if __name__ == "__main__":
    app.run()
