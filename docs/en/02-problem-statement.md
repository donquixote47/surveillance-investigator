# 02 - Problem statement

## The problem in one paragraph

Every broker, investment firm and algorithmic trading firm in the EU must monitor its order flow for market manipulation and report suspicious orders and transactions (MAR Art. 16(2); RTS 6 Art. 13 for algorithmic traders). The monitoring is done by rule-based detectors that are tuned for recall, so they produce many alerts, the large majority of which are legitimate activity: market making, algorithmic re-pricing, risk cuts, reactions to news. Each alert must still be reviewed by a trained person, and the reasoning behind each closure must be recorded and kept for the regulator. At a mid-sized firm this is a small compliance team working through a queue every morning, spending minutes per alert on the same evidence-gathering steps: pull the order book around the alert, check who the trader is and what they normally do, check whether anything happened in the market at that moment, compare the pattern to the firm's definition of spoofing, write a paragraph. The cost is analyst time and attention; the risk is the true case buried in a queue of false positives.

## Why it is unsolved for the firms we care about

Large banks have bought or built alert-reduction technology: better thresholds, trader profiling, machine-learning scoring of alerts, and recently vendor "AI" features that pre-fill case notes. Mid-sized brokers, prop firms and HFT firms, which are George's customers, typically have:

- a vendor surveillance platform with default or lightly tuned scenarios, producing a high false-positive rate;
- one to five people in compliance, often not full-time on surveillance;
- no data science team to build and validate a scoring model, and no appetite to defend one to a regulator;
- a regulator that expects "human analysis by appropriately trained staff" and records of that analysis (2016/957).

What they do not have is a way to make each alert cheaper to resolve without removing the human, and without buying a tier-1 platform.

## What "solved" looks like

A tool that sits after the detector and before the analyst:

1. Takes an alert and the raw order and trade events around it.
2. Gathers the evidence an L1 analyst would gather, through governed tools: order-book reconstruction, trader profile and role, trader's alert history, market events in the window, instrument statistics.
3. Computes the discriminators deterministically: order-to-trade ratio, cancel latency, size relative to depth, distance from the touch, opposite-side fills, price move and reversion, symmetry of cancels across sides.
4. Writes an investigation report in the vocabulary of the firm's procedures and the regulation's indicators, citing the evidence it used.
5. Proposes one disposition: close as false positive, escalate, or draft STOR narrative. States what would change its mind.
6. Records nothing. The analyst reads, edits if needed, and records the disposition. The analyst's decision and any correction go back into the tool's memory for next time.
7. Leaves a complete trace: which tools were called with which inputs, which policy rules allowed or denied each call, and what the agent concluded. That trace is the record the regulation asks for.

## Why an agent, not a model

A classifier scores an alert. It cannot explain, cannot look for the one more fact that would change its mind, and cannot write the paragraph the regulator will read. A rule engine handles the structured discriminators well but not the judgement that combines them with context ("this trader is a registered market maker on this name, cancels were two-sided, the mid moved 3 ticks on the macro print at 14:30:00, so the cancels at 14:30:00.4 are consistent with re-pricing"). The analyst's job is exactly that combination, and it is sequential: each finding decides what to look at next. That is agent work.

The agent does not replace the deterministic parts. Metric computation, threshold checks and book reconstruction are code, called as tools, so the numbers in the report are reproducible and the LLM is used for sequencing, interpretation and writing.

## Why AgentCore specifically

Compliance teams and model-risk functions block general-purpose agents in this setting for concrete reasons. Each one maps to a platform capability, which is the point of the project:

| Objection | Answer in the design |
|---|---|
| "The agent could close an alert on its own." | It has no tool that records a disposition. AgentCore Policy at the Gateway forbids the action for the agent's identity; a human with an L1 or L2 identity records it through a different path. |
| "The agent could write a conclusion without looking at the evidence." | A temporal policy permits `propose_disposition` only after the evidence tools have returned responses in the same session. The denial is logged. |
| "We can't prove why it decided." | Every tool call, input, output and policy decision is in Observability traces and policy logs. The report cites evidence ids that resolve to tool outputs. |
| "It will learn the wrong lesson from one analyst's mistake." | Memory holds analyst decisions and feedback per trader and instrument, but the policy requires current-window evidence; memory can inform, not decide. The evaluation harness checks that reports cite current evidence. |
| "Who is allowed to use it?" | Identity: Cognito groups L1 and L2; Gateway inbound JWT; per-user rate limits. |
| "How do we know it is any good, and still good after a prompt change?" | A labelled dataset and AgentCore Evaluations, with the recall-at-100% gate, run before any change is promoted. |
| "Will it improve, or just drift?" | It does not change on its own. Analyst decisions go to Memory and are recalled as worked examples; overrides become new labelled cases; prompt changes come from Optimization recommendations, are A/B tested through the Gateway and promoted only through the deterministic gate; thresholds are re-tuned from labelled data. Every change is versioned and logged (design doc section 11). |

## The metric

Define, over a labelled dataset of alerts where each alert is `true_abuse` or `false_positive`:

- **Gate (must hold):** zero `true_abuse` alerts proposed as `close_fp`. Equivalently, recall on true abuse = 100%.
- **Primary:** share of `false_positive` alerts proposed as `close_fp`. Call it the **safe close rate**.
- **Secondary:** share of `true_abuse` proposed as `draft_stor` rather than `escalate` (precision of the strong call); rationale quality against a rubric; evidence faithfulness (every number in the report appears in a tool output); tool-trajectory compliance; latency and cost per alert.

If the gate fails on any run, the safe close rate for that run is reported as "not applicable" rather than as a number. This is deliberate: a tool with 80% safe close and one missed spoofer is worse than a tool with 40% safe close and none missed, and the reporting must not hide that.

## Who the buyer would be, if this were a product

- **Primary:** head of compliance at a mid-sized EU broker, CFD/FX broker, or prop trading firm with an existing surveillance platform and an alert backlog. Budget authority, regulatory pain, small team.
- **Secondary:** compliance consultants and outsourced compliance providers who run surveillance for several small firms.
- **Not the buyer:** tier-1 banks (already served by NICE Actimize, Nasdaq and their own teams), and firms with no surveillance platform (they need a detector first).

Positioning in one line: *we do not detect market abuse; we investigate the alerts your detector already raises, and we leave the decision with your analyst.*

## What this project does not claim

- It does not claim to reduce false positives at the detector. It reduces the cost of resolving them.
- It does not claim regulatory approval or that any regulator has accepted agent-written rationales. The design is meant to be defensible; whether a given NCA accepts it is a question for a firm's compliance officer.
- It does not claim a market gap nobody has seen. Vendors are adding AI investigation features. The claim is narrower: for mid-sized firms, a governed, auditable investigation layer that works alongside any detector is useful and, as far as we have checked, not well served. Verify the current vendor feature set before presenting (`01-domain-primer.md` section 3.1).
