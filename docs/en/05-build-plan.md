# 05 - Build plan

Phases are ordered so that each ends with something demoable and so that AWS cost arrives as late as possible. Phases 0-1 cost nothing on AWS. Tick milestones here and update `STATUS.md` when a phase changes.

## Phase 0 - Setup and verification (no AWS cost)

Goal: know the toolchain works and that every AgentCore feature we plan to use exists in eu-west-2 today.

- [x] `uv python pin 3.14` (system Python 3.14.2), `pyproject.toml` with strands-agents, strands-agents-tools, bedrock-agentcore, boto3, pandas, pyarrow, numpy, pydantic; dev group ruff, pytest, mypy. `uv sync` resolves and imports on 3.14.2 (2026-11-02: strands-agents 1.63.0, bedrock-agentcore 1.25.2, boto3 1.43.123, pandas 3.1.0, pyarrow 26.0.0). Deployment targets match: Lambda runtime `python3.14` is GA and AgentCore Runtime accepts `PYTHON_3_14`.
- [x] Install the `agentcore` CLI (Node): `npm install -g @aws/agentcore`, version 1.0.1. `agentcore add` covers runtime, runtime-endpoint, gateway, gateway-target, gateway-connector, policy-engine, policy, credentials, memory, evaluator, online-eval, config-bundle, payment-manager. Recorded in `agentcore-gotchas.md`.
- [x] Verify availability in eu-west-2 (London): read-only `list-*` calls on `bedrock-agentcore-control` succeed for agent runtimes, gateways, memories, policy engines, code interpreters, evaluators and browsers (2026-11-02). Temporal policy behaviour is verified against the docs; a live check happens in Phase 4.
- [x] Bedrock model access: `eu.anthropic.claude-haiku-5-5` (dev loops) and `eu.anthropic.claude-sonnet-5-5` (default agent) both answer a one-token `converse` call from eu-west-2 (2026-11-02); `eu.anthropic.claude-opus-5-5` is listed and is the Phase 5 comparison arm and rationale judge. The `eu.` inference profiles route across seven EU regions including London.
- [x] Read Delegated Regulation (EU) 2026/788 (OJ text via the Publications Office; EUR-Lex itself is behind a bot challenge) and the ESMA STOR report (2026-11-02). Primer section 3.2 has the EEA STOR denominator and section 4.1 the exact Annex II changes; spoofing wording is substantively unchanged, time frames and volume indicators are new.
- [x] Decide: CDK Python for the mock back end in its own stack (`infra/`), `agentcore.json` (AgentCore CLI project) for Runtime, Gateway, targets, Policy Engine, Memory and evaluators. Logged in `decision-log.md`.

Exit (reached 2026-11-02): `STATUS.md` says Phase 1; gotchas file has dated "verified" sections for the CLI, Optimization and the eu-west-2 control-plane checks.

## Phase 1 - Simulator, detector, labelled dataset (no AWS cost)

Goal: a reproducible dataset of alerts with ground truth, runnable locally.

- [x] `src/market_sim/`: order book with price-time priority, self-trade prevention, iceberg and pegged orders, pre-event BBO on the tape; discrete-event kernel; background market with 2 market makers, 12 noise traders, 3 value traders, an agency desk, an algo desk and 3 institutional counterparties; `order_events`, `trades`, `traders`, `market_events`, `instrument_stats` as parquet. One session day in 0.6 s. (2026-11-02)
- [x] Scenario injection for all 6 S- and 9 F- scenarios (`src/market_sim/scenarios.py`), every one verified to trip the detector; `manifest.json` with seed, generator and detector versions, parameters, counts. (2026-11-02)
- [x] `src/detector/`: two-trigger noisy rule (`rule.py`, K tuned to 3.25), label attribution (`labels.py`), threshold baseline (`baseline.py`); writes `alerts`. (2026-11-02)
- [x] `src/tools/discriminators.py`: 27 deterministic fields as a pure function, unit-tested on hand-built tapes (same code the Lambda will call). (2026-11-02)
- [x] Threshold baseline and its results: raw safe close 96% but gate failed on 6 of 7 S-SPOOF-5 alerts, so reported n/a. Recorded in `data/synthetic/seed7/report.md`. (2026-11-02)
- [x] Hand-check 10-15 alerts with George: 17 alerts over three rounds (2026-11-02). Round 1 found F-SPOOFLIKE-HARD-1 buying instead of selling and `reversion_ticks` counting the trader's own market impact; round 2 found F-ICE-1 without executions on the iceberg and desk profiles whose typical size did not match their quotes. All fixed in the generator or the metrics, labels unchanged. Round 3 re-read one alert of each of the five changed scenarios on the rebuilt dataset: all five match their labels (data doc section 2.4).
- [x] Book-replay script `scripts/replay_alert.py`: the trader's events around the window with pre-event BBO, the discriminators, the baseline's decision and (with `--reveal`) the label. (2026-11-02)
- [x] 23 unit and end-to-end tests (`uv run pytest`); `ruff check` and `ruff format` clean.

