# Dataset run `20261105T1233-pilot`

- Dataset `seed7`, 6 alerts (0 TRUE_ABUSE, 6 FALSE_POSITIVE); backend `runtime`, model `eu.anthropic.claude-sonnet-5-5`, analyst `L1`, mode `investigate`, concurrency 2.
- Started 2026-11-05T12:33:04+00:00, finished 2026-11-05T12:38:12+00:00 (5.1 min).
- Notes: harness pilot: 6 stratified alerts, concurrency 2

## Headline

| metric | value |
|---|---|
| gate | **holds** (0 TRUE_ABUSE proposed CLOSE_FP) |
| safe close rate | 50.0% (3 of 6 false positives closed) |
| escalation precision | 0.0% (3 ESCALATE/DRAFT_STOR) |
| strong-call precision | n/a (0 DRAFT_STOR) |
| agreement with label (exact disposition) | 50.0% |
| **override rate** (1 - agreement) | **50.0%** |
| direction agreement (close vs not-close) | 50.0% |
| proposals | {'ESCALATE': 3, 'CLOSE_FP': 3} |
| run status | {'ok': 6} |
| alerts with a disposition recorded before this run (visible to the agent through history and Memory) | 1: A-261009-0003 |
| latency, agent p50 / p95 | 31.7 s / 44.9 s (wall p50 38.6 s) |
| tokens per alert, in / out (mean) | 80453 / 4025 (max in 131120) |
| tool calls per alert (mean / median) | 10.3 / 10.0 |
| estimated model cost | $1.21 total, $0.201 per alert (assumed $2.0/$10.0 per M tokens in/out; not verified against the pricing page) |

## Against the baselines (same alerts)

| scorer | gate | safe close rate | raw safe close | escalation precision | agreement | override rate |
|---|---|---|---|---|---|---|
| agent (this run) | holds | 50.0% | 50.0% | 0.0% | 50.0% | 50.0% |
| threshold baseline (detector rules) | holds | 100.0% | 100.0% | n/a | 100.0% | 0.0% |
| escalate everything | holds | 0.0% | 0.0% | 0.0% | 0.0% | 100.0% |
| close everything (the gate at work) | holds | 100.0% | 100.0% | n/a | 100.0% | 0.0% |

## Confusion: expected (rows) x proposed (columns)

| expected \ proposed | CLOSE_FP | ESCALATE | DRAFT_STOR | none |
|---|---|---|---|---|
| CLOSE_FP | 3 | 3 | 0 | 0 |
| ESCALATE | 0 | 0 | 0 | 0 |
| DRAFT_STOR | 0 | 0 | 0 | 0 |

## Per scenario

| scenario | truth | expected | n | CLOSE_FP | ESCALATE | DRAFT_STOR | none | agreement | mean conf | gate misses |
|---|---|---|---|---|---|---|---|---|---|---|
| BACKGROUND | FALSE_POSITIVE | CLOSE_FP | 1 | 1 | 0 | 0 | 0 | 100% | 0.72 | - |
| F-ALGO-1 | FALSE_POSITIVE | CLOSE_FP | 1 | 1 | 0 | 0 | 0 | 100% | 0.78 | - |
| F-FAT-1 | FALSE_POSITIVE | CLOSE_FP | 1 | 0 | 1 | 0 | 0 | 0% | 0.6 | - |
| F-ICE-1 | FALSE_POSITIVE | CLOSE_FP | 1 | 0 | 1 | 0 | 0 | 0% | 0.65 | - |
| F-MM-1 | FALSE_POSITIVE | CLOSE_FP | 1 | 1 | 0 | 0 | 0 | 100% | 0.9 | - |
| F-NEWS-1 | FALSE_POSITIVE | CLOSE_FP | 1 | 0 | 1 | 0 | 0 | 0% | 0.65 | - |

## Regression against the previous run

no previous run to compare with

## Evidence faithfulness

6 reports checked against their sessions' tool results (`evals/faithfulness.py`): **83.3% of reports** have every number grounded; 155 of 156 numbers matched (99.4%).

| alert | scenario | proposed | source | unmatched | fact |
|---|---|---|---|---|---|
| A-261015-0008 | F-NEWS-1 | ESCALATE | get_market_events | 142 | NEWS 'issuer announces unscheduled trading update' at 15:13:22.998, 142 ms before the cancels |

## AgentCore Evaluations

6 sessions scored against ground truth generated from the labels (`evals/ground_truth.py`); 0 evaluator error(s). Pass = score 1.0.

| evaluator | n | mean | pass rate | judge tokens in / out |
|---|---|---|---|---|
| Correctness | 6 | 0.50 | 50% | 5,353 / 1,451 |
| GoalSuccessRate | 6 | 0.50 | 50% | 92,144 / 1,594 |
| TrajectoryAnyOrderMatch | 6 | 1.00 | 100% | programmatic |
| TrajectoryInOrderMatch | 6 | 1.00 | 100% | programmatic |
| surv_rationale_rubric | 6 | 0.58 | 0% | 125,907 / 9,651 |

