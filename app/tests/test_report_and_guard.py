"""Report model rules, the guard's behaviour on propose_disposition, and alignment with the Gateway schema."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# The tests live beside the agent's folder, not inside it: the Runtime bundle is that folder, whole.
APP = Path(__file__).resolve().parents[1] / "surv_investigator_l1"
SRC = APP.parents[1] / "src"
for p in (APP, SRC):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from investigator import PROPOSE, InvestigationGuard  # noqa: E402
from report import InvestigationReport  # noqa: E402

GOOD = {
    "alert_id": "A-261006-0006",
    "scenario": "SPOOFING",
    "summary": "A single 38,461-share bid, 15.7x top-5 depth, rested 2 ticks behind the touch for 2.9 s, during which the trader sold 1,423 shares; all 38,461 were cancelled 360 ms later and the mid reverted 1 tick.",
    "evidence": [
        {
            "id": "E1",
            "source": "compute_discriminators",
            "fact": "max_resting_size_vs_depth 15.70, distance_from_touch_ticks 2.0",
        },
        {
            "id": "E2",
            "source": "compute_discriminators",
            "fact": "opposite_side_fill_qty 1423, 360 ms before the first cancel",
        },
        {"id": "E3", "source": "get_trader_profile", "fact": "role PROP, registered_mm_instruments empty"},
        {"id": "E4", "source": "get_market_events", "fact": "no events within 60 s of the window"},
    ],
    "indicators_matched": [
        "orders with no intention to execute (Annex II 5(e))",
        "opposite-side execution before the cancel",
    ],
    "indicators_not_matched": ["several price levels on one side (layering)"],
    "legitimate_explanations_considered": [
        {"explanation": "market making", "ruled_out_by": ["E3"], "verdict": "ruled_out"},
        {"explanation": "reaction to a public event", "ruled_out_by": ["E4"], "verdict": "ruled_out"},
        {"explanation": "fat finger", "ruled_out_by": ["E2"], "verdict": "ruled_out"},
    ],
    "proposed_disposition": "ESCALATE",
    "confidence": 0.85,
    "what_would_change_my_mind": "A parent order or hedge instruction that explains the 38,461 bid.",
    "memory_used": [],
    "window_used": "12:49:41.863 to 12:50:49.339 (detector window); the trader's whole session was checked for repetitions (1 found).",
}


def test_good_report_validates():
    r = InvestigationReport.model_validate(GOOD)
    assert r.proposed_disposition == "ESCALATE"
    gw = r.for_gateway()
    assert "proposed_disposition" not in gw and "confidence" not in gw
    assert gw["evidence"][0]["source"] == "compute_discriminators"


def test_close_fp_needs_a_supported_explanation():
    bad = {**GOOD, "proposed_disposition": "CLOSE_FP"}
    with pytest.raises(ValueError, match="supported"):
        InvestigationReport.model_validate(bad)
    ok = {
        **GOOD,
        "proposed_disposition": "CLOSE_FP",
        "legitimate_explanations_considered": [
            {"explanation": "market making", "ruled_out_by": [], "verdict": "supported"}
        ],
    }
    assert InvestigationReport.model_validate(ok).proposed_disposition == "CLOSE_FP"


def test_escalate_with_supported_explanation_is_inconsistent():
    bad = {**GOOD, "legitimate_explanations_considered": [{"explanation": "market making", "verdict": "supported"}]}
    with pytest.raises(ValueError, match="inconsistent"):
        InvestigationReport.model_validate(bad)


def test_ruled_out_needs_evidence_and_known_ids():
    bad = {**GOOD, "legitimate_explanations_considered": [{"explanation": "market making", "verdict": "ruled_out"}]}
    with pytest.raises(ValueError, match="cites no evidence"):
        InvestigationReport.model_validate(bad)
    bad = {
        **GOOD,
        "legitimate_explanations_considered": [
            {"explanation": "market making", "ruled_out_by": ["E9"], "verdict": "ruled_out"}
        ],
    }
    with pytest.raises(ValueError, match="unknown evidence ids"):
        InvestigationReport.model_validate(bad)


def test_ruled_out_is_accepted_as_an_alias_and_emitted_as_ruled_out_by():
    """The v3 slip (24/167 sessions): the model writes `ruled_out` for `ruled_out_by`. Accepted on input, a lone
    id is wrapped in a list, and the Gateway payload always carries the declared name."""
    slip = {
        **GOOD,
        "legitimate_explanations_considered": [
            {"explanation": "market making", "ruled_out": ["E3"], "verdict": "ruled_out"},
            {"explanation": "fat finger", "ruled_out": "E2", "verdict": "ruled_out"},
            # both keys at once, as Runtime v13 produced on 2026-11-10: the declared one wins when it is filled
            {"explanation": "iceberg", "ruled_out": ["E1"], "ruled_out_by": ["E4"], "verdict": "ruled_out"},
            {"explanation": "algo re-pricing", "ruled_out": [], "ruled_out_by": [], "verdict": "undetermined"},
            {"explanation": "news", "ruled_out": None, "verdict": "undetermined"},
        ],
    }
    r = InvestigationReport.model_validate(slip)
    assert [e.ruled_out_by for e in r.legitimate_explanations_considered] == [["E3"], ["E2"], ["E4"], [], []]
    gw = r.for_gateway()["legitimate_explanations_considered"]
    assert all("ruled_out_by" in e and "ruled_out" not in e for e in gw)
    # the alias does not loosen the rest: an unknown id under the alias is still caught
    bad = {
        **GOOD,
        "legitimate_explanations_considered": [
            {"explanation": "market making", "ruled_out": ["E9"], "verdict": "ruled_out"}
        ],
    }
    with pytest.raises(ValueError, match="unknown evidence ids"):
        InvestigationReport.model_validate(bad)
    # and other unknown keys are still refused
    bad = {
        **GOOD,
        "legitimate_explanations_considered": [
            {"explanation": "market making", "ruled_out_by": ["E3"], "verdict": "ruled_out", "reason": "because"}
        ],
    }
    with pytest.raises(ValueError, match="Extra inputs are not permitted"):
        InvestigationReport.model_validate(bad)


def test_evidence_source_must_be_a_tool():
    bad = {
        **GOOD,
        "evidence": [*GOOD["evidence"][:2], {"id": "E3", "source": "my_intuition", "fact": "he looked guilty"}],
    }
    with pytest.raises(ValueError, match="source must be one of"):
        InvestigationReport.model_validate(bad)
    ok = {
        **GOOD,
        "evidence": [*GOOD["evidence"][:3], {"id": "E4", "source": "surv___get_market_events", "fact": "no events"}],
    }
    assert InvestigationReport.model_validate(ok).evidence[3].source == "get_market_events"


def test_report_fields_are_declared_on_the_gateway_schema():
    from tools.schema import TOOLS

    gw = next(t for t in TOOLS if t["name"] == "propose_disposition")["inputSchema"]["properties"]["report"][
        "properties"
    ]
    ours = InvestigationReport.model_json_schema()["properties"]
    missing = set(ours) - set(gw) - {"proposed_disposition", "confidence"}  # these two travel as separate tool inputs
    assert not missing, f"fields the agent sends that the Gateway schema does not declare: {sorted(missing)}"


class _Event:
    def __init__(self, name, inputs):
        self.tool_use = {"toolUseId": "t1", "name": name, "input": inputs}
        self.cancel_tool = False
        self.invocation_state = {}


class _AfterEvent:
    def __init__(self, name, inputs, result, cancel_message=None):
        self.tool_use = {"toolUseId": "t2", "name": name, "input": inputs}
        self.result = result
        self.cancel_message = cancel_message
        self.invocation_state = {}


EVIDENCE_TOOLS = [
    "get_alert",
    "get_procedures",
    "get_order_events",
    "compute_discriminators",
    "get_trader_profile",
    "get_market_events",
    "get_trader_alert_history",
]


def _ran(g, tool, inputs=None, body=None):
    """One tool call as the guard sees it: the request, then the result the Gateway returned. A body with an
    `error` key is what the tools Lambda answers when a tool fails (an ordinary result, not an exception)."""
    inputs = {"alert_id": g.alert_id} if inputs is None else inputs
    name = f"surv___{tool}"
    before = _Event(name, inputs)
    g.before_tool(before)
    if before.cancel_tool:
        g.after_tool(_AfterEvent(name, inputs, None, cancel_message=before.cancel_tool))
        return before
    body = {"alert_id": g.alert_id} if body is None else body
    result = {"toolUseId": "t1", "status": "success", "content": [{"text": json.dumps(body)}]}
    g.after_tool(_AfterEvent(name, inputs, result))
    return before


def _evidence(g, skip=()):
    for t in EVIDENCE_TOOLS:
        if t not in skip:
            _ran(g, t)


def test_guard_rejects_bad_report_fills_tool_calls_and_blocks_second_proposal():
    g = InvestigationGuard(alert_id="A-261006-0006")
    _evidence(g)

    bad = _Event(
        PROPOSE,
        {"alert_id": "A-261006-0006", "disposition": "CLOSE_FP", "confidence": 0.9, "report": {"summary": "too short"}},
    )
    g.before_tool(bad)
    assert isinstance(bad.cancel_tool, str) and "report rejected" in bad.cancel_tool
    assert g.proposal is None and len(g.rejections) == 1

    report = {k: v for k, v in GOOD.items() if k not in ("proposed_disposition", "confidence")}
    good = _Event(
        PROPOSE, {"alert_id": "A-261006-0006", "disposition": "ESCALATE", "confidence": 0.85, "report": report}
    )
    g.before_tool(good)
    assert good.cancel_tool is False
    sent = good.tool_use["input"]["report"]
    assert sent["tool_calls"] == EVIDENCE_TOOLS
    assert "proposed_disposition" not in sent
    assert g.proposal["disposition"] == "ESCALATE"

    wrong_alert = _Event(
        PROPOSE, {"alert_id": "A-000000-0001", "disposition": "ESCALATE", "confidence": 0.5, "report": report}
    )
    g2 = InvestigationGuard(alert_id="A-261006-0006")
    g2.before_tool(wrong_alert)
    assert "this investigation is for alert" in wrong_alert.cancel_tool

    second = _Event(
        PROPOSE, {"alert_id": "A-261006-0006", "disposition": "CLOSE_FP", "confidence": 0.5, "report": report}
    )
    g.before_tool(second)
    assert "already called" in second.cancel_tool


def test_guard_modes_for_stor_drafting():
    """Level-1 mode never drafts; `draft_stor` (the L2 second step on the proposing session) drafts once for its own
    alert and never proposes; `stor_drafting` (the harness arm) may do both in one run."""
    from investigator import DRAFT_STOR

    l1 = InvestigationGuard(alert_id="A-261006-0006")
    e = _Event(DRAFT_STOR, {"alert_id": "A-261006-0006"})
    l1.before_tool(e)
    assert "Level-2 action" in e.cancel_tool

    d = InvestigationGuard(alert_id="A-261006-0006", mode="draft_stor")
    p = _Event(PROPOSE, {"alert_id": "A-261006-0006", "disposition": "DRAFT_STOR", "confidence": 0.9, "report": {}})
    d.before_tool(p)
    assert "only drafts" in p.cancel_tool and d.proposal is None
    wrong = _Event(DRAFT_STOR, {"alert_id": "A-000000-0001"})
    d.before_tool(wrong)
    assert "this session is for alert" in wrong.cancel_tool
    ok = _Event(DRAFT_STOR, {"alert_id": "A-261006-0006"})
    d.before_tool(ok)
    assert ok.cancel_tool is False
    d.stor_draft = {"narrative": "..."}  # as after_tool would set it on a good result
    again = _Event(DRAFT_STOR, {"alert_id": "A-261006-0006"})
    d.before_tool(again)
    assert "already called" in again.cancel_tool

    both = InvestigationGuard(alert_id="A-261006-0006", mode="stor_drafting")
    e2 = _Event(DRAFT_STOR, {"alert_id": "A-261006-0006"})
    both.before_tool(e2)
    assert e2.cancel_tool is False


def test_guard_blocks_stor_draft_in_l1_mode():
    g = InvestigationGuard(alert_id="A-1", mode="investigate")
    ev = _Event("surv___draft_stor_narrative", {"alert_id": "A-1"})
    g.before_tool(ev)
    assert "Level-2" in ev.cancel_tool
    g2 = InvestigationGuard(alert_id="A-1", mode="stor_drafting")
    ev2 = _Event("surv___draft_stor_narrative", {"alert_id": "A-1"})
    g2.before_tool(ev2)
    assert ev2.cancel_tool is False


def test_guard_releases_the_proposal_when_the_gateway_denies_it():
    """A policy denial reaches Strands as an error tool result; the guard must forget the proposal so the model can
    run the missing prerequisite and propose again, and it must keep the Gateway's reason for the record."""
    g = InvestigationGuard(alert_id="A-261006-0006")
    _evidence(g)
    report = {k: v for k, v in GOOD.items() if k not in ("proposed_disposition", "confidence")}
    inputs = {"alert_id": "A-261006-0006", "disposition": "ESCALATE", "confidence": 0.8, "report": report}
    before = _Event(PROPOSE, inputs)
    g.before_tool(before)
    assert g.proposal is not None
    denied = {
        "toolUseId": "t2",
        "status": "error",
        "content": [
            {
                "text": "Tool Execution Denied: Tool call not allowed due to policy enforcement [Policy evaluation denied due to p03b_profile_and_market_before_proposal-x]"
            }
        ],
    }
    g.after_tool(_AfterEvent(PROPOSE, inputs, denied))
    assert g.proposal is None, "a denied proposal must not count as the one proposal per run"
    assert g.proposal_result is None
    assert any("p03b" in r for r in g.rejections)
    assert g.calls[-1]["status"] == "error"

    # the model runs the prerequisite and proposes again: allowed this time
    g.before_tool(_Event("surv___get_trader_profile", {"trader_id": "T-X1006-04", "alert_id": "A-261006-0006"}))
    again = _Event(PROPOSE, inputs)
    g.before_tool(again)
    assert again.cancel_tool is False, "second attempt after a denial must not be blocked by the one-proposal rule"
    ok = {
        "toolUseId": "t3",
        "status": "success",
        "content": [
            {
                "text": '{"alert_id": "A-261006-0006", "disposition": "ESCALATE", "case_id": "C-A-261006-0006", "status": "PROPOSED"}'
            }
        ],
    }
    g.after_tool(_AfterEvent(PROPOSE, inputs, ok))
    assert g.proposal_result["case_id"] == "C-A-261006-0006"
    assert g.proposal["report"]["tool_calls"][-1] == "get_trader_profile"


