# 03 - Solution design

## 1. Architecture

```
                     ┌──────────────────────────────────────────────────────────────┐
                     │                      "The firm" (mock back end, CDK)          │
                     │  DynamoDB: alerts, order_events, trades, traders, events,     │
                     │            cases, dispositions                                │
                     │  S3: synthetic market data (parquet), reports                 │
                     │  Lambda: one function per tool (src/tools/)                   │
                     │  Cognito: user pool, groups L1 and L2                         │
                     └───────────────▲──────────────────────────────▲───────────────┘
                                     │ invoke (Gateway IAM role)    │ invoke (direct, human path)
                     ┌───────────────┴───────────────┐    ┌─────────┴────────────────────┐
                     │  AgentCore Gateway            │    │  Analyst UI (Streamlit/CLI)  │
                     │  target "surv" -> MCP tools   │    │  Cognito login as L1 or L2   │
                     │  inbound: Cognito JWT         │    │  reads report, records       │
                     │  Policy Engine (ENFORCE)      │    │  disposition, sends feedback │
                     │  per-user rate limits         │    └─────────┬────────────────────┘
                     └───────────────▲───────────────┘              │ invoke agent
                                     │ MCP                          │
                     ┌───────────────┴──────────────────────────────▼───────────────┐
                     │  AgentCore Runtime: Strands agent "L1 investigator"          │
                     │  - reads alert, calls tools in evidence order                │
                     │  - Code Interpreter for ad-hoc analysis and charts           │
                     │  - Memory: trader/instrument namespaces, analyst feedback    │
                     │  - writes InvestigationReport (JSON) -> propose_disposition  │
                     └───────────────┬──────────────────────────────────────────────┘
                                     │ OTel traces + policy decision logs
                     ┌───────────────▼───────────────┐    ┌──────────────────────────────┐
                     │  AgentCore Observability      │───▶│  AgentCore Evaluations        │
                     │  (CloudWatch)                 │    │  ground truth + custom        │
                     └───────────────────────────────┘    │  evaluators; our harness      │
                                                          │  computes the gate + metric   │
                                                          └──────────────────────────────┘
```

Two paths touch the back end. The agent path goes through the Gateway, where Policy decides on every call. The human path goes from the analyst UI to a small set of Lambdas (record disposition, send feedback) with the analyst's Cognito identity, and never through the agent. The tool `record_disposition` is deliberately not registered as a Gateway target tool at all, so the agent cannot discover it, and a Policy rule forbids it anyway in case someone adds it later. Belt and braces.

## 2. AgentCore services and why each one

| Service | Role here | Why this primitive |
|---|---|---|
| **Runtime** | Hosts the Strands agent as an HTTP agent; one session per alert investigation. | Isolated microVM per session gives per-alert isolation; versions and endpoints let us pin a `demo` endpoint. |
| **Gateway** | Turns the tool Lambdas into MCP tools under target `surv`; enforces inbound JWT; applies per-user rate limits; attaches the Policy Engine. | Single choke point for every agent action. Without it, Policy has nothing to intercept. |
| **Identity** | Cognito user pool as inbound JWT provider; groups `L1`, `L2`; agent workload identity. | Lets policies and rate limits key on *who* is driving the agent, and lets the human path carry a different identity from the agent path. |
| **Policy** | Deny-by-default Cedar/Dogwood rules: which tools, in what order, how many times, never `record_disposition`. | Deterministic control outside the prompt. The temporal rules (evidence before conclusion) are the demo's strongest moment. |
| **Memory** | Episodic and semantic records per trader and instrument: past dispositions, analyst corrections, firm procedures text. | The agent should know "this trader is a registered market maker and the last six alerts were closed for that reason" without being told each time, and should learn from overrides. |
| **Code Interpreter** | Ad-hoc computation and charts for the report (price path with order placements and cancels overlaid). | Keeps arbitrary code off the Runtime and out of the Lambdas; the deterministic metrics stay in Lambda for reproducibility. |
| **Observability** | OTel traces of every step; policy decision logs. | This *is* the record-keeping requirement. |
| **Evaluations** | Ground-truth evaluators (expected disposition, assertions, tool trajectory) and a custom evaluator for rationale quality; on-demand runs over the labelled dataset. | Regression gate before any prompt or tool change. |
| **Optimization** | Recommendations for the system prompt and tool descriptions generated from traces against our rationale evaluator; versioned configuration bundles; A/B test of a candidate bundle through the Gateway; promotion only if the deterministic gate holds. | The governed answer to "does it get better?": measured, versioned, human-approved changes, never silent drift. See section 11. |
| Registry, A2A (stretch) | Publish the agent; L2 reviewer agent. | Only if the core is done. |

