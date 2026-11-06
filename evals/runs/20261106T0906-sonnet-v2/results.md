# Dataset run `20261106T0906-sonnet-v2`

- Dataset `seed7`, 167 alerts (28 TRUE_ABUSE, 139 FALSE_POSITIVE); backend `runtime`, model `eu.anthropic.claude-sonnet-5-5`, analyst `L1`, mode `investigate`, memory on, bundle none (code defaults), concurrency 2.
- Started 2026-11-06T09:06:44+00:00, finished 2026-11-06T10:06:58+00:00 (60.2 min).
- Notes: iteration 1: fill-sequencing discriminators (same_side_fill_qty_before/after_opposite_trade, same_side_fill_share) and the closure standard genuine-execution rule; Runtime v8 unchanged, Sonnet 5.5 effort medium, Memory on, ENFORCE, l1.analyst

## Headline

| metric | value |
|---|---|
| gate | **holds** (0 TRUE_ABUSE proposed CLOSE_FP) |
| safe close rate | 88.5% (123 of 139 false positives closed) |
| escalation precision | 63.6% (44 ESCALATE/DRAFT_STOR) |
| strong-call precision | 100.0% (2 DRAFT_STOR) |
| agreement with label (exact disposition) | 88.6% |
| **override rate** (1 - agreement) | **11.4%** |
| direction agreement (close vs not-close) | 90.4% |
| proposals | {'CLOSE_FP': 123, 'ESCALATE': 42, 'DRAFT_STOR': 2} |
| run status | {'ok': 167} |
| alerts with a disposition recorded before this run (visible to the agent through history and Memory) | 3: A-261005-0003, A-261009-0003, A-261016-0003 |
| latency, agent p50 / p95 | 31.0 s / 46.2 s (wall p50 37.0 s) |
| tokens per alert, in / out (mean) | 76279 / 3647 (max in 133105) |
| tool calls per alert (mean / median) | 10.2 / 10 |
| estimated model cost | $31.57 total, $0.189 per alert (assumed $2.0/$10.0 per M tokens in/out; not verified against the pricing page) |

## Against the baselines (same alerts)

| scorer | gate | safe close rate | raw safe close | escalation precision | agreement | override rate |
|---|---|---|---|---|---|---|
| agent (this run) | holds | 88.5% | 88.5% | 63.6% | 88.6% | 11.4% |
| threshold baseline (detector rules) | 6 missed | n/a | 95.7% | 78.6% | 92.8% | 7.2% |
| escalate everything | holds | 0.0% | 0.0% | 16.8% | 15.0% | 85.0% |
| close everything (the gate at work) | 28 missed | n/a | 100.0% | n/a | 83.2% | 16.8% |

## Confusion: expected (rows) x proposed (columns)

| expected \ proposed | CLOSE_FP | ESCALATE | DRAFT_STOR | none |
|---|---|---|---|---|
| CLOSE_FP | 123 | 16 | 0 | 0 |
| ESCALATE | 0 | 24 | 1 | 0 |
| DRAFT_STOR | 0 | 2 | 1 | 0 |

## Per scenario