def test_prompt_memory_switch():
    from prompt import TOOL_PREFIX, system_prompt

    on, off = system_prompt("investigate", memory=True), system_prompt("investigate", memory=False)
    assert f"{TOOL_PREFIX}recall_memory` with the alert id" in on and "memory_used` lists" in on
    assert "Memory is switched off" in off and "`memory_used` is an empty list" in off
    assert "Read it before the evidence" not in off


def test_retry_on_429_replays_the_request(monkeypatch):
    """A throttled Gateway call is retried with back-off instead of closing the MCP connection."""
    import asyncio

    from investigator import RetryOn429
    from investigator import _httpx as httpx2

    calls = []

    async def fake_handle(self, request):
        calls.append(request.content)
        status = 429 if len(calls) < 3 else 200
        return httpx2.Response(status, headers={"retry-after": "0"} if status == 429 else {}, content=b"{}")

    slept = []

    async def fake_sleep(d):
        slept.append(d)

    monkeypatch.setattr(httpx2.AsyncHTTPTransport, "handle_async_request", fake_handle)
    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    t = RetryOn429(max_retries=3)
    req = httpx2.Request("POST", "https://gw.example/mcp", content=b'{"jsonrpc":"2.0"}')
    resp = asyncio.run(t.handle_async_request(req))
    assert resp.status_code == 200
    assert calls == [b'{"jsonrpc":"2.0"}'] * 3  # same body each time
    assert slept == [0.0, 0.0]  # Retry-After honoured

    calls.clear()
    t = RetryOn429(max_retries=1)
    resp = asyncio.run(t.handle_async_request(httpx2.Request("POST", "https://gw.example/mcp", content=b"x")))
    assert resp.status_code == 429 and len(calls) == 2  # gives up after max_retries and returns the last answer


