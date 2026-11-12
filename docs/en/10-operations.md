# 10 - Operating and improving the product

How the investigator is run after the alpha, how a change becomes a release, what to watch, and where the measured room for improvement is. Written 2026-11-08 against the then promoted configuration (Runtime v12, run `20261106T1126-sonnet-v3`); section 5 updated 2026-11-10 with the measured result of iteration 3 (Runtime v14, run `20261110T1833-sonnet-v4`). The numbers come from `04-synthetic-data-and-evaluation.md` section 4.6 and from the span analysis in section 4 below.

## 1. From alpha to pilot, in order

1. **Freeze the regression set.** `seed7` (167 alerts) stays as it is; every change is compared with the last promoted run on it. Done 2026-11-11: a second set, `seed8` (seed 8, November dates, detector K = 4 from the tuning report, 100 alerts, loaded beside seed7), that no configuration was tuned against; the promoted configuration on it: gate 0 of 24, the ten scenarios the standard defines 76 of 76, safe close 86.8% on a mix with 24% boundary cases (92.7% reweighted to seed7's mix), the disagreements in the same four undefined scenarios plus one F-RISK-1 (data doc 4.6). The harness refuses a promotion verdict across datasets; `--rescore` and `--resume` take the run's own dataset.
2. **Measure run-to-run variance.** Done 2026-11-11 (`evals/run_dataset.py --repeat 5`, 21 alerts x 5, 34 minutes, $7.94; data doc 4.6): 18 of 21 alerts stable, no true-abuse alert ever closed, the three unstable ones are an F-FAT-1, an F-NEWS-1 and the ESCALATE/DRAFT_STOR level on one S-LAYER-1, all at confidence 0.60-0.72. Scaled to the full set the noise on the safe close rate is about 0.9 points (one standard deviation), so the promotion rule's two-point tolerance is about two standard deviations. Repeat it after any change to the standard or the model, because the noise sits exactly on the alerts the standard leaves open.
3. **Decide the three open scenarios.** F-STOP-1 (0/6) is a question for the firm's standard, not code: does a one-sided large order pulled after a loss-making exit close at Level 1, given MAR Art. 15 on attempts? F-NEWS-1 (2/4) and S-SPOOF-2 (1/3) are iteration-3 candidates (section 5).
4. **Pilot on a customer's labelled alerts.** The harness runs on the firm's own data with the firm's own procedure text; the gate is the acceptance criterion. Until then every number is synthetic and is said to be.
5. **Configure the two production items** left open in the alpha: retention on the log groups (five years, or export to S3 with a cold-storage lifecycle) and access control on the log groups equal to that on the tables (broker brief section 7).

## 2. How a change becomes a release

The promotion rule (data doc 4.4) is the process; the Runtime endpoint alias is the release mechanism.

```
change: tool field | sentence in the firm's standard | prompt | model | dependency
  -> pytest + ruff locally (51 tests, ~30 s)
  -> deploy to the DEFAULT endpoint (the pinned alias does not move)
  -> evals/run_dataset.py on the frozen set, --compare with the last promoted run (~1 h, ~$31)
  -> promotion rule: gate holds; safe close not down > 2 pts; faithfulness not down;
     no scenario the previous run closed >= 2 times and >= 25% falls to 0%
  -> PASS: faithfulness (free); judged pass for substantive changes (~$25);
           decision-log entry; move the alias (demo / prod) to the new version
  -> FAIL: fix or revert; the alias never moved, users saw nothing
```

**Deploy is not release.** Every `agentcore deploy` creates a new Runtime version behind `DEFAULT`. Release is moving the alias: set `endpoints.<alias>.version` in `agentcore/agentcore.json` and run `agentcore deploy`; rollback is the same edit with the previous N. The CLI's `add runtime-endpoint` creates an alias and refuses an existing name (verified 2026-11-10 moving `demo` v12 -> v14). A deploy cuts a new version only when the agent artefact changed: the 2026-11-11 alias move also carried a changed artefact and produced v15, the 2026-11-12 alias move did not and produced no version, leaving `demo` and `DEFAULT` both on v16. So after a release the two can be equal; `DEFAULT` runs ahead only while unreleased code is deployed. No downtime, no code change on the released alias until you move it.

**When the judge runs, and only then.** The judge (AgentCore Evaluations: Correctness, GoalSuccessRate, the Trajectory checks and the rationale rubric on Opus) costs about $0.17 per session, almost twice the investigation it scores, so it never runs on its own: not from the UI, not inside a harness run, not on a schedule. It runs when a person starts `evals/evaluate_sessions.py` on a saved run, which prints the estimate and asks for a yes (`--yes` for scripts), and when a person starts an Optimization recommendation (`evals/recommend.py start`, same confirmation). The cadence says when that person should: on the candidate run of any change that touches the prompt, the standard, the tools, the model or the report format (mandatory before promotion), and monthly for the trend. It is not run on an arm whose model is the judge's model (the Opus arm). An **online** evaluation, the judge on a sample of live sessions, is not configured in the alpha (section 3); if a firm wants it, 10-20% of sessions at $0.17 each is the cost to put next to the trend it buys.

**The firm's standard needs the same discipline.** Because `get_procedures` reads it at run time, an edit applies on the next investigation without a deploy. Edit it in a staging table or Memory namespace, run the harness, then promote; otherwise compliance changes a sentence on Tuesday and the override rate moves on Wednesday with nothing in the log to say why.

**Cadence.**

| When | What |
|---|---|
| Per change | harness on the frozen set, promotion rule, decision-log entry |
| Weekly | `evals/ingest_overrides.py` (overrides become test cases); review Policy denials by rule and the no-proposal count |
| Monthly | judged pass (rubric trend); dependency check (`agentcore/.cache/<runtime>/staging/*.dist-info` is what the Runtime really gets); cost per alert |
| Quarterly | `python -m detector.tune` on the accumulated labelled alerts; review of the standard with compliance; new model release evaluated as a configuration bundle (the Opus arm is the template) |
| After a change to the standard or the model | variance run (`--repeat 5` on the boundary alerts, ~$8): the noise band moves with exactly these two things, and the promotion tolerance is read against it |

## 3. What to watch

| Signal | Source | What a move means |
|---|---|---|
| **Gate** (true abuse proposed CLOSE_FP) | harness, per run | Anything above zero does not ship. There is no online version; it needs a labelled set. Held in 6 full runs and in all 35 true-abuse repetitions of the variance run. |
| **Run-to-run noise** on the safe close rate | `--repeat` run, after a change to the standard or the model | About 0.9 points (one sd) as of 2026-11-11. A difference between two runs under two points is not a finding; a new unstable alert outside F-FAT-1 / F-NEWS-1 / F-STOP-1 / layering level is. |
| **Override rate**, overall and by scenario / desk / analyst | `surv-cases` (`override` flag), weekly | Rising: the agent got worse or a new pattern appeared. Very uneven by analyst: someone is not reading, or someone applies a different standard; both are findings for compliance. |
| **Safe close rate** | harness | The headline, reported only with the gate. |
| **Evidence faithfulness** | `evals/faithfulness.py`, free | Below 99%: the model or the tool outputs changed. |
| **No-proposal rate** | cases without `proposed_*` after a run | Above zero: the agent stops before proposing (the rejected recommendation did this on 100%). |
| **Guard rejections** | `rejections` in responses | Field-name slips (14% in v3, section 4) cost a full report rewrite each. |
| **Policy denials by rule** | Gateway log; metrics `AWS/Bedrock-AgentCore` | Should be about zero for the agent itself. Rising: the model changed behaviour, or someone calls the Gateway with their own client. |
| **Latency p50/p95, tokens, cost per alert** | harness, spans | Rising with no change of ours: a new model snapshot behind the inference profile, or larger tool outputs. |
| **429 / 424 / 5xx** | harness errors, Gateway log | Clusters: rate limits too tight for the team, or availability. |
| **Rubric mean and distribution** | judged pass, monthly | Quality of reasoning. Falling while agreement holds: the reports weaken before the decisions do. |
| **Memory size, extraction lag, recall latency** | Memory API, spans | Records growing without bound: a TTL policy is due. |
| **Dependency drift** | staging dist-info at each deploy | The Runtime bundle resolves different versions from the workstation (mcp 1.30 vs 2.3 broke v11). |
| **Replay mismatch** | `scripts/replay_trajectory.py` on a sample of sessions, after any data load or tool change | A read-only tool returning something other than what the agent saw means the data or the tool changed under the record: find out which before anything else. |

Two things turn this table from scripts into operations: an **online evaluation config** (the rubric on a 10-20% sample of live sessions, which gives the quality trend without a labelled set and is the prerequisite for a Gateway A/B test), and a **dashboard** with the first five rows. Days of work, not weeks; neither is in the alpha.

## 4. Where the time and the tokens go (measured, 2026-11-08)

Two v3 sessions, span by span (`A-261006-0006`, a spoof, 24 s; `A-261005-0003`, a market maker, 38 s):

| Step | Spoof | Market maker |
|---|---|---|
| model turn -> `get_alert` | 1.0 s | 1.0 s |
| model turn -> `get_procedures` + `recall_memory` | 1.7 s | 1.6 s |
| model turn -> the six evidence tools, requested **in one turn** | 3.0 s | 3.1 s |
| the six tools, executed sequentially | 1.3 s | 1.4 s |
| model turn: writes the report, calls `propose_disposition` | 11.7 s (1,875 out tokens) | 12.3 s |
| guard rejects the report (`ruled_out` instead of `ruled_out_by`), model rewrites it | - | **10.4 s** |
| model turn: closing summary | 3.3 s | 4.3 s |
| **model / tools** | **20.7 s / 3.2 s** | **32.7 s / 4.8 s** |

Findings:

- **Time is in the model (85%), not in the tools (15%).** The model already asks for all six evidence tools in one turn; executing them concurrently instead of sequentially would save about one second, not the ten first estimated.
- **A field-name slip costs a full rewrite in 14% of sessions.** In 24 of 167 v3 sessions the model wrote `ruled_out` where the schema says `ruled_out_by`; the guard rejected the report and the model wrote it again: +8.6 s and +32k input tokens on those sessions (mean 35.7 s / 104k tokens against 27.1 s / 72k without). A schema alias accepting both names removes it.
- **The input tokens are the same prefix re-read five or six times.** 77k input tokens per alert over about six model turns, each re-reading the system prompt, the tool definitions and all earlier results. Bedrock prompt caching applies: Claude Sonnet 5.5 (and Haiku, Opus 5.5) support explicit caching on Bedrock with a 512-token minimum, four checkpoints, 5-minute TTL, in `system`, `messages` and `tools`, plus "automatic caching" that moves one checkpoint forward as the conversation grows [Bedrock user guide, prompt caching, read 2026-11-08]. Strands 1.63 implements it with one argument, `BedrockModel(cache_config=CacheConfig(strategy="auto"))`, which places cache points at the end of the system prompt, on the tools and on the last user message. Estimated effect: 55-65% less input cost (cache reads at a fraction of the input price; writes carry a premium) and 2-4 s less latency. One risk to measure, not assume: the `eu.` inference profile routes across seven Regions and the cache lives on the server that wrote it; the user guide says cross-region inference "may lead to increased cache writes".
- **The report-writing turn is the largest single cost** (12 s, 1,800 output tokens with adaptive thinking). The only lever is `effort` (medium -> low) as a configuration-bundle A/B, with the rubric watching quality.

## 5. Backlog, grouped and ranked

**Iteration 3 (done 2026-11-10, run `20261110T1833-sonnet-v4`, Runtime v14): latency and cost, low risk.** Estimated against measured:

| Change | Estimated | Measured (167 alerts, paired with v3) |
|---|---|---|
| Fold `ruled_out` into `ruled_out_by` in the report model | -1.2 s mean, -6% tokens, 14% fewer guard rejections | rejections **24 -> 1** (the one left is a report sent as a string); p95 38.0 -> 35.6 s; output tokens -8%; mean latency unchanged |
| `CacheConfig` on the Bedrock model (system prompt, tools, last user message) | -55-65% input cost, -2-4 s | **-51% model cost** ($31.26 -> $15.25; $0.187 -> $0.091 per alert); 72.7% of prompt tokens read from cache, 27.3% written, 11 at full price; **0 s** saved |
| `ConcurrentToolExecutor` for the evidence tools | -1 s | not done; the measured ceiling is ~1 s |
| `get_case_context` (alert + procedures + memory in one tool) | -3 s, -8-15% tokens | not done; design doc section 7 |
| `effort` low as a bundle | perhaps -5 s | done as iteration 4 (below): **0 s**, -10% output tokens, 0 of 30 decisions changed; the report turn is writing, not thinking |

Three lessons from the measurement. The cache saves money, not time: Bedrock still processes the cached prefix, cheaper, and the model's output time is the latency. A field alias on a model with `extra="forbid"` has to handle the model sending **both** names at once (seen on v13 in the first smoke test, which a plain pydantic `AliasChoices` does not cover; a `model_validator(mode="before")` does). And Bedrock reports `inputTokens` without the cached tokens, so a token or cost metric that reads only that field shows a 99.98% fall; `metrics.py` adds `cacheReadInputTokens` and `cacheWriteInputTokens` back as `prompt_total`, and the cost line prices reads at 0.1x and writes at 1.25x of the input price (conservative; the pricing page announced a lower read price for Sonnet 5.5 from 2026-10-07 that is not yet read off the page). Four of 167 dispositions moved (three towards the label, one away), which neither change can cause; the variance run the next day (item 2 in section 1) measured that noise at about 0.9 points, and the four flips sit inside it.

**Iteration 4 (2026-11-11): `effort` low, measured and rejected for $3.** Bundle `surv_effort_low` (the code's prompt, Sonnet 5.5, `effort: low`; `evals/bundles.json`), no deploy, 30-alert slice on the Runtime against the same 30 alerts of v4 (`evals/runs/compare-v4-effort-low.md`): **0 of 30 dispositions changed**, p50 27.8 s against 26.9 s, p95 30.5 against 32.9, output tokens -10% (2,843 against 3,172), cost -2%. The spans explain why (`scripts/span_turns.py`, the per-turn view of section 4 as a command): the report turn is 9.6-10.9 s and 1,580-1,830 output tokens at both settings, and its `gen_ai.choice` carries 3,300-3,800 characters of `propose_disposition` input and an empty reasoning text. **The 10 seconds are the model writing the report, not thinking about it.** `effort` has nothing to cut; the full run and the judged pass ($45) were not spent. Two consequences. The only lever left on latency is the size of the report (nine evidence items, eight explanations with verdicts and evidence ids, summary, window, what-would-change-my-mind), and that is a product decision for compliance (P3, regulator-grade report), not a setting. And `effort` high is unlikely to buy anything on the decisions: the systematic disagreements are stable with consistent reasoning ("the standard gives me no reason to close"), and the Opus arm already asked the more expensive version of the same question. The one test that could still show something is `effort` high on the variance subset (21 x 5, ~$12): if the three unstable alerts become 5/5, more thinking buys stability and its cost in time is measured; if not, the question is closed. Backlog, not next.

**Decision quality (measured gaps).**
- F-STOP-1 0/6: a question for the standard first. If "close", a field `loss_making_exit` (adverse move + negative round trip + no reversion, which exist separately) and a sentence; if "escalate", the label changes.
- F-NEWS-1 2/4: the agent will not accept "the sale was a hedge" without evidence. A field for the time from the sale to the news, and the hedge named in the standard.
- S-SPOOF-2 1/3: the escalation standard says "repeats" without a number; `repetitions_in_session >= 3` explicitly.
- Report quality (rubric 0.61): the judge's lowest explanations are specific (derived timings wrong, indicators matched loosely). One sentence in the report instructions: times and differences as the tools return them.

**Iteration 5 (candidate): the confidence definition.** `evals/calibration.py` shows the figure ranks cases well but sits at 0.70-0.75 on textbook spoofs because "same disposition" includes the ESCALATE-vs-DRAFT_STOR choice. Redefining it on the direction (close vs not close) is one sentence in the prompt, so it is an iteration with the judged pass mandatory and the calibration table as the acceptance measure (clear spoofs up, boundary cases where they are, closes unchanged). Separately, for a pilot: recompute the table against the firm's recorded Level-2 decisions (`evals/ingest_overrides.py`) and either keep the figure, remap it, or show the band only.

**Resilience.** 429 retry is in (v12). Next: Bedrock throttling and model timeouts, not yet seen at this volume. The harness runs from a laptop; for a customer it becomes a scheduled job in the account.

**Security.** Done 2026-11-11: `tests/test_agent_tools_boundary.py` asserts the agent is built with exactly one tool source (the Gateway MCP client, with the analyst's bearer token and the policy session header), no direct tools, and no tool library or HTTP client imported in the agent package; it fails on a second tool (checked by adding one). That is broker brief section 2b's warning as code. Still open: retention and log access (section 1, item 5).

**Operations.** Online evaluation config and dashboard (section 3). The analyst's pre-run briefing (the UI's instruction box) written on the case record next to the proposal: a `analyst_instruction` field on `propose_disposition`, passed through by the guard from the invocation payload, stored by the tools Lambda; today it is in the trace only (design doc section 9). Overnight pre-investigation as an option (product doc roadmap). The UI is a reference; the customer embeds the calls in its case tool.

**Scope.** A second abuse type (wash trades or marking the close): new discriminators and standard paragraphs on the same architecture, which is the proof that this is a platform and not one scenario.

## 6. What this document is not

It is not a runbook for incidents (none has happened yet beyond the two the resume guide records) and not a capacity plan: one analyst runs two investigations at a time inside the rate limits, and a firm with a larger queue sizes the limits and the Runtime from its own volume.
