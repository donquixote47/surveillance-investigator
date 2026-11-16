# Dataset run `20261116T1828-sonnet-v5`

- Dataset `seed7`, 167 alerts (28 TRUE_ABUSE, 139 FALSE_POSITIVE); backend `runtime`, model `eu.anthropic.claude-sonnet-5-5`, analyst `L1`, mode `investigate`, memory on, bundle none (code defaults), concurrency 2.
- Started 2026-11-16T18:28:06+00:00, finished 2026-11-16T19:23:49+00:00 (55.7 min).
- Notes: review hardening of 2026-11-16: Runtime v17 on DEFAULT (guard asks for evidence that returned a result, stop on a decided alert, proposal provenance, alert_id to the market and history tools, large_orders clause in the prompt) on the tools Lambda and the firm's standard of that date (large_orders block, five new sentences in the closure and escalation standards, priors-only history, Memory hides the alert's own recorded decision); the three decided seed7 alerts reopened for the run and restored after; compared with promoted v4

## Headline

| metric | value |
|---|---|
| gate | **holds** (0 TRUE_ABUSE proposed CLOSE_FP) |
| safe close rate | 94.2% (131 of 139 false positives closed) |
| escalation precision | 77.8% (36 ESCALATE/DRAFT_STOR) |
| strong-call precision | 100.0% (1 DRAFT_STOR) |
| agreement with label (exact disposition) | 94.0% |
| **override rate** (1 - agreement) | **6.0%** |
| direction agreement (close vs not-close) | 95.2% |
| proposals | {'CLOSE_FP': 131, 'ESCALATE': 35, 'DRAFT_STOR': 1} |
| run status | {'ok': 167} |
| configuration bundle reported by the agent | none |
| latency, agent p50 / p95 | 28.5 s / 41.5 s (wall p50 34.4 s) |
| tokens per alert, in / out (mean) | 11 / 2961 (max in 12) |
| prompt cache, per alert | read 53520 / write 21796 / full price 11 tokens; hit rate 0.711 of 75327 prompt tokens |
| tool calls per alert (mean / median) | 10 / 10 |
| estimated model cost | $15.84 total, $0.095 per alert (assumed $2.0/$10.0 per M tokens in/out; cache read 0.1x, write 1.25x of input; not verified against the pricing page) |

## Against the baselines (same alerts)

| scorer | gate | safe close rate | raw safe close | escalation precision | agreement | override rate |
|---|---|---|---|---|---|---|
| agent (this run) | holds | 94.2% | 94.2% | 77.8% | 94.0% | 6.0% |
| threshold baseline (detector rules) | 6 missed | n/a | 95.7% | 78.6% | 92.8% | 7.2% |
| escalate everything | holds | 0.0% | 0.0% | 16.8% | 15.0% | 85.0% |
| close everything (the gate at work) | 28 missed | n/a | 100.0% | n/a | 83.2% | 16.8% |

## Confusion: expected (rows) x proposed (columns)

| expected \ proposed | CLOSE_FP | ESCALATE | DRAFT_STOR | none |
|---|---|---|---|---|
| CLOSE_FP | 131 | 8 | 0 | 0 |
| ESCALATE | 0 | 25 | 0 | 0 |
| DRAFT_STOR | 0 | 2 | 1 | 0 |

## Per scenario