def test_a_throttled_call_waits_long_enough_to_outlast_the_per_minute_limit(monkeypatch):
    """The Gateway counts requests per minute. With 14 s of back-off in all, an investigation that met a full
    bucket died (2 of 167 in run v6, 2026-11-18). The wait now adds up to more than a minute, so a throttled
    investigation is slower and does not fail; a Retry-After the Gateway sends is honoured, but never for more
    than a minute."""
    import asyncio

    from investigator import RetryOn429
    from investigator import _httpx as httpx2

    answers = [429] * 5 + [200]
    headers = [{}] * 6
    calls, slept = [], []

    async def fake_handle(self, request):
        calls.append(request.content)
        i = len(calls) - 1
        return httpx2.Response(answers[i], headers=headers[i], content=b"{}")

    async def fake_sleep(d):
        slept.append(d)

    monkeypatch.setattr(httpx2.AsyncHTTPTransport, "handle_async_request", fake_handle)
    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    resp = asyncio.run(
        RetryOn429().handle_async_request(httpx2.Request("POST", "https://gw.example/mcp", content=b"x"))
    )
    assert resp.status_code == 200 and len(calls) == 6, "five throttled answers in a row are waited out"
    assert [int(d) for d in slept] == [2, 4, 8, 16, 32], "doubling, each with less than a second of jitter"
    assert sum(slept) >= 60, "the waits add up to more than the limit's minute"
    assert all(0 <= d - b < 1 for d, b in zip(slept, [2, 4, 8, 16, 32], strict=True))

    # the Gateway's own Retry-After wins, capped at a minute
    calls.clear()
    slept.clear()
    answers[:] = [429, 429, 200]
    headers[:] = [{"retry-after": "7"}, {"retry-after": "3600"}, {}]
    resp = asyncio.run(
        RetryOn429().handle_async_request(httpx2.Request("POST", "https://gw.example/mcp", content=b"x"))
    )
    assert resp.status_code == 200 and slept == [7.0, 60.0]

    # and it still gives up: six throttled answers in a row come back as the last 429
    calls.clear()
    slept.clear()
    answers[:] = [429] * 6
    headers[:] = [{}] * 6
    resp = asyncio.run(
        RetryOn429().handle_async_request(httpx2.Request("POST", "https://gw.example/mcp", content=b"x"))
    )
    assert resp.status_code == 429 and len(calls) == 6 and len(slept) == 5


