"""The policy files, the project file that deploys them, and the tool schema they are validated against.

No AWS: these are the facts that have to hold in the repository before a deploy is worth starting. The service
validates the rest (`scripts/validate_policies.py`), and the probes after a deploy show the behaviour.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
POLICIES = ROOT / "policies"

# policy file -> the evidence tools whose answer it requires before a proposal
PREREQUISITES = {
    "03a-evidence-before-proposal.dw": ["get_alert", "get_order_events", "compute_discriminators"],
    "03b-profile-and-market-before-proposal.dw": ["get_trader_profile", "get_market_events"],
    "04-history-before-close.dw": ["get_trader_alert_history"],
}
PREDICATE = re.compile(r'AgentCore::Action::"surv___(\w+)"::(request|response|error)\{([^}]*)\}')


def test_the_project_file_deploys_exactly_the_policy_files() -> None:
    """`agentcore.json` carries each statement verbatim next to its `sourceFile`. Nothing kept the two equal:
    an edit to a `.dw` file that did not reach the project file would be reviewed and never deployed."""
    project = json.loads((ROOT / "agentcore" / "agentcore.json").read_text())
    policies = [p for engine in project["policyEngines"] for p in engine["policies"]]
    assert {Path(p["sourceFile"]).name for p in policies} == {f.name for f in POLICIES.iterdir()}
    for p in policies:
        assert p["statement"] == (ROOT / p["sourceFile"]).read_text(), p["name"]


def test_look_before_you_propose_matches_on_what_each_tool_returned() -> None:
    """A proposal needs each evidence tool to have RETURNED this alert's id (`output.alert_id`), in a `::response`
    event on this Gateway. Matching on the request (`input.alert_id`), or on nothing, let a lookup that failed,
    or one made for another alert, count: until 2026-11-17 the first was true of three tools and the second of
    two."""
    from tools.lambda_handlers.gateway_tools import EVIDENCE_TOOLS

    seen: list[str] = []
    for name, tools in PREREQUISITES.items():
        found = PREDICATE.findall((POLICIES / name).read_text())
        assert [t for t, _, _ in found] == tools, name
        for tool, kind, body in found:
            fields = {k.strip(): v.strip() for k, v in (line.split(":", 1) for line in body.split(",") if ":" in line)}
            assert kind == "response", (name, tool)
            assert fields == {"eventResource": "resource", "output.alert_id": "context.input.alert_id"}, (name, tool)
            seen.append(tool)
    assert sorted(seen) == sorted(EVIDENCE_TOOLS)


def test_every_evidence_tool_declares_the_alert_id_it_returns() -> None:
    """`output.<field>` exists on a response event only when the target declares it in the tool's output schema;
    a policy that names an undeclared field is rejected when it is created (devguide, "Temporal policy
    examples"). The exported file is what the Gateway target is created from."""
    from tools import schema
    from tools.lambda_handlers.gateway_tools import EVIDENCE_TOOLS

    exported = {t["name"]: t for t in json.loads((ROOT / "surv-tools.json").read_text())}
    for tool in EVIDENCE_TOOLS:
        for source in (next(t for t in schema.TOOLS if t["name"] == tool), exported[tool]):
            assert source["outputSchema"]["properties"]["alert_id"]["type"] == "string", tool


def test_the_project_file_fits_the_cli_limits() -> None:
    """The AgentCore CLI rejects the whole project file when an endpoint description is longer than 200
    characters, and says so only at deploy time (2026-11-18: the move of `demo` to v20 failed on a 250-character
    description before anything was deployed)."""
    project = json.loads((ROOT / "agentcore" / "agentcore.json").read_text())
    for runtime in project["runtimes"]:
        for name, endpoint in runtime.get("endpoints", {}).items():
            assert len(endpoint.get("description", "")) <= 200, f"{runtime['name']}.{name}"
            assert isinstance(endpoint["version"], int), f"{runtime['name']}.{name}"
