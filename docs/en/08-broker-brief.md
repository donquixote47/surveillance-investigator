# 08 - How the investigator works: a brief for a broker's surveillance team

Written for a head of compliance or a surveillance analyst at a mid-sized broker, prop firm or market maker. No model internals, no code. Every statement here is what the deployed system does on 2026-11-07 (Runtime v12); the measurements are from the full runs described in `04-synthetic-data-and-evaluation.md` section 4.6.

## 1. In one paragraph

Your detector raises spoofing and layering alerts; most are legitimate activity. This tool does the Level-1 analyst's first pass on each alert: it pulls the trader's order and trade events around the alert, computes the numbers an analyst computes (order-to-trade ratio, size versus depth, distance from the touch, who executed on which side and when, price move and reversion, round-trip P&L, repetitions), reads the trader's profile and alert history, checks for market events, applies **your firm's written closure and escalation standards**, and writes a report in the regulation's vocabulary that proposes one of three dispositions: **close as false positive**, **escalate to Level 2**, or **draft a STOR**. It records nothing. Your analyst reads the report, agrees or overrides, and records the decision with a note. The analyst's decision and note become part of what the tool knows about that trader and desk next time. Every tool call, every number, every rule that allowed or refused an action is in an audit trace a regulator can open.

## 2. What the alert goes through

| Step | What happens | Who or what does it |
|---|---|---|
| 1 | Detector raises an alert (trader, instrument, window, trigger). | Your detector (a naive two-trigger rule in the demo). |
| 2 | Analyst opens the queue, picks an alert, presses "Investigate". Nothing starts an investigation on its own: no scheduler, no trigger from the detector. | Level-1 analyst, logged in with their own credentials. |
| 3 | The investigator reads the alert, then **the firm's procedures** (definition of spoofing, closure standard, escalation standard) and what analysts recorded before about this trader, desk and instrument. | Agent, through governed tools. |
| 4 | It pulls the evidence: the trader's raw order events in the window (with the best bid and ask before each), the deterministic discriminators, the trader's profile (role, desk, registered market-making instruments, typical size, risk-limit events), market events in the window, instrument statistics (depth, spread), and the trader's alert history. The order book around the window can be reconstructed if the price picture is unclear. | Agent, through governed tools. Every number comes from code, not from the model. |
| 5 | It considers every legitimate explanation the firm accepts (section 4), gives each a verdict with the evidence that rules it in or out, and tests the two core features of spoofing against the tape. | Agent, applying the firm's standard. |
| 6 | It proposes **one** disposition with a confidence, a report, and "what would change my mind". The proposal is written to the case as *proposed*, never as decided. | Agent; the platform allows this call only after the evidence calls have completed. |
| 7 | The analyst reads the report and the trace, records **CLOSE_FP** or **ESCALATE** (Level 1) or **DRAFT_STOR** (Level 2 only) with a mandatory note. If the decision differs from the proposal, it is flagged as an override. | Human, through a separate path the agent cannot reach. |
| 8 | The decision and the note are stored per trader and per desk; the next investigation on that trader or desk sees them as context. The analyst can also leave free-text feedback ("treat a cancel within 200 ms of unscheduled news as a news reaction"). | Human path writes; agent reads next time. |

Time per alert: about 30 seconds on the default model (27 s median, 38 s at the 95th percentile in the last full run). Cost per alert: about $0.19 in model tokens at list prices.

## 2a. Where the data comes from, and when

The agent reads only the firm's own tables. It has no tool that reaches outside them: no internet, no web search, no external API. The closed tool list (section 5) is what makes that a guarantee and not a habit. The reason is auditability: "the agent found on the web that news came out at 14:30" cannot be checked five years later; "the firm's news feed recorded this headline for this ISIN at 14:30:00.187" can.

| Table the agent reads | In the demo | In production, fed by |
|---|---|---|
| Order events (with best bid/ask before each) and trades | simulator, 20 days, 1.8 M events | the order-record keeping the firm already does under MiFID II (RTS 25 clock-synchronised timestamps) |
| Trader master: role, desk, market-making registrations, typical size, risk-limit events | simulator | compliance and risk; the registrations from the venue agreements |
| Alerts | the demo's naive detector | the firm's surveillance platform |
| Alert history and recorded decisions | simulator seed + what analysts record in the tool | the tool itself, from day one |
| Instrument statistics (average depth, spread, tick size) | simulator | computed from the firm's own market data |
| Market events: open/close, scheduled macro prints, unscheduled issuer news, halts | simulator (92 events in 20 days) | the market data feed and the news feed the firm already pays for (exchange announcements, RNS, Bloomberg/Refinitiv headlines) |

