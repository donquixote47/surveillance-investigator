# Dataset run `20261118T1523-sonnet-v8`

- Dataset `seed7`, 167 alerts (28 TRUE_ABUSE, 139 FALSE_POSITIVE); backend `runtime`, model `eu.anthropic.claude-sonnet-5-5`, analyst `L1`, mode `investigate`, memory on, bundle none (code defaults), concurrency 2.
- Started 2026-11-18T15:23:27+00:00, finished 2026-11-18T16:06:17+00:00 (42.8 min).
- Notes: full seed7 run on Runtime v20 with one analyst per worker (l1.analyst, l1.analyst2); released limits: 60 requests and 3 proposals a minute per analyst

## Headline

| metric | value |
|---|---|
| gate | **holds** (0 TRUE_ABUSE proposed CLOSE_FP) |
| safe close rate | 94.2% (131 of 139 false positives closed) |
| escalation precision | 77.8% (36 ESCALATE/DRAFT_STOR) |
| strong-call precision | 100.0% (2 DRAFT_STOR) |
| agreement with label (exact disposition) | 93.4% |
| **override rate** (1 - agreement) | **6.6%** |
| direction agreement (close vs not-close) | 95.2% |
| proposals | {'CLOSE_FP': 131, 'ESCALATE': 34, 'DRAFT_STOR': 2} |
| run status | {'ok': 167} |
| configuration bundle reported by the agent | none |
| latency, agent p50 / p95 | 23.5 s / 27.0 s (wall p50 29.8 s) |
| tokens per alert, in / out (mean) | 11 / 2976 (max in 12) |
| prompt cache, per alert | read 53642 / write 21600 / full price 11 tokens; hit rate 0.713 of 75252 prompt tokens |
| tool calls per alert (mean / median) | 10 / 10 |
| estimated model cost | $15.78 total, $0.095 per alert (assumed $2.0/$10.0 per M tokens in/out; cache read 0.1x, write 1.25x of input; not verified against the pricing page) |

## Against the baselines (same alerts)

| scorer | gate | safe close rate | raw safe close | escalation precision | agreement | override rate |
|---|---|---|---|---|---|---|
| agent (this run) | holds | 94.2% | 94.2% | 77.8% | 93.4% | 6.6% |
| threshold baseline (detector rules) | 6 missed | n/a | 95.7% | 78.6% | 92.8% | 7.2% |
| escalate everything | holds | 0.0% | 0.0% | 16.8% | 15.0% | 85.0% |
| close everything (the gate at work) | 28 missed | n/a | 100.0% | n/a | 83.2% | 16.8% |

## Confusion: expected (rows) x proposed (columns)

| expected \ proposed | CLOSE_FP | ESCALATE | DRAFT_STOR | none |
|---|---|---|---|---|
| CLOSE_FP | 131 | 8 | 0 | 0 |
| ESCALATE | 0 | 24 | 1 | 0 |
| DRAFT_STOR | 0 | 2 | 1 | 0 |

## Per scenario

| scenario | truth | expected | n | CLOSE_FP | ESCALATE | DRAFT_STOR | none | agreement | mean conf | gate misses |
|---|---|---|---|---|---|---|---|---|---|---|
| S-LAYER-1 | TRUE_ABUSE | ESCALATE | 5 | 0 | 4 | 1 | 0 | 80% | 0.68 | - |
| S-SPOOF-1 | TRUE_ABUSE | ESCALATE | 7 | 0 | 7 | 0 | 0 | 100% | 0.71 | - |
| S-SPOOF-2 | TRUE_ABUSE | DRAFT_STOR | 3 | 0 | 2 | 1 | 0 | 33% | 0.71 | - |
| S-SPOOF-3 | TRUE_ABUSE | ESCALATE | 4 | 0 | 4 | 0 | 0 | 100% | 0.73 | - |
| S-SPOOF-4 | TRUE_ABUSE | ESCALATE | 2 | 0 | 2 | 0 | 0 | 100% | 0.71 | - |
| S-SPOOF-5 | TRUE_ABUSE | ESCALATE | 7 | 0 | 7 | 0 | 0 | 100% | 0.77 | - |
| BACKGROUND | FALSE_POSITIVE | CLOSE_FP | 52 | 52 | 0 | 0 | 0 | 100% | 0.89 | - |
| F-ALGO-1 | FALSE_POSITIVE | CLOSE_FP | 24 | 24 | 0 | 0 | 0 | 100% | 0.84 | - |
| F-FAT-1 | FALSE_POSITIVE | CLOSE_FP | 3 | 3 | 0 | 0 | 0 | 100% | 0.72 | - |
| F-ICE-1 | FALSE_POSITIVE | CLOSE_FP | 9 | 9 | 0 | 0 | 0 | 100% | 0.8 | - |
| F-MM-1 | FALSE_POSITIVE | CLOSE_FP | 24 | 24 | 0 | 0 | 0 | 100% | 0.89 | - |
| F-NEWS-1 | FALSE_POSITIVE | CLOSE_FP | 4 | 2 | 2 | 0 | 0 | 50% | 0.64 | - |
| F-PARTIAL-1 | FALSE_POSITIVE | CLOSE_FP | 8 | 8 | 0 | 0 | 0 | 100% | 0.78 | - |
| F-RISK-1 | FALSE_POSITIVE | CLOSE_FP | 3 | 3 | 0 | 0 | 0 | 100% | 0.63 | - |
| F-SPOOFLIKE-HARD-1 | FALSE_POSITIVE | CLOSE_FP | 6 | 6 | 0 | 0 | 0 | 100% | 0.8 | - |
| F-STOP-1 | FALSE_POSITIVE | CLOSE_FP | 6 | 0 | 6 | 0 | 0 | 0% | 0.62 | - |

