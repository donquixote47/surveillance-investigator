# Dataset run `20261110T1833-sonnet-v4`

- Dataset `seed7`, 167 alerts (28 TRUE_ABUSE, 139 FALSE_POSITIVE); backend `runtime`, model `eu.anthropic.claude-sonnet-5-5`, analyst `L1`, mode `investigate`, memory on, bundle none (code defaults), concurrency 2.
- Started 2026-11-10T18:33:47+00:00, finished 2026-11-10T19:29:54+00:00 (56.1 min).
- Notes: iteration 3: ruled_out folded into ruled_out_by (guard rejections) + Bedrock prompt caching via Strands CacheConfig (system, tools, last user message); Runtime v14 on DEFAULT; compared with promoted v3

## Headline

| metric | value |
|---|---|
| gate | **holds** (0 TRUE_ABUSE proposed CLOSE_FP) |
| safe close rate | 95.0% (132 of 139 false positives closed) |
| escalation precision | 80.0% (35 ESCALATE/DRAFT_STOR) |
| strong-call precision | 100.0% (1 DRAFT_STOR) |
| agreement with label (exact disposition) | 94.6% |
| **override rate** (1 - agreement) | **5.4%** |
| direction agreement (close vs not-close) | 95.8% |
| proposals | {'CLOSE_FP': 132, 'ESCALATE': 34, 'DRAFT_STOR': 1} |
| run status | {'ok': 167} |
| alerts with a disposition recorded before this run (visible to the agent through history and Memory) | 3: A-261005-0003, A-261009-0003, A-261016-0003 |
| configuration bundle reported by the agent | none |
| latency, agent p50 / p95 | 27.9 s / 35.3 s (wall p50 33.8 s) |
| tokens per alert, in / out (mean) | 11 / 3125 (max in 14) |
| prompt cache, per alert | read 52691 / write 19811 / full price 11 tokens; hit rate 0.727 of 72514 prompt tokens |
| tool calls per alert (mean / median) | 10.0 / 10 |
| estimated model cost | $15.25 total, $0.091 per alert (assumed $2.0/$10.0 per M tokens in/out; cache read 0.1x, write 1.25x of input; not verified against the pricing page) |

## Against the baselines (same alerts)

| scorer | gate | safe close rate | raw safe close | escalation precision | agreement | override rate |
|---|---|---|---|---|---|---|
| agent (this run) | holds | 95.0% | 95.0% | 80.0% | 94.6% | 5.4% |
| threshold baseline (detector rules) | 6 missed | n/a | 95.7% | 78.6% | 92.8% | 7.2% |
| escalate everything | holds | 0.0% | 0.0% | 16.8% | 15.0% | 85.0% |
| close everything (the gate at work) | 28 missed | n/a | 100.0% | n/a | 83.2% | 16.8% |

## Confusion: expected (rows) x proposed (columns)

| expected \ proposed | CLOSE_FP | ESCALATE | DRAFT_STOR | none |
|---|---|---|---|---|
| CLOSE_FP | 132 | 7 | 0 | 0 |
| ESCALATE | 0 | 25 | 0 | 0 |
| DRAFT_STOR | 0 | 2 | 1 | 0 |

## Per scenario

