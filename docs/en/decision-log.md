# Decision log

Format: date, decision, alternatives considered, reason, consequences. Newest at the bottom.

## 2026-11-02 Switch the project domain from sanctions screening to trade surveillance

- **Decision:** Build the alert-investigation agent for spoofing/layering alerts in trade surveillance, not for sanctions-screening alerts in cross-border payments.
- **Alternatives:** (a) keep sanctions; (b) build both with a shared core; (c) adverse-media/KYB screening.
- **Reason:** George's AWS customers are brokers, trading firms and HFT firms, all with a surveillance obligation (MAR Art. 16(2), RTS 6 Art. 13) and few with large payment flows. Same architecture, better fit, more credible synthetic data (order events vs identity data), richer agent reasoning. Building both would halve the depth of each for the TFC deadline.
- **Consequences:** Sanctions project archived at `shared/tam-work/archive/agentcore-sanctions-triage-2026-09/`. Domain primer, data model, tools, policies and evaluation all rewritten. One presentation slide keeps the sanctions plug-in as "same core, next domain".

## 2026-11-02 Scope to spoofing and layering, cash equities, one venue

- **Decision:** One abuse family, one asset class, one simulated lit order book.
- **Alternatives:** insider dealing (needs news and non-public information, hard to simulate credibly); wash trades (simpler, less agent reasoning); multi-venue (realistic but doubles the data model).
- **Reason:** Spoofing lives entirely in order and trade events, so synthetic ground truth is credible, and its false positives (market making, algos, risk cuts, news) need real multi-step reasoning. Depth over breadth for the demo and the evaluation.
- **Consequences:** Other abuse types described in the primer only.

## 2026-11-02 The agent proposes; a human records; enforced by Policy and by tool absence

- **Decision:** `record_disposition` is not a Gateway tool; a `forbid` rule covers it anyway; `propose_disposition` is gated by temporal prerequisites.
- **Alternatives:** let the agent auto-close low-risk alerts under a policy cap (the earlier sanctions design did this for payments).
- **Reason:** 2016/957 expects human analysis by trained staff; compliance buyers will not accept autonomous closure; and the demo's strongest moment is the Gateway denying the agent. Autonomy adds risk without adding learning value here.
- **Consequences:** The metric is about proposals, not actions. The human path needs its own UI and identity.

## 2026-11-02 Deterministic metrics in Lambda, LLM for sequencing and writing

- **Decision:** `compute_discriminators` is code with unit tests; the LLM never computes the numbers.
- **Alternatives:** let the agent compute metrics in Code Interpreter from raw events.
- **Reason:** Reproducibility and auditability; evidence faithfulness is checkable only if the numbers have a deterministic source. Code Interpreter remains for ad-hoc analysis and charts.
- **Consequences:** Code Interpreter's role is thin; say so in the presentation.

## 2026-11-02 Primary metric: safe close rate at 100% recall on true abuse

- **Decision:** Report the share of false positives proposed for closure only when zero true-abuse alerts were proposed for closure; otherwise report "n/a (gate failed)".
- **Alternatives:** accuracy, F1, AUC on a confidence score.
- **Reason:** The business asymmetry: a missed spoofer costs more than any efficiency gain. Accuracy hides this.
- **Consequences:** The harness, not AgentCore Evaluations, computes the aggregate; Evaluations provides per-case scores. Both are reported.

## 2026-11-02 Own simulator first, ABIDES as stretch

- **Decision:** Write a small LOB simulator with scenario injection; consider ABIDES only after the core is evaluated.
- **Alternatives:** ABIDES from the start.
- **Reason:** ABIDES is a research codebase with its own learning curve and dependencies; the project's value is in the agent and the governance, not in market realism. Scenario injection with known labels is simpler on our own simulator.
- **Consequences:** Realism is limited and must be stated in the presentation.

## 2026-11-02 Bilingual documentation, English canonical

- **Decision:** `docs/en/` canonical, `docs/el/` twin with identical structure; technical terms kept in English inside Greek text.
- **Alternatives:** Greek only; English only; mixed-language single docs.
- **Reason:** George learns the domain in Greek; the mentor and any future design partner read English; identical structure keeps them in sync.
- **Consequences:** Every edit is doubled; the docs-sync hook and `docs-maintenance.md` enforce it.