## 3. Data model (synthetic)

All ids are synthetic. Timestamps are integer nanoseconds since the epoch in the simulator and in parquet; the loader keeps them as integers in DynamoDB (so range queries on the sort key work) and every tool adds a `time` field (`HH:MM:SS.mmm`) next to each `ts` for the agent and the reader. Prices are integer ticks (`price_ticks`, tick size in `instrument_stats`). Every table carries a `date` column (one simulated session day).

**DynamoDB keys** (`src/tools/ddb_items.py` builds them, `src/tools/data_access.py` queries by them; table names are `surv-<name>` with underscores as hyphens): `order_events` pk `<trader_id>#<date>`, sk `<ts:019d>#<seq:06d>` with a GSI `by_date` (`date`, `sk`) so one query returns a trader's day and another the whole market around a timestamp; `trades` and `market_events` pk `date`, sk `<ts:019d>#<id or type>`; `traders` pk `trader_id`; `instrument_stats` pk `instrument`, sk `date`; `alerts` pk `alert_id` plus an attribute `trigger_sk` = `<trigger_ts:019d>#<alert_id>` for the GSI `by_date` that feeds the analyst's queue; `cases_history` pk `trader_id`, sk `<date>#<alert_id>`; `cases` pk `alert_id` with a GSI `by_trader` (`trader_id`, `proposed_at`). `seq` is the event's position within its day after a stable sort by `ts`, so two events in the same nanosecond keep the simulator's order. Zero-padding `ts` to 19 digits makes string comparison equal numeric comparison. NaN and None attributes are dropped at load time.

| Table / object | Key fields | Notes |
|---|---|---|
| `order_events` | `instrument`, `date`, `ts`, `order_id`, `trader_id`, `event` (NEW, MODIFY, CANCEL, FILL, PARTIAL_FILL), `side`, `price_ticks`, `qty`, `remaining_qty`, `order_type` (LIMIT, MARKET, PEGGED, ICEBERG), `parent_order_id`, `best_bid`, `best_ask` | Full lifecycle. `qty` is the quantity the event concerns: NEW = order size, FILL/PARTIAL_FILL = executed, CANCEL = removed, MODIFY = signed delta (negative = reduction); `remaining_qty` is the open quantity after the event. `best_bid`/`best_ask` are the touch immediately *before* the event, as a drop copy would carry it; they let the tools compute distance from the touch without replaying the book. |
| `trades` | `instrument`, `date`, `ts`, `trade_id`, `buy_order_id`, `sell_order_id`, `buy_trader_id`, `sell_trader_id`, `price_ticks`, `qty`, `aggressor_side` | Derived from fills; kept separately for convenience. |
| `traders` | `trader_id`, `name` (synthetic), `desk`, `role` (MARKET_MAKER, PROP, AGENCY, CLIENT, ALGO), `registered_mm_instruments` (JSON list), `typical_order_size`, `typical_daily_otr`, `risk_limit_events` (JSON list of `ts`, `instrument`, `reason`) | The profile an analyst would look up. Background traders get typical size and OTR from their own tape across the dataset; scenario traders carry the profile their scenario assigned. |
| `market_events` | `date`, `ts`, `instrument` or `*`, `type` (NEWS, MACRO_PRINT, HALT, AUCTION, OPEN, CLOSE), `description` | Public events that explain many participants acting at once. |
| `instrument_stats` | `instrument`, `date`, `adv`, `n_trades`, `avg_spread_ticks`, `avg_depth_top5`, `tick_size`, `open_ticks`, `close_ticks` | Normalisers for "large" and "far from the touch"; sampled every 10 s during the session. |
| `alerts` | `alert_id`, `date`, `scenario` (SPOOFING, LAYERING), `instrument`, `trader_id`, `trigger` (OPPOSITE_FILL_CANCEL, LARGE_QUICK_CANCEL), `trigger_ts`, `window_start`, `window_end`, `trigger_summary`, `detector_version`, `detector_params` (JSON), `status` (OPEN, IN_REVIEW, CLOSED, ESCALATED) | Output of `src/detector/`. Ids look like `A-261005-0002`. |
| `cases_history` | `alert_id`, `trader_id`, `instrument`, `date`, `scenario`, `proposed_disposition`, `recorded_disposition`, `recorded_by`, `analyst_note`, `override` | Prior dispositions from before the dataset's first day: six CLOSE_FP for the S-SPOOF-4 trader (the memory trap) and two benign ones for each background market maker and algo desk. Read by `get_trader_alert_history` and seeded into Memory. |
| `labels` (not visible to the agent) | `alert_id`, `truth` (TRUE_ABUSE, FALSE_POSITIVE), `injected_scenario` (catalogue id or BACKGROUND), `expected_disposition`, `key_discriminators`, `expected_tools`, `notes`, `trader_role` | Ground truth for evaluation only. Lives in `<dataset>/labels/` next to `injections`, `discriminators` and `baseline`; never loaded into anything the Gateway can reach. |
| `cases` | `alert_id`, `case_id` (`C-<alert_id>`), `trader_id`, `date`, `scenario`, `report` (InvestigationReport JSON), `proposed_disposition`, `confidence`, `proposed_at`, `proposal_count`, `recorded_disposition`, `recorded_by`, `recorded_at`, `analyst_note`, `override` (bool), `status` (PROPOSED, CLOSED, ESCALATED), `feedback[]` (`by`, `at`, `note`) | Two writers, two disjoint sets of attributes: the Gateway Lambda `SET`s only `proposed_*`, `confidence`, `report`, `proposal_count` and the initial `status`; the human-path Lambda `SET`s `recorded_*`, `analyst_note`, `override`, `status` and appends to `feedback`, and also mirrors the decision into `cases_history` and the alert's `status`. The moto test asserts that a proposal never creates a `recorded_disposition`. |