def test_guard_accepts_a_json_encoded_report_and_rejects_garbage():
    """Opus 5.5 passed `report` as a JSON string in 5 of 167 runs; dict() on a string raised inside the hook and
    killed the investigation. A string that parses to an object is accepted; anything else is a clean rejection."""
    from investigator import InvestigationGuard

    class Ev:
        def __init__(self, inputs):
            self.tool_use = {"name": PROPOSE, "toolUseId": "t1", "input": inputs}
            self.cancel_tool = None

    g = InvestigationGuard(alert_id="A-1")
    _evidence(g)
    ev = Ev({"alert_id": "A-1", "disposition": "ESCALATE", "confidence": 0.7, "report": "not json {"})
    g.before_tool(ev)
    assert ev.cancel_tool and "JSON object" in ev.cancel_tool and g.proposal is None
    ev = Ev({"alert_id": "A-1", "disposition": "ESCALATE", "confidence": 0.7, "report": '["a", "b"]'})
    g.before_tool(ev)
    assert ev.cancel_tool and "JSON object" in ev.cancel_tool
    ev = Ev({"alert_id": "A-1", "disposition": "ESCALATE", "confidence": 0.7, "report": "{}"})
    g.before_tool(ev)
    assert ev.cancel_tool and "report rejected" in ev.cancel_tool  # parsed as an object, then fails validation