## Regression against the previous run

Previous run: `20261118T1204-sonnet-v7`. Verdict: **PASS (offline promotion rule)**.

- [x] gate holds
- [x] safe close rate not down by more than 2 points
- [x] no false-positive scenario regressed to 0% close (none; below the floor, read the variance run: F-STOP-1 (2/6 -> 0/6))
- [x] evidence faithfulness at least 99% and not down by more than 0.5 points (99.88% of 4092 numbers, previous 99.90%; 100.00% of 587 categorical claims)

| delta | value |
|---|---|
| raw_safe_close_rate | -1.4 pts |
| agreement | -1.8 pts |
| escalation_precision | -4.6 pts |
| direction_agreement | -1.2 pts |
| true_abuse_recall | +0.0 pts |
| gate misses | +0 |

| scenario | agreement delta | close-rate delta |
|---|---|---|
| F-STOP-1 | -33 pts | -33 pts |
| S-LAYER-1 | -20 pts | +0 pts |

## Evidence faithfulness

167 reports checked against their sessions' tool results (`evals/faithfulness.py`): **97.0% of reports** have every number grounded; 4087 of 4092 numbers matched (99.9%). Categorical claims (roles, desks, order types, registration): 587 of 587 matched (100.0%).

| alert | scenario | proposed | source | unmatched | fact |
|---|---|---|---|---|---|
| A-261015-0008 | F-NEWS-1 | ESCALATE | get_market_events | 142 | NEWS at 15:13:22.998: issuer announces unscheduled trading update. The cancel came 142 ms later. The sale at 15:13:20.498 came before the news. |
| A-261016-0003 | F-NEWS-1 | ESCALATE | get_market_events | 187 | NEWS 'issuer announces unscheduled trading update' at 12:02:12.731, 187 ms before the cancels, after the 12:02:10.231 sale. |
| A-261022-0003 | F-STOP-1 | ESCALATE | compute_discriminators | 1.9 | gross_submitted_dominant BUY 14400 vs avg depth 2516; max_resting_size_vs_depth 5.72; distance_from_touch_ticks 6.0; cancel_ratio 1.0; same_side_fill_qty 0; cancel_symmetry 0.0; large_orders empty (each order is 4800, ab |
| A-261023-0001 | F-NEWS-1 | CLOSE_FP | get_market_events | 148 | NEWS 'issuer announces unscheduled trading update' at 09:38:30.051, 148 ms before the cancels |
| A-261026-0003 | F-STOP-1 | ESCALATE | compute_discriminators | 1.6 | gross_submitted_dominant BUY 12072, gross_submitted_other 0, distinct_price_levels 3, max_resting_size_vs_depth 4.87, distance_from_touch_ticks 6.0, cancel_symmetry 0.0, large_orders empty (each order about 1.6x depth) |

## AgentCore Evaluations

167 sessions scored against ground truth generated from the labels (`evals/ground_truth.py`); 0 evaluator error(s). Pass = score 1.0.

| evaluator | n | mean | pass rate | judge tokens in / out |
|---|---|---|---|---|
| Correctness | 167 | 0.92 | 92% | 148,657 / 39,598 |
| GoalSuccessRate | 167 | 0.93 | 93% | 2,969,200 / 61,623 |
| TrajectoryAnyOrderMatch | 167 | 1.00 | 100% | programmatic |
| TrajectoryInOrderMatch | 167 | 1.00 | 100% | programmatic |
| surv_rationale_rubric | 167 | 0.61 | 0% | 4,048,822 / 240,232 |

| scenario | Correctness | GoalSuccessRate | TrajectoryAnyOrderMatch | TrajectoryInOrderMatch | surv_rationale_rubric |
|---|---|---|---|---|---|
| BACKGROUND | 1.00 | 1.00 | 1.00 | 1.00 | 0.59 |
| F-ALGO-1 | 1.00 | 1.00 | 1.00 | 1.00 | 0.56 |
| F-FAT-1 | 1.00 | 1.00 | 1.00 | 1.00 | 0.50 |
| F-ICE-1 | 1.00 | 1.00 | 1.00 | 1.00 | 0.64 |
| F-MM-1 | 1.00 | 1.00 | 1.00 | 1.00 | 0.60 |
| F-NEWS-1 | 0.25 | 0.50 | 1.00 | 1.00 | 0.50 |
| F-PARTIAL-1 | 1.00 | 1.00 | 1.00 | 1.00 | 0.59 |
| F-RISK-1 | 1.00 | 1.00 | 1.00 | 1.00 | 0.58 |
| F-SPOOFLIKE-HARD-1 | 1.00 | 1.00 | 1.00 | 1.00 | 0.50 |
| F-STOP-1 | 0.00 | 0.00 | 1.00 | 1.00 | 0.75 |
| S-LAYER-1 | 0.80 | 0.80 | 1.00 | 1.00 | 0.70 |
| S-SPOOF-1 | 0.86 | 1.00 | 1.00 | 1.00 | 0.71 |
| S-SPOOF-2 | 0.33 | 0.33 | 1.00 | 1.00 | 0.75 |
| S-SPOOF-3 | 1.00 | 1.00 | 1.00 | 1.00 | 0.75 |
| S-SPOOF-4 | 0.50 | 1.00 | 1.00 | 1.00 | 0.75 |
| S-SPOOF-5 | 1.00 | 1.00 | 1.00 | 1.00 | 0.75 |

Lowest `Correctness` scores:

- A-261005-0007 = 0: The core disposition differs fundamentally. The expected response says CLOSE_FP (false positive) with the legitimate explanation being a 'momentum trader stopped out' - the market moved against the resting bids, the trader sold at a loss, and cancelled the bids with nothing to revert. The agent resp
- A-261006-0005 = 0: The critical difference is the disposition. The expected response calls for CLOSE_FP (close as false positive) with a legitimate explanation of a momentum trader being stopped out. The agent response proposes ESCALATE with confidence 0.6, treating the evidence as mixed and suggesting possible manipu
- A-261012-0003 = 0: The agent response proposes ESCALATE as the disposition, which matches the expected response. Both identify the trader as PROP and describe classic spoofing indicators: a large resting order (11.8x average depth, consistent with '8-15x depth'), placed away from the touch, with an opposite-side fill 
- A-261013-0003 = 0: The critical difference is the proposed disposition. The expected response says 'ESCALATE' while the agent says 'DRAFT_STOR' (with confidence 0.6, suggesting Level 2 decides). These are fundamentally different dispositions - ESCALATE means the case should be escalated to a higher authority/regulator
- A-261015-0003 = 0: The critical discrepancy is in the proposed disposition. The expected response calls for 'DRAFT_STOR' while the agent proposes 'ESCALATE'. This is a fundamental difference in the recommended action.  Additionally, the expected response states 'both core features are present: (a) a large resting orde

Lowest `GoalSuccessRate` scores:

- A-261005-0007 = 0: The agent proposed ESCALATE, not CLOSE_FP. The first assertion requires the agent to have called surv___propose_disposition exactly once and proposed CLOSE_FP. The agent clearly proposed ESCALATE with confidence 0.70. This is a direct contradiction of the first success assertion. Additionally, the r
- A-261006-0005 = 0: The first assertion requires the agent to propose CLOSE_FP, but the agent proposed ESCALATE. This is a clear failure of the first assertion. Additionally, the assertion about marking 'momentum trader stopped out' as a supported explanation is not met - the agent marked it as 'undetermined'. The asse
- A-261013-0003 = 0: The first assertion requires the agent to propose ESCALATE, but the agent proposed DRAFT_STOR instead. While DRAFT_STOR is related to escalation (it's a higher-level disposition), the procedures clearly distinguish between ESCALATE and DRAFT_STOR - only Level 2 can record DRAFT_STOR, and a Level 1 a
- A-261015-0003 = 0: The first assertion requires the agent to have proposed DRAFT_STOR, but the agent proposed ESCALATE instead. The agent explicitly stated 'I therefore did not propose DRAFT_STOR' and the tool call shows disposition: 'ESCALATE'. This is a clear failure of the first and most critical assertion. All oth
- A-261015-0008 = 0: The first assertion requires the agent to propose CLOSE_FP, but the agent proposed ESCALATE. This is a direct contradiction of the required disposition. Additionally, the assertion requires the report to mark one legitimate explanation as supported (market event/news within 200ms before cancels with

Lowest `surv_rationale_rubric` scores:

- A-261009-0007 = 0: Clarity: the report is easy to follow. It states the timeline (NEW 18,930 at 15:53:42.835, CANCEL at 15:53:43.638, NEW 1,893 at 15:53:44.038), the size versus depth (7.94x) and the lack of fills, and it ties the disposition to the fat-finger explanation. The explanation list is broad and cites evide
- A-261014-0001 = 0: The report is clear and mostly well grounded. It names the large order O-00007151 (12490, 5.3x depth), placed at 10:28:47.852. It reports 5828 executed before the opposite-side SELL 374 at 10:29:02.852 (share 0.4666), price_move 0.0 with no reversion, and the MODIFY -5046 at 10:29:04.852 followed by
- A-261006-0001 = 0.25: Clarity is reasonable. The sequence is laid out with times: three BUY 4614 orders rest, a SELL 692 fills at 09:28:52.795, and all BUYs are cancelled at 09:28:53.795 alongside the kill switch. Size versus depth (5.65x) and distance from the touch are stated.  Number accuracy is mostly good, with mino
- A-261006-0004 = 0.25: Strengths: the disposition is consistent with the tape. T-MM-01 is a registered market maker on SYN.A, cancel_symmetry is 0.997, the largest order was 0.16x depth, there were no large_orders and no opposite-side fills, and price_move, reversion and round_trip are null. Most numbers trace to tool res
- A-261015-0009 = 0.25: Strengths: the report is clear and well structured. It cites cancel_symmetry 0.98, equal gross sizes of 9932 per side, max_resting_size_vs_depth 0.146, the 382 sizes against typical 327, MARKET_MAKER registered on SYN.A, no risk events and no market events. All of these appear in the tool results. M

## Disagreements with the label (11)

| alert | scenario | expected | proposed | conf | status | summary |
|---|---|---|---|---|---|---|
| A-261013-0003 | S-LAYER-1 | ESCALATE | DRAFT_STOR | 0.6 | ok | PROP trader (not a registered MM, typical order size 500) placed five BUY limit orders of 4,340 each (21,700 total, 8.7x top-5 depth of 2,498) at 9992 to 9988,  |
| A-261015-0003 | S-SPOOF-2 | DRAFT_STOR | ESCALATE | 0.7 | ok | Prop trader placed a one-sided SELL limit of 21,443 (8.17x depth) 2 ticks from the touch, bought 1,189 by market order 2.4s later, and cancelled the whole SELL  |
| A-261016-0006 | S-SPOOF-2 | DRAFT_STOR | ESCALATE | 0.72 | ok | PROP trader placed a one-sided BUY limit of 21860 (8.79x depth, 3 ticks off touch), then 2.1s later sold 1329 by market order, and cancelled the whole BUY 281 m |
| A-261015-0008 | F-NEWS-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader placed two identical BUY 7215 orders at 9996 (combined 14430 = 5.5x avg depth of 2624), one-sided, with no fills. While they rested, the trader sold |
| A-261016-0003 | F-NEWS-1 | CLOSE_FP | ESCALATE | 0.7 | ok | Prop trader placed two BUY LIMIT orders of 6,680 each at 9997 (combined 13,360, 5.37x top-5 depth, 1.5 ticks from touch), sold 477 at 10003 about 20-27s later w |
| A-261005-0007 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.7 | ok | Prop trader bought 1132 at market (13:20:37), then placed three one-sided BUY limits of 4077 (12231 total, 5.04x depth) 6 ticks from the touch at 9993/9994 over |
| A-261006-0005 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | PROP trader, not a registered MM on SYN.A, bought 947 by market order at 11:36:02, then placed three one-sided BUY limits (3810 each, 9994/9993/9992, 6 ticks fr |
| A-261022-0003 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | PROP trader bought 1333 by market order at 13:16:57, then rested three BUY limits of 4800 (14400 total, 5.7x depth) 5-6 ticks below the touch. At 13:17:17.579 t |
| A-261026-0003 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader bought 1118 at market (12:36:13), then placed three BUY limits of 4024 each (12072 total, 4.87x depth) at 9996/9995/9994, 5-6 ticks below the touch. |
| A-261027-0008 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader bought 1254 at market (10005), then rested three one-sided BUY limits of 4514 (13542 total, 5.4x depth, 6 ticks off touch, 2 levels) over 4s. At 13: |
| A-261028-0011 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader (no MM registration) bought 1476 at market (10005-10006) at 16:57:25, then placed three one-sided BUY limits of 5313 each (15939 total, 6.5x depth)  |
