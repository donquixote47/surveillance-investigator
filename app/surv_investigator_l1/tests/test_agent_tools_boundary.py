"""The agent can reach exactly one thing: the `surv` Gateway over MCP, as the analyst. Nothing else.

This is the broker brief's warning (section 2b) as code: a generic HTTP tool, or any second tool source, would let
the agent call the recording API with the analyst's token and record a disposition itself. The four layers that keep
it on the proposing side are (1) no recording tool on the Gateway, (2) Policy rule 02's closed allow-list, (3) no
code path in the agent that writes `recorded_*`, (4) the recording API being a separate Lambda the agent has no URL
for. This test pins the agent's side of (1) and (4): one tool provider, the Gateway MCP client, built with the
analyst's bearer token and the policy session header; no function tools, no `strands_tools`, no HTTP client in the
agent's tool set.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, ClassVar

import pytest
from strands.tools.tool_provider import ToolProvider

APP = Path(__file__).resolve().parents[1]
if str(APP) not in sys.path:
    sys.path.insert(0, str(APP))

import investigator  # noqa: E402

GATEWAY = "https://gateway.example.invalid"


class _FakeGatewayClient(ToolProvider):
    """Stands in for MCPClient: records how it was built, serves no tools, never opens a connection."""

    instances: ClassVar[list[_FakeGatewayClient]] = []

    def __init__(self, transport_callable=None, **kwargs: Any):
        self.transport_callable = transport_callable
        self.kwargs = kwargs
        _FakeGatewayClient.instances.append(self)

    async def load_tools(self, **kwargs: Any):
        return []

    def add_consumer(self, consumer_id: Any, **kwargs: Any) -> None:
        pass

    def remove_consumer(self, consumer_id: Any, **kwargs: Any) -> None:
        pass

    async def cleanup(self, **kwargs: Any) -> None:
        pass


@pytest.fixture
def captured(monkeypatch):
    """Patch the Gateway client and the transport factory inside `investigator`; return what they were given."""
    seen: dict[str, Any] = {}

    def fake_transport(url: str, headers: dict[str, str]):
        seen["url"] = url
        seen["headers"] = headers
        return object()

    monkeypatch.setenv("SURV_GATEWAY_URL", GATEWAY)
    monkeypatch.setattr(investigator, "MCPClient", _FakeGatewayClient)
    monkeypatch.setattr(investigator, "gateway_transport", fake_transport)
    _FakeGatewayClient.instances.clear()
    return seen


def test_agent_has_exactly_one_tool_source_and_it_is_the_gateway(captured):
    agent, _guard, mcp = investigator.build_agent(
        alert_id="A-261006-0006", access_token="analyst-jwt", analyst="l1.analyst", policy_session_id="ps-1"
    )
    try:
        providers = agent.tool_registry._tool_providers
        assert providers == [mcp], "the agent's only tool source must be the Gateway MCP client"
        assert isinstance(mcp, _FakeGatewayClient) and len(_FakeGatewayClient.instances) == 1
        # no function tools, no strands_tools, no HTTP client registered beside the Gateway
        assert agent.tool_registry.registry == {}, f"unexpected direct tools: {sorted(agent.tool_registry.registry)}"
        assert agent.tool_registry.dynamic_tools == {}
        # the client was built for the Gateway's MCP endpoint ...
        mcp.transport_callable()
        assert captured["url"] == f"{GATEWAY}/mcp"
        # ... as the analyst, inside this investigation's policy session
        assert captured["headers"]["Authorization"] == "Bearer analyst-jwt"
        assert captured["headers"][investigator.POLICY_SESSION_HEADER] == "ps-1"
    finally:
        agent.cleanup()


def test_memory_off_hides_only_recall_memory(captured):
    """The one tool filter the agent applies removes recall_memory and nothing else (the memory-off arm)."""
    agent, _g, mcp = investigator.build_agent(alert_id="A-261006-0006", access_token="t", memory=False)
    try:
        assert mcp.kwargs["tool_filters"] == {"rejected": [f"{investigator.TOOL_PREFIX}recall_memory"]}
    finally:
        agent.cleanup()
    agent, _g, mcp = investigator.build_agent(alert_id="A-261006-0006", access_token="t", memory=True)
    try:
        assert mcp.kwargs["tool_filters"] is None
    finally:
        agent.cleanup()


def test_build_agent_fills_the_provenance_from_the_request(captured, monkeypatch):
    """What the case will say about a proposal's origin comes from the Runtime request (session, analyst, model,
    mode, memory, the analyst's briefing), never from the model; `SURV_PROVENANCE=off` sends nothing."""
    agent, guard, _mcp = investigator.build_agent(
        alert_id="A-1",
        access_token="t",
        analyst="l1.analyst",
        policy_session_id="sess-9",
        instruction="  the desk says this was a client parent order  ",
    )
    try:
        assert guard.provenance["session_id"] == "sess-9" and guard.provenance["analyst"] == "l1.analyst"
        assert guard.provenance["analyst_instruction"] == "the desk says this was a client parent order"
        assert guard.provenance["memory"] == "on" and guard.provenance["mode"] == "investigate"
        assert guard.provenance["model_id"]
    finally:
        agent.cleanup()
    monkeypatch.setenv("SURV_PROVENANCE", "off")
    agent, guard, _mcp = investigator.build_agent(alert_id="A-1", access_token="t")
    try:
        assert guard.provenance == {}
    finally:
        agent.cleanup()


def test_agent_source_imports_no_other_tool_library():
    """Static guard: the agent package must not import a tool library or an HTTP client for the model's use.
    `httpx`/`httpx2` appear only as the MCP transport (RetryOn429), which is what the Gateway client rides on."""
    forbidden = ("strands_tools", "http_request", "import requests", "from requests", "urllib.request")
    for f in ("investigator.py", "main.py", "prompt.py", "report.py"):
        src = (APP / f).read_text()
        for word in forbidden:
            assert word not in src, f"{f} mentions {word!r}: a second way for the agent to reach the network"
    # the sole decorator that could register a function tool
    assert "@tool" not in (APP / "investigator.py").read_text()
    assert "@tool" not in (APP / "main.py").read_text()