## 2026-11-02 Steering rule: challenge and verify

- **Decision:** Added `.kiro/steering/challenge-and-verify.md` requiring Kiro to treat George's claims as hypotheses, verify from primary sources, and state counter-arguments before agreeing.
- **Reason:** George asked for it explicitly; he is learning the domain and wants calibration, not confirmation.
- **Consequences:** Verification markers `[verified ...]` / `[unverified]` throughout the docs; unverified claims must be checked before the presentation.

## 2026-11-02 Correction: Policy and Evaluations are listed as services, not preview

- **What was said earlier (in chat):** "Policy and Evaluations were announced recently as preview; check availability."
- **What the source says:** The devguide overview (fetched 2026-11-02) lists Policy, Evaluations, Optimization and Registry as services alongside Runtime and Gateway, with no preview flag on that page. Regional availability still needs a per-service check in eu-west-2 (Phase 0).

## 2026-11-02 Hooks enforce bilingual doc updates on every code or architecture change

- **Decision:** Two hooks in `.kiro/hooks/docs-sync.json`: a PostToolUse nudge (`docs-twin-nudge.py`) that, after every file write, names the documents to update in both `docs/en` and `docs/el`; and a Stop check (`docs-sync-check.py`) that verifies source-vs-docs freshness and EN/EL parity (file presence, Greek not older than English, same counts of headings, table rows, checkboxes and code fences).
- **Alternatives:** (a) Stop hook only (the earlier bash script); (b) a hook that rewrites the Greek file automatically with a translation call; (c) relying on the steering rule alone.
- **Reason:** George asked for automatic updates of both language versions whenever code or architecture changes. Kiro hooks cannot edit files, but a PostToolUse message makes the agent act within the same turn, and the Stop check catches what was missed. Option (b) would hide translation quality from review and cost tokens on every save. Option (c) depends on memory.
- **Consequences:** Every source edit produces a doc edit in two languages in the same turn, or an explicit one-line "no change needed" plus a marker touch. The structural parity check is cheap and can be fooled by a lazy translation; content fidelity remains the agent's responsibility.

## 2026-11-02 IaC: CDK Python for the mock back end, `agentcore.json` for AgentCore resources, no Terraform

- **Decision:** Two deployable units. (1) `infra/`: a CDK Python app for "the firm" (DynamoDB, S3, tool Lambdas, Cognito user pool, human-path Lambdas), outputs Lambda ARNs and the Cognito discovery URL. (2) An AgentCore CLI project (`agentcore.json`) for Runtime, Gateway with Lambda targets referencing those ARNs, Policy Engine and policies, Memory, evaluators and configuration bundles. Deploy order: infra first, then `agentcore deploy`.
- **Alternatives:** (a) one stack by adding the firm's resources to the CLI's generated TypeScript CDK stack (`agentcore/cdk/lib/cdk-stack.ts`, construct `AgentCoreApplication` from `@aws/agentcore-cdk`); (b) Terraform for everything; (c) CDK Python for everything including AgentCore resources via CloudFormation.
- **Reason:** The CLI is the paved path for AgentCore resources and the dev loop (`agentcore dev`, `agentcore add policy-engine --attach-to-gateways ... --attach-mode log-only`, `agentcore add gateway-target --target-configuration '{"targetType":"lambdaFunctionArn", ...}'`) [verified 2026-11-02, devguide "Add a target using the CLI", "Create a policy engine", "Customize the CDK code"]. Lambda targets are declared by ARN, so the firm's stack naturally comes first. Keeping the firm in Python matches the rest of the code and George's experience. (a) would put all infra in TypeScript and rely on construct APIs we have not verified; (b) is not the paved path for the CLI dev loop and Policy support in the Terraform provider is unverified; (c) the CloudFormation resource coverage for Policy and Optimization is unverified.
- **Consequences:** Cross-stack references are ARNs passed into `agentcore.json`; a small `scripts/wire_agentcore.py` fills them from the CDK outputs. The CLI names a deployed policy engine `<project>_<target>_<name>` and the whole name must be at most 48 characters with no hyphens, so the project name is short (`surv`). The docs-sync hook watches the `agentcore/` directory.