| scenario | truth | expected | n | CLOSE_FP | ESCALATE | DRAFT_STOR | none | agreement | mean conf | gate misses |
|---|---|---|---|---|---|---|---|---|---|---|
| S-LAYER-1 | TRUE_ABUSE | ESCALATE | 5 | 0 | 5 | 0 | 0 | 100% | 0.69 | - |
| S-SPOOF-1 | TRUE_ABUSE | ESCALATE | 7 | 0 | 7 | 0 | 0 | 100% | 0.7 | - |
| S-SPOOF-2 | TRUE_ABUSE | DRAFT_STOR | 3 | 0 | 2 | 1 | 0 | 33% | 0.69 | - |
| S-SPOOF-3 | TRUE_ABUSE | ESCALATE | 4 | 0 | 4 | 0 | 0 | 100% | 0.72 | - |
| S-SPOOF-4 | TRUE_ABUSE | ESCALATE | 2 | 0 | 2 | 0 | 0 | 100% | 0.7 | - |
| S-SPOOF-5 | TRUE_ABUSE | ESCALATE | 7 | 0 | 7 | 0 | 0 | 100% | 0.71 | - |
| BACKGROUND | FALSE_POSITIVE | CLOSE_FP | 52 | 52 | 0 | 0 | 0 | 100% | 0.88 | - |
| F-ALGO-1 | FALSE_POSITIVE | CLOSE_FP | 24 | 24 | 0 | 0 | 0 | 100% | 0.85 | - |
| F-FAT-1 | FALSE_POSITIVE | CLOSE_FP | 3 | 3 | 0 | 0 | 0 | 100% | 0.72 | - |
| F-ICE-1 | FALSE_POSITIVE | CLOSE_FP | 9 | 9 | 0 | 0 | 0 | 100% | 0.81 | - |
| F-MM-1 | FALSE_POSITIVE | CLOSE_FP | 24 | 24 | 0 | 0 | 0 | 100% | 0.89 | - |
| F-NEWS-1 | FALSE_POSITIVE | CLOSE_FP | 4 | 1 | 3 | 0 | 0 | 25% | 0.65 | - |
| F-PARTIAL-1 | FALSE_POSITIVE | CLOSE_FP | 8 | 8 | 0 | 0 | 0 | 100% | 0.76 | - |
| F-RISK-1 | FALSE_POSITIVE | CLOSE_FP | 3 | 3 | 0 | 0 | 0 | 100% | 0.62 | - |
| F-SPOOFLIKE-HARD-1 | FALSE_POSITIVE | CLOSE_FP | 6 | 6 | 0 | 0 | 0 | 100% | 0.75 | - |
| F-STOP-1 | FALSE_POSITIVE | CLOSE_FP | 6 | 2 | 4 | 0 | 0 | 33% | 0.63 | - |

## Regression against the previous run

Previous run: `20261106T1126-sonnet-v3`. Verdict: **PASS (offline promotion rule)**.

- [x] gate holds
- [x] safe close rate not down by more than 2 points
- [x] no false-positive scenario regressed to 0% close (none)

| delta | value |
|---|---|
| raw_safe_close_rate | +1.4 pts |
| agreement | +1.2 pts |
| escalation_precision | +4.3 pts |
| direction_agreement | +1.2 pts |
| true_abuse_recall | +0.0 pts |
| gate misses | +0 |

| scenario | agreement delta | close-rate delta |
|---|---|---|
| F-NEWS-1 | -25 pts | -25 pts |
| F-FAT-1 | +33 pts | +33 pts |
| F-STOP-1 | +33 pts | +33 pts |

## AgentCore Evaluations

167 sessions scored against ground truth generated from the labels (`evals/ground_truth.py`); 0 evaluator error(s). Pass = score 1.0.

| evaluator | n | mean | pass rate | judge tokens in / out |
|---|---|---|---|---|
| Correctness | 167 | 0.92 | 92% | 152,176 / 39,407 |
| GoalSuccessRate | 167 | 0.95 | 95% | 2,799,342 / 64,005 |
| TrajectoryAnyOrderMatch | 167 | 1.00 | 100% | programmatic |
| TrajectoryInOrderMatch | 167 | 1.00 | 100% | programmatic |
| surv_rationale_rubric | 167 | 0.60 | 0% | 3,826,730 / 248,045 |

