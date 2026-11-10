"""Build and run the Level-1 investigator: a Strands agent whose only tools are the `surv` Gateway's.

The analyst's Cognito access token is forwarded to the Gateway on every tool call, so the Gateway (and later the
Policy Engine and the rate limits) see the analyst, not the agent, as the principal.

`InvestigationGuard` is the agent's own belt before the Gateway's braces: it validates the report against the
strict `InvestigationReport` model before `propose_disposition` leaves, fills `tool_calls` from the calls it
observed (the model does not get to self-report its trajectory), refuses a second proposal in the same run, and
keeps the proposal and its result for the caller.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from prompt import TOOL_PREFIX, system_prompt
from pydantic import ValidationError
from report import InvestigationReport
from strands import Agent
from strands.hooks import AfterToolCallEvent, BeforeToolCallEvent, HookProvider, HookRegistry
from strands.models.bedrock import BedrockModel
from strands.models.model import CacheConfig
from strands.tools.executors import SequentialToolExecutor
from strands.tools.mcp import MCPClient
from strands.tools.mcp._compat import MCP_V2

# mcp 2.x (this machine) rides on `httpx2`; mcp 1.x (what the Runtime bundle resolves, 2026-11-07) on `httpx`.
# The retrying transport subclasses whichever the installed mcp uses, so the same file runs in both places.
if MCP_V2:
    import httpx2 as _httpx
else:
    import httpx as _httpx

log = logging.getLogger("surv.investigator")

DEFAULT_MODEL = "eu.anthropic.claude-sonnet-5-5"
REGION = os.environ.get("AWS_REGION", "eu-west-2")
PROPOSE = f"{TOOL_PREFIX}propose_disposition"
POLICY_SESSION_HEADER = "x-amzn-bedrock-agentcore-policy-session-id"
DRAFT_STOR = f"{TOOL_PREFIX}draft_stor_narrative"


def bundle_config() -> tuple[dict[str, Any], str]:
    """The AgentCore configuration bundle for this request, if the caller sent one (W3C `baggage` header with
    `aws.agentcore.configbundle_arn` and `_version`; the Gateway sets it during an A/B test, the evaluation harness
    sets it by hand). Returns ({}, "none") outside a Runtime request or when no bundle is referenced. Keys we read:
    `system_prompt`, `model_id`, `effort`. Any failure falls back to the code defaults and is logged."""
    try:
        from bedrock_agentcore.runtime import BedrockAgentCoreContext

        ref = BedrockAgentCoreContext.get_config_bundle_ref()
        if ref is None:
            return {}, "none"
        cfg = BedrockAgentCoreContext.get_config_bundle() or {}
        return cfg, f"{ref.bundle_id}:{ref.bundle_version}"
    except Exception as exc:  # bundle service unavailable, or not running under the Runtime app
        log.warning("config bundle unavailable, using code defaults: %s", exc)
        return {}, "error"


class RetryOn429(_httpx.AsyncHTTPTransport):
    """The Gateway's per-analyst rate limit answers 429 and the MCP client treats that as a dead connection, which
    ends the investigation with "Connection to the MCP server was closed" (6 of 167 runs on 2026-11-06). A tool
    call is idempotent at the Gateway (the policy session records the *response*, so a throttled request leaves no
    trace), so a short back-off and a retry is the right reaction. Honours Retry-After; 2, 4, 8 s otherwise."""

    RETRY_STATUS = (429, 503)

    def __init__(self, *args: Any, max_retries: int = 3, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.max_retries = max_retries

    async def handle_async_request(self, request: Any) -> Any:
        await request.aread()  # make the JSON body replayable
        for attempt in range(self.max_retries + 1):
            response = await super().handle_async_request(request)
            if response.status_code not in self.RETRY_STATUS or attempt == self.max_retries:
                return response
            await response.aclose()
            retry_after = response.headers.get("retry-after")
            delay = float(retry_after) if retry_after and retry_after.isdigit() else 2.0 * (2**attempt)
            log.warning(
                "gateway answered %s; retry %d/%d in %.0fs", response.status_code, attempt + 1, self.max_retries, delay
            )
            await asyncio.sleep(delay)
        return response  # unreachable, keeps type checkers quiet


def gateway_transport(url: str, headers: dict[str, str]):
    """Streamable-HTTP MCP transport with the retrying client. mcp 2.x takes a pre-built `httpx2.AsyncClient`;
    mcp 1.x takes an `httpx_client_factory(headers, timeout, auth)` that returns an `httpx.AsyncClient`."""
    timeout = _httpx.Timeout(30.0, read=300.0)
    if MCP_V2:
        from contextlib import asynccontextmanager

        from mcp.client.streamable_http import streamable_http_client

        @asynccontextmanager
        async def _transport():
            async with (
                _httpx.AsyncClient(headers=headers, timeout=timeout, transport=RetryOn429()) as client,
                streamable_http_client(url=url, http_client=client) as streams,
            ):
                yield streams

        return _transport()

    from mcp.client.streamable_http import streamablehttp_client

    def _factory(headers: dict[str, str] | None = None, timeout: Any = None, auth: Any = None) -> Any:
        return _httpx.AsyncClient(
            headers=headers, timeout=timeout or _httpx.Timeout(30.0, read=300.0), auth=auth, transport=RetryOn429()
        )

    return streamablehttp_client(url=url, headers=headers, httpx_client_factory=_factory)


def gateway_mcp_url() -> str:
    """The Gateway is declared with protocolType None, so its URL is a bare origin and MCP lives at /mcp."""
    url = os.environ.get("SURV_GATEWAY_URL") or os.environ.get("AGENTCORE_GATEWAY_SURV_INVESTIGATOR_URL")
    if not url:
        raise RuntimeError("SURV_GATEWAY_URL (or AGENTCORE_GATEWAY_SURV_INVESTIGATOR_URL) is not set")
    return url.rstrip("/") + ("" if url.rstrip("/").endswith("/mcp") else "/mcp")


@dataclass
class InvestigationGuard(HookProvider):
    alert_id: str
    mode: str = "investigate"
    calls: list[dict[str, Any]] = field(default_factory=list)
    proposal: dict[str, Any] | None = None
    proposal_result: dict[str, Any] | None = None
    rejections: list[str] = field(default_factory=list)
    stor_draft: dict[str, Any] | None = None

    def register_hooks(self, registry: HookRegistry, **kwargs: Any) -> None:
        registry.add_callback(BeforeToolCallEvent, self.before_tool)
        registry.add_callback(AfterToolCallEvent, self.after_tool)

    # -- before: validate what is about to leave ------------------------------------------------------
    def before_tool(self, event: BeforeToolCallEvent) -> None:
        name = event.tool_use["name"]
        inputs = event.tool_use.get("input") or {}
        self.calls.append({"tool": name.removeprefix(TOOL_PREFIX), "input": _compact(inputs), "t": time.time()})

        if name == DRAFT_STOR and self.mode != "stor_drafting":
            event.cancel_tool = "draft_stor_narrative is a Level-2 action; you are in Level-1 mode. Do not call it."
            return

        if name != PROPOSE:
            return
        if self.proposal is not None:
            event.cancel_tool = (
                "propose_disposition was already called in this investigation. One proposal per alert; "
                "finish with your summary."
            )
            return
        if inputs.get("alert_id") != self.alert_id:
            event.cancel_tool = (
                f"this investigation is for alert {self.alert_id}; the proposal names {inputs.get('alert_id')!r}."
            )
            return
        report_in = inputs.get("report") or {}
        if isinstance(report_in, str):  # Opus 5.5 sometimes passes the object JSON-encoded (5 of 167 runs, 2026-11-07)
            try:
                report_in = json.loads(report_in)
            except json.JSONDecodeError:
                report_in = None
        if not isinstance(report_in, dict):
            msg = (
                "report rejected before it reached the Gateway: `report` must be a JSON object, not a string or a list"
            )
            self.rejections.append(msg)
            event.cancel_tool = msg
            return
        raw = dict(report_in)
        raw.setdefault("alert_id", self.alert_id)
        raw["proposed_disposition"] = inputs.get("disposition")
        raw["confidence"] = inputs.get("confidence")
        raw["tool_calls"] = [
            c["tool"] for c in self.calls[:-1] if c["tool"] != "propose_disposition"
        ]  # evidence calls so far
        try:
            report = InvestigationReport.model_validate(raw)
        except ValidationError as exc:
            msg = (
                "report rejected before it reached the Gateway; fix these and call propose_disposition again:\n"
                + _explain(exc)
            )
            self.rejections.append(msg)
            event.cancel_tool = msg
            return
        gateway_report = report.for_gateway()
        event.tool_use = {**event.tool_use, "input": {**inputs, "report": gateway_report}}
        self.proposal = {
            "disposition": report.proposed_disposition,
            "confidence": report.confidence,
            "report": report.model_dump(),
        }

    # -- after: keep what came back --------------------------------------------------------------------
    def after_tool(self, event: AfterToolCallEvent) -> None:
        name = event.tool_use["name"]
        body = _result_json(event.result)
        if self.calls and self.calls[-1]["tool"] == name.removeprefix(TOOL_PREFIX):
            self.calls[-1]["ms"] = int((time.time() - self.calls[-1].pop("t")) * 1000)
            self.calls[-1]["status"] = "error" if (event.cancel_message or _is_error(event.result, body)) else "ok"
        if name == PROPOSE and self.proposal is not None:
            if event.cancel_message or _is_error(event.result, body):
                # the Gateway or a policy refused it: let the model try again with the same report
                self.proposal = None
                self.rejections.append(f"gateway refused the proposal: {event.cancel_message or body}")
            else:
                self.proposal_result = body
        if name == DRAFT_STOR and isinstance(body, dict) and "error" not in body:
            self.stor_draft = body


def _compact(inputs: dict) -> dict:
    """Tool inputs for the trace summary; the report is large and already kept separately."""
    return {k: ("<report>" if k == "report" else v) for k, v in inputs.items()}


def _explain(exc: ValidationError) -> str:
    lines = []
    for e in exc.errors():
        loc = ".".join(str(p) for p in e["loc"]) or "report"
        lines.append(f"- {loc}: {e['msg']}")
    return "\n".join(lines)


def _result_json(result: Any) -> Any:
    try:
        for block in result.get("content", []):
            if "text" in block:
                try:
                    return json.loads(block["text"])
                except json.JSONDecodeError:
                    return block["text"]
            if "json" in block:
                return block["json"]
    except Exception:  # not a ToolResult dict
        return None
    return None


def _is_error(result: Any, body: Any) -> bool:
    try:
        if result.get("status") == "error":
            return True
    except Exception:
        pass
    return isinstance(body, dict) and "error" in body


@dataclass
class InvestigationResult:
    alert_id: str
    mode: str
    model_id: str
    proposal: dict[str, Any] | None
    proposal_result: dict[str, Any] | None
    stor_draft: dict[str, Any] | None
    rejections: list[str]
    tool_calls: list[dict[str, Any]]
    final_text: str
    usage: dict[str, Any]
    duration_s: float
    session_id: str | None = None
    error: str | None = None
    bundle: str = "none"

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


def build_agent(
    *,
    alert_id: str,
    access_token: str,
    mode: str = "investigate",
    analyst: str | None = None,
    model_id: str | None = None,
    policy_session_id: str | None = None,
    memory: bool = True,
) -> tuple[Agent, InvestigationGuard, MCPClient]:
    """`policy_session_id` scopes the Gateway's temporal policies: one investigation = one policy session, so
    "evidence before proposal" and "one proposal per alert" are judged on this run's history only. The Runtime
    session id is reused when there is one, so policy session, Runtime session and trace line up."""
    cfg, bundle = bundle_config()
    model_id = cfg.get("model_id") or model_id or os.environ.get("SURV_MODEL_ID", DEFAULT_MODEL)
    policy_session_id = policy_session_id or f"surv-{alert_id}-{uuid.uuid4().hex}"
    # Claude 5.5: `temperature` is rejected; adaptive thinking is on by default (Sonnet at effort "high") and its
    # tokens count against max_tokens, so the budget must cover thinking plus the report. Effort is a tuning knob
    # for Phase 5 (A/B low vs high).
    effort = cfg.get("effort") or os.environ.get("SURV_EFFORT", "medium")
    # A bundle's system_prompt is used verbatim (that is what a bundle is for); the mode/memory variants apply only
    # to the code's own prompt. The harness uses bundles with the default mode and memory on.
    prompt_text = cfg.get("system_prompt") or system_prompt(mode, memory=memory)
    # Prompt caching (iteration 3): an investigation is ~6 model turns that each re-read the same system prompt, the
    # 12 tool definitions and every earlier tool result (77k input tokens per alert in v3). Strands places cache
    # points at the end of the system prompt, on the tool block and on the last user message, so each turn re-reads
    # the prefix from cache (5-minute TTL, 512-token minimum per checkpoint). `SURV_PROMPT_CACHE=off` is the
    # evaluation arm without it; `cacheReadInputTokens` in the usage says whether the cross-region profile hits.
    cache = None if os.environ.get("SURV_PROMPT_CACHE", "on").lower() == "off" else CacheConfig(tools_ttl=True)
    model = BedrockModel(
        model_id=model_id,
        region_name=REGION,
        max_tokens=int(os.environ.get("SURV_MAX_TOKENS", "32000")),
        additional_request_fields={"thinking": {"type": "adaptive"}, "output_config": {"effort": effort}},
        cache_config=cache,
    )
    mcp_headers = {"Authorization": f"Bearer {access_token}", POLICY_SESSION_HEADER: policy_session_id}
    mcp = MCPClient(
        lambda: gateway_transport(gateway_mcp_url(), mcp_headers),
        startup_timeout=60,
        # Memory off (evaluation arm, data doc 4.5.1): the recall tool is not offered to the model at all
        tool_filters=None if memory else {"rejected": [f"{TOOL_PREFIX}recall_memory"]},
    )
    guard = InvestigationGuard(alert_id=alert_id, mode=mode)
    agent = Agent(
        model=model,
        tools=[mcp],
        system_prompt=prompt_text,
        hooks=[guard],
        tool_executor=SequentialToolExecutor(),  # temporal policies need each response recorded before the next request
        callback_handler=None,
        trace_attributes={
            "surv.alert_id": alert_id,
            "surv.mode": mode,
            "surv.analyst": analyst or "unknown",
            "surv.model_id": model_id,
            "surv.policy_session_id": policy_session_id,
            "surv.memory": "on" if memory else "off",
            "surv.bundle": bundle,
        },
        name="surv_investigator_l1",
        description="Level-1 spoofing/layering alert investigator",
    )
    return agent, guard, mcp


def investigate(
    *,
    alert_id: str,
    access_token: str,
    mode: str = "investigate",
    analyst: str | None = None,
    model_id: str | None = None,
    session_id: str | None = None,
    extra_instruction: str | None = None,
    memory: bool = True,
) -> InvestigationResult:
    """Run one investigation to completion and return everything the caller needs to show or store."""
    t0 = time.time()
    agent, guard, _mcp = build_agent(
        alert_id=alert_id,
        access_token=access_token,
        mode=mode,
        analyst=analyst,
        model_id=model_id,
        policy_session_id=session_id,
        memory=memory,
    )
    prompt = f"Investigate alert {alert_id}."
    if mode == "stor_drafting":
        prompt += " If you propose DRAFT_STOR, draft the STOR narrative afterwards."
    if extra_instruction:
        prompt += f"\n\nAnalyst instruction: {extra_instruction}"
    error: str | None = None
    text = ""
    usage: dict[str, Any] = {}
    try:
        result = agent(prompt)  # the Agent starts the MCP client as a ToolProvider and stops it in cleanup()
        text = "".join(b.get("text", "") for b in result.message.get("content", []) if isinstance(b, dict))
        try:
            u = result.metrics.accumulated_usage
            usage = {
                # Bedrock reports cached prefix tokens separately: `input_tokens` is what was read at full price,
                # the two cache counts are what was read from / written to the cache.
                "input_tokens": u.get("inputTokens"),
                "output_tokens": u.get("outputTokens"),
                "total_tokens": u.get("totalTokens"),
                "cache_read_tokens": u.get("cacheReadInputTokens", 0),
                "cache_write_tokens": u.get("cacheWriteInputTokens", 0),
                "model_calls": len(result.metrics.cycle_durations),
            }
        except Exception:  # metrics shape changed; the run itself is fine
            pass
    except Exception as exc:  # keep the trajectory so the failure can be read
        error = f"{type(exc).__name__}: {exc}"
        log.exception("investigation of %s failed", alert_id)
        try:  # the partial assistant message is already in the history; keep its text for diagnosis
            last = agent.messages[-1]
            if last.get("role") == "assistant":
                text = "".join(b.get("text", "") for b in last.get("content", []) if isinstance(b, dict))
        except Exception:
            pass
    finally:
        agent.cleanup()
    return InvestigationResult(
        alert_id=alert_id,
        mode=mode,
        model_id=agent.model.config.get("model_id", "?") if hasattr(agent.model, "config") else "?",
        proposal=guard.proposal,
        proposal_result=guard.proposal_result,
        stor_draft=guard.stor_draft,
        rejections=guard.rejections,
        tool_calls=guard.calls,
        final_text=text,
        usage=usage,
        duration_s=round(time.time() - t0, 1),
        session_id=session_id,
        error=error,
        bundle=agent.trace_attributes.get("surv.bundle", "none") if hasattr(agent, "trace_attributes") else "none",
    )