**Timing.** The flow is T+1, the way this kind of surveillance usually runs: the session closes, the day's orders, trades and market events are loaded in the evening, the detector runs over the completed day and fills the queue, and the next morning the analyst investigates. Everything the agent needs for an alert exists before the alert is opened. A firm with intraday surveillance would feed the tables continuously; the agent does not change, since it only asks for what happened in the alert's window. The demo loads all twenty days once and lets the analyst pick a session day.

**One requirement to check with the first customer.** The news-reaction discrimination rests on "cancel 187 ms after the headline". That needs the time the headline reached the market, not the editorial time, with millisecond precision in the same clock as the orders. Market data feeds provide it; not every firm stores it. Without it, news reactions are escalated rather than closed, which is the safe failure.

## 2b. The three outcomes, and who can produce each

Every alert ends in exactly one disposition.

| Disposition | What it says | Who may propose | Who may record |
|---|---|---|---|
| **CLOSE_FP** (close as false positive) | The detector was wrong. A legitimate explanation covers what it saw, and the two features of spoofing are absent. The case closes at Level 1 with its note and evidence and is kept for five years. This is where 80-95% of alerts belong, which is why the safe close rate is the number we optimise. | the agent | L1 or L2 |
| **ESCALATE** | Cannot be closed in good conscience, but not clear-cut abuse either: the features are present with no supported explanation, or the evidence is mixed. A Level-2 analyst takes it further. This is the *safe* outcome: an ESCALATE on a false positive costs analyst time; a CLOSE_FP on a spoofer costs a fine. The gate counts only the second mistake. | the agent | L1 or L2 |
| **DRAFT_STOR** | Clear enough to report to the regulator. STOR = Suspicious Transaction and Order Report, the filing MAR Art. 16(2) requires when a firm has reasonable suspicion; it has fixed fields (who, what, when, why suspicious, which Annex II indicators). Needs both features, a clear benefit, and repetition or scale that leaves no reasonable alternative. | the agent (Level 1 may propose it) | **L2 only**; only L2 may ask the agent to draft the STOR fields; nothing is filed by the system |

In the evaluation set, 139 alerts have ground truth CLOSE_FP, 25 ESCALATE and 3 DRAFT_STOR (the spoofer who repeats the cycle three to six times in ten minutes). The promoted run proposed 130 / 36 / 1: it under-called two of the three STOR cases as ESCALATE, which is safe (Level 2 sees them) but counts as an override.

**Can the agent close an alert by itself? No.** When the agent "closes", it calls `propose_disposition` with CLOSE_FP, and the case gets `proposed_disposition`, `proposed_at`, `confidence`, `report` and the status *PROPOSED*. The alert is still open. Closing is the analyst pressing "record", writing the mandatory note, and the human path writing `recorded_disposition`, `recorded_by`, `recorded_at` and the status *CLOSED*. Four layers keep the agent on the proposing side:

1. There is no recording tool among the twelve on its gateway.
2. Rule 02 denies any action outside the twelve; a recording tool added by mistake tomorrow is denied until someone lists it on purpose.
3. The tools Lambda has no code path that writes `recorded_*`; a unit test asserts it.
4. The recording API is a different Lambda behind a different gateway, which the tools gateway's role cannot invoke, and the agent's only tools are the gateway's: it has no generic HTTP or code-execution tool. **This is the layer to protect when the agent is extended:** the analyst's token would be accepted by the recording API, so a general-purpose HTTP tool given to the agent "for convenience" would hand it the ability to record. Any new tool goes through the gateway or not at all.

**What can still go wrong, as in any system with a human in the loop.** The agent can propose CLOSE_FP on a real spoofer; nothing forbids a wrong judgement, nor should it. That is what the gate measures (zero such proposals on 167 alerts in every run) and why the analyst reads before recording. If an analyst records without reading, the tool does not prevent the error; it makes it faster. That is a question of the firm's procedure and supervision, the same as for any Level-1 process, and it should be said plainly rather than hidden behind the controls above.

## 3. The firm's standard is the decision logic

The agent does not carry its own theory of spoofing. On every alert it first reads the firm's three procedure texts through a tool, and the report has to apply them. In the demo these texts are synthetic but written the way a mid-sized firm's manual reads, aligned with Delegated Regulation (EU) 2016/522 Annex II (indicator 5(e) and supplementary indicator 4(f)), Delegated Regulation (EU) 2016/957 (record-keeping) and Delegated Regulation (EU) 2026/788 (time frames). The texts live in one file (`src/tools/procedures.py`) and are also stored in the agent's memory; a firm would replace them with its own.