## 2026-11-02 Learning loop: Optimization moves from stretch to Phase 5; override rate becomes a headline metric

- **Decision:** The agent improves only through four governed mechanisms (design doc section 11): case-based recall from Memory, dataset growth from analyst overrides, Optimization recommendations promoted through the deterministic gate after an A/B test, and quarterly threshold re-tuning in our code. Override rate is reported alongside the safe close rate. Fine-tuning is out of scope.
- **Alternatives:** (a) "the agent learns on its own" via Memory only; (b) fine-tuning a Bedrock model on dispositions; (c) letting Optimization auto-promote the A/B winner.
- **Reason:** George asked for an agent that gets more accurate over time. AgentCore does not change the model; it offers Memory, Evaluations and Optimization as building blocks [verified 2026-11-02, devguide "AgentCore optimization" and "How it works": recommendations, configuration bundles, A/B through Gateway, then the operator routes traffic to the winner]. In a compliance control, silent behaviour change is a liability; versioned, evaluated, human-approved change is what a head of compliance and a regulator accept. (a) cannot show improvement and can entrench errors; (b) lacks data, costs, and needs full model validation; (c) would let an LLM-judge metric drive production behaviour past the gate.
- **Consequences:** Phase 5 grows by two or three dataset runs (memory on/off, A/B) and one Optimization iteration. New demo step 7 (override then recall). Promotion rule in data doc section 4.4 also governs bundles.

## 2026-11-02 Region eu-west-2 (London) instead of us-east-1

- **Decision:** All AgentCore and supporting resources in eu-west-2. Earlier mentions of us-east-1 in the docs and steering were replaced mechanically the same day.
- **Alternatives:** (a) us-east-1 as drafted; (b) an EU region such as eu-central-1 or eu-west-1.
- **Reason:** George's choice; all AgentCore control-plane services and the `eu.` Claude inference profiles (Haiku, Sonnet and Opus 5.5) are available there [verified 2026-11-02, read-only `list-*` calls and one-token `converse` calls from eu-west-2]. The counter-argument was stated: the customers in the story are EU firms and London is UK, so (b) would match the narrative slightly better; it does not change anything for a synthetic demo.
- **Consequences:** Model ids are `eu.anthropic.claude-*`. The `eu.` profiles route inference across seven EU regions, so inference may run outside London; say so if a customer asks about residency. The AgentCore CLI project, CDK stack and deploy-guard hook all carry eu-west-2.

## 2026-11-02 Python 3.14 instead of 3.12

- **Decision:** Pin the system Python 3.14.2 (`uv python pin 3.14`, `requires-python >=3.14,<3.15`, ruff target `py314`).
- **Alternatives:** keep 3.12 as the September note recommended.
- **Reason:** George prefers the system interpreter, and the earlier reason no longer holds: every dependency installs and imports on 3.14.2 (strands-agents 1.63.0, bedrock-agentcore 1.25.2, pandas 3.1.0, pyarrow 26.0.0, numpy 2.5.4, pydantic 2.14.2), Lambda has a GA `python3.14` runtime, and AgentCore Runtime accepts `PYTHON_3_14` [verified 2026-11-02, uv sync, Lambda runtimes page, bedrock-agentcore-control API reference]. Dev and deployment versions match.
- **Consequences:** The "3.14 too new for the SDKs" claim in the gotchas file was wrong as of today and has been corrected. CDK `Runtime.PYTHON_3_14` constant to confirm in Phase 2.

## 2026-11-02 Model strategy: Sonnet 5.5 default, Opus 5.5 as a measured comparison arm and as judge