def _proposal(disposition="ESCALATE", **report_overrides):
    report = {k: v for k, v in GOOD.items() if k not in ("proposed_disposition", "confidence")}
    report.update(report_overrides)
    return {"alert_id": GOOD["alert_id"], "disposition": disposition, "confidence": 0.8, "report": report}


def test_guard_holds_a_proposal_until_the_evidence_tools_returned_a_result():
    """Review 2026-11-16. The tools Lambda answers a failure as an ordinary result `{"error": ...}`, and until
    2026-11-17 the Gateway's rules 03a/03b counted any call that completed, so a failed evidence call satisfied
    "evidence before proposal". The guard asks that each evidence tool answered, for this alert, in this run; the
    rules now ask the same (the next test)."""
    g = InvestigationGuard(alert_id=GOOD["alert_id"])
    _evidence(g, skip=("compute_discriminators", "get_trader_alert_history"))
    _ran(g, "compute_discriminators", body={"error": "compute_discriminators failed: no instrument statistics"})
    assert g.calls[-1]["status"] == "error" and "compute_discriminators" not in g.ok_tools
    e = _Event(PROPOSE, _proposal())
    g.before_tool(e)
    assert "held back" in e.cancel_tool and "compute_discriminators" in e.cancel_tool
    assert g.proposal is None and len(g.rejections) == 1

    # a result for ANOTHER alert is not evidence for this one
    _ran(g, "compute_discriminators", inputs={"alert_id": "A-000000-0001"}, body={"alert_id": "A-000000-0001"})
    e = _Event(PROPOSE, _proposal())
    g.before_tool(e)
    assert "held back" in e.cancel_tool

    _ran(g, "compute_discriminators")  # answers this time
    e = _Event(PROPOSE, _proposal())
    g.before_tool(e)
    assert e.cancel_tool is False and g.proposal["disposition"] == "ESCALATE"