**Definition.** Spoofing is one or more orders on one side, typically away from the touch and large relative to visible depth, that the trader does not intend to execute, placed to move other participants' prices and execute on the other side, then removed once the opposite-side trade has taken place. Layering is the same with orders spread over several price levels. Attempts are reportable (MAR Art. 15). The analyst must state the window used.

**Closure standard (Level 1 may close only when all of this holds).** The record shows, with reference to the tape, at least one accepted legitimate explanation that accounts for the pattern **and** the absence of the two core features in the window: (a) a resting order the trader did not intend to execute, and (b) a benefit to the trader from an opposite-side execution before that order was removed. The accepted explanations, each with the evidence it needs:

| Explanation | What must be on the tape |
|---|---|
| Registered market making | Registration on the instrument; two-sided quoting; cancels follow re-quotes; sizes typical for the desk. The spread earned between the firm's own bid and ask executions is ordinary income, not feature (b). |
| Algorithmic re-pricing | Pegged or child orders of a parent; cancels symmetric with the touch. |
| Risk-system cancellation | A risk event recorded; all sides pulled together; no beneficial opposite fill. |
| Market-wide reaction to a public event | The event recorded; other participants cancelling in the same second. |
| Genuine execution of the resting order | Partial executions, iceberg replenishment, size reduction after a partial. The test is the **order of events**: executions on the resting order *before* the trader's first opposite-side trade show an order that was working; executions that arrive only *after* it, followed by the cancel, are a spoofer caught in the book. Hidden (iceberg) orders cannot move prices. For an agency trader, different parent order ids are different clients. |
| Evident entry error | One-off, cancelled within seconds, no opposite execution, a corrected order follows. |
| Position closed at a loss after an adverse move | No favourable move before the trader's trade, negative round trip, no reversion. |

How the pieces fit: a supported explanation is what shows feature (a) absent, because it gives the resting order a purpose other than moving the price. Feature (b) is a **benefit**: an opposite-side execution at a price the one-sided resting order moved in the trader's favour (with reversion after the cancel), or a positive round trip earned off a one-sided resting order. An opposite-side execution with no favourable move and no reversion is an ordinary trade. Size alone is not a feature. Prior dispositions are context and never a sufficient reason to close. Every closure records the analyst, the time, the evidence cited and the explanation relied upon, kept for five years.

**Escalation standard.** Escalate when the core features are present and no accepted explanation is supported, or when the evidence is mixed. Level 1 may *propose* a STOR draft when the pattern also repeats within or across sessions, or the profile offers no legitimate reason for one-sided large resting orders; only Level 2 records that decision and decides on filing under MAR Art. 16(2).

