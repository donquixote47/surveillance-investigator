# 09 - Product decisions: what was built, why, and how it is sold

The record of every product-level decision in this project, with the reason and the evidence, written so that a solutions person can explain the product to a buyer and a mentor can see where Amazon Bedrock AgentCore does the work. The detector and the simulator are deliberately left in the background: they are the test bench, not the product. Each decision links to the dated entry in `decision-log.md` where the alternatives were weighed; the measured numbers are from `04-synthetic-data-and-evaluation.md` section 4.6. State as of 2026-11-07, Runtime v12.

## 1. The product in three sentences

A governed Level-1 investigator for trade-surveillance alerts. It sits after any detector and before the analyst, gathers the evidence through controlled tools, applies the firm's own written standards, writes the report the regulator will read, and proposes a disposition that a human records. It runs in the firm's AWS account on Amazon Bedrock AgentCore, which supplies the controls a compliance function needs before it will let an AI agent near a surveillance case: a single choke point for every action, deterministic rules the model cannot talk its way past, identity of the human behind every call, a full trace, and a measured, versioned path for change.

## 2. Who buys it and why

| | |
|---|---|
| Buyer | Head of compliance at a mid-sized EU broker, CFD/FX broker, prop trading firm or market maker: a surveillance platform with default scenarios, a backlog of alerts, one to five people in compliance, no data-science team, a regulator who expects "human analysis by appropriately trained staff" and records of it (Delegated Regulation (EU) 2016/957). |
| Pain | Each alert costs 20-40 minutes of a trained person; 80-95% are legitimate activity; the reasoning behind every closure must be written and kept. The firm cannot remove the human and cannot afford a tier-1 platform. |
| Promise | Each alert resolved in the analyst's time of reading a report instead of building one. Nothing decided without a human. Every closure documented to the standard the regulation sets, as a by-product. |
| Not the buyer | Tier-1 banks (served by NICE Actimize, Nasdaq and in-house teams); firms without a detector. |
| Positioning | *We do not detect market abuse. We investigate the alerts your detector already raises, and we leave the decision with your analyst.* |
| Secondary channel | Compliance consultancies and outsourced compliance providers who run surveillance for several small firms: one deployment per client account, the same procedures text per client. |

Decision log: 2026-11-02 "Switch the project domain", "Scope to spoofing and layering".

## 3. Product principles (the decisions that define it)

| # | Principle | Decision and reason | Evidence |
|---|---|---|---|
| P1 | **Propose, never record.** | The agent has no tool that records a disposition; recording is a separate API behind the firm's identity provider, callable only with a human's credentials. This is a design principle, not a phase limitation. A buyer's model-risk function asks this first. | Policy 02 closed allow-list; human path `POST /cases/{id}/disposition`; decision log 2026-11-02 "The agent proposes; a human records". |
| P2 | **The firm's standard is the logic.** | The agent reads the firm's procedure texts at run time and the report has to apply them. Behaviour is changed at three levels, in this order of preference: a deterministic field in the tools (engineering owns it; the agent quotes the number), a sentence in the firm's standard (compliance owns it; every analyst reads it), and last the prompt (engineering owns it; the least auditable: "we told the model to"). Both improvements in evaluation (79.9% -> 93.5% safe close) used the first two; the prompt did not change. | Decision log 2026-11-05 "The learning fix went into the firm's procedure", 2026-11-06, 2026-11-07; broker brief section 8. |
| P3 | **Numbers from code, judgement from the model.** | Every metric in a report is computed by a deterministic function and returned by a tool; the model sequences, interprets and writes. 99.9% of 4,132 numbers in the last run's reports match a tool output. | Decision log 2026-11-02 "Deterministic metrics in Lambda, LLM for sequencing and writing"; `evals/faithfulness.py`. |
| P4 | **One metric a regulator would accept.** | Gate: zero true-abuse alerts proposed as closed, computed by code. Only if the gate holds is the safe close rate reported. The threshold rules fail this gate on the same data (6 of 28); every run of the product holds it. | Decision log 2026-11-02 "Primary metric"; data doc 4.2 and 4.6. |
| P5 | **Controls outside the prompt.** | Order of evidence before conclusion, one proposal per alert, Level-2-only STOR drafting, caps on data pulls, per-analyst rate limits: all evaluated by the platform on every call, logged with the rule that fired. The agent itself ignores "just close this quickly"; the rules are there for the day it does not. | Design doc section 6; `scripts/policy_demo.py`. |
| P6 | **The human's identity on every call.** | The analyst's own token is forwarded to every tool call; the gateway, the rules and the rate limits see the person. Two roles, L1 and L2, from the firm's identity provider. | Design doc section 8. |
| P7 | **Trace as the record.** | Every tool call, output, rule decision and the analyst's decision are in one trace per investigation, in the firm's account, with the firm's retention. This is the 2016/957 record, not an export produced for the audit. | Design doc section 9. |
| P8 | **Learning that is versioned and measured, never silent.** | Case memory informs but cannot decide; overrides become test cases; prompt recommendations are candidates replayed offline; thresholds are re-tuned with a report. A change ships only through the gate. | Design doc section 11 with the measured ranking; decision log 2026-11-07. |
| P9 | **Model-agnostic by configuration.** | The model id is a configuration-bundle field. Opus 5.5 was run on the same prompt: the same override rate at 3.6x the cost. Sonnet 5.5 is the default; a firm can choose. | `evals/runs/compare-v3-opus.md`. |
| P10 | **In the customer's account, in region.** | Everything deploys into the firm's AWS account (eu-west-2 in the demo) from infrastructure code; the model is called through Bedrock EU inference profiles; nothing leaves. | `infra/`, `agentcore/`; STATUS resource table. |