def test_guard_counts_an_evidence_tool_only_when_its_answer_names_the_alert():
    """2026-11-18. Policies 03a, 03b and 04 match `output.alert_id`: what the tool answered, not what was asked.
    The guard used to accept a call made without an alert id; the Gateway would then have refused the proposal
    with a rule's name and nothing else. The guard now holds it first and says what to run."""
    g = InvestigationGuard(alert_id=GOOD["alert_id"])
    _evidence(g, skip=("get_market_events", "get_trader_profile", "get_trader_alert_history"))
    # asked by instrument and window, as callers before 2026-11-16 did: the answer names no alert
    _ran(
        g, "get_market_events", inputs={"instrument": "SYN.A", "window_start": 1, "window_end": 2}, body={"events": []}
    )
    # asked without the alert id: the profile comes back, and it names no alert either
    _ran(g, "get_trader_profile", inputs={"trader_id": "T-1"}, body={"trader_id": "T-1", "role": "PROP"})
    assert g.calls[-1]["status"] == "ok", "the call itself succeeded"
    assert not {"get_market_events", "get_trader_profile"} & g.ok_tools
    e = _Event(PROPOSE, _proposal())
    g.before_tool(e)
    assert "held back" in e.cancel_tool and "without the alert_id" in e.cancel_tool
    assert "get_market_events" in e.cancel_tool and "get_trader_profile" in e.cancel_tool
    assert "get_alert" not in e.cancel_tool.split("investigation:")[1].split(".")[0], "only the missing ones are named"

    _ran(g, "get_market_events")
    _ran(g, "get_trader_profile", inputs={"trader_id": "T-1", "alert_id": g.alert_id})
    e = _Event(PROPOSE, _proposal())
    g.before_tool(e)
    assert e.cancel_tool is False and g.proposal["disposition"] == "ESCALATE"