| scenario | truth | expected | n | CLOSE_FP | ESCALATE | DRAFT_STOR | none | agreement | mean conf | gate misses |
|---|---|---|---|---|---|---|---|---|---|---|
| S-LAYER-1 | TRUE_ABUSE | ESCALATE | 5 | 0 | 5 | 0 | 0 | 100% | 0.73 | - |
| S-SPOOF-1 | TRUE_ABUSE | ESCALATE | 7 | 0 | 7 | 0 | 0 | 100% | 0.71 | - |
| S-SPOOF-2 | TRUE_ABUSE | DRAFT_STOR | 3 | 0 | 2 | 1 | 0 | 33% | 0.69 | - |
| S-SPOOF-3 | TRUE_ABUSE | ESCALATE | 4 | 0 | 4 | 0 | 0 | 100% | 0.69 | - |
| S-SPOOF-4 | TRUE_ABUSE | ESCALATE | 2 | 0 | 2 | 0 | 0 | 100% | 0.7 | - |
| S-SPOOF-5 | TRUE_ABUSE | ESCALATE | 7 | 0 | 7 | 0 | 0 | 100% | 0.73 | - |
| BACKGROUND | FALSE_POSITIVE | CLOSE_FP | 52 | 52 | 0 | 0 | 0 | 100% | 0.89 | - |
| F-ALGO-1 | FALSE_POSITIVE | CLOSE_FP | 24 | 24 | 0 | 0 | 0 | 100% | 0.85 | - |
| F-FAT-1 | FALSE_POSITIVE | CLOSE_FP | 3 | 3 | 0 | 0 | 0 | 100% | 0.77 | - |
| F-ICE-1 | FALSE_POSITIVE | CLOSE_FP | 9 | 9 | 0 | 0 | 0 | 100% | 0.82 | - |
| F-MM-1 | FALSE_POSITIVE | CLOSE_FP | 24 | 24 | 0 | 0 | 0 | 100% | 0.89 | - |
| F-NEWS-1 | FALSE_POSITIVE | CLOSE_FP | 4 | 1 | 3 | 0 | 0 | 25% | 0.6 | - |
| F-PARTIAL-1 | FALSE_POSITIVE | CLOSE_FP | 8 | 8 | 0 | 0 | 0 | 100% | 0.78 | - |
| F-RISK-1 | FALSE_POSITIVE | CLOSE_FP | 3 | 3 | 0 | 0 | 0 | 100% | 0.62 | - |
| F-SPOOFLIKE-HARD-1 | FALSE_POSITIVE | CLOSE_FP | 6 | 6 | 0 | 0 | 0 | 100% | 0.78 | - |
| F-STOP-1 | FALSE_POSITIVE | CLOSE_FP | 6 | 1 | 5 | 0 | 0 | 17% | 0.61 | - |

## Regression against the previous run

Previous run: `20261110T1833-sonnet-v4`. Verdict: **PASS (offline promotion rule)**.

- [x] gate holds
- [x] safe close rate not down by more than 2 points
- [x] no false-positive scenario regressed to 0% close (none)
- [x] evidence faithfulness at least 99% and not down by more than 0.5 points (99.72% of 3976 numbers, previous 99.90%; 100.00% of 589 categorical claims)

| delta | value |
|---|---|
| raw_safe_close_rate | -0.7 pts |
| agreement | -0.6 pts |
| escalation_precision | -2.2 pts |
| direction_agreement | -0.6 pts |
| true_abuse_recall | +0.0 pts |
| gate misses | +0 |

| scenario | agreement delta | close-rate delta |
|---|---|---|
| F-STOP-1 | -17 pts | -17 pts |

## AgentCore Evaluations

167 sessions scored against ground truth generated from the labels (`evals/ground_truth.py`); 0 evaluator error(s). Pass = score 1.0.

| evaluator | n | mean | pass rate | judge tokens in / out |
|---|---|---|---|---|
| Correctness | 167 | 0.93 | 93% | 148,538 / 39,701 |
| GoalSuccessRate | 167 | 0.94 | 94% | 2,961,835 / 60,606 |
| TrajectoryAnyOrderMatch | 167 | 1.00 | 100% | programmatic |
| TrajectoryInOrderMatch | 167 | 1.00 | 100% | programmatic |
| surv_rationale_rubric | 167 | 0.61 | 0% | 4,039,258 / 239,371 |