- **Decision:** Haiku 5.5 for development loops; Sonnet 5.5 as the default agent model; Opus 5.5 (a) as the judge model for the rationale rubric and (b) as a Phase 5 comparison arm on the fixed seed, same prompt, as a configuration-bundle change. Opus becomes the default only if both models hold the gate and Opus improves safe close rate or override rate on the hard scenarios beyond noise, with cost and latency per alert recorded.
- **Alternatives:** (a) Opus as default from the start; (b) Sonnet only; (c) Haiku for everything.
- **Reason:** George asked whether Opus makes sense. Cost is not the blocker it used to be: list prices Haiku $0.10/$0.50, Sonnet $2/$10, Opus $4/$20 per million tokens, so Opus is about 2x Sonnet and roughly $0.30 per alert against an analyst's several euros [prices from third-party summaries of the Anthropic rate card, Oct 2026; unverified against the Bedrock pricing page]. Where Opus could matter is the hard judgement calls and the written rationale, which is also where errors cost most. But model choice in a compliance control is a model-risk decision and needs evidence, not intuition; the harness exists for exactly this, and the result is a finding either way. Using Opus as judge keeps the judge distinct from the Sonnet agent and reduces self-preference bias.
- **Consequences:** Phase 5 gains one more full run (about $45 on Opus). If Opus wins, the demo endpoint is pinned to the Opus bundle and the rubric is treated as secondary because judge and agent then share a model; the deterministic gate and faithfulness check carry the decision.

## 2026-11-02 Detector formulation: two triggers on gross submitted size, K = 3.25, merge and cooldown

- **Decision:** `spoof-naive-v1` fires on (1) an execution on side X preceded by at least K × average top-5 depth of *gross submitted* non-market size on the other side in 60 s and followed within 5 s by cancellation of at least 70% of what was still resting, or (2) a single order of at least 6 × depth cancelled by at least 70% within 10 s with no execution required. MODIFY reductions count as cancels; market orders never count as resting size. Overlapping candidates merge into one alert with the union window; otherwise one alert per trader per 15 minutes. K = 3.25.
- **Alternatives:** (a) net resting size instead of gross submitted; (b) one trigger only; (c) K = 3 as first drafted; (d) no cooldown.
- **Reason:** (a) would make active market makers almost never fire, which is the opposite of the alert quality firms complain about; gross submitted is the classic naive measure. (b) would miss attempted spoofing with no fill (MAR Art. 15 prohibits attempts) and lose the F-FAT-1 scenario. (c) produced up to ten background market-maker alerts a day in some sessions and none in others; 3.25 gives about two a day, which keeps the TRUE_ABUSE share near 17% at the chosen mix. (d) turned one repeated spoof into six alerts; the repetition is better surfaced by `repetitions_in_session`.
- **Consequences:** Documented in data doc section 3 with the exact pseudo-code. The agent's report must state the 60 s window it was given (Delegated Regulation (EU) 2026/788 point 10 allows other frames). Parameters are stored as JSON on every alert so later re-tuning (Phase 5, `tune.py`) is traceable.

## 2026-11-02 Scenario counterparties are dedicated institutional traders

- **Decision:** Scripted third-party trades (a client hitting a quote) come from `T-INST-01..03`, who never rest orders.
- **Alternatives:** pick a random background client, as first implemented.
- **Reason:** The book has self-trade prevention (cancel-incoming). A background client chosen as counterparty sometimes had its own resting order at the touch, so the scripted market order was cancelled unfilled and the scenario silently failed to trip the detector (one F-PARTIAL-1 injection in the first build).
- **Consequences:** Every injection in the seed-7 build now produces an alert. Noted in the data doc 2.1.

## 2026-11-02 First-build finding: the threshold baseline fails the gate on the partially executed spoof

- **What happened:** The nine-rule baseline reaches a raw safe close rate of 93% but proposes CLOSE_FP for 6 of 7 S-SPOOF-5 alerts (rule R5 "the resting order was genuinely executing") and so fails the gate; by the project's reporting rule its safe close rate is n/a. It also closes none of F-SPOOFLIKE-HARD-1 and half of F-STOP-1.
- **Why it matters:** It is exactly the agent's job description: the heuristic that clears F-ICE-1 and F-PARTIAL-1 ("the order was executing, so the intent was genuine") is the one a messy spoof exploits, and only the sequence (a third party hit the order *before* the trader traded the other side, then everything was pulled) separates them. Recorded here so the Phase 5 comparison has its baseline row fixed before the agent exists.