def test_the_guard_and_the_gateway_rules_name_the_same_evidence_tools():
    """The guard's list and the three policy files are two statements of one control; they must not drift."""
    import re

    from investigator import CLOSE_EVIDENCE, REQUIRED_EVIDENCE

    policies = APP.parents[1] / "policies"

    def named(file: str) -> set[str]:
        text = (policies / file).read_text()
        return set(re.findall(r'AgentCore::Action::"surv___(\w+)"::response', text))

    before_a_proposal = named("03a-evidence-before-proposal.dw") | named("03b-profile-and-market-before-proposal.dw")
    assert before_a_proposal == set(REQUIRED_EVIDENCE)
    assert named("04-history-before-close.dw") == set(CLOSE_EVIDENCE)
    for file in (
        "03a-evidence-before-proposal.dw",
        "03b-profile-and-market-before-proposal.dw",
        "04-history-before-close.dw",
    ):
        text = (policies / file).read_text()
        assert text.count("::response") == text.count("output.alert_id: context.input.alert_id"), file


def test_guard_needs_the_history_for_a_closure_only():
    g = InvestigationGuard(alert_id=GOOD["alert_id"])
    _evidence(g, skip=("get_trader_alert_history",))
    supported = [{"explanation": "market making", "ruled_out_by": [], "verdict": "supported"}]
    close = _Event(PROPOSE, _proposal("CLOSE_FP", legitimate_explanations_considered=supported))
    g.before_tool(close)
    assert "held back" in close.cancel_tool and "get_trader_alert_history" in close.cancel_tool
    escalate = _Event(PROPOSE, _proposal("ESCALATE"))
    g.before_tool(escalate)
    assert escalate.cancel_tool is False  # rule 04 asks for the history only before a closure


def test_guard_rejects_evidence_attributed_to_a_tool_that_did_not_answer():
    g = InvestigationGuard(alert_id=GOOD["alert_id"])
    _evidence(g)
    evidence = [*GOOD["evidence"], {"id": "E5", "source": "reconstruct_book", "fact": "bid 9,998 held 38,461 shares"}]
    e = _Event(PROPOSE, _proposal(evidence=evidence))
    g.before_tool(e)
    assert "did not return a result" in e.cancel_tool and "reconstruct_book" in e.cancel_tool
    # `memory` is the report's name for recall_memory
    evidence = [*GOOD["evidence"], {"id": "E5", "source": "memory", "fact": "desk note: two prior closures"}]
    e = _Event(PROPOSE, _proposal(evidence=evidence))
    g.before_tool(e)
    assert "recall_memory" in e.cancel_tool
    _ran(g, "recall_memory")
    e = _Event(PROPOSE, _proposal(evidence=evidence))
    g.before_tool(e)
    assert e.cancel_tool is False