Exit (reached 2026-11-02): `uv run scripts/build_dataset.py --seed 7 --sessions 20` produces 167 alerts in 15 s (28 TRUE_ABUSE = 17%, 87 injected false positives, 52 background market-maker alerts); detector recall on injected abuse 100%, precision 17%; baseline results table exists and fails the gate on S-SPOOF-5 only; 17 alerts hand-checked over three rounds.

Demo moment: show an injected spoof and a market-maker false positive in the book replay side by side.

## Phase 2 - Back end and Gateway (small AWS cost)

Goal: the tools exist as Lambdas behind an AgentCore Gateway with Cognito auth, callable from an MCP client.

- [x] CDK app under `infra/` (`app.py`, `surv_firm/stack.py`, synthesizes clean): eight DynamoDB tables, S3 bucket, one Lambda for all Gateway tools (`surv-gateway-tools`, Python 3.14 arm64, pandas+numpy layer from `infra/build_layer.sh`), the human-path Lambda behind an HTTP API with a Cognito JWT authoriser, user pool with groups L1/L2 and two users. Tags `Project` and `auto-delete=no` on the whole app.
- [x] Loader script `scripts/load_dynamodb.py` (dataset parquet -> DynamoDB; labels never loaded; dry run counts 1,961,720 items for seed7). Key construction in `src/tools/ddb_items.py`.
- [x] Tests: `src/tools/tests/test_gateway_tools.py` runs every tool against a moto DynamoDB loaded through the same `ddb_items`; the discriminators computed through DynamoDB equal the label-side values for a true-abuse alert, and the proposal path never sets `recorded_disposition`. 30 tests pass.
- [x] `scripts/check_tags.py`: lists every project resource (Tagging API plus AgentCore control plane) and flags missing `auto-delete=no`; `--fix` adds them.
- [x] `cdk bootstrap` and `cdk deploy SurvFirm` in eu-west-2 (75 s, 44 resources); Cognito passwords set with `admin-set-user-password --permanent`, kept in `~/.config/surv-investigator/`; seed7 loaded (1,961,720 items, ~12 min at 2,500-3,500 items/s after shuffling items across `by_date` partitions).
- [x] Gateway `surv-investigator` via `agentcore add gateway` + `agentcore add gateway-target` + `agentcore deploy` (stack `AgentCore-surv-default`); target `surv` is the Lambda with the 11 inline schemas from `surv-tools.json` (exported by `src/tools/schema.py`); inbound `CUSTOM_JWT` with `allowedClients` = the analyst UI client; the Gateway role may invoke only `surv-gateway-tools`.
- [x] Smoke test `scripts/smoke_gateway.py` (MCP streamable HTTP, Cognito access token as L1): `tools/list` returns 11 `surv___*` tools; `get_alert`, `compute_discriminators` (3.6 s cold), `get_trader_profile`, `get_instrument_stats`, `get_procedures` all answer; the 13 scalar discriminators for A-261006-0006 equal the label-side values; no token and a forged token both get 401.
- [x] Per-user rate limits on the Gateway: `per-analyst-requests` (60/min on `$.context.jwt.sub`) and `per-analyst-writes` (3/min per analyst on `propose_disposition` and `draft_stor_narrative`), declared as `CfnGatewayRateLimit` in the AgentCore stack. Verified: `rate: 0` blocks, `toolName` and `$.context.jwt.sub` both resolve, burst allowance of 15-20 calls measured at 1/min (design doc section 8).

Exit: all read tools and `propose_disposition` callable through the Gateway; `record_disposition` callable only from the human path.