## 2026-11-02 Hand-check round 1: two generator/metric defects found and fixed, labels kept

- **What happened:** George replayed five alerts. F-SPOOFLIKE-HARD-1's tape contradicted its label (the "inventory-shedding" market maker had bought 5,381 and sold 206, because his asks joined the queue at the touch while his bids improved it). F-STOP-1 showed `reversion_ticks` = 1.0 against a label saying "no reversion", because the metric was measured from the cancel and so counted the recovery from the trader's own market sale. Two smaller issues: scripted market orders of 1.0× depth swept the whole visible book, and `market_wide_cancels` counted cancel events, so one re-quoting market maker looked like a news storm and the baseline closed a true layering case.
- **Decision:** Fix the generator and the metrics, not the labels. Asks one tick inside and bids one tick behind the touch for the hard negative; `reversion_ticks` redefined as the undone part of a favourable pre-trade move, with `post_cancel_move_ticks` and a new `round_trip_ticks` (SELL VWAP minus BUY VWAP) alongside; market orders capped at 0.5× depth; distinct traders in the cancel-storm count; S-SPOOF-5's third-party sweep moved to just after the spoofer's trade; F-STOP-1 pulls a bid that sits at the touch before selling, since self-trade prevention otherwise blocked the sale in two sessions.
- **Alternatives:** (a) soften the labels to what the tape happened to show; (b) leave the metric and document the caveat.
- **Reason:** A label that does not describe the tape would teach the agent and the evaluator the wrong lesson, and the evaluator's assertions are written from these labels. (b) would have let a stop-out look like a spoof on one of the strongest discriminators.
- **Consequences:** Rebuilt dataset: 167 alerts, 28 TRUE_ABUSE, 0 missed injections. Baseline raw safe close 95%, gate still failed, now only on S-SPOOF-5 via R5, which sharpens the finding. 23 tests. Round 2 of the hand-check (F-ICE-1 and F-NEWS-1 have not been read by a human yet) is George's next task. Lesson recorded in data doc 2.4: the hand-check is where the generator's realism gets audited, and it found real defects after a few minutes.

## 2026-11-02 Hand-check round 2: F-ICE-1 fixed, desk profiles aligned, Phase 1 closed

- **What happened:** George replayed seven more alerts. Six matched. F-ICE-1's label promised partial executions on the iceberg; the tape had none (one-tick spread, no price improvement possible, back of the queue, 0.25× depth counterparty sells never reached it). F-MM-1's label said "quote size typical for the desk" while the profile said 900 against quotes of about 3,100; F-ALGO-1 and F-SPOOFLIKE-HARD-1 had the same mismatch.
- **Decision:** Counterparty sells in F-ICE-1 sized at 1.0× depth so they sweep the level and hit the tip; desk scenarios write their quoted size into `typical_order_size`; PROP scenarios keep a modest typical size on purpose. Phase 1 declared complete with 12 alerts hand-checked.
- **Alternatives:** (a) weaken the F-ICE-1 label to "iceberg order type" only; (b) leave profile sizes and let the agent read "4× typical" as a flag on market makers.
- **Reason:** (a) would remove the discriminator that separates an executing client order from a spoof, which is the one R5 and the agent both need. (b) would teach the agent that registered market makers quoting their normal size are suspicious, the opposite of the lesson.
- **Consequences:** Rebuilt dataset unchanged in shape (167 alerts, 28 TRUE_ABUSE, 0 missed); all nine F-ICE-1 alerts show 2,990-12,197 shares executed on the iceberg; baseline raw safe close 96%, gate still failed on S-SPOOF-5 only. Three generator or metric defects were found across the two rounds, none in a label's intent. Next: Phase 2.

## 2026-11-02 Phase 1 closed after a human confirmation pass, not after a programmatic one