| scenario | Correctness | GoalSuccessRate | TrajectoryAnyOrderMatch | TrajectoryInOrderMatch | surv_rationale_rubric |
|---|---|---|---|---|---|
| BACKGROUND | 1.00 | 1.00 | 1.00 | 1.00 | 0.60 |
| F-ALGO-1 | 0.96 | 1.00 | 1.00 | 1.00 | 0.57 |
| F-FAT-1 | 1.00 | 1.00 | 1.00 | 1.00 | 0.25 |
| F-ICE-1 | 1.00 | 1.00 | 1.00 | 1.00 | 0.58 |
| F-MM-1 | 1.00 | 1.00 | 1.00 | 1.00 | 0.60 |
| F-NEWS-1 | 0.25 | 0.25 | 1.00 | 1.00 | 0.56 |
| F-PARTIAL-1 | 1.00 | 1.00 | 1.00 | 1.00 | 0.47 |
| F-RISK-1 | 1.00 | 1.00 | 1.00 | 1.00 | 0.58 |
| F-SPOOFLIKE-HARD-1 | 1.00 | 1.00 | 1.00 | 1.00 | 0.54 |
| F-STOP-1 | 0.17 | 0.17 | 1.00 | 1.00 | 0.67 |
| S-LAYER-1 | 1.00 | 1.00 | 1.00 | 1.00 | 0.75 |
| S-SPOOF-1 | 1.00 | 1.00 | 1.00 | 1.00 | 0.75 |
| S-SPOOF-2 | 0.33 | 0.33 | 1.00 | 1.00 | 0.75 |
| S-SPOOF-3 | 1.00 | 1.00 | 1.00 | 1.00 | 0.75 |
| S-SPOOF-4 | 0.50 | 1.00 | 1.00 | 1.00 | 0.75 |
| S-SPOOF-5 | 1.00 | 1.00 | 1.00 | 1.00 | 0.75 |

Lowest `Correctness` scores:

- A-261005-0007 = 0: The core disposition differs fundamentally. The expected response calls for CLOSE_FP (close as false positive) with the explanation that this is a legitimate stop-out scenario - the trader lost money, price moved against the resting bids, and there was nothing to revert. The agent instead proposes E
- A-261006-0005 = 0: The critical difference is the disposition. The expected response calls for CLOSE_FP (close as false positive) with the explanation that this is a legitimate momentum trader who was stopped out — price moved against the resting bids, the trader sold at a loss (negative round trip), and there was not
- A-261015-0003 = 0: The critical difference is the proposed disposition. The expected response clearly states 'DRAFT_STOR' as the correct disposition, while the agent proposed 'ESCALATE'. This is a fundamental factual error, not a stylistic difference.  Additionally, the expected response identifies the trader role as 
- A-261015-0008 = 0: The critical difference is the proposed disposition. The expected response says CLOSE_FP (close as false positive), while the agent proposes ESCALATE. This is a fundamental factual error about the core outcome of the investigation.  The expected response identifies this as a legitimate news-reaction
- A-261016-0003 = 0: The core factual content differs critically between the agent response and the expected response. The expected response proposes CLOSE_FP (close as false positive) with key discriminators including: news event within 200ms before cancels, market-wide cancel storm, and hedge sale preceding the event.

Lowest `GoalSuccessRate` scores:

- A-261005-0007 = 0: The first assertion requires the agent to propose CLOSE_FP, but the agent proposed ESCALATE. This is a clear failure of the first assertion. Additionally, the assertion requires that the report marks the 'momentum trader stopped out' explanation as supported and matching the tape, but the agent mark
- A-261006-0005 = 0: The agent proposed ESCALATE, not CLOSE_FP. The first assertion requires the agent to have called surv___propose_disposition exactly once and proposed CLOSE_FP. The agent clearly proposed ESCALATE with confidence 0.65. This is a direct contradiction of the first assertion. Additionally, the assertion
- A-261015-0003 = 0: The first assertion requires the agent to propose DRAFT_STOR, but the agent proposed ESCALATE instead. The agent explicitly stated 'I did not propose DRAFT_STOR because there is no clear benefit.' This is a clear failure of the first assertion. Regardless of whether other assertions are satisfied, t
- A-261015-0008 = 0: The agent proposed ESCALATE, not CLOSE_FP. The first assertion requires the agent to have called surv___propose_disposition exactly once and proposed CLOSE_FP. The agent instead proposed ESCALATE with confidence 0.60. This is a direct failure of the primary success assertion. Additionally, the repor
- A-261016-0003 = 0: The first assertion requires the agent to propose CLOSE_FP, but the agent proposed ESCALATE. This is a direct contradiction of the required disposition. The agent also failed to mark the news event as a supported legitimate explanation - instead treating it as 'undetermined' because the sale came be

Lowest `surv_rationale_rubric` scores:

- A-261006-0009 = 0: Clarity: the summary is easy to follow. A 12,210 BUY order (4.98x depth) rests at the touch at 9999. It takes fills, then the 366 SELL at 10001 executes at 14:20:29.681. A 4,198 MODIFY reduction follows at 14:20:31.681, and the order then fills to completion. The disposition rests on the genuine-exe
- A-261006-0014 = 0: Strengths: the report gives the core sequence clearly. A BUY of 21,230 at 9999 (bid 10000) was placed at 15:24:55.884 and cancelled at 15:24:56.827. A BUY of 2,123 at the same price followed at 15:24:57.227. The report states there was no opposite-side fill, no fill at all and no repetition. Most nu
- A-261014-0001 = 0: Strengths: The report is clear and mostly well grounded. It states the large order's size relative to depth (5.3x) and its placement (10:28:47.852 at 10001, inside the 10000/10004 touch). It gives the fills before the opposite trade (5828, share 0.4666) against the opposite SELL of 374, the MODIFY -
- A-261019-0009 = 0: Most of the report is well grounded. The figures 8.64x depth, 4941 executed before the opposite trade (22.2%), 556 SELL (386+170 at 10003), 17315 cancelled, a cancel about 4s after the trade (3999 ms), price_move 3.5, reversion 0, otr 0.3, cancel_symmetry 0, round_trip 4.0, one repetition, one marke
- A-261006-0001 = 0.25: Strengths: the report gives a readable sequence. Three BUY limits of 4614 rest 1-2 ticks below the bid. A 692 SELL is placed at the ask and fills at 09:28:52.795. All BUYs are cancelled at 09:28:53.795, the same timestamp as a recorded kill-switch event. Most figures trace to tool results: 5.649x de

## Disagreements with the label (10)

| alert | scenario | expected | proposed | conf | status | summary |
|---|---|---|---|---|---|---|
| A-261015-0003 | S-SPOOF-2 | DRAFT_STOR | ESCALATE | 0.7 | ok | PROP-EQ trader T-X1015-02 placed one SELL limit of 21443 (8.17x depth) at 10000, 2 ticks from the touch, with nothing on the other side. 2.4s later he bought 11 |
| A-261016-0006 | S-SPOOF-2 | DRAFT_STOR | ESCALATE | 0.65 | ok | PROP trader placed one BUY LIMIT of 21860 (8.8x avg top-5 depth) 3 ticks below the touch, with nothing on the other side. 2.1s later a SELL market order of 1329 |
| A-261015-0008 | F-NEWS-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader placed two BUY orders of 7,215 each (14,430 total, about 5.5x top-5 depth, about 14x typical size 500) at 9996, 1.5 ticks from the touch. A SELL of  |
| A-261016-0003 | F-NEWS-1 | CLOSE_FP | ESCALATE | 0.65 | ok | Prop trader (no MM registration) rested two identical one-sided BUY orders of 6680 at 9997 (combined 5.37x depth, 1.5 ticks off touch). While they rested, the t |
| A-261016-0005 | F-NEWS-1 | CLOSE_FP | ESCALATE | 0.55 | ok | Prop trader placed two one-sided BUY limits of 7,162 each (14,324 total, 5.76x avg top-5 depth) at 9999, 1.5 ticks from the touch. They rested about 27-30s with |
| A-261005-0007 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader T-X1005-04 bought 1132 at market (13:20:37), then placed three one-sided BUY limits of 4077 each (12231 total, 5.04x depth, 4-6 ticks behind the tou |
| A-261006-0005 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.65 | ok | PROP-EQ trader (no MM registration) bought 947 at market (10002-10005), then placed three one-sided BUY limits of 3810 each at 9994/9993/9992 (total 11430, 4.66 |
| A-261026-0003 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader bought 1118 at market (12:36:13), then placed three one-sided BUY limits of 4024 each (12,072 total, 4.87x depth) at 9996/9995/9994, 5-7 ticks below |
| A-261027-0008 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader bought 1254 at market (13:50:44, filled at 10005), then placed three one-sided BUY limits of 4514 each (13542 total, 5.4x depth) at 9998/9998/9997,  |
| A-261028-0011 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader bought 1476 by market order at 16:57:25, then placed three one-sided BUY limits of 5313 each (15939 total, 6.5x depth, 6 ticks off the touch, 2 pric |
