# 10 - Operating and improving the product

How the investigator is run after the alpha, how a change becomes a release, what to watch, and where the measured room for improvement is. Written 2026-11-08 against the promoted configuration (Runtime v12, run `20261106T1126-sonnet-v3`). The numbers come from `04-synthetic-data-and-evaluation.md` section 4.6 and from the span analysis in section 4 below.

## 1. From alpha to pilot, in order

1. **Freeze the regression set.** `seed7` (167 alerts) stays as it is; every change is compared with the last promoted run on it. Build a second set (`seed8`, detector K = 4 from the tuning report) that no configuration has been tuned against, to measure generalisation and not only regression.
2. **Measure run-to-run variance.** The same alert five times, for twenty alerts (two hours, about $10). We know the agent is not deterministic (alert E flipped between days); we do not know by how much. Without that number, a one- or two-point difference between runs cannot be called a change.
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

**Deploy is not release.** Every `agentcore deploy` creates a new Runtime version behind `DEFAULT`. Release is `agentcore add runtime-endpoint --version N` on the alias; rollback is the same command with the previous N. No downtime, no redeploy.

**The firm's standard needs the same discipline.** Because `get_procedures` reads it at run time, an edit applies on the next investigation without a deploy. Edit it in a staging table or Memory namespace, run the harness, then promote; otherwise compliance changes a sentence on Tuesday and the override rate moves on Wednesday with nothing in the log to say why.

**Cadence.**

| When | What |
|---|---|
| Per change | harness on the frozen set, promotion rule, decision-log entry |
| Weekly | `evals/ingest_overrides.py` (overrides become test cases); review Policy denials by rule and the no-proposal count |
| Monthly | judged pass (rubric trend); dependency check (`agentcore/.cache/<runtime>/staging/*.dist-info` is what the Runtime really gets); cost per alert |
| Quarterly | `python -m detector.tune` on the accumulated labelled alerts; review of the standard with compliance; new model release evaluated as a configuration bundle (the Opus arm is the template) |

## 3. What to watch

| Signal | Source | What a move means |
|---|---|---|
| **Gate** (true abuse proposed CLOSE_FP) | harness, per run | Anything above zero does not ship. There is no online version; it needs a labelled set. |
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

**Iteration 3 (next): latency and cost, low risk.**

| Change | Estimated gain | Risk | Measured by |
|---|---|---|---|
| Schema alias `ruled_out` -> `ruled_out_by` | -1.2 s mean, -6% tokens, 14% fewer guard rejections | none | harness, rejection count |
| `cache_config=CacheConfig(strategy="auto")` | -55-65% input cost, -2-4 s | cache hit rate on the cross-region profile | harness; `cacheReadInputTokens` in the spans |
| `ConcurrentToolExecutor` for the evidence tools | -1 s | temporal policies under concurrent requests | harness, Policy denials |
| `get_case_context` (alert + procedures + memory in one tool) | -3 s, -8-15% tokens | loses the agent's targeted memory query and the separate memory switch | harness, memory on/off arm |
| `effort` low as a bundle | perhaps -5 s | report quality | rubric + harness |

Plan: the first two on a branch, a 30-alert slice locally, then a full run v4 under the promotion rule.

**Decision quality (measured gaps).**
- F-STOP-1 0/6: a question for the standard first. If "close", a field `loss_making_exit` (adverse move + negative round trip + no reversion, which exist separately) and a sentence; if "escalate", the label changes.
- F-NEWS-1 2/4: the agent will not accept "the sale was a hedge" without evidence. A field for the time from the sale to the news, and the hedge named in the standard.
- S-SPOOF-2 1/3: the escalation standard says "repeats" without a number; `repetitions_in_session >= 3` explicitly.
- Report quality (rubric 0.61): the judge's lowest explanations are specific (derived timings wrong, indicators matched loosely). One sentence in the report instructions: times and differences as the tools return them.

**Resilience.** 429 retry is in (v12). Next: Bedrock throttling and model timeouts, not yet seen at this volume. The harness runs from a laptop; for a customer it becomes a scheduled job in the account.

**Security.** A unit test that the agent's tools are exactly the one MCP client to the Gateway and nothing else: the warning in broker brief section 2b (a generic HTTP tool would hand the agent the ability to record) as code. Retention and log access (section 1, item 5).

**Operations.** Online evaluation config and dashboard (section 3). Overnight pre-investigation as an option (product doc roadmap). The UI is a reference; the customer embeds the calls in its case tool.

**Scope.** A second abuse type (wash trades or marking the close): new discriminators and standard paragraphs on the same architecture, which is the proof that this is a platform and not one scenario.

## 6. What this document is not

It is not a runbook for incidents (none has happened yet beyond the two the resume guide records) and not a capacity plan: one analyst runs two investigations at a time inside the rate limits, and a firm with a larger queue sizes the limits and the Runtime from its own volume.
