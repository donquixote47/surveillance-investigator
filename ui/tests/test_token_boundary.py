"""The token the agent holds cannot record a decision (2026-11-17).

One analyst, two Cognito app clients, two access tokens. The agent-session token goes to the AgentCore Runtime,
which forwards it to the Gateway; those two accept that client only. The analyst-records token stays in the UI
process and is the only one the recording API accepts. Until this change one client served both, so the token
inside the agent's session was also a valid credential for `POST /cases/{id}/disposition`.

Three places have to agree for that to hold, and each is checked here without AWS: the firm's stack (which client
the recording API accepts), the AgentCore project file (which client the Runtime and the Gateway accept), and the
UI's client module (which token goes where).
"""

from __future__ import annotations

import base64
import json
import sys
from pathlib import Path
from typing import ClassVar

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ui"))

import surv_client  # noqa: E402


def _jwt(claims: dict) -> str:
    body = base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip("=")
    return f"h.{body}.s"


def _cfg() -> surv_client.Config:
    return surv_client.Config(
        region="eu-west-2",
        user_pool_id="eu-west-2_test",
        client_id="agent-session-client",
        records_client_id="analyst-records-client",
        api_url="https://api.example.invalid",
        runtime_arn="arn:aws:bedrock-agentcore:eu-west-2:000000000000:runtime/test",
        runtime_log_group=None,
    )


class _Idp:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def initiate_auth(self, ClientId, AuthFlow, AuthParameters):  # noqa: N803 (boto3's parameter names)
        self.calls.append(ClientId)
        token = _jwt({"username": AuthParameters["USERNAME"], "cognito:groups": ["L1"], "client_id": ClientId})
        return {"AuthenticationResult": {"AccessToken": token, "IdToken": "id", "ExpiresIn": 28800}}


class _Http:
    """Stands in for httpx.Client and records what was sent where."""

    sent: ClassVar[list[tuple[str, str]]] = []

    def __init__(self, *a, **k) -> None:
        pass

    def __enter__(self):
        return self

    def __exit__(self, *a) -> bool:
        return False

    def _reply(self, url: str, headers: dict):
        _Http.sent.append((url, headers["Authorization"]))

        class R:
            status_code = 200
            text = "{}"

            @staticmethod
            def json() -> dict:
                return {}

        return R()

    def request(self, method, url, headers=None, **kw):
        return self._reply(url, headers)

    def post(self, url, params=None, headers=None, json=None):
        return self._reply(url, headers)


@pytest.fixture
def session(monkeypatch):
    idp = _Idp()
    monkeypatch.setattr(surv_client.boto3, "client", lambda *a, **k: idp)
    monkeypatch.setattr(surv_client.httpx, "Client", _Http)
    _Http.sent = []
    return surv_client.login(_cfg(), "l1.analyst", "pw"), idp


def test_one_login_gets_a_token_from_each_client(session) -> None:
    sess, idp = session
    assert idp.calls == ["agent-session-client", "analyst-records-client"]
    assert surv_client.jwt_claims(sess.access_token)["client_id"] == "agent-session-client"
    assert surv_client.jwt_claims(sess.records_token)["client_id"] == "analyst-records-client"
    assert sess.access_token != sess.records_token and sess.groups == ["L1"]


def test_the_recording_api_gets_the_records_token_and_the_runtime_gets_the_agent_session_token(session) -> None:
    sess, _ = session
    api = surv_client.HumanPath(_cfg(), sess)
    api.queue("2026-10-05")
    api.case("A-1")
    api.record("A-1", "CLOSE_FP", "note")
    api.feedback("A-1", "note")
    surv_client.invoke_runtime(_cfg(), sess, "A-1")
    to_api = [auth for url, auth in _Http.sent if url.startswith("https://api.example.invalid")]
    to_runtime = [auth for url, auth in _Http.sent if "bedrock-agentcore" in url]
    assert len(to_api) == 4 and set(to_api) == {f"Bearer {sess.records_token}"}
    assert to_runtime == [f"Bearer {sess.access_token}"]
    # the token that reaches the agent is never the one the recording API accepts
    assert sess.records_token not in " ".join(to_runtime)


def test_the_recording_api_accepts_the_records_client_only() -> None:
    """Synthesizes the firm's stack: the HTTP API's JWT authorizer has one audience, the analyst-records client,
    and the agent-session client is not in it."""
    cdk = pytest.importorskip("aws_cdk")
    from aws_cdk.assertions import Template

    sys.path.insert(0, str(ROOT / "infra"))
    from surv_firm.stack import SurvFirmStack

    app = cdk.App()
    stack = SurvFirmStack(app, "SurvFirmTest", env=cdk.Environment(account="000000000000", region="eu-west-2"))
    template = Template.from_stack(stack).to_json()
    clients = {
        v["Properties"]["ClientName"]: k
        for k, v in template["Resources"].items()
        if v["Type"] == "AWS::Cognito::UserPoolClient"
    }
    assert set(clients) == {"surv-agent-session", "surv-analyst-records"}
    (authorizer,) = [v for v in template["Resources"].values() if v["Type"] == "AWS::ApiGatewayV2::Authorizer"]
    assert authorizer["Properties"]["JwtConfiguration"]["Audience"] == [{"Ref": clients["surv-analyst-records"]}]
    outputs = template["Outputs"]
    assert outputs["UserPoolClientId"]["Value"] == {"Ref": clients["surv-agent-session"]}
    assert outputs["RecordsClientId"]["Value"] == {"Ref": clients["surv-analyst-records"]}


def test_the_runtime_and_the_gateway_accept_one_client_and_it_is_not_the_records_client() -> None:
    project = json.loads((ROOT / "agentcore" / "agentcore.json").read_text())
    allowed = [
        tuple(r["authorizerConfiguration"]["customJwtAuthorizer"]["allowedClients"])
        for kind in ("runtimes", "gateways", "agentCoreGateways")
        for r in project.get(kind, [])
        if "authorizerConfiguration" in r
    ]
    assert len(allowed) == 2 and allowed[0] == allowed[1] and len(allowed[0]) == 1
    # with the stack's recorded outputs at hand (a deployed checkout), the ids themselves are compared
    outputs_file = ROOT / "infra" / "build" / "outputs.json"
    if outputs_file.exists():
        outputs = json.loads(outputs_file.read_text())["SurvFirm"]
        assert allowed[0] == (outputs["UserPoolClientId"],)
        if "RecordsClientId" in outputs:
            assert outputs["RecordsClientId"] not in allowed[0]