- **Decision:** Phase 1 is complete only after George re-read one alert from each of the five scenarios changed by the hand-check fixes; all five matched their labels.
- **Alternatives:** close Phase 1 on the programmatic checks alone (all nine F-ICE-1 alerts with executions, profile sizes updated), as first proposed.
- **Reason:** George objected, and he was right: the programmatic checks are the kind of check that had missed all three defects. The project's own rule (data doc 2.4) says the hand-check is where the generator is audited.
- **Consequences:** 17 alerts read by a human. Two caveats recorded for the Phase 3 prompt: `price_move_ticks` is uninformative when the trader executed on the resting side, and a spoofer's own market order can sweep up to his resting level in a thin book. Phase 2 starts next.

## 2026-11-03 Cost is not a constraint; every resource carries `auto-remove=no`
- **Decision:** No data cuts to save money (the full seed7 tape goes to DynamoDB). Every AWS resource the project creates carries `Project=agentcore-surveillance-investigator` and `auto-remove=no`; `scripts/check_tags.py` audits both sources (Resource Groups Tagging API and the AgentCore control plane) and can add missing tags.
- **Alternatives:** load five sessions instead of twenty (proposed by the assistant to keep the load under $1); tag only the CDK stack.
- **Reason:** George's instruction. The account's cleaner removes untagged resources; AgentCore resources created by the CLI are not covered by the CDK app's tags, so they need the audit script.
- **Consequences:** Loading seed7 costs about $3 of writes once (Pricing API, London). `cdk.Tags.of(app)` covers the stack; AgentCore resources are tagged at creation or by `check_tags.py --fix`.
## 2026-11-03 One Lambda for all Gateway tools; least privilege at the data layer
- **Decision:** All eleven tools under target `surv` are one function, `surv-gateway-tools`, dispatching on `bedrockAgentCoreToolName`. The function may read every table and write only `surv-cases`, and contains no code that sets `recorded_*`. The human path is a second function behind an HTTP API with a Cognito JWT authoriser, which the Gateway role cannot invoke.
- **Alternatives:** one Lambda per tool (as the build plan first said); one Lambda per read/write class.
- **Reason:** A Gateway target maps one Lambda ARN to one tool schema and the target name is the policy prefix (`surv___`); eleven functions would mean eleven targets and eleven prefixes, or one target that cannot exist. The separation that matters for the demo (agent proposes, human records) is between the two functions, not between tools.
- **Consequences:** One deployment unit and one log group for the tools; the test suite exercises every tool through the same handler; the design doc's section 4 and 8 were rewritten to match. The tool-name contract was verified against the Gateway developer guide before writing the handler.
## 2026-11-03 pandas layer without pyarrow; manylinux_2_28 wheels
- **Decision:** The Lambda layer carries pandas and numpy only, built from `manylinux_2_28` aarch64 wheels pinned to `uv.lock`; pyarrow stays local.
- **Alternatives:** ship pyarrow too (the layer would be 219 MB unzipped, close to the 250 MB limit); build the layer in Docker.
- **Reason:** The tools read DynamoDB, never parquet, and pandas 3 falls back to Python-backed strings without pyarrow. cp314 wheels for all three packages only exist as `manylinux_2_28`, which the `python3.14` runtime (Amazon Linux 2023, glibc 2.34) accepts; the first attempt with `manylinux2014` found no wheels. Docker is not needed when wheels exist.
- **Consequences:** Layer is 80 MB unzipped, 22 MB zipped. The moto test shows the Lambda-path discriminators equal the parquet-path values, so the missing pyarrow changes nothing numerically.