Cost note (Pricing API, Europe (London), 2026-11-03): DynamoDB on-demand writes $0.7423 per million WRU, reads $0.1487 per million RRU, storage $0.29715 per GB-month after the first 25 GB. Loading seed7 is about 1.96 M items plus the `by_date` index copy of 1.82 M order events, roughly 3.9 M WRU, so about $3 once; storage is inside the free 25 GB. Lambda, Cognito Essentials and the HTTP API are inside the free tier at demo volume. Gateway pricing to be checked on the pricing page and noted in `STATUS.md`.

## Phase 3 - Agent on Runtime (small AWS cost)

Goal: the Strands agent investigates one alert end to end, locally first, then on Runtime.

- [x] `app/surv_investigator_l1/` (the CLI's convention, see decision log): `report.py` (strict InvestigationReport), `prompt.py` (system prompt as data; the procedures are read with `get_procedures` at the start of every run, not embedded), `investigator.py` (Strands agent, `MCPClient` to the Gateway with the analyst's token, `SequentialToolExecutor`, `InvestigationGuard` hook), `main.py` (Runtime entrypoint: payload `{alert_id, mode, instruction}`, token from the forwarded `Authorization` header). 8 tests.
- [x] Local runs through `scripts/investigate.py` (model from this machine, tools through the deployed Gateway). First four alerts: A-261006-0006 S-SPOOF-1 -> ESCALATE (match, Haiku and Sonnet); A-261005-0002 market maker -> Haiku ESCALATE at 0.6 (safe but wrong), Sonnet CLOSE_FP at 0.72 (match); A-261006-0015 S-SPOOF-5 -> ESCALATE (match: the alert the threshold baseline got wrong); A-261015-0008 F-NEWS-1 -> ESCALATE at 0.6 (safe but wrong: the model saw the news 142 ms before the cancel and still would not close). 27-57 s and 34-100k input tokens per investigation.
- [x] Deployed to Runtime `surv_default_surv_investigator_l1` (direct code deploy, Python 3.14, `opentelemetry-instrument main.py`, CUSTOM_JWT inbound with the analyst pool, `Authorization` allowlisted). `scripts/invoke_runtime.py` calls it over plain HTTPS with the analyst's token: A-261006-0006 -> ESCALATE in 35 s wall; the proposal is visible through the human-path API with the real `tool_calls`; an L1 token asking for `stor_drafting` is refused. 35 spans per run in the Runtime log group (`spans` stream), each tool call its own span, `surv.alert_id` on the agent spans.
- [x] Analyst UI `ui/analyst_app.py` (Streamlit, loopback only via `.streamlit/config.toml`; `uv run --group ui streamlit run ui/analyst_app.py`): Cognito login (the UI never stores a password), queue per session day from `GET /alerts` with case state, case view, "Investigate" button that POSTs to the Runtime with the analyst's own token and an optional instruction, run view (trajectory with timings, rejections, report, Gateway answer, closing note), trace panel reading the session's spans from CloudWatch with X-Ray trace links, record disposition (L1: CLOSE_FP/ESCALATE; L2 adds DRAFT_STOR and `stor_drafting` mode) and feedback through the human-path API. `ui/surv_client.py` holds the clients, Streamlit-free; 3 tests (`SURV_UI_LIVE=1` logs in for real).
- [x] Demo alerts A/B/C run end to end through the UI's client on the Runtime as `l1.analyst` (2026-11-03): A `A-261006-0006` S-SPOOF-1 -> ESCALATE 0.70 (match, 35 s); B `A-261005-0003` F-MM-1 -> CLOSE_FP 0.85 (match, 29 s, 72k input tokens for a two-sided quoting tape), recorded CLOSE_FP by L1; C `A-261016-0003` F-NEWS-1 -> ESCALATE 0.70 (safe miss; news 187 ms before the cancel and 6 market-wide cancels seen, still escalated), recorded CLOSE_FP by L1 as an **override** with the note on the record. Both F-NEWS-1 alerts tried so far escalated: a candidate for the first Memory/feedback demonstration and a prompt revision in Phase 4.