| scenario | truth | expected | n | CLOSE_FP | ESCALATE | DRAFT_STOR | none | agreement | mean conf | gate misses |
|---|---|---|---|---|---|---|---|---|---|---|
| S-LAYER-1 | TRUE_ABUSE | ESCALATE | 5 | 0 | 4 | 1 | 0 | 80% | 0.66 | - |
| S-SPOOF-1 | TRUE_ABUSE | ESCALATE | 7 | 0 | 7 | 0 | 0 | 100% | 0.69 | - |
| S-SPOOF-2 | TRUE_ABUSE | DRAFT_STOR | 3 | 0 | 2 | 1 | 0 | 33% | 0.71 | - |
| S-SPOOF-3 | TRUE_ABUSE | ESCALATE | 4 | 0 | 4 | 0 | 0 | 100% | 0.69 | - |
| S-SPOOF-4 | TRUE_ABUSE | ESCALATE | 2 | 0 | 2 | 0 | 0 | 100% | 0.7 | - |
| S-SPOOF-5 | TRUE_ABUSE | ESCALATE | 7 | 0 | 7 | 0 | 0 | 100% | 0.71 | - |
| BACKGROUND | FALSE_POSITIVE | CLOSE_FP | 52 | 48 | 4 | 0 | 0 | 92% | 0.8 | - |
| F-ALGO-1 | FALSE_POSITIVE | CLOSE_FP | 24 | 21 | 3 | 0 | 0 | 88% | 0.73 | - |
| F-FAT-1 | FALSE_POSITIVE | CLOSE_FP | 3 | 2 | 1 | 0 | 0 | 67% | 0.68 | - |
| F-ICE-1 | FALSE_POSITIVE | CLOSE_FP | 9 | 9 | 0 | 0 | 0 | 100% | 0.81 | - |
| F-MM-1 | FALSE_POSITIVE | CLOSE_FP | 24 | 24 | 0 | 0 | 0 | 100% | 0.8 | - |
| F-NEWS-1 | FALSE_POSITIVE | CLOSE_FP | 4 | 1 | 3 | 0 | 0 | 25% | 0.66 | - |
| F-PARTIAL-1 | FALSE_POSITIVE | CLOSE_FP | 8 | 8 | 0 | 0 | 0 | 100% | 0.74 | - |
| F-RISK-1 | FALSE_POSITIVE | CLOSE_FP | 3 | 3 | 0 | 0 | 0 | 100% | 0.64 | - |
| F-SPOOFLIKE-HARD-1 | FALSE_POSITIVE | CLOSE_FP | 6 | 6 | 0 | 0 | 0 | 100% | 0.79 | - |
| F-STOP-1 | FALSE_POSITIVE | CLOSE_FP | 6 | 1 | 5 | 0 | 0 | 17% | 0.63 | - |

## Regression against the previous run

Previous run: `20261105T1238-sonnet-v1`. Verdict: **PASS (offline promotion rule)**.

- [x] gate holds
- [x] safe close rate not down by more than 2 points
- [x] no false-positive scenario regressed to 0% close (none)

| delta | value |
|---|---|
| raw_safe_close_rate | +8.6 pts |
| agreement | +7.2 pts |
| escalation_precision | +13.6 pts |
| direction_agreement | +7.2 pts |
| true_abuse_recall | +0.0 pts |
| gate misses | +0 |

| scenario | agreement delta | close-rate delta |
|---|---|---|
| F-FAT-1 | -33 pts | -33 pts |
| F-ALGO-1 | -12 pts | -12 pts |
| BACKGROUND | -4 pts | -4 pts |
| F-STOP-1 | +17 pts | +17 pts |
| F-RISK-1 | +33 pts | +33 pts |
| F-ICE-1 | +89 pts | +89 pts |
| F-PARTIAL-1 | +100 pts | +100 pts |

## AgentCore Evaluations

167 sessions scored against ground truth generated from the labels (`evals/ground_truth.py`); 0 evaluator error(s). Pass = score 1.0.

| evaluator | n | mean | pass rate | judge tokens in / out |
|---|---|---|---|---|
| Correctness | 167 | 0.87 | 87% | 155,391 / 40,461 |
| GoalSuccessRate | 167 | 0.89 | 89% | 2,742,551 / 63,413 |
| TrajectoryAnyOrderMatch | 167 | 1.00 | 100% | programmatic |
| TrajectoryInOrderMatch | 167 | 1.00 | 100% | programmatic |
| surv_rationale_rubric | 167 | 0.55 | 0% | 3,749,142 / 254,674 |