def test_guard_stamps_the_proposal_with_its_provenance_and_ignores_the_models_own():
    g = InvestigationGuard(alert_id=GOOD["alert_id"])
    g.provenance = {"session_id": "sess-1", "analyst": "l1.analyst", "model_id": "m", "mode": "investigate"}
    _evidence(g)
    e = _Event(PROPOSE, {**_proposal(), "provenance": {"analyst": "someone.else", "session_id": "forged"}})
    g.before_tool(e)
    assert e.cancel_tool is False
    assert e.tool_use["input"]["provenance"] == g.provenance

    bare = InvestigationGuard(alert_id=GOOD["alert_id"])  # SURV_PROVENANCE=off: nothing is sent, not even the model's
    _evidence(bare)
    e = _Event(PROPOSE, {**_proposal(), "provenance": {"analyst": "someone.else"}})
    bare.before_tool(e)
    assert "provenance" not in e.tool_use["input"]


def test_guard_stops_an_investigation_of_a_decided_alert():
    """A decided alert takes no new proposal (the tools Lambda refuses the write). The guard reads the alert's
    status from get_alert and cancels everything after it, so the refusal costs one tool call, not an
    investigation. Level 2 drafting the STOR after recording DRAFT_STOR is not an investigation and goes on."""
    g = InvestigationGuard(alert_id="A-1")
    _ran(g, "get_alert", body={"alert_id": "A-1", "status": "CLOSED"})
    assert g.decided == "CLOSED"
    nxt = _ran(g, "get_order_events")
    assert "already decided" in nxt.cancel_tool and g.calls[-1]["status"] == "error"
    assert "get_order_events" not in g.ok_tools

    open_alert = InvestigationGuard(alert_id="A-1")
    _ran(open_alert, "get_alert", body={"alert_id": "A-1", "status": "OPEN"})
    assert open_alert.decided is None and _ran(open_alert, "get_order_events").cancel_tool is False

    draft = InvestigationGuard(alert_id="A-1", mode="draft_stor")
    _ran(draft, "get_alert", body={"alert_id": "A-1", "status": "ESCALATED"})
    assert draft.decided is None
    assert _ran(draft, "draft_stor_narrative", body={"alert_id": "A-1", "stor_fields": {}}).cancel_tool is False


def test_payload_flag_reads_strings():
    import main

    assert main._flag(None) is True and main._flag(True) is True and main._flag(False) is False
    assert main._flag("false") is False and main._flag("off") is False and main._flag("0") is False
    assert main._flag("true") is True and main._flag("on") is True


def test_prompt_and_standard_say_which_record_governs_a_large_order():
    """The model never sees the tool's output-schema descriptions (Strands sends name, description and input schema
    to Bedrock), so what `large_orders` means has to be said where it does read: the prompt's line on reading the
    discriminators, the tool description, and the firm's closure standard."""
    from prompt import system_prompt

    from tools.procedures import PROCEDURES
    from tools.schema import TOOLS

    assert "when `large_orders` is not empty, each entry is one large order measured on its own" in system_prompt()
    closure = PROCEDURES["closure_standard"]
    assert "both features are decided on that order's own record" in closure
    assert "executed_qty_before_opposite_trade" in closure and "do not make it a quote" in closure
    assert "round_trip_ticks" in closure and "is not a figure for that order" in closure
    escalation = PROCEDURES["escalation_standard"]  # the caught-in-the-book test, read on the order's own record
    assert "this test is read on that order's own record" in escalation
    assert "executed_qty_after_opposite_trade > 0" in escalation
    assert (
        "first cancel or size reduction" in system_prompt()
        and "`round_trip_ticks` stays a window total" in system_prompt()
    )
    description = next(t for t in TOOLS if t["name"] == "compute_discriminators")["description"]
    assert "`large_orders` gives that order's own facts" in description and "says nothing about layering" in description


def test_prompt_passes_the_alert_id_to_the_market_and_history_tools():
    from prompt import system_prompt

    p = system_prompt()
    assert "get_market_events` (pass the alert_id" in p
    assert "get_trader_alert_history` (pass the trader_id and the alert_id" in p