Exit: demo steps 1-4 work (step 3's `memory_used` waits for Memory in Phase 4; today the report cites the two prior closures through `get_trader_alert_history`). Runtime sessions end with each invocation. **Phase 3 complete 2026-11-03.**

## Phase 4 - Policy and Memory (small AWS cost)

Goal: the deterministic controls and the learning loop.

- [x] Policy Engine `investigator_pe` declared in `agentcore.json`, attached to the Gateway; nine statements in `policies/` (01-08, with 03 split in two because a policy may hold at most three temporal operators). Gateway role granted `GetWorkloadAccessToken`; Gateway vended logs and traces delivered to CloudWatch (`CfnDeliverySource/Destination/Delivery` in the AgentCore CDK stack). Engine mode `ENFORCE` since 2026-11-04: `LOG_ONLY` records no `::response` events, so every response-dependent rule denied under it (decision log). `scripts/validate_policies.py` prints the service's findings per statement.
- [x] Demo steps 5 and 6 reproducible with `scripts/policy_demo.py`: proposal before evidence denied (03b), CLOSE_FP without history denied (04), allowed after history, second proposal denied (06), STOR draft as L1 denied (07), `record_disposition` absent from `tools/list`. Sonnet itself ignores a "just close this quickly" instruction and runs the full procedure, so the scripted client is what shows the denial. Agent on Runtime v6 (policy session header) runs clean under `ENFORCE`: A-261006-0006 ESCALATE, A-261006-0015 ESCALATE, A-261005-0003 CLOSE_FP.
- [x] Memory `investigator_memory` (SEMANTIC strategy, `/traders/{actorId}/notes/`) declared in `agentcore.json`; `src/tools/memory_access.py`; human path writes a direct record per disposition and per feedback (trader and desk namespaces) and a conversational event for extraction; new Gateway tool `recall_memory` (12 tools now; policies 01/02 extended; deployed in two steps because the engine validates tool names against the deployed manifest). Lambda layer now carries boto3 1.43.123 (the runtime's copy rejected `metadata` on memory records). Design §7 rewritten to what was built.
- [x] `scripts/memory_admin.py ingest-procedures` (3 records in `/procedures/`), `seed-history` (18 prior dispositions, fanned out to 36 trader+desk records), `list`, `delete`.
- [x] Demo B through the Runtime (v8): `memory_used` cites the desk's prior closures, "same explanation holds on today's tape", CLOSE_FP 0.85.
- [x] Demo step 7: feedback on D `A-261016-0003` (recorded as an L1 override) -> E `A-261023-0001`, same desk a week later, cites it in `memory_used` and proposes CLOSE_FP 0.65. Needed one change to the firm's procedures, not the prompt: the closure standard now says how an accepted explanation accounts for feature (a) and that feature (b) is a benefit (favourable move with reversion, or positive round trip), not any opposite-side execution. Regression: S-SPOOF-1 x2, S-SPOOF-2, S-SPOOF-5, S-LAYER-1 still ESCALATE.

Exit: demo steps 5-7 work; policy decision logs visible; memory influence and an analyst correction visible in a report. **Phase 4 complete 2026-11-05.**

Verification sweep before Phase 5 (2026-11-05), the paths that had never run end to end: (1) L2 path: `policy_demo.py --user L2 --stor` shows 05 and 07 *permitting* (12 tools visible to L2, DRAFT_STOR proposal allowed, `draft_stor_narrative` allowed and returns STOR fields); the agent itself on S-SPOOF-2 chose ESCALATE over DRAFT_STOR because no numeric benefit shows on that scenario (repetition is its tell), a Phase 5 item. (2) `POST /disposition` after the Memory change: case, `cases_history`, alert status, and Memory records under the trader and the desk all written; read back through `get_trader_alert_history` and `recall_memory`. (3) Guard recovery from a Gateway denial: unit test (a denied proposal is released, the retry is not blocked by the one-proposal rule). (4) Policy 08 headroom: the largest alert window holds 320 events, one page; the cap of 6 pulls is seven times that. (5) Fresh `git clone` + `uv sync --all-groups` + `pytest`: 41 pass, dataset present, replay works.

## Phase 5 - Evaluation harness and learning loop (moderate AWS cost: two or three full dataset runs on a Sonnet-class model)

Goal: the metric table, and evidence that the agent improves in a governed way.

- [x] `evals/run_dataset.py` (invoke as the analyst, proposal read from `surv-cases`, metrics in `evals/metrics.py` with tests against the Phase 1 baseline numbers, baselines, regression report, `--resume`/`--rescore`), `evals/ground_truth.py` (`expected_response`, assertions and the `surv___`-prefixed trajectory per alert; `evals/ground_truth/seed7.json` in the SDK's dataset schema), `evals/evaluate_sessions.py` (scores the run's sessions with the built-in evaluators and the rubric through `EvaluationClient.run`), `evals/faithfulness.py` (numbers in `evidence[].fact` vs the session's tool-result spans). Pilot of six alerts, then the full run (2026-11-05). Data doc section 4.6.
- [x] Custom evaluator `surv_rationale_rubric` (trace level, Opus 5.5 judge, single 0-1 scale, no ground truth so it can run online and in A/B tests; created with `create_evaluator` from `evals/evaluators/rationale_rubric.json` via `evals/evaluators.py`, tagged). On the pilot it scored a correctly closed F-ALGO-1 at 0.25 for an unsupported "spread capture" claim: it reads the reasoning, not the label.
- [x] Full run `20261105T1238-sonnet-v1` on seed7 (167 alerts, 56.8 min, about $34 in model tokens): **gate holds (0 missed), safe close rate 79.9%, override rate 18.6%**, escalation precision 50%, evidence faithfulness 99.8% of 4,550 numbers; threshold baseline fails the gate (6 S-SPOOF-5), escalate-everything closes nothing. `evals/runs/20261105T1238-sonnet-v1/results.md`.
- [ ] Per-scenario breakdown done (true abuse 100% escalated; losses F-PARTIAL-1 0/8, F-STOP-1 0/6, F-ICE-1 1/9, F-NEWS-1 1/4). Next: fill-sequencing discriminators (same-side executions before vs after the opposite trade: zero in every true-abuse alert, thousands in F-ICE-1 and F-PARTIAL-1) plus the closure standard's "genuine execution" sentence; re-run; promotion decision.
- [ ] Memory on/off run to quantify memory's effect on safe close rate, override rate, S-SPOOF-4 and F-MM-1 (data doc section 4.5.1).
- [x] `evals/ingest_overrides.py`: overrides from `cases` become rows of `labels/overrides.parquet` with truth, the analyst's note, who recorded it and the run whose proposal it overrode (or `ui`, flagged when the recording predates the current proposal). One override in the table so far (alert E).
- [ ] Optimization iteration: configuration bundle v1 from the current prompt; recommendation against the rationale evaluator; bundle v2; A/B v1 vs v2 through the Gateway on a dataset replay; offline promotion rule; decision-log entry (section 4.5.3).
- [ ] `src/detector/tune.py`: threshold re-tuning report, old vs new (section 4.5.4). Applied to the next dataset build only.
- [ ] Model-comparison arm: Opus 5.5 vs Sonnet 5.5 as a configuration-bundle change, same prompt and seed; gate, safe close rate, override rate on the hard scenarios (F-SPOOFLIKE-HARD-1, S-SPOOF-3, S-SPOOF-4), rubric, cost and latency per alert; promotion decision in the log (data doc section 4.3).

Exit: demo step 8's table exists with gate = 0 missed and an override-rate trend across at least two runs; one Optimization iteration documented end to end. If the gate fails, the table says so and the next step is the fix, not the presentation.

Cost note: one run of ~150 alerts with 8-12 tool calls each on a Sonnet-class model is the single largest cost in the project, and this phase needs two or three such runs (baseline, memory on/off, A/B). Estimate before running and record the actual in `STATUS.md`. Use Haiku-class for iteration.

## Phase 6 - Presentation

- [ ] Slides from the docs: problem (primer sections 2-3), design (architecture), demo, evaluation, honest limitations, next steps.
- [ ] Pin a `demo` Runtime endpoint to the evaluated version.
- [ ] Rehearse the demo script with timings; prepare answers to the anticipated questions.
- [ ] Greek and English versions of the deck if the mentor prefers Greek.

## Stretch (after Phase 6)

- ABIDES background flow with our scenario injection on top.
- L2 reviewer agent over A2A that challenges the L1 report.
- Online evaluation on live traffic with a second Optimization iteration.
- Thin sanctions plug-in reusing the core.

## Cost rules (all phases)

- eu-west-2 only; tag `Project=agentcore-surveillance-investigator`.
- Stop Runtime and Code Interpreter sessions after every run.
- Haiku 5.5 for development; Sonnet 5.5 as the default agent for demo and evaluation runs; Opus 5.5 only for the Phase 5 model-comparison arm and as the rationale judge. Rough list prices: Haiku $0.10/$0.50, Sonnet $2/$10, Opus $4/$20 per million tokens in/out, so a 150-alert run is about $22 on Sonnet and $45 on Opus [unverified against the Bedrock pricing page].
- Record every billable resource in `STATUS.md` with a cost note; delete everything after the presentation except the code and the docs.
