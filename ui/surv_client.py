"""Plain clients for the three things the analyst UI talks to: Cognito (login), the human-path HTTP API
(queue, case, record, feedback) and the AgentCore Runtime (run an investigation). Plus an optional reader of the
run's spans from CloudWatch so the UI can show the trace next to the report.

No Streamlit here, so these can be tested and reused by a CLI.

Configuration (environment first, then ~/.config/surv-investigator/analyst-credentials.env; passwords are never read
by the UI, the analyst types them): SURV_USER_POOL_ID, SURV_CLIENT_ID, SURV_API_URL, SURV_RUNTIME_ARN,
SURV_RUNTIME_LOG_GROUP, SURV_REGION.
"""

from __future__ import annotations

import base64
import json
import os
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

import boto3
import httpx

CONFIG_FILE = Path.home() / ".config" / "surv-investigator" / "analyst-credentials.env"
NEEDED = ("SURV_USER_POOL_ID", "SURV_CLIENT_ID", "SURV_API_URL", "SURV_RUNTIME_ARN")


@dataclass(frozen=True)
class Config:
    region: str
    user_pool_id: str
    client_id: str
    api_url: str
    runtime_arn: str
    runtime_log_group: str | None

    @classmethod
    def load(cls) -> Config:
        values: dict[str, str] = {}
        if CONFIG_FILE.exists():
            for line in CONFIG_FILE.read_text().splitlines():
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    if "PASSWORD" not in k:  # the UI never reads a password
                        values[k.strip()] = v.strip()
        values.update({k: v for k, v in os.environ.items() if k.startswith("SURV_")})
        missing = [k for k in NEEDED if not values.get(k)]
        if missing:
            raise RuntimeError(f"missing configuration {missing}; set them in the environment or {CONFIG_FILE}")
        return cls(
            region=values.get("SURV_REGION", "eu-west-2"),
            user_pool_id=values["SURV_USER_POOL_ID"],
            client_id=values["SURV_CLIENT_ID"],
            api_url=values["SURV_API_URL"].rstrip("/"),
            runtime_arn=values["SURV_RUNTIME_ARN"],
            runtime_log_group=values.get("SURV_RUNTIME_LOG_GROUP"),
        )


# ----------------------------------------------------------------------------------------------- identity


@dataclass
class Session:
    username: str
    groups: list[str]
    access_token: str
    id_token: str
    expires_at: float

    @property
    def level(self) -> str:
        return "L2" if "L2" in self.groups else ("L1" if "L1" in self.groups else "none")

    @property
    def expired(self) -> bool:
        return time.time() > self.expires_at - 60


def jwt_claims(token: str) -> dict:
    """Unverified read of the body, for display only; every service verifies the signature itself."""
    part = token.split(".")[1]
    part += "=" * (-len(part) % 4)
    return json.loads(base64.urlsafe_b64decode(part))


def login(cfg: Config, username: str, password: str) -> Session:
    idp = boto3.client("cognito-idp", region_name=cfg.region)
    r = idp.initiate_auth(
        ClientId=cfg.client_id,
        AuthFlow="USER_PASSWORD_AUTH",
        AuthParameters={"USERNAME": username, "PASSWORD": password},
    )
    auth = r["AuthenticationResult"]
    claims = jwt_claims(auth["AccessToken"])
    return Session(
        username=claims.get("username", username),
        groups=list(claims.get("cognito:groups") or []),
        access_token=auth["AccessToken"],
        id_token=auth["IdToken"],
        expires_at=time.time() + int(auth.get("ExpiresIn", 3600)),
    )


# ----------------------------------------------------------------------------------------------- human path API


class HumanPath:
    def __init__(self, cfg: Config, session: Session):
        self._base = cfg.api_url
        self._headers = {"Authorization": f"Bearer {session.access_token}"}

    def _call(self, method: str, path: str, **kwargs) -> dict:
        with httpx.Client(timeout=30.0) as c:
            r = c.request(method, self._base + path, headers=self._headers, **kwargs)
        try:
            body = r.json()
        except ValueError:
            body = {"error": r.text[:300]}
        if r.status_code >= 400 and "error" not in body:
            body["error"] = f"HTTP {r.status_code}"
        body["_status"] = r.status_code
        return body

    def queue(self, date: str) -> dict:
        return self._call("GET", "/alerts", params={"date": date})

    def case(self, alert_id: str) -> dict:
        return self._call("GET", f"/cases/{alert_id}")

    def record(self, alert_id: str, disposition: str, note: str) -> dict:
        return self._call("POST", f"/cases/{alert_id}/disposition", json={"disposition": disposition, "note": note})

    def feedback(self, alert_id: str, note: str) -> dict:
        return self._call("POST", f"/cases/{alert_id}/feedback", json={"note": note})