| scenario | Correctness | GoalSuccessRate | TrajectoryAnyOrderMatch | TrajectoryInOrderMatch | surv_rationale_rubric |
|---|---|---|---|---|---|
| BACKGROUND | 0.92 | 0.92 | 1.00 | 1.00 | 0.53 |
| F-ALGO-1 | 0.88 | 0.88 | 1.00 | 1.00 | 0.44 |
| F-FAT-1 | 0.67 | 0.67 | 1.00 | 1.00 | 0.42 |
| F-ICE-1 | 1.00 | 1.00 | 1.00 | 1.00 | 0.64 |
| F-MM-1 | 1.00 | 1.00 | 1.00 | 1.00 | 0.48 |
| F-NEWS-1 | 0.25 | 0.25 | 1.00 | 1.00 | 0.69 |
| F-PARTIAL-1 | 1.00 | 1.00 | 1.00 | 1.00 | 0.53 |
| F-RISK-1 | 1.00 | 1.00 | 1.00 | 1.00 | 0.50 |
| F-SPOOFLIKE-HARD-1 | 1.00 | 1.00 | 1.00 | 1.00 | 0.58 |
| F-STOP-1 | 0.17 | 0.17 | 1.00 | 1.00 | 0.54 |
| S-LAYER-1 | 0.80 | 0.80 | 1.00 | 1.00 | 0.75 |
| S-SPOOF-1 | 0.86 | 1.00 | 1.00 | 1.00 | 0.64 |
| S-SPOOF-2 | 0.33 | 0.33 | 1.00 | 1.00 | 0.75 |
| S-SPOOF-3 | 1.00 | 1.00 | 1.00 | 1.00 | 0.69 |
| S-SPOOF-4 | 0.50 | 1.00 | 1.00 | 1.00 | 0.75 |
| S-SPOOF-5 | 1.00 | 1.00 | 1.00 | 1.00 | 0.75 |

Lowest `Correctness` scores:

- A-261005-0006 = 0: The expected response calls for a disposition of CLOSE_FP (close as false positive), identifying the trader as a market maker whose activity is legitimate background market-making that tripped a naive detector. The key conclusion is that this should be closed as a false positive.  The agent response
- A-261005-0007 = 0: The critical difference is the proposed disposition. The expected response says CLOSE_FP (close as false positive), explaining this is a momentum trader stopped out with a legitimate explanation supported. The agent response says ESCALATE with confidence 0.70, explicitly stating the closure standard
- A-261006-0005 = 0: The core factual disagreement is the proposed disposition. The expected response says CLOSE_FP (close as false positive) with the explanation that this is a legitimate 'momentum trader stopped out' scenario - price moved against the resting bids, the trader sold at a loss, price kept falling after c
- A-261009-0004 = 0: Both responses agree on the core disposition: ESCALATE. Both identify the same key facts: a large resting SELL order (agent says 13.9x average depth, expected says 8-15x depth), an opposite-side fill (buy) shortly before cancel, and a cancel within ~500ms of the fill. Both note no legitimate explana
- A-261009-0005 = 0: The core disposition differs fundamentally. The expected response calls for CLOSE_FP (close as false positive) with trader role MARKET_MAKER, recognizing this as legitimate market maker activity. The agent response proposes ESCALATE with confidence 0.55, explicitly stating it could not close as fals

Lowest `GoalSuccessRate` scores:

- A-261005-0006 = 0: Checking each assertion:  1. 'Agent called surv___propose_disposition exactly once and proposed CLOSE_FP.' - The agent proposed ESCALATE, not CLOSE_FP. This assertion FAILS.  2. 'Agent called surv___compute_discriminators and surv___get_trader_profile before surv___propose_disposition.' - Both were 
- A-261005-0007 = 0: The first assertion requires the agent to call surv___propose_disposition exactly once and propose CLOSE_FP. However, the agent proposed ESCALATE, not CLOSE_FP. This is a direct contradiction of the first assertion. Additionally, the assertion about marking 'momentum trader stopped out' as a support
- A-261006-0005 = 0: Checking each assertion: 1. Agent called surv___propose_disposition exactly once with disposition 'ESCALATE', not 'CLOSE_FP'. This assertion FAILS. 2. Agent did call compute_discriminators and get_trader_profile before propose_disposition. PASSES. 3. Numbers in evidence facts appear in tool results.
- A-261009-0005 = 0: Checking each assertion:  1. 'The agent called surv___propose_disposition exactly once and proposed CLOSE_FP.' - The agent proposed ESCALATE, not CLOSE_FP. This assertion FAILS.  2. 'The agent called surv___compute_discriminators and surv___get_trader_profile before surv___propose_disposition.' - Bo
- A-261012-0002 = 0: The agent proposed ESCALATE, not CLOSE_FP. The first assertion requires the agent to have called surv___propose_disposition exactly once and proposed CLOSE_FP. The agent instead proposed ESCALATE. This is a clear failure of the first assertion.  Additionally, the last assertion states the report sho