## 4. Where AgentCore does the work

This is the part a mentor should weigh. Each service answers a specific objection a compliance function raises, and each was exercised in the evaluation, not only declared.

| AgentCore service | What it does in the product | The objection it answers | What we learned using it |
|---|---|---|---|
| **Runtime** | Hosts the investigator as an HTTP agent; one isolated session per alert; the analyst's JWT is the inbound authorizer and is forwarded to the tools; configuration bundles read per request from the W3C `baggage` header. Versions 1-12 over five days; a `demo` endpoint will be pinned to v12. | "Where does this run and who can call it?" | Direct code deploy of Python 3.14 works; the bundle resolves mcp 1.x while the workstation has 2.x, so transport code must be version-agnostic (v11 failed on an import, v12 fixed it). |
| **Gateway** | Turns one Lambda with twelve tools into MCP tools under target `surv`; inbound JWT from the firm's identity provider; per-analyst rate limits (60 calls/min, 3 proposals/min); the Policy Engine attached; vended logs with every call and every rule decision. | "How do we see and control every action the agent takes?" | A 429 from the rate limit kills the MCP connection unless the client retries; the Gateway's built-in rule reads configuration bundles too and needs the IAM grant. |
| **Policy** | Nine Cedar and temporal statements in ENFORCE: closed allow-list, evidence-before-proposal, history-before-close, one proposal per alert, STOR drafting after a DRAFT_STOR proposal and only for L2, a cap on event pulls. Denials name the rule. | "The agent could conclude without looking, or close on its own." | `LOG_ONLY` records no response events, so temporal rules can only be tested in ENFORCE; a policy may hold three temporal operators; the Gateway role needs `GetWorkloadAccessToken`. |
| **Identity** | Cognito user pool with groups L1 and L2 as the inbound JWT provider; the agent runs under the analyst's identity; the Gateway's workload identity for the tool path. | "Who is allowed to use it, and who did what?" | Send the access token, not the id token (`allowedClients` reads `client_id`); the groups claim arrives as a string tag. |
| **Memory** | One resource per firm (never per analyst, never across firms), a SEMANTIC strategy; direct records per disposition and feedback fanned out to trader and desk namespaces, plus extraction from free-text feedback; recall once per investigation as a Gateway tool so it is under Policy and in the log. | "It will learn the wrong lesson from one analyst." | Measured: +0.7 points safe close, override 6.6% vs 7.8% without; the clean-history spoofer was caught with and without. The agent labels memory "context only". |
| **Observability** | OTel traces of every step in CloudWatch, Transaction Search on, Gateway logs with policy decisions, the analyst UI linking each case to its trace. | "How would a regulator check this?" | The spans carry the full tool outputs, which is what makes the faithfulness check possible. |
| **Evaluations** | Built-in Correctness, GoalSuccessRate and Trajectory evaluators against ground truth generated from the labels; a custom rationale rubric judged by Opus 5.5; scored on the sessions the harness already ran. | "How do we know it is any good, and still good after a change?" | Ground-truth tool names carry the Gateway prefix; the judge reads the report, not the label, and its lowest scores pointed at real reasoning gaps. |
| **Optimization** | A system-prompt recommendation against the rubric from 167 real sessions; two configuration bundles (control, recommendation) plus a third for the model arm; the recommendation replayed offline through the harness. | "Will it improve, or just drift?" | The recommendation inserted an approval gate its explanation claimed to have "preserved" and optimised toward the judge, not the firm's metric; the offline gate rejected it. Recommendations are candidates. |
| Code Interpreter | Designed for ad-hoc charts in the report. **Not built**; the deterministic metrics stayed in Lambda and no demo step needed it. | | Say so when asked. |