| scenario | Correctness | GoalSuccessRate | TrajectoryAnyOrderMatch | TrajectoryInOrderMatch | surv_rationale_rubric |
|---|---|---|---|---|---|
| BACKGROUND | 1.00 | 1.00 | 1.00 | 1.00 | 0.61 |
| F-ALGO-1 | 1.00 | 1.00 | 1.00 | 1.00 | 0.60 |
| F-FAT-1 | 1.00 | 1.00 | 1.00 | 1.00 | 0.25 |
| F-ICE-1 | 1.00 | 1.00 | 1.00 | 1.00 | 0.53 |
| F-MM-1 | 1.00 | 1.00 | 1.00 | 1.00 | 0.59 |
| F-NEWS-1 | 0.25 | 0.25 | 1.00 | 1.00 | 0.69 |
| F-PARTIAL-1 | 1.00 | 1.00 | 1.00 | 1.00 | 0.69 |
| F-RISK-1 | 0.67 | 1.00 | 1.00 | 1.00 | 0.50 |
| F-SPOOFLIKE-HARD-1 | 1.00 | 1.00 | 1.00 | 1.00 | 0.58 |
| F-STOP-1 | 0.33 | 0.33 | 1.00 | 1.00 | 0.46 |
| S-LAYER-1 | 1.00 | 1.00 | 1.00 | 1.00 | 0.40 |
| S-SPOOF-1 | 0.86 | 1.00 | 1.00 | 1.00 | 0.75 |
| S-SPOOF-2 | 0.33 | 0.33 | 1.00 | 1.00 | 0.75 |
| S-SPOOF-3 | 1.00 | 1.00 | 1.00 | 1.00 | 0.69 |
| S-SPOOF-4 | 0.00 | 1.00 | 1.00 | 1.00 | 0.62 |
| S-SPOOF-5 | 1.00 | 1.00 | 1.00 | 1.00 | 0.75 |

Lowest `Correctness` scores:

- A-261005-0007 = 0: The core disposition differs fundamentally. The expected response calls for CLOSE_FP (close as false positive) with a legitimate explanation of 'momentum trader stopped out' - the price moved against the resting bids before the trade, the trader sold at a loss (negative round trip), and there was no
- A-261006-0001 = 0: The agent response correctly identifies the proposed disposition as CLOSE_FP and correctly identifies the kill switch as the primary legitimate explanation. The agent mentions the kill switch at 09:28:53.795 cancelling all resting orders, which aligns with the expected response's mention of a risk-l
- A-261006-0005 = 0: The core factual disagreement is in the proposed disposition. The expected response says CLOSE_FP with the explanation that this is a legitimate 'momentum trader stopped out' scenario. The agent response proposes ESCALATE with confidence 0.62, explicitly stating the momentum-stopped-out explanation 
- A-261012-0003 = 0: The agent response and expected response both propose ESCALATE as the disposition. Both identify the trader as PROP, note the large resting order (agent says 11.8x depth, expected says 8-15x), the opposite-side fill before cancel, and the cancel within 500ms. Both note no legitimate explanation.  Ho
- A-261015-0003 = 0: The critical difference is the proposed disposition. The expected response calls for DRAFT_STOR, while the agent proposes ESCALATE with confidence 0.65. This is a fundamental disagreement on the core action to take.  The expected response states both core spoofing features are present: (a) large res

Lowest `GoalSuccessRate` scores:

- A-261005-0007 = 0: Checking each assertion: 1. 'Agent called surv___propose_disposition exactly once and proposed CLOSE_FP' - The agent proposed ESCALATE, not CLOSE_FP. This assertion FAILS. 2. 'Agent called surv___compute_discriminators and surv___get_trader_profile before surv___propose_disposition' - Both were call
- A-261006-0005 = 0: The success assertions require: (1) surv___propose_disposition called exactly once with CLOSE_FP disposition; (2) compute_discriminators and get_trader_profile called before propose_disposition; (3) all numbers in evidence facts appear in tool results; (4) report names detector window and states whe
- A-261015-0003 = 0: The first assertion requires the agent to have called surv___propose_disposition with disposition 'DRAFT_STOR'. However, the agent proposed 'ESCALATE' with confidence 0.65, explicitly stating it did not propose DRAFT_STOR because 'a clear benefit is not shown.' The tool call confirms disposition='ES
- A-261015-0008 = 0: The success assertions require: (1) agent called surv___propose_disposition exactly once and proposed CLOSE_FP. The agent proposed ESCALATE, not CLOSE_FP. This is a direct contradiction of the first assertion. All other assertions are moot since the first critical one fails - the agent escalated ins
- A-261016-0003 = 0: Let me check each assertion:  1. 'Agent called surv___propose_disposition exactly once and proposed CLOSE_FP.' - The agent called surv___propose_disposition once but proposed ESCALATE, not CLOSE_FP. This assertion FAILS.  2. 'Agent called surv___compute_discriminators and surv___get_trader_profile b

Lowest `surv_rationale_rubric` scores:

- A-261006-0014 = 0: The report is generally well structured. It gives the sequence (NEW 21230 at 15:24:55.884, CANCEL at 15:24:56.827, NEW 2123 at 15:24:57.227), size versus depth (8.66x), distance from the touch, and cancel latency. It lists matched and unmatched indicators and considers market making, algorithmic re-
- A-261013-0003 = 0: The report is well structured. It is ESCALATE, which follows from the procedure: the ladder is one-sided (cancel_symmetry 0.0), several times depth (8.69x), has no same-side fills before the opposite trade, a +2 tick favourable move and 2 ticks of reversion, and no market events, risk events, MM reg
- A-261019-0009 = 0: The report is mostly well grounded and the logic is coherent. It identifies an AGENCY trader with a BUY ICEBERG of 22256 at the touch. That order took 4941 in fills (share 0.222) before any opposite trade, and same_side_fill_qty_after_opposite_trade was 0. The SELL sat under a different parent (B vs
- A-261028-0008 = 0: Clarity: the report is clear. A reviewer can follow the sequence without the tape: five 5,708-lot BUY layers at 9985–9989 against a 9990 bid, entered within 60 ms; a SELL market order filled 649 at 9991; then all BUY layers were cancelled. Size relative to depth (11.73x) and the context (PROP role, 
- A-261009-0007 = 0.25: The report is clearly structured. It gives the sequence explicitly: NEW 18930 @9997 at 15:53:42.835, CANCEL at 43.638, NEW 1893 at 44.038. It states size relative to depth (7.9x) and the absence of any fill.  The disposition is broadly coherent. Per the closure standard, an entry error needs a one-o

## Disagreements with the label (9)

| alert | scenario | expected | proposed | conf | status | summary |
|---|---|---|---|---|---|---|
| A-261015-0003 | S-SPOOF-2 | DRAFT_STOR | ESCALATE | 0.65 | ok | Prop trader T-X1015-02 placed a single one-sided SELL limit of 21443 (8.17x avg top-5 depth, 2 ticks from touch) at 11:04:43.303, then sent a 1189 MARKET BUY at |
| A-261016-0006 | S-SPOOF-2 | DRAFT_STOR | ESCALATE | 0.7 | ok | PROP-EQ trader (no MM registration) placed one BUY LIMIT of 21,860 (8.8x avg top-5 depth) 3 ticks below the touch, then 2.1s later sold 1,329 by market order (1 |
| A-261015-0008 | F-NEWS-1 | CLOSE_FP | ESCALATE | 0.62 | ok | PROP trader placed two identical BUY limits of 7,215 (5.5x avg top-5 depth, ~14x typical size 500) at 9996, 1-4 ticks below the touch, held them ~30s with no fi |
| A-261016-0003 | F-NEWS-1 | CLOSE_FP | ESCALATE | 0.7 | ok | Two BUY limit orders of 6680 each (5.37x avg top-5 depth) rested one-sided at 9997, 1.5 ticks from the touch, for ~27-30s with no fills. The trader sold 477 at  |
| A-261016-0005 | F-NEWS-1 | CLOSE_FP | ESCALATE | 0.6 | ok | PROP trader (no MM registration) rested two BUY LIMITs of 7,162 each at 9999 (14,324 total, 5.76x avg top-5 depth, 1.5 ticks from touch, one-sided), sold 511 at |
| A-261005-0007 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | PROP trader (no MM registration) bought 1132 at market (13:20:37), then placed three one-sided 4077 BUY limits (~5x depth, 6 ticks from touch) at 13:20:39-43, s |
| A-261006-0005 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.62 | ok | Prop trader T-X1006-03 placed three one-sided BUY limits of 3810 each (11430 total, max 4.66x top-5 depth) at 9994/9993/9992, 6 ticks from the touch, over 4s. N |
| A-261022-0003 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | PROP trader bought 1333 by market order (13:16:57, 10003-10004), then placed three one-sided BUY limits of 4800 each (14400 total, up to 5.7x top-5 depth, 5-6 t |
| A-261027-0008 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.7 | ok | PROP trader with no market-making registration placed three one-sided BUY limit orders (3 x 4514 = 13542, max 5.4x top-5 depth, 6 ticks from touch) between 13:5 |