| scenario | Correctness | GoalSuccessRate | TrajectoryAnyOrderMatch | TrajectoryInOrderMatch | surv_rationale_rubric |
|---|---|---|---|---|---|
| BACKGROUND | 1.00 | 1.00 | 1.00 | 1.00 | 0.50 |
| F-ALGO-1 | 1.00 | 1.00 | 1.00 | 1.00 | 0.25 |
| F-FAT-1 | 0.00 | 0.00 | 1.00 | 1.00 | 0.50 |
| F-ICE-1 | 0.00 | 0.00 | 1.00 | 1.00 | 0.75 |
| F-MM-1 | 1.00 | 1.00 | 1.00 | 1.00 | 0.75 |
| F-NEWS-1 | 0.00 | 0.00 | 1.00 | 1.00 | 0.75 |

Lowest `Correctness` scores:

- A-261005-0009 = 0: The core disposition differs fundamentally. The expected response calls for CLOSE_FP (close as false positive) because the iceberg was a genuine agency order for one client, and the sale was a different client's parent order - making this a legitimate agency scenario with no manipulation. The agent 
- A-261009-0007 = 0: The critical difference is the proposed disposition. The expected response says CLOSE_FP (close as false positive) because the evidence supports a fat-finger entry error explanation. The agent response proposes ESCALATE with confidence 0.6, treating the fat-finger explanation as unconfirmed and requ
- A-261015-0008 = 0: The expected response calls for a CLOSE_FP disposition based on a news reaction pattern, with key discriminators including: market event within 200ms before cancels, market-wide cancel storm (not just this trader), and hedge sale preceding the event. The agent response instead proposes ESCALATE with

Lowest `GoalSuccessRate` scores:

- A-261005-0009 = 0: The agent proposed ESCALATE, not CLOSE_FP. The first assertion requires the agent to call surv___propose_disposition exactly once and propose CLOSE_FP. The agent instead proposed ESCALATE with confidence 0.65. This is a clear failure of the first assertion. Additionally, the report does not mark any
- A-261009-0007 = 0: The first assertion requires the agent to call surv___propose_disposition exactly once and propose CLOSE_FP. However, the agent proposed ESCALATE, not CLOSE_FP. This is a direct contradiction of the first success assertion. Additionally, the report does not mark any legitimate explanation as 'suppor
- A-261015-0008 = 0: The first assertion requires the agent to have called surv___propose_disposition exactly once and proposed CLOSE_FP. However, the agent proposed ESCALATE, not CLOSE_FP. This is a direct contradiction of the first success assertion. All other assertions are moot since the primary disposition requirem

Lowest `surv_rationale_rubric` scores:

- A-261012-0002 = 0.25: All numbers trace to tool results: 163 events, 76 PEGGED orders, size 2424, symmetry 0.996, OTR 30.0, cancel ratio 0.959, fills 1708/1043, price move 0.5, reversion 0.0, round trip 1.41, depth 2338.39. The algo re-pricing explanation is well grounded: pegged children of two parents, at the touch, sy
- A-261009-0007 = 0.5: Grounding: the numbers trace to tool results. These are 18,930, 9997/9998/10001, the cancel at 15:53:43.638 (803 ms), 7.94x depth, cancel_ratio 0.909, the 1,893 re-entry at 15:53:44.038, typical size 500 and 2 market-wide cancels. The '~38x' figure and '1.2 s later' (measured from the NEW) are corre
- A-261009-0008 = 0.5: Grounding: almost every figure traces to a tool result, including cancel_symmetry 0.9925, max_resting 0.149, distance 0.66, price_move -1, reversion 0, otr 41 vs 15.9, round_trip 2.59, gross 8900, typical size 327 and depth 2385. Two descriptions are inaccurate. The summary says quotes refreshed 'ev
- A-261005-0009 = 0.75: Grounding: every number checks against a tool result. The iceberg is 21768 at 10002. The fills total 5835 (2036+2150+1649). The remaining 15933 was cancelled at 15:09:20.881, 2s after the 544 SELL filled at 10006 at 15:09:18.881. Size vs depth is 8.97, price_move is 3, round_trip is 4 and reversion 
- A-261009-0003 = 0.75: Grounding: every number in the report traces to a tool result: 2464, 0.963, 1.03, -0.64, 4 levels, price_move 0.0, reversion 0.0, round trip -0.19, 7731/1709, OTR 4.83 vs 40, cancel ratio 0.92, and the 11:24:56.453 SELL 120 on O-00011920. No invented figures.  Consistency: CLOSE_FP rests on one supp

## Disagreements with the label (3)

| alert | scenario | expected | proposed | conf | status | summary |
|---|---|---|---|---|---|---|
| A-261009-0007 | F-FAT-1 | CLOSE_FP | ESCALATE | 0.6 | ok | PROP-EQ trader (no MM registration) placed a single BUY of 18,930 (7.9x top-5 depth) 1 tick below the bid and cancelled it after 803 ms with no fills of any kin |
| A-261005-0009 | F-ICE-1 | CLOSE_FP | ESCALATE | 0.65 | ok | Agency trader T-X1005-05 placed a 21768 ICEBERG BUY at 10002 (about 9x top-5 depth). 5835 of it executed in slices over 15:08:57-15:09:09. At 15:09:16 the trade |
| A-261015-0008 | F-NEWS-1 | CLOSE_FP | ESCALATE | 0.65 | ok | Prop trader placed two BUY limits of 7215 each (14430 total, 5.5x avg top-5 depth, ~1.5 ticks from touch, 1 level) at 15:12:52.998 and 15:12:55.998. At 15:13:20 |