## 2026-11-03 Gateway declared in `agentcore.json`, deployed with `agentcore deploy`; AgentCore resources stay out of `infra/`
- **Decision:** The Gateway and its Lambda target are declared in `agentcore/agentcore.json` (project `surv`) and deployed by the CLI into its own stack `AgentCore-surv-default`. The firm's resources stay in the CDK Python stack `SurvFirm`. The two meet at one point: the Lambda ARN written into the target configuration. Tags are added in `agentcore/cdk/bin/cdk.ts` with `Tags.of(app)` and repeated on the Gateway with `--tags`.
- **Alternatives:** create the Gateway with `aws bedrock-agentcore-control create-gateway`; put the Gateway into `SurvFirm` with the `AWS::BedrockAgentCore::Gateway` CloudFormation resource.
- **Reason:** The CLI generates the IAM role, grants it `lambda:InvokeFunction` on exactly the target's function, creates the workload identity, enables CloudWatch Transaction Search and records the state; the same file will carry the Runtime, Memory, Policy Engine and evaluators in later phases, so one declaration covers the whole AgentCore side. Raw CLI calls are not reproducible; the CloudFormation route would make `infra/` depend on the AgentCore schema for every service added later.
- **Consequences:** Two stacks, one dependency direction (AgentCore depends on the Lambda ARN). The CLI scaffolds into `./surv/`; the `agentcore/` folder was moved to the project root where the hooks watch it. `toolSchemaFile` resolves from the project root, so `surv-tools.json` lives there (exported from `src/tools/schema.py`; re-export after any schema change). The project-file key is `customJwtAuthorizer`, not the API's `customJWTAuthorizer`. The auto-created workload identity is not tagged by the stack: `check_tags.py` found it and it was tagged by hand.
## 2026-11-03 Loader shuffles items before writing
- **Decision:** `scripts/load_dynamodb.py` shuffles all items of a table before batch-writing them, uses one boto3 session per thread with adaptive retries, and runs detached (`nohup`).
- **Alternatives:** write in date order (the first attempt: 630 items/s, and the Kiro shell killed it at the 120 s tool timeout); provision WCU temporarily.
- **Reason:** The `by_date` GSI partitions on `date`; writing one day at a time pushes every in-flight write through one index partition (1,000 WCU/s). Shuffled, the same writes spread over 20 partitions and ran at 2,500-3,500 items/s. Provisioned capacity would have saved nothing at this size.
- **Consequences:** Full load in about 12 minutes. The interrupted first run left about 213k items that were overwritten by the second (puts are idempotent on the key), about $0.15 of duplicate writes.

## 2026-11-03 Rate limits as a brake, not a counter; declared in the AgentCore CDK stack
- **Decision:** Two Gateway rate limits per analyst (`$.context.jwt.sub`): 60 requests a minute over all tools, and 3 a minute each on `propose_disposition` and `draft_stor_narrative`. Declared as `CfnGatewayRateLimit` in `agentcore/cdk/lib/cdk-stack.ts`, next to the `AgentCoreApplication` construct, so `agentcore deploy` carries them.
- **Alternatives:** `BatchPutGatewayRateLimits` from a script; a `*` default entry on `toolName`; tighter numbers.
- **Reason:** The CDK route keeps one deployment unit for the AgentCore side and the IDs are stable. Probing showed request limits carry a burst allowance (18 calls admitted at 1/min before the first refusal; `rate: 0` blocks outright), so "3 a minute" bounds a runaway loop but cannot count proposals per alert; that stays with Policy 05 (temporal). Tighter numbers would throttle a legitimate investigation (8-12 calls, often inside 20 s cold) without buying a real boundary.
- **Consequences:** The probe wrote 16 test proposals on A-261005-0001 as `l2.reviewer`; the case record was deleted so the demo queue is clean. Design doc sections 6 and 8 record the burst measurement; the Phase 4 policy tests must not assume the rate limit has fired first.