Two of these sentences were added during evaluation because the agent read the first version too strictly (it refused to close icebergs that had traded, and treated a market maker's one-tick spread as a benefit). Each change was made in the firm's text, not in the model's instructions, so every analyst reads the same rule. The history is in `decision-log.md` (2026-11-05, 2026-11-06, 2026-11-07).

## 4. What the report contains

The analyst sees, for every alert, a report with fixed fields. The platform refuses a proposal that lacks any of them.

- **Summary**: one paragraph a Level-2 reviewer can read in 30 seconds, with the sequence of events, sizes relative to depth and times.
- **Evidence**: at least three facts, each with the tool it came from and the number as the tool returned it. In the last full run 99.9% of 4,132 numbers in these facts matched a tool output exactly or by rounding; the remainder were derived figures (a "142 ms" difference), none invented.
- **Indicators matched / not matched**: in the Annex II vocabulary (size versus depth, orders away from the touch, opposite-side execution before the cancel, high order-to-trade ratio, several price levels, repetition).
- **Legitimate explanations considered**: each of the seven with a verdict (supported, ruled out, undetermined) and the evidence ids behind the verdict.
- **Proposed disposition and confidence**: the agent's probability that Level 2 would record the same disposition.
- **What would change my mind**: the fact that would flip the proposal, so the analyst knows what to look for.
- **Memory used**: which prior dispositions, overrides or feedback it relied on, quoted, and what it did with them ("same explanation holds on today's tape, checked against the tape, not relied on alone").
- **Window used**: the detector window and whether the agent looked beyond it (2026/788 asks for this).
- **Tool trajectory**: filled in by the system from the calls it observed, not by the model.

## 5. What the agent cannot do, and how that is enforced

These are not instructions to the model. They are rules evaluated by the platform (AgentCore Policy, attached to the tools gateway) on every tool call, in the analyst's own identity, and every decision is logged with the rule that fired.

| The agent cannot... | Enforced by |
|---|---|
| Record a disposition. | There is no such tool on its gateway. The recording path is a separate API that only a human's credentials can call. |
| Call any tool the firm has not declared. | A closed allow-list of twelve tools; anything else is denied. |
| Propose before looking. | The proposal is denied unless the alert, the order events, the discriminators, the trader profile and the market events have **completed** in the same investigation, for the same alert. |
| Close without the history. | A CLOSE_FP proposal is denied unless the trader's alert history has been read. |
| Propose twice. | One proposal per alert per investigation. |
| Draft a STOR as Level 1. | Only an identity in the L2 group may call the drafting tool; Level 1 does not even see it in the tool list. |
| Draft a STOR without a DRAFT_STOR proposal. | The drafting tool is permitted only after such a proposal for the same alert. |
| Pull the tape without limit. | At most six pages of order events per investigation; the largest alert window in the dataset fits in one. |
| Flood the back end. | Per-analyst rate limits: 60 tool calls a minute, 3 proposals a minute. These count tool calls, not alerts: an investigation is about ten calls in thirty seconds, so an analyst working normally never meets them. They exist for a looping bug, a leaked credential, or a script, and they are a brake (a burst of 15-20 calls passes before the limit bites), not a counter; the counting rules are Policy's. |

Demonstrated live: a scripted client that tries to propose before gathering evidence is refused with the rule's name ("Policy evaluation denied due to p03b..."); the agent itself, told by an analyst to "just close this quickly", ignores the instruction and runs the full procedure.

## 6. Who can do what

Two roles, carried by the firm's identity provider (Cognito in the demo; any OIDC provider works):

| | Level 1 analyst | Level 2 reviewer |
|---|---|---|
| Run an investigation | yes | yes |
| Record CLOSE_FP, ESCALATE | yes | yes |
| Record DRAFT_STOR | no | yes |
| Ask the agent to draft the STOR narrative | no | yes |
| Leave feedback for memory | yes | yes |

The agent runs *as the analyst*: the analyst's token is forwarded to every tool call, so the gateway, the rules and the rate limits see the person, not the machine.

## 7. The audit record

For each investigation there is one trace, produced as a by-product of running and not written up afterwards. It is the "records of the analysis" that Delegated Regulation (EU) 2016/957 asks for, and it lives in the firm's own AWS account and region.

**What is in it, in three layers.**

| Layer | What it records | Independent of |
|---|---|---|
| Runtime traces (OpenTelemetry, automatic) | About 40 spans per investigation: the invocation, each model turn with token counts, each tool call with its arguments and its **full** output (a 38 KB page of order events is stored whole), and on every span: alert id, analyst, mode, model, configuration bundle, memory on/off. | the Gateway |
| Gateway logs | Every request (tool, arguments, the analyst's identity), every rule decision (allowed or denied, which rule, how long the temporal check took), every error with its exact cause. Written even if someone bypasses the agent and calls the gateway with their own client. | the agent's code |
| The case record | The proposal as written, the analyst's decision, name, time and note, the override flag. | both of the above |

The analyst UI links each case to its trace. Metrics per rule and per tool (how often each rule denied, how many calls per tool) are available for a dashboard; the alpha uses the CloudWatch console.

**What the record is used for besides the regulator.** Every defect found during the build was found here. The evidence-faithfulness check reads the tool outputs from the spans and compares them with the numbers in the report; the quality judges (section 8) read the same spans; the prompt-recommendation service reads the same traces. One record, four consumers.

**Two decisions the firm makes before go-live.**

- *Retention.* The demo keeps Gateway and Lambda logs for 30 days and Runtime traces indefinitely (the default). 2016/957 asks for five years. The options are a five-year retention on the log groups or a scheduled export to S3 with a lifecycle to cold storage, which costs a fraction. Measured size: about 150 KB per investigation; a thousand alerts a month for five years is about 9 GB.
- *Who may read the traces.* Because the spans hold the full tool outputs, a trader's order history, profile and alert history are in the log store. It is the same account and region as the data itself, and it needs the same access controls (who may read the log groups) and, if the firm wants it, the PII masking CloudWatch offers. In the demo the data is synthetic; in production this is a conversation with the data protection officer before the first real alert.

## 8. How it learns, and how it is kept from drifting

Nothing in the model changes on its own. Four governed mechanisms, each with a human in control:

1. **Case memory.** Every recorded disposition, override and feedback note is stored per trader and per desk and shown to the agent on the next alert, marked as context. The memory is the firm's: every analyst's decisions are visible to every later investigation, with the analyst's name and the override flag, so the same trader is treated the same way whoever has the shift; it never leaves the firm's deployment. Recall is one tool call per alert and costs about a quarter of the model tokens, because the recalled notes are re-read at every step of the reasoning. Measured effect over 167 alerts: +0.7 points safe close rate, override rate 6.6% with memory against 7.8% without; the one trader in the evaluation set with six prior closures who then spoofs was escalated both with and without memory.
2. **Overrides become test cases.** Every analyst override is exported as a labelled case with the analyst's note, so the evaluation set grows with the alerts the agent got wrong.
3. **Prompt recommendations are candidates, not changes.** The platform can propose a revised instruction set from the traces. The first recommendation was tested and rejected: it would have stopped the agent before every proposal to ask for approval, and it pushed toward escalating market makers. A change is promoted only if, on the fixed evaluation set, no true-abuse alert is closed, the safe close rate does not fall, and no scenario collapses.
4. **Detector thresholds re-tuned from labelled decisions**, applied to the next dataset only, with the report showing the trade-off. The first report found a threshold that halves the alert queue but sits too close to the smallest injected spoof to be adopted.

## 9. What the measurements say

On a synthetic dataset of 167 alerts over 20 trading days (28 true spoofing or layering cases, 139 false positives of ten kinds: market makers, execution algorithms, icebergs, partial fills, stop-outs, news reactions, fat fingers, risk cuts, a hard look-alike), with the detector's own threshold rules as the comparison:

| | threshold rules | investigator (promoted run) |
|---|---|---|
| True-abuse alerts proposed as "close" | **6 of 28** (partially executed spoofs) | **0 of 28** |
| False positives closed | 95.7% | 93.5% |
| Share of alerts the analyst would have to override | 7.2% | **6.6%** |
| Share of escalations that are real abuse | 78.6% | 75.7% |

Read it this way: the rules close more, but they close six real spoofers, which no compliance function can accept. The investigator closes nearly as many, closes no spoofer, and needs fewer corrections from the analyst. The run before the last two procedure clarifications closed 79.9% with 18.6% overrides; the gain came from the firm's written standard being made precise, which is how a compliance team would want it to come.

Still open: six "stop-out" alerts (a trader who buys, stacks large bids below, is stopped out at a loss and pulls the bids) are escalated, not closed. The agent's reasoning is that a failed spoof and a stop-out look the same in one window and attempts are reportable; the label says close. That is a question for the firm's standard, and it is the safe failure.

## 10. Questions a head of surveillance asks

**Can it close an alert by itself?** No. There is no tool for it and the human path requires a human credential. The proposal is visible as "proposed, awaiting a human decision" until an analyst acts.

**Can it be told to go easy on a desk?** An analyst can leave feedback, and it will be shown to the agent as context, with the analyst's name. The closure standard says prior dispositions are never a sufficient reason to close, the platform still requires current-window evidence before any proposal, and the evaluation set includes a trader with a clean history who spoofs. Overrides are stored with a flag and are visible in the trader's history to every later investigation.

**What does the regulator see?** The trace of section 7, the report with evidence ids that resolve to tool outputs, the rule decisions, the analyst's decision and note, the retention you set.

**Does it replace Level 1?** It does the gathering, the arithmetic and the first draft. The analyst still reads the tape when the report says "mixed", still decides, and still signs. In the measured runs the proposal disagreed with the ground truth, which stands in for the analyst's decision, on 1 alert in 15.

**What if the model is wrong in a new way?** The gate (no true-abuse closed) is computed by code over a labelled set before any change goes live; every change is a versioned, logged step with a rollback. A model that escalates too much costs analyst time; a model that closes a spoofer fails the gate and does not ship.

**Does our data leave our account?** No. Everything runs in the firm's AWS account and region; the model is called through Amazon Bedrock in the same region family (EU inference profiles in the demo).

**What do we have to provide?** Order events with timestamps and best bid/ask, trades, a trader master (role, desk, registrations, typical size), market events, instrument statistics, the alerts, and the firm's written procedures. Section 3 of `03-solution-design.md` has the schemas.

**Which detector does it need?** Any. It investigates the alerts you already have; it does not detect.

**Can it pre-investigate the whole queue overnight, so the reports are ready in the morning?** Not in the alpha, by choice. Today every investigation runs under the analyst who pressed the button, and that is what lets the trace say who did what. An overnight run has no analyst behind it: the agent would run under a service identity, the rules would need their own statements for that identity, and the record would read "pre-investigated by the system, decided by the analyst". Defensible, and a reasonable first customer request; it is on the roadmap with that trade-off stated.

**Does it look at the news?** Only at the market events in your own table (section 2a), with your timestamps. It never reaches outside your data.