Lowest `surv_rationale_rubric` scores:

- A-261005-0011 = 0: The disposition logic is coherent. The trader is a registered MM on SYN.A. Gross submission was symmetric (8736/8736) with cancel_symmetry 0.9998 and paired 364-lot re-quotes about 13 ms after each cancel. The only fill was 4 lots on the SELL quote, with price_move_ticks -1, reversion 0 and round tr
- A-261006-0006 = 0: Strengths: the sequence is explicit and grounded. The BUY 38461 LIMIT at 9994 was placed at 12:50:39.339, 2 ticks below a 9996 bid. A SELL market order of 1423 filled at 9997/9996 at 12:50:41.863. The BUY was cancelled at 12:50:42.223, 360.5 ms after the fill, with zero same-side fills. Size of 15.7
- A-261006-0009 = 0: The report is clear and mostly well grounded, but it contains an altered number and an indicator verdict that contradicts the tape.  What holds up: - The core logic follows the closure standard. 6744 filled on the BUY before the opposite trade (share 0.6513), which exceeds 10% of 12210 and exceeds t
- A-261006-0014 = 0: The report reads clearly and most figures trace to tool results: 21230, 8.7x/8.66 depth, 9999, bid 10000, 943 ms, 2123, typical size 500, avg depth 2450.3 and 2 market-wide cancels. Several defects follow.  1) Wrong gap. The summary, repeated in the closing message, says the corrected BUY of 2123 ca
- A-261016-0004 = 0: Clarity: the report is strong. It gives a precise timeline: NEW BUY 15555 @10003 at 14:02:38.955, partial fills of 1866 and 1329, SELL 466 @10006 filled at 14:02:53.955, MODIFY -11116 at 14:02:55.955 leaving 1244. It states size relative to depth (6.25x) and puts the mixed points up front.  Indicato

## Disagreements with the label (19)