# ----------------------------------------------------------------------------------------------- the agent


def new_session_id(alert_id: str) -> str:
    return f"surv-{alert_id}-{uuid.uuid4().hex}"  # the Runtime wants 33+ characters


def invoke_runtime(
    cfg: Config,
    session: Session,
    alert_id: str,
    *,
    mode: str = "investigate",
    instruction: str | None = None,
    session_id: str | None = None,
    timeout_s: float = 600.0,
) -> tuple[dict, str, float]:
    """POST to the Runtime with the analyst's token. Returns (result, session id, wall seconds)."""
    session_id = session_id or new_session_id(alert_id)
    url = f"https://bedrock-agentcore.{cfg.region}.amazonaws.com/runtimes/{quote(cfg.runtime_arn, safe='')}/invocations"
    payload: dict = {"alert_id": alert_id, "mode": mode}
    if instruction:
        payload["instruction"] = instruction
    headers = {
        "Authorization": f"Bearer {session.access_token}",
        "Content-Type": "application/json",
        "X-Amzn-Bedrock-AgentCore-Runtime-Session-Id": session_id,
    }
    t0 = time.time()
    with httpx.Client(timeout=httpx.Timeout(timeout_s, connect=30.0)) as c:
        r = c.post(url, params={"qualifier": "DEFAULT"}, headers=headers, json=payload)
    wall = time.time() - t0
    if r.status_code != 200:
        return {"error": f"Runtime HTTP {r.status_code}: {r.text[:500]}"}, session_id, wall
    return r.json(), session_id, wall


# ----------------------------------------------------------------------------------------------- trace


@dataclass
class SpanRow:
    name: str
    kind: str
    start_ns: int
    duration_ms: float
    status: str
    trace_id: str
    tool: str | None
    alert_id: str | None


def session_spans(cfg: Config, session_id: str, lookback_s: int = 3600) -> list[SpanRow]:
    """Spans of one Runtime session from the log group's `spans` stream. Needs CloudWatch Logs read permission on
    this machine; the UI treats failure as 'trace not available here'."""
    if not cfg.runtime_log_group:
        return []
    logs = boto3.client("logs", region_name=cfg.region)
    now = int(time.time() * 1000)
    rows: list[SpanRow] = []
    token = None
    while True:
        kwargs = {
            "logGroupName": cfg.runtime_log_group,
            "logStreamNames": ["spans"],
            "startTime": now - lookback_s * 1000,
            "endTime": now + 60_000,
            "filterPattern": f'"{session_id}"',
            "limit": 500,
        }
        if token:
            kwargs["nextToken"] = token
        resp = logs.filter_log_events(**kwargs)
        for ev in resp.get("events", []):
            try:
                d = json.loads(ev["message"])
            except json.JSONDecodeError:
                continue
            a = d.get("attributes", {})
            if a.get("session.id") != session_id:
                continue
            rows.append(
                SpanRow(
                    name=d.get("name", "?"),
                    kind=a.get("aws.genai.span_kind") or a.get("gen_ai.operation.name") or "",
                    start_ns=int(d.get("startTimeUnixNano", 0)),
                    duration_ms=int(d.get("durationNano", 0)) / 1e6,
                    status=a.get("gen_ai.tool.status") or (d.get("status") or {}).get("code", ""),
                    trace_id=d.get("traceId", ""),
                    tool=a.get("gen_ai.tool.name"),
                    alert_id=a.get("surv.alert_id"),
                )
            )
        token = resp.get("nextToken")
        if not token:
            break
    rows.sort(key=lambda r: r.start_ns)
    return rows


def trace_console_url(cfg: Config, trace_id: str) -> str:
    return f"https://{cfg.region}.console.aws.amazon.com/cloudwatch/home?region={cfg.region}#xray:traces/{trace_id}"


def logs_console_url(cfg: Config, session_id: str) -> str:
    """Logs Insights query over the Runtime log group filtered by the session id."""
    if not cfg.runtime_log_group:
        return ""
    query = f"fields @timestamp, @message | filter @message like '{session_id}' | sort @timestamp asc | limit 200"
    # the console encodes the query with its own escaping; a plain URL-encoded form is accepted
    q = quote(query, safe="")
    g = quote(cfg.runtime_log_group, safe="")
    return (
        f"https://{cfg.region}.console.aws.amazon.com/cloudwatch/home?region={cfg.region}"
        f"#logsV2:logs-insights$3FqueryDetail$3D~(end~0~start~-3600~timeType~'RELATIVE~unit~'seconds~editorString~'{q}~source~(~'{g}))"
    )