Decision log: 2026-11-03 "Gateway declared in `agentcore.json`", "Rate limits as a brake", "Report validation in the agent"; 2026-11-04 "Policy Engine enforced from day one", "Policy 02 as a closed allow-list"; 2026-11-05 "Memory: direct records plus extraction"; 2026-11-05 "Evaluation harness"; 2026-11-06 recommendation entry.

## 5. What the customer gets

- **The investigator**: agent code, tool Lambdas, the human-path API, the analyst UI (Streamlit, a reference UI; a firm would embed the calls in its case tool), the policy set, the memory scheme, infrastructure as code (CDK) for the firm's account.
- **A report format** with fixed fields the platform enforces (section 5 of the design doc), in the Annex II vocabulary.
- **The evaluation harness**: run the firm's own labelled alerts, get the gate, the safe close rate, the override rate, per-scenario breakdown, faithfulness, judged quality, regression against the previous configuration, and the promotion rule. This is also the acceptance test at go-live.
- **The learning loop** with its four mechanisms and the promotion rule.
- **Documentation** for the surveillance team (`08-broker-brief.md`), for the regulator conversation (design sections 6-9), and for operating it (`07-resume.md`).

What the customer provides: order events with best bid/ask, trades, trader master, market events, instrument statistics, the alerts, the firm's written procedures, an OIDC identity provider with two groups. Integration is at the data layer (DynamoDB tables in the demo; any store the tool Lambdas can read).

## 6. What it costs to run (list prices, measured consumption)

| Item | Measured | Note |
|---|---|---|
| Model tokens per alert, Sonnet 5.5 | 72k read / 3.1k out, about **$0.09** with Bedrock prompt caching (run v4, 2026-11-10): 73% of what the model reads comes from cache at a tenth of the price | $0.19 without caching (v3); Opus 5.5 without caching: 147k / 4.4k, about $0.68. |
| Latency per alert | 28 s median, 36 s p95 (Sonnet); 51 s / 64 s (Opus) | Ten tool calls per investigation. 85% of the time is the model writing; caching did not change it. |
| Gateway | about 10 InvokeTool calls per alert at $5 per million | cents per thousand alerts |
| Policy | about 10 authorizations per alert at $0.000025 | cents per thousand alerts |
| Runtime | per active session second; one session ends with each investigation | about 30 s per alert |
| Memory | one retrieval per alert; one or two records per recorded decision | small |
| Observability | CloudWatch ingestion of about 40 spans per alert | small |
| Evaluation (acceptance or regression run) | about $15 per 167-alert run on Sonnet without judging (was $31 before caching); about $45 with the built-in judges and the rubric | run per release, not per alert |

A thousand alerts a month on Sonnet is roughly $90 in model tokens plus a few dollars of platform; the analyst time it replaces is the business case. The project itself cost about $390 in model and judge tokens for six full dataset runs, four judged passes, pilots and a recommendation.

## 7. What was measured (the proof points)