## 4. Tool contracts (Gateway target `surv`)

All eleven tools live in **one** Lambda (`surv-gateway-tools`, `src/tools/lambda_handlers/gateway_tools.py`), each with an input and output JSON schema declared on the Gateway target (`src/tools/schema.py`, exported to the target's inline `toolSchema`). The Gateway invokes the Lambda with the tool's input properties as the event and the full tool name (`surv___get_alert`) in `context.client_context.custom['bedrockAgentCoreToolName']`; the handler strips the target prefix and dispatches. One function rather than eleven because a Gateway target maps one Lambda ARN to one tool schema and the target name is the policy prefix; least privilege is then applied at the data layer (the function may read every table and write only `surv-cases`, and it has no code path that sets a recorded disposition). Missing required inputs and unknown tools return `{"error": ...}` so the agent sees why, instead of a Lambda exception. Output fields that policies reference are marked. Tool names are what the agent sees after the Gateway prefix: `surv___get_alert` etc.

| Tool | Input | Output (policy-referenced fields in bold) | Purpose |
|---|---|---|---|
| `get_alert` | `alert_id` | **`alert_id`**, `scenario`, `instrument`, **`trader_id`**, `window_start`, `window_end`, `trigger_summary` | Start of every investigation. |
| `get_order_events` | `alert_id`, optional `pad_seconds` | **`alert_id`**, `events[]` (capped; paginates), `event_count` | Raw evidence for the window. |
| `reconstruct_book` | `alert_id`, optional `at_ts` (default: the trigger), `levels` (1-20), `sample_every_ms` | **`alert_id`**, `at_time`, `bids[]` and `asks[]` (per level: `price_ticks`, `total_qty`, `trader_qty` = the alerted trader's share), `mid_ticks`, `spread_ticks`, `bbo_path[]` (best bid, best ask and mid sampled through the window) | What the market looked like at one instant, and how the touch moved through the window. Depth is tabulated from the previous 20 minutes of tape (orders resting longer are not shown; the tool says so in `note`). |
| `compute_discriminators` | `alert_id` | **`alert_id`**, **`evidence_id`**, `window_seconds`, `dominant_side`, `gross_submitted_dominant`, `gross_submitted_other`, `otr`, `cancel_ratio`, `median_cancel_latency_ms`, `max_resting_size_vs_depth`, `distance_from_touch_ticks`, `distinct_price_levels`, `large_order_ids[]`, `same_side_fill_qty`, `opposite_side_fill_qty`, `opposite_side_fills[]` (ts, price, qty, ms before first cancel), `modify_reduction_qty`, `cancel_symmetry`, `price_move_ticks` (mid before the trader's opposite-side execution vs mid at the first large placement, + = in a spoofer's favour), `post_cancel_move_ticks` (mid 10 s after the last cancel vs the same pre-execution mid, same orientation), `reversion_ticks` (how much of a favourable pre-trade move was undone after the cancel; 0 when there was none), `round_trip_ticks` (SELL VWAP minus BUY VWAP of the trader's executions in the window; negative = he lost on the round trip), `repetitions_in_session`, `market_wide_cancels_1s_before_first_cancel` (distinct other traders cancelling in the second before his first cancel), `order_types{}`, `parent_order_ids[]`, `notes[]` | The deterministic numbers (`src/tools/discriminators.py`, pure function, unit-tested). Computed in Lambda, not by the LLM. `same_side_fill_qty` and `modify_reduction_qty` are the F-ICE/F-PARTIAL tells; `market_wide_cancels` the F-NEWS tell; `cancel_symmetry` the market-maker and algo tell; `round_trip_ticks` the F-STOP tell; `repetitions_in_session` the S-SPOOF-2 tell. |
| `get_trader_profile` | `trader_id`, optional `alert_id` (narrows `risk_limit_events_in_window` to the alert window ±5 s) | **`trader_id`**, `name`, `desk`, `role`, `registered_mm_instruments[]`, `typical_order_size`, `typical_daily_otr`, `risk_limit_events_in_window[]`, `risk_limit_events_total` | Who they are and whether cancels are their job. |
| `get_trader_alert_history` | `trader_id`, optional `lookback_days` (default 90), `before_date` (default today) | `alerts[]` with `alert_id`, `date`, `scenario`, `proposed_disposition`, `recorded_disposition`, `recorded_by`, `analyst_note`, `override`; `count` | Pattern or one-off. Merges the seeded `cases_history` with dispositions analysts recorded during this dataset's life (`cases` GSI `by_trader`), so the agent's history grows as the demo runs. |
| `get_market_events` | `instrument`, `window_start`, `window_end`, `pad_seconds` | `events[]` | External explanations. |
| `get_instrument_stats` | `instrument`, `date` | `adv`, `avg_spread_ticks`, `avg_depth_top5`, `tick_size` | Normalisers for "large" and "far from touch". |
| `get_procedures` | `topic` | `text` | The firm's written definition of spoofing and the closure standard (also ingested into Memory). |
| `propose_disposition` | `alert_id`, `disposition` (CLOSE_FP, ESCALATE, DRAFT_STOR), `confidence`, `report` (InvestigationReport) | **`alert_id`**, **`disposition`**, `case_id` | The agent's only write. Temporal policies gate it. |
| `draft_stor_narrative` | `alert_id` | `stor_fields` (description of the suspicious activity, instrument, persons involved, reasons for suspicion as the report's evidence list, indicators, period, regulatory reference), `status`, `draft_id` | Reads the stored proposal's report; refuses unless the proposal on file is `DRAFT_STOR` (the policy layer enforces the same order, this is the belt to its braces). Nothing is filed. |

**Not on the Gateway:** `record_disposition`, `send_feedback`. These are routes of the human-path Lambda (`surv-human-path`) behind an HTTP API with a Cognito JWT authoriser (section 8); the Gateway's role has no permission to invoke that function and no route reaches it.

## 5. InvestigationReport schema

The agent must produce this structure. The strict version is the pydantic model `InvestigationReport` in `app/surv_investigator_l1/report.py`; the agent's `InvestigationGuard` hook validates the report against it **before** `propose_disposition` leaves the agent (a Strands `BeforeToolCallEvent` with `cancel_tool`), and hands the validation errors back to the model as the tool result, so a malformed or inconsistent report never reaches the Gateway. The model's rules beyond shape: `evidence[].source` must be one of the tools (or `memory`); a `ruled_out` explanation must cite evidence ids that exist; a CLOSE_FP needs at least one explanation with verdict `supported`; an ESCALATE or DRAFT_STOR must carry none. `tool_calls` is not written by the model: the guard fills it from the calls it observed, so the trajectory in the report is the real one. The guard also refuses a second proposal in the same run, a proposal for another alert id, and `draft_stor_narrative` outside `stor_drafting` mode (which `main.py` grants only to tokens whose `cognito:groups` contains L2).

```json
{
  "alert_id": "A-000123",
  "scenario": "SPOOFING",
  "summary": "One paragraph an L2 can read in 30 seconds.",
  "evidence": [
    {"id": "E1", "source": "compute_discriminators", "fact": "OTR 48:1 in window vs trader typical 6:1"},
    {"id": "E2", "source": "get_trader_profile", "fact": "Trader is not a registered market maker on XYZ"},
    {"id": "E3", "source": "get_market_events", "fact": "No public events within ±60s"}
  ],
  "indicators_matched": ["orders with no intention to execute", "opposite-side fill before cancel"],
  "indicators_not_matched": ["two-sided symmetric cancels"],
  "legitimate_explanations_considered": [
    {"explanation": "market making", "ruled_out_by": ["E2"]},
    {"explanation": "news reaction", "ruled_out_by": ["E3"]}
  ],
  "proposed_disposition": "ESCALATE",
  "confidence": 0.78,
  "what_would_change_my_mind": "Evidence that the sell orders were child orders of a hedging parent.",
  "memory_used": ["prior disposition 2026-10-14 on same trader: CLOSE_FP, reason: pegged algo"],
  "tool_calls": ["get_alert", "get_order_events", "compute_discriminators", "get_trader_profile", "get_market_events"]
}
```

Rules the evaluator checks: every `fact` must be traceable to a tool output in the trace (evidence faithfulness); `legitimate_explanations_considered` must list every scenario row from the primer's table 2.3 that applies to the detector scenario; `proposed_disposition` must be consistent with the evidence (a CLOSE_FP with an unmatched legitimate explanation is a rubric failure).

## 6. Policy set
Policies live in `policies/` (one rule per file, `.cedar` for stateless Cedar, `.dw` for Dogwood temporal rules) and are declared in `agentcore/agentcore.json` under the Policy Engine `investigator_pe`, which `agentcore deploy` creates and attaches to the Gateway. Deny by default: every tool needs a `permit`, and a `permit` is also what makes a tool's completion count as a `::response` event for the temporal rules. Deployed and enforced since 2026-11-04 (engine mode `ENFORCE`; see the decision log for why `LOG_ONLY` could not be used to test these rules).

| # | Control | Rule type | File |
|---|---|---|---|
| 01 | Any authenticated analyst (`AgentCore::OAuthUser`) may call the nine read tools. | plain `permit`, `action in [...]` | `01-permit-read-tools.cedar` |
| 02 | Any action outside the eleven known tools is forbidden for everyone. A `record_disposition` tool cannot be named in a policy (the Cedar schema is generated from the Gateway's manifest, so an undeclared action is rejected at creation); the closed list is the strongest form the engine accepts, and a tool added later is denied until this list is edited. | `forbid ... unless action in [...]` | `02-forbid-unknown-tools.cedar` |
| 03a | `propose_disposition` is permitted only after `get_alert`, `get_order_events` and `compute_discriminators` have **completed** in this session for the **same `alert_id`** (`input.alert_id: context.input.alert_id`). | temporal `permit`, three `formerly within 2h ...::response` predicates (the per-policy maximum) | `03a-evidence-before-proposal.dw` |
| 03b | ... and `get_trader_profile` (same `alert_id`) and `get_market_events` have completed. A `forbid ... unless temporal` cannot be overridden by any permit. | temporal `forbid-unless` | `03b-profile-and-market-before-proposal.dw` |
| 04 | A `CLOSE_FP` proposal additionally needs a completed `get_trader_alert_history`. | `forbid ... when { context.input.disposition == "CLOSE_FP" } unless temporal {...}` | `04-history-before-close.dw` |
| 05 | `draft_stor_narrative` is permitted only after a `propose_disposition` response for the same `alert_id` with `input.disposition: "DRAFT_STOR"`. Correlates on the proposal's input, which exists whether or not outputs are declared. | temporal `permit` | `05-stor-after-proposal.dw` |
| 06 | At most one `propose_disposition` per `alert_id` per session. Matching `::response` makes the self-reference safe: the request being authorised has no response yet. | temporal `forbid` | `06-one-proposal-per-alert.dw` |
| 07 | Only principals whose `cognito:groups` claim contains `L2` may call `draft_stor_narrative`. JWT claims arrive as string tags; the array claim is the text `["L2"]`, matched with `like "*L2*"`. | `forbid ... unless { principal.hasTag(...) && principal.getTag(...) like ... }` | `07-stor-drafting-requires-l2.cedar` |
| 08 | At most 6 `get_order_events` per session (`count` includes the current request, so the seventh is denied). | temporal `forbid` with `exists (n: Long). (count ...) == n && n > 6` | `08-cap-event-pulls.dw` |

Every temporal predicate carries `eventResource: resource` (mandatory). The agent sends `x-amzn-bedrock-agentcore-policy-session-id` on every Gateway call (one investigation = one policy session, the Runtime session id when there is one), and the Gateway's role has `bedrock-agentcore:GetWorkloadAccessToken` on its workload-identity directory, without which every call fails as soon as a session header is present. Validation: `scripts/validate_policies.py` creates each statement on the live engine with `FAIL_ON_ANY_FINDINGS` and prints the service's findings; the `forbid` rules trip the engine's "overly restrictive" heuristic (it cannot see that other permits exist) and are therefore declared with `IGNORE_ALL_FINDINGS`.

Observed decisions (`scripts/policy_demo.py`, 2026-11-04, engine `ENFORCE`): a proposal before any evidence -> `DENIED by p03b` (03a also fails; the forbid is reported first); `CLOSE_FP` without history -> `DENIED by p04`; after the history -> `ALLOWED`; a second proposal -> `DENIED by p06`; `draft_stor_narrative` as L1 -> `DENIED by p07`; an L1 token's `tools/list` shows **10** tools (the Gateway's `PartiallyAuthorizeActions` hides what 07 forbids). The Gateway's refusal names the policy: `Tool Execution Denied: ... [Policy evaluation denied due to p06_one_proposal_per_alert-...]`, and the vended log group `/aws/vendedlogs/bedrock-agentcore/<gateway id>` records every evaluation (`decision`, `determiningPolicies`, `clientSuppliedPolicySessionId`, `temporal_latency_ms`, about 30-60 ms).

Session-scoped counts can be reset by starting a new session; they shape behaviour and are not a security boundary. The hard boundary is 02 plus the tool not existing on the Gateway. Gateway per-user rate limits (section 8) add a brake on volume, with a measured burst allowance of 15-20 calls, so they do not replace the count either.
## 7. Memory scheme

One Memory resource `surv_investigator_memory`, strategies: episodic (dispositions), semantic (procedures and analyst feedback), summary (per-trader summaries).

Namespaces:

- `/traders/{trader_id}/dispositions` : JSON events `{alert_id, scenario, proposed, recorded, override, analyst_note, ts}` written by the human path after each recording.
- `/traders/{trader_id}/feedback` : free-text analyst corrections ("this desk runs a pegged algo on XYZ; cancels on both sides are normal").
- `/instruments/{instrument}/notes` : instrument-specific facts (tick size changes, market-maker programmes).
- `/procedures` : ingested procedures document, retrieved semantically.

Retrieval is one of the first steps, after `get_alert` and before evidence tools, so the agent knows what to look for. The report's `memory_used` field makes memory influence visible, and Policy 03 ensures memory can never replace current-window evidence.

Risk to say out loud in the presentation: memory can entrench a wrong closure. Mitigations: overrides are stored and surfaced; the evaluation set contains a scenario where a previously "always closed" trader actually spoofs, and the gate catches it if the agent leans on memory.

## 8. Identity

- Cognito user pool with groups `L1` and `L2`; two test users.
- Gateway inbound auth `CUSTOM_JWT` with the pool's discovery URL and `allowedClients` = the `surv-analyst-ui` client id. The token presented is the Cognito **access** token: `allowedClients` is checked against the `client_id` claim, which Cognito puts in access tokens only (the id token carries the client in `aud`; `allowedAudience` would be the matching option for it). The access token also carries `cognito:groups`, which is what Policy 07 reads. The agent is invoked by the UI with the analyst's token, so the Gateway sees the analyst, not the agent, as principal.
- The Gateway's workload identity (`surv-default-surv-investigator-<id>`) is created with the Gateway. The Gateway's IAM role may invoke exactly one function, `surv-gateway-tools`; it has no path to `surv-human-path`.
- The human path is one Lambda (`surv-human-path`) behind an API Gateway HTTP API (`surv-analyst-api`) with an `HttpUserPoolAuthorizer` on every route: `GET /alerts?date=` (the day's queue joined with case state), `GET /cases/{alert_id}` (alert, proposal, report, decision), `POST /cases/{alert_id}/disposition` (`{disposition, note}`; a note is mandatory for the record), `POST /cases/{alert_id}/feedback` (`{note}`). Group membership is read from the verified JWT's `cognito:groups` claim: L1 may record `CLOSE_FP` and `ESCALATE`; only L2 may record `DRAFT_STOR` as the firm's decision. `override` is set when the recorded disposition differs from the proposed one.
- User pool `surv-analysts` (Essentials plan, no self sign-up, 12-character passwords), client `surv-analyst-ui` (no secret, USER_PASSWORD and SRP flows, 8-hour tokens), users `l1.analyst` and `l2.reviewer` created by the stack without passwords; passwords are set once with `admin-set-user-password` and never stored in the repo.
- **Gateway rate limits** (declared in `agentcore/cdk/lib/cdk-stack.ts` as `CfnGatewayRateLimit`, so they deploy with the Gateway): `per-analyst-requests`, dimension `$.context.jwt.sub` with a `*` entry, 60 requests a minute per analyst (an investigation makes 8-12 calls); `per-analyst-writes`, dimensions `toolName` + `$.context.jwt.sub`, 3 a minute per analyst for `surv___propose_disposition` and for `surv___draft_stor_narrative`. Every analyst gets independent buckets; the analyst's `sub` comes from the validated access token. Measured behaviour (2026-11-03): a throttled call reaches the MCP client as `MCPError: Rate limit exceeded`; `rate: 0` blocks at once (after the ≤30 s propagation); a limit of 1 a minute admitted 18 calls in 3.6 s before the first refusal and about 42 of 120 calls over 15 s, so request limits carry a burst allowance of roughly 15-20 calls above the stated rate and the configured rate is a sustained average, not a hard per-minute count. The limits are therefore a brake on a runaway loop, not a count of proposals; the per-alert count is Policy 05's job, and rate limits fail open when a dimension cannot be resolved (devguide, "Rate limits").

## 9. Observability as the audit record

Runtime with OTel auto-instrumentation (`opentelemetry-instrument` entry point) sends traces to CloudWatch. Policy decision logs record each permit/deny with the rule that fired. The analyst UI shows, per case, a link to the trace and the list of policy decisions. The mentor question "how would a regulator check this?" is answered by opening one trace.

## 10. Evaluation (detail in `04-synthetic-data-and-evaluation.md`)

Per alert: ground-truth `expectedResponse` (the expected disposition), `assertions` (e.g. "the report rules out market making citing the trader profile"), `expectedTrajectory` (the evidence tools in order), plus a custom evaluator with a rubric for rationale quality and evidence faithfulness. Our harness runs the dataset through `OnDemandEvaluationDatasetRunner` (or the CLI), collects per-case results, and computes the gate and the safe close rate.

## 11. Learning loop

The model's weights never change. "Learning" here means four governed mechanisms, from fastest to slowest, each measurable and each with a human in control. In a compliance control, behaviour that changes silently is a liability; behaviour that changes in versioned, evaluated steps is what a head of compliance and a regulator can accept.

| Level | Cadence | Mechanism | AgentCore part | Our part | Signal that it works |
|---|---|---|---|---|---|
| 1. Case-based recall | Every alert | After the human records a disposition, the event (proposal, decision, override flag, analyst note) is written to Memory per trader and instrument. On the next alert the agent retrieves the most similar past cases *with the analyst's reasoning* and treats them as worked examples before judging. | Memory (episodic and semantic strategies, namespaces in section 7) | Human-path Lambda writes the event; agent prompt asks for similar cases and requires `memory_used` in the report | Override rate falls for traders and instruments with history; S-SPOOF-4 still caught |
| 2. Dataset growth from overrides | Weekly | Every override (analyst changed the proposal) becomes a new labelled case with the analyst's note as the key discriminator. The evaluation set grows with the hard cases the agent got wrong. | Observability traces give the full context of the failed case | `evals/ingest_overrides.py` appends to the dataset; per-scenario breakdown shows where the agent is weak | Override rate trend; per-scenario close rate on the newly added cases |
| 3. Prompt and tool-description optimisation | Per release | Point Optimization at the traces with the rationale evaluator as target; it returns a revised system prompt or tool descriptions with an explanation. Package as a configuration bundle; A/B test against the current bundle through the Gateway; promote only if the deterministic gate and the promotion rule (data doc section 4.4) hold. | Optimization (recommendations, configuration bundles, A/B testing), Evaluations, Gateway | Promotion rule, decision-log entry with run id, rollback = route back to the previous bundle | Rationale rubric and safe close rate up on the fixed seed, gate = 0 missed |
| 4. Threshold re-tuning | Quarterly | Detector and threshold-baseline parameters (K, P, C, symmetry cut-offs) are re-estimated from the labelled dispositions. Plain statistics in our code, not AgentCore. | none | `src/detector/tune.py` with a report of old vs new thresholds and their recall/precision | Detector precision up at unchanged recall on injected abuse |

Guard-rails for the loop itself:

- The gate (zero true-abuse alerts proposed as CLOSE_FP) is deterministic code, never an LLM judge, so Optimization cannot "learn to please the judge" past it.
- Memory informs, Policy 03 ensures it cannot replace current-window evidence, and the report's `memory_used` field makes its influence auditable.
- Every behaviour change (bundle version, thresholds) is a decision-log entry with the evaluation run id. Rollback is routing traffic back to the previous bundle.
- Fine-tuning the model is out of scope: no data volume, cost, and a custom model inside a compliance control would need full model validation.

## 12. Demo script (keep current)

1. Open the analyst UI as L1 (`uv run --group ui streamlit run ui/analyst_app.py`, log in as `l1.analyst`, session day 2026-10-06). Queue of alerts from this morning's detector run, with the case state column. (30 s)
2. Pick alert A (`A-261006-0006`, S-SPOOF-1): true spoofing. Run investigation (about 35 s). Show the report: discriminators, indicators matched, explanations ruled out, proposed ESCALATE. Open the trace: tool sequence; every number in the report has a source. (3 min)
3. Pick alert B (`A-261005-0003`, F-MM-1, day 2026-10-05): registered market maker. Report rules out spoofing citing the profile and symmetric cancels; proposes CLOSE_FP; `memory_used` shows two prior closures with analyst notes. Record the disposition as L1. (2 min)
4. Pick alert C (`A-261016-0003`, F-NEWS-1, day 2026-10-16): news cancel storm. Report cites `get_market_events`; expected CLOSE_FP. Today's agent escalates it at 0.70, so this step doubles as the override demonstration: record CLOSE_FP as L1 with the note; the override flag is set and the case goes into the trader's history. (1 min)
5. Policy moment: invoke the agent with a prompt that asks it to "just close this one quickly". Show the Gateway denying `propose_disposition` because evidence tools have not returned; show the decision log line; agent recovers and does the work. (2 min)
6. Policy moment 2: show that `record_disposition` is not a tool the agent has, and the forbid rule for good measure. (30 s)
7. Learning moment: pick alert D, where the agent proposes ESCALATE on a pegged-algo desk. Record CLOSE_FP as L2 with the note "desk runs a pegged algo on this name". Run alert E, same desk, next day: `memory_used` shows the correction and the proposal is CLOSE_FP with the note cited as evidence. (2 min)
8. Evaluation table: dataset size, true cases missed = 0, safe close rate, override rate across runs, rationale rubric mean, per-scenario breakdown. One slide on the loop: Evaluations -> Optimization recommendation -> bundle -> A/B -> promotion rule. (2 min)
9. Architecture slide and "what I'd do next". (2 min)

## 13. Anticipated mentor questions

- *Does it learn on its own?* No, and it must not. The model does not change. It recalls analyst decisions (Memory), its weak spots are measured (Evaluations, override rate), prompt changes are generated and A/B tested (Optimization) and promoted only through a deterministic gate, and thresholds are re-tuned from labelled data. Every change is versioned. Section 11.

- *Why not just tune the detector?* Firms do, and it helps; thresholds are a trade-off against recall, and the regulator asks why you raised them. The investigation layer does not change recall.
- *Why not a classifier on the discriminators?* We have one, in effect: `compute_discriminators` plus thresholds. The agent adds sequencing, context, and the written argument. The evaluation compares the agent to a threshold baseline on the same dataset.
- *Isn't the LLM going to hallucinate numbers?* The numbers come from tools; the evaluator fails any report with a number not in a tool output. Show the faithfulness score.
- *What stops it from closing a real case?* Nothing stops it from *proposing* a wrong close, which is why the metric gate exists and why the human records. What stops it from *recording* one is Policy and the absence of the tool.
- *How would a regulator look at this?* Open a trace and the policy log. Point to 2016/957's record-keeping requirement.
- *Why AgentCore and not Lambda plus Bedrock?* Gateway plus Policy is the deterministic choke point; Memory, Evaluations and Observability would otherwise be built by hand. Be honest about what is thin: Code Interpreter is a convenience here, not a necessity.
- *Is the data realistic?* No; it is a simulator with injected scenarios and ground truth. Say so. ABIDES is the upgrade path; real data would come from a design partner under NDA.
- *What about the sanctions idea?* Same core, different tools. One slide.