## 2026-11-03 Agent code lives in `app/surv_investigator_l1/`, not `src/agent/`
- **Decision:** The Runtime's code sits where the AgentCore CLI expects it (`codeLocation: app/<runtime name>`, its own `pyproject.toml`, `main.py` entrypoint, direct code deploy). `src/` keeps the firm side (simulator, detector, tools). The agent carries its own copy of nothing: the report model is the agent's, the Gateway's loose `report` schema is checked against it by a test, and the procedures text is read through `get_procedures` at run time.
- **Alternatives:** `src/agent/` as the build plan said, with `codeLocation: src` (ships the simulator and tests in the zip, and the root `pyproject.toml` with pandas and the CDK group); a container build with a Dockerfile.
- **Reason:** One convention beats two; the CLI's `findManifest` walks up from `codeLocation` and would otherwise pick the root manifest with 20 unrelated dependencies. CodeZip builds in seconds and needs no Docker; every dependency has aarch64 wheels.
- **Consequences:** Deploy is `agentcore deploy` (same command as the Gateway). Tests for the agent live in `app/surv_investigator_l1/tests/` and `pytest` `testpaths` includes `app`. The CLI's `.cache/` staging dir is excluded from ruff.
## 2026-11-03 Report validation in the agent, procedures read at run time, trajectory not self-reported
- **Decision:** `InvestigationGuard` (a Strands hook on `BeforeToolCallEvent`/`AfterToolCallEvent`) validates the report with the strict pydantic model and cancels the tool call with the errors as the tool result; it fills `tool_calls` from observed calls; it blocks a second proposal, a foreign alert id, and `draft_stor_narrative` in L1 mode. The system prompt tells the agent to read the firm's procedures with `get_procedures` first instead of embedding them.
- **Alternatives:** validate in the Lambda only (the Gateway side already requires three keys); let the model write `tool_calls`; embed the procedures in the prompt.
- **Reason:** The Lambda cannot see the trajectory and should not know the model's rules; the guard can, and a rejected report costs one model turn instead of a Gateway round trip. A self-reported trajectory is what a faithfulness evaluator must not trust. Reading procedures at run time means a manual change reaches the agent without a redeploy and the trace proves the agent read them.
- **Consequences:** Every stored report's `tool_calls` equals the real sequence (checked through the human-path API). The Gateway `report` schema gained `alert_id`, `scenario`, `tool_calls` so the model sees the same shape in both places (`surv-tools.json` re-exported and redeployed).
## 2026-11-03 Claude 5.5 on Bedrock: adaptive thinking on by default, `temperature` rejected, 32k output budget
- **Decision:** `BedrockModel(max_tokens=32000, additional_request_fields={"thinking": {"type": "adaptive"}, "output_config": {"effort": "medium"}})`, no `temperature`. `SURV_EFFORT` and `SURV_MAX_TOKENS` override for Phase 5 experiments.
- **Alternatives:** disable thinking; `max_tokens` 4096 as first written; effort `high`.
- **Reason:** Verified on the Bedrock user guide (2026-11-03): adaptive thinking is on by default for Claude 5.5, thinking tokens count against `max_tokens`, `temperature` returns a ValidationException. The first runs hit `MaxTokensReachedException` at 4,096 and again while the model was writing the `propose_disposition` input; a market-maker alert with 400 order events needed about 9,600 output tokens with Haiku at effort medium. Disabling thinking would remove the reasoning Observability shows and the evaluator reads.
- **Consequences:** Sonnet investigations run 27-40 s and 34-37k input tokens; Haiku on the market maker took 97k input tokens over 6 model calls and still escalated. Effort level becomes an A/B arm in Phase 5.

## 2026-11-03 Analyst UI in Streamlit, loopback only, the analyst's token everywhere
- **Decision:** `ui/analyst_app.py` (Streamlit) with the clients in `ui/surv_client.py`. The UI logs the analyst in against Cognito and uses that access token for the human-path API and for the Runtime, which forwards it to the Gateway; the UI holds no AWS credentials for the agent path and never stores a password. The server binds to 127.0.0.1 (`.streamlit/config.toml`). The trace panel reads the session's spans from CloudWatch (this needs the machine's AWS credentials and is optional) and links to X-Ray.
- **Alternatives:** a CLI only; a web app behind the HTTP API with its own hosting; Streamlit on 0.0.0.0 for sharing on the LAN.
- **Reason:** The demo needs a queue, a report and a record button on one screen; Streamlit gives that in 300 lines and runs where the presenter sits. One token through the whole chain is the Identity story of the design (section 8). Loopback is the security default for a local tool; anyone else gets an SSH tunnel.
- **Consequences:** Streamlit added as the `ui` dependency group. Streamlit's first start printed a LAN URL, which is why the config file exists. The three demo alerts ran through the UI's client; C (F-NEWS-1) was recorded as an override, so the first override is on file for the learning-loop story.