| Claim | Number | Source |
|---|---|---|
| Never closes real abuse on the evaluation set | 0 of 28 true-abuse alerts proposed as closed, in every run; the detector's own rules close 6 | data doc 4.6 |
| Closes most false positives | 95.0% (132 of 139) | run `20261110T1833-sonnet-v4`; 93.5% on v3, the difference within run-to-run variance |
| Fewer corrections than the rules | override rate 5.4% vs 7.2% for the threshold rules | same |
| Numbers in reports are real | 99.9% of 4,096 numbers trace to a tool output | `evals/faithfulness.py` |
| Cost halves without touching the decision | $0.187 -> $0.091 per alert, gate and faithfulness unchanged | `compare-v3-v4.md` |
| Holds on alerts nothing was tuned against | second dataset (seed 8, K = 4, 100 alerts): gate 0 of 24, the ten defined scenarios 76 of 76, 86.8% safe close on a mix with twice the boundary cases (92.7% on seed7's mix) | run `20261111T1326-seed8-generalisation` |
| Procedure follows the standard every time | 100% trajectory match on 167 sessions | Builtin.TrajectoryInOrderMatch |
| Improves in governed steps | 79.9% -> 88.5% -> 93.5% safe close across three runs, gate held each time, each step a dated decision | decision log |
| Memory helps and does not bias | +0.7 points; clean-history spoofer caught with and without | `compare-v3-memory.md` |
| Larger model buys little | same override rate at 3.6x cost | `compare-v3-opus.md` |
| Optimization is governed | recommendation rejected by the offline gate; would have produced 0 proposals | `pilot-v2rec` |

## 8. Honest limitations (say these before the buyer finds them)

- **Synthetic data.** The dataset is generated; the numbers above are on it. The harness is built to run on a firm's own labelled alerts, and that run is the acceptance test, not these numbers.
- **One abuse type, one asset class, one venue.** Spoofing and layering in cash equities. Other scenarios need their own discriminators and standard text; the architecture does not change.
- **The confidence figure is the model's own estimate.** It ranks cases well (372 proposals: escalations under 0.65 are the boundary false positives, those at 0.70 and above the spoofs, every close right), but 0.60 does not mean sixty percent and no real reviewer has scored it. The UI shows a band, not a percentage; calibration against recorded Level-2 decisions is a pilot deliverable (data doc 4.6).
- **Measured on two datasets from one generator.** The second (`seed8`) was never used for tuning and the gate and every defined scenario held on it, but both come from the same simulator; the first run on a firm's own alerts is the generalisation test that counts (section 9, roadmap item 2).
- **Not deterministic between runs, and measured.** The same alert can flip between close and escalate on different days (alert E did). Measured 2026-11-11 by investigating 21 alerts five times each: 18 stable, no true-abuse alert ever closed, the three that flipped are the boundary false positives (a fat finger, a news reaction) and the escalation level on one layering case, all at confidence 0.72 or below; on the full set this is about 0.9 points of safe close rate, one standard deviation. Single-alert demos show behaviour; only the dataset run measures it, and a difference under two points between two runs is not read as a change.
- **Stop-outs are escalated.** A trader stopped out at a loss after stacking large one-sided bids looks, in one window, like a failed spoof; attempts are reportable. The product escalates these (safe); whether a firm's standard should close them is the firm's call.
- **Data the customer must have.** The agent reads only the firm's tables and reaches nothing outside them (no web, no external API), which is the auditability promise. It therefore needs the firm's market-event feed with market-time, millisecond timestamps for the news-reaction explanation to work; without it those alerts are escalated, not closed.
- **Throughput.** One analyst's investigations run two at a time within the rate limit; the rate limit is a brake by design. A firm with a large queue sizes the limits and the Runtime accordingly.
- **No regulatory approval is claimed.** The design is meant to be defensible; whether a given NCA accepts agent-written rationales is the compliance officer's question.
- **Vendors are adding AI investigation features.** The claim is narrower: a governed, auditable layer that works beside any detector, for firms that will not buy a tier-1 platform.

## 9. Roadmap, in the order a customer would ask for it

1. Pin a `demo` endpoint; Greek and English decks (Phase 6).
2. Run the harness on a pilot customer's labelled alerts; the firm's own procedures text; acceptance = the gate.
3. A retrying MCP client is in (v12); next, a Gateway A/B test with an online evaluation config for firms that want live comparison of two bundles.
4. Overnight pre-investigation of the queue (detector event -> Runtime under a service identity), so reports are ready when the analyst arrives. Needs its own Policy statements for the machine principal and changes the record from "investigated by analyst X" to "pre-investigated by the system, decided by X". Offered as an option, not the default.
5. Second abuse type (wash trades or marking the close) as a new set of discriminators and standard paragraphs.
6. L2 reviewer agent over A2A that challenges the L1 report; publication in the Agent Registry.
7. Code Interpreter for the price-path chart in the report.
8. Cost and latency pass: fold alert, procedures and memory recall into one `get_case_context` tool (one or two model turns fewer, about 8-15% of tokens and 2-4 s per alert), keeping `recall_memory` for targeted follow-ups; decided on the customer's data with the harness, since it trades the separate memory switch and a Policy handle for the saving (design doc section 7).

## 10. The one-page story for a sales conversation

Your detector raises 150 alerts a month and 130 of them are your own market makers and algos. Each one still takes an analyst half an hour and a written note. This runs the analyst's first pass in 30 seconds, in your account, under your written standard, and hands your analyst a report with every number sourced, every legitimate explanation ruled in or out, and a proposal. It cannot record anything: the platform has no such tool for it, and the rule engine refuses a proposal made before the evidence was read. On a labelled test set it closed 93.5% of false positives, closed no real spoofer, and disagreed with the ground truth on 1 alert in 15, while the detector's own rules, which close more, closed six spoofers. Every investigation leaves the trace the regulation asks for. When you correct it, the correction is stored, shown to it next time, and becomes a test case. When we change it, the change ships only if it still closes no real abuse on your test set.