| alert | scenario | expected | proposed | conf | status | summary |
|---|---|---|---|---|---|---|
| A-261013-0003 | S-LAYER-1 | ESCALATE | DRAFT_STOR | 0.6 | ok | PROP trader with no registered market making placed five BUY limit orders of 4340 each (21700 total, 8.7x average top-5 depth) at 9988-9992, 1-5 ticks below the |
| A-261015-0003 | S-SPOOF-2 | DRAFT_STOR | ESCALATE | 0.7 | ok | PROP trader (no MM registration, typical size 500) placed a single SELL LIMIT of 21443 (8.2x avg top-5 depth) at 10000, 2 ticks from the touch. 2.4s later a BUY |
| A-261016-0006 | S-SPOOF-2 | DRAFT_STOR | ESCALATE | 0.7 | ok | PROP trader placed a single 21,860 BUY limit (8.8x avg top-5 depth, 3 ticks from touch, ~44x typical size 500) at 16:38:01.976, sold 1,329 at market at 16:38:04 |
| A-261005-0006 | BACKGROUND | CLOSE_FP | ESCALATE | 0.6 | ok | T-MM-01 is a registered market maker on SYN.A quoting both sides at about desk-typical size, with a 1-second refresh cycle and symmetric cancels. That pattern f |
| A-261009-0005 | BACKGROUND | CLOSE_FP | ESCALATE | 0.55 | ok | Registered MM T-MM-02 quotes SYN.A two-sided at about 356 per side, re-quoted every 1-6s, which looks like market making. But the closure standard is not cleanl |
| A-261021-0001 | BACKGROUND | CLOSE_FP | ESCALATE | 0.6 | ok | Registered market maker T-MM-01 on SYN.A. The tape looks like two-sided quoting: 391 lots a side, re-quoted about every second, symmetric, at the touch and smal |
| A-261027-0004 | BACKGROUND | CLOSE_FP | ESCALATE | 0.55 | ok | Registered market maker T-MM-02 on SYN.A shows a classic two-sided quote-refresh pattern (symmetric, desk-typical size, touch-level, no event, no repetition, no |
| A-261012-0002 | F-ALGO-1 | CLOSE_FP | ESCALATE | 0.55 | ok | Two-sided PEGGED quotes from parents P-T-X1012-02-B/S, at the touch, typical size 2424, cancelled and re-pegged every 2-3 s with near-perfect symmetry. This loo |
| A-261029-0015 | F-ALGO-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Pegged two-sided algo (ALGO-EXEC) on SYN.A re-quoting 2874-lot BUY and SELL child orders at the touch every 2-4 s. Much points to algorithmic re-pricing: PEGGED |
| A-261030-0003 | F-ALGO-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Pegged two-sided algo (parents P-T-X1030-03-B/S) on SYN.A refreshed 2665-lot orders at the touch every few seconds; the detector fired on gross size and cancel- |
| A-261021-0009 | F-FAT-1 | CLOSE_FP | ESCALATE | 0.6 | ok | PROP-EQ trader T-X1021-06 placed a single BUY LIMIT of 23,620 on SYN.A, 9.5x average top-5 depth and 1 tick below the best bid. They cancelled it after about 1s |
| A-261015-0008 | F-NEWS-1 | CLOSE_FP | ESCALATE | 0.65 | ok | PROP trader placed two identical BUY 7,215 LIMIT orders at 9996 (14,430 total, 5.5x avg top-5 depth, ~29x typical size of 500) with no fills on them. While they |
| A-261016-0003 | F-NEWS-1 | CLOSE_FP | ESCALATE | 0.7 | ok | Prop trader placed two BUY LIMIT orders of 6,680 each at 9997 (about 1.5 ticks off the touch, 5.4x top-5 depth) at 12:01:42 and 12:01:45. At 12:02:08 the trader |
| A-261016-0005 | F-NEWS-1 | CLOSE_FP | ESCALATE | 0.6 | ok | PROP trader placed two BUY 7162 limit orders at 9999 (14324 total, 5.76x avg top-5 depth, 1.5 ticks from touch), never filled, rested ~28s, sold 511 at 10001 at |
| A-261005-0007 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.7 | ok | PROP trader placed three large BUY limit orders (3 x 4077 = 12231, up to 5.04x avg top-5 depth, 6 ticks from touch) between 13:20:39 and 13:20:43, none executed |
| A-261006-0005 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader bought 1058 at market (11:36:02), then placed three BUY limits of 3810 each at 9994/9993/9992 (6 ticks from touch, ~4.7x top-5 depth) over 4s, none  |
| A-261026-0003 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.7 | ok | Prop trader placed three BUY limit orders of 4,024 each (12,072 total, about 4.9x average top-5 depth) at 9996/9995/9994, 4-6 ticks below the touch. Then a SELL |
| A-261027-0008 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | PROP-EQ trader (no registered MM) bought 1254 at market (10005), then placed three 4514 BUY limits (13542 total, 5.4x top-5 depth, 6 ticks off touch) with no fi |
| A-261028-0011 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader bought 1476 by market order at 16:57:25, then placed three identical-size BUY limits (5313 each, 15939 total, 6.5x avg top-5 depth, ~6 ticks below t |
