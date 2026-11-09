# Dataset run `20261106T1126-sonnet-v3`

- Dataset `seed7`, 167 alerts (28 TRUE_ABUSE, 139 FALSE_POSITIVE); backend `runtime`, model `eu.anthropic.claude-sonnet-5-5`, analyst `L1`, mode `investigate`, memory on, bundle none (code defaults), concurrency 1.
- Started 2026-11-06T11:26:05+00:00, finished 2026-11-07T19:52:54+00:00 (100.8 min).
- Notes: iteration 2: closure standard says a two-sided quoter's spread is not feature (b) and the fill-sequencing test applies to one-sided patterns only; Runtime v10 (bundle+memory switch), Memory on, ENFORCE, l1.analyst

## Headline

| metric | value |
|---|---|
| gate | **holds** (0 TRUE_ABUSE proposed CLOSE_FP) |
| safe close rate | 93.5% (130 of 139 false positives closed) |
| escalation precision | 75.7% (37 ESCALATE/DRAFT_STOR) |
| strong-call precision | 100.0% (1 DRAFT_STOR) |
| agreement with label (exact disposition) | 93.4% |
| **override rate** (1 - agreement) | **6.6%** |
| direction agreement (close vs not-close) | 94.6% |
| proposals | {'CLOSE_FP': 130, 'ESCALATE': 36, 'DRAFT_STOR': 1} |
| run status | {'ok': 167} |
| alerts with a disposition recorded before this run (visible to the agent through history and Memory) | 3: A-261005-0003, A-261009-0003, A-261016-0003 |
| configuration bundle reported by the agent | none |
| latency, agent p50 / p95 | 27.4 s / 37.9 s (wall p50 33.3 s) |
| tokens per alert, in / out (mean) | 76679 / 3384 (max in 140600) |
| tool calls per alert (mean / median) | 10.1 / 10 |
| estimated model cost | $31.26 total, $0.187 per alert (assumed $2.0/$10.0 per M tokens in/out; not verified against the pricing page) |

## Against the baselines (same alerts)

| scorer | gate | safe close rate | raw safe close | escalation precision | agreement | override rate |
|---|---|---|---|---|---|---|
| agent (this run) | holds | 93.5% | 93.5% | 75.7% | 93.4% | 6.6% |
| threshold baseline (detector rules) | 6 missed | n/a | 95.7% | 78.6% | 92.8% | 7.2% |
| escalate everything | holds | 0.0% | 0.0% | 16.8% | 15.0% | 85.0% |
| close everything (the gate at work) | 28 missed | n/a | 100.0% | n/a | 83.2% | 16.8% |

## Confusion: expected (rows) x proposed (columns)

| expected \ proposed | CLOSE_FP | ESCALATE | DRAFT_STOR | none |
|---|---|---|---|---|
| CLOSE_FP | 130 | 9 | 0 | 0 |
| ESCALATE | 0 | 25 | 0 | 0 |
| DRAFT_STOR | 0 | 2 | 1 | 0 |

## Per scenario

| scenario | truth | expected | n | CLOSE_FP | ESCALATE | DRAFT_STOR | none | agreement | mean conf | gate misses |
|---|---|---|---|---|---|---|---|---|---|---|
| S-LAYER-1 | TRUE_ABUSE | ESCALATE | 5 | 0 | 5 | 0 | 0 | 100% | 0.71 | - |
| S-SPOOF-1 | TRUE_ABUSE | ESCALATE | 7 | 0 | 7 | 0 | 0 | 100% | 0.69 | - |
| S-SPOOF-2 | TRUE_ABUSE | DRAFT_STOR | 3 | 0 | 2 | 1 | 0 | 33% | 0.73 | - |
| S-SPOOF-3 | TRUE_ABUSE | ESCALATE | 4 | 0 | 4 | 0 | 0 | 100% | 0.71 | - |
| S-SPOOF-4 | TRUE_ABUSE | ESCALATE | 2 | 0 | 2 | 0 | 0 | 100% | 0.7 | - |
| S-SPOOF-5 | TRUE_ABUSE | ESCALATE | 7 | 0 | 7 | 0 | 0 | 100% | 0.7 | - |
| BACKGROUND | FALSE_POSITIVE | CLOSE_FP | 52 | 52 | 0 | 0 | 0 | 100% | 0.89 | - |
| F-ALGO-1 | FALSE_POSITIVE | CLOSE_FP | 24 | 24 | 0 | 0 | 0 | 100% | 0.85 | - |
| F-FAT-1 | FALSE_POSITIVE | CLOSE_FP | 3 | 2 | 1 | 0 | 0 | 67% | 0.67 | - |
| F-ICE-1 | FALSE_POSITIVE | CLOSE_FP | 9 | 9 | 0 | 0 | 0 | 100% | 0.79 | - |
| F-MM-1 | FALSE_POSITIVE | CLOSE_FP | 24 | 24 | 0 | 0 | 0 | 100% | 0.89 | - |
| F-NEWS-1 | FALSE_POSITIVE | CLOSE_FP | 4 | 2 | 2 | 0 | 0 | 50% | 0.64 | - |
| F-PARTIAL-1 | FALSE_POSITIVE | CLOSE_FP | 8 | 8 | 0 | 0 | 0 | 100% | 0.77 | - |
| F-RISK-1 | FALSE_POSITIVE | CLOSE_FP | 3 | 3 | 0 | 0 | 0 | 100% | 0.65 | - |
| F-SPOOFLIKE-HARD-1 | FALSE_POSITIVE | CLOSE_FP | 6 | 6 | 0 | 0 | 0 | 100% | 0.75 | - |
| F-STOP-1 | FALSE_POSITIVE | CLOSE_FP | 6 | 0 | 6 | 0 | 0 | 0% | 0.62 | - |

## Regression against the previous run

Previous run: `20261106T0906-sonnet-v2`. Verdict: **PASS (offline promotion rule)**.

- [x] gate holds
- [x] safe close rate not down by more than 2 points
- [x] no false-positive scenario regressed to 0% close (none; within noise: F-STOP-1 (1/6 -> 0/6, below the floor))

| delta | value |
|---|---|
| raw_safe_close_rate | +5.0 pts |
| agreement | +4.8 pts |
| escalation_precision | +12.0 pts |
| direction_agreement | +4.2 pts |
| true_abuse_recall | +0.0 pts |
| gate misses | +0 |

| scenario | agreement delta | close-rate delta |
|---|---|---|
| F-STOP-1 | -17 pts | -17 pts |
| BACKGROUND | +8 pts | +8 pts |
| F-ALGO-1 | +12 pts | +12 pts |
| S-LAYER-1 | +20 pts | +0 pts |
| F-NEWS-1 | +25 pts | +25 pts |

## Evidence faithfulness

167 reports checked against their sessions' tool results (`evals/faithfulness.py`): **97.0% of reports** have every number grounded; 4127 of 4132 numbers matched (99.9%).

| alert | scenario | proposed | source | unmatched | fact |
|---|---|---|---|---|---|
| A-261015-0008 | F-NEWS-1 | ESCALATE | get_market_events | 142 | NEWS on SYN.A at 15:13:22.998: issuer announces unscheduled trading update. This is 2.5 s after the sale fill and about 142 ms before the cancels. |
| A-261016-0003 | F-NEWS-1 | ESCALATE | get_market_events | 187 | NEWS 12:02:12.731: issuer announces unscheduled trading update, 187 ms before the cancels at 12:02:12.918. |
| A-261016-0005 | F-NEWS-1 | CLOSE_FP | get_market_events | 106 | NEWS at 15:48:00.644: issuer announces unscheduled trading update (106 ms before the cancels) |
| A-261023-0006 | S-SPOOF-5 | ESCALATE | get_order_events | 686 | SELL LIMIT 24428 at 10005 placed 14:44:35.719 with bid 10001 / ask 10003; BUY MARKET 1226 at 14:44:38.395 filled 70@10001, 331@10002, 147@10003, 686@10005; SELL partial fill 3606 at 14:44:38.631; CANCEL of 20822 at 14:44 |
| A-261028-0006 | F-ALGO-1 | CLOSE_FP | get_order_events | 0.1 | 150 events, all order_type PEGGED, under two parents P-T-X1028-05-B and P-T-X1028-05-S; each BUY cancel/replace is paired within ~0.1s with a SELL cancel/replace at 2196 qty |

## AgentCore Evaluations

167 sessions scored against ground truth generated from the labels (`evals/ground_truth.py`); 0 evaluator error(s). Pass = score 1.0.

| evaluator | n | mean | pass rate | judge tokens in / out |
|---|---|---|---|---|
| Correctness | 167 | 0.90 | 90% | 153,448 / 39,779 |
| GoalSuccessRate | 167 | 0.93 | 93% | 2,795,661 / 63,909 |
| TrajectoryAnyOrderMatch | 167 | 1.00 | 100% | programmatic |
| TrajectoryInOrderMatch | 167 | 1.00 | 100% | programmatic |
| surv_rationale_rubric | 167 | 0.61 | 1% | 3,822,539 / 248,929 |

| scenario | Correctness | GoalSuccessRate | TrajectoryAnyOrderMatch | TrajectoryInOrderMatch | surv_rationale_rubric |
|---|---|---|---|---|---|
| BACKGROUND | 1.00 | 1.00 | 1.00 | 1.00 | 0.59 |
| F-ALGO-1 | 1.00 | 1.00 | 1.00 | 1.00 | 0.59 |
| F-FAT-1 | 0.67 | 0.67 | 1.00 | 1.00 | 0.42 |
| F-ICE-1 | 1.00 | 1.00 | 1.00 | 1.00 | 0.67 |
| F-MM-1 | 1.00 | 1.00 | 1.00 | 1.00 | 0.59 |
| F-NEWS-1 | 0.25 | 0.50 | 1.00 | 1.00 | 0.50 |
| F-PARTIAL-1 | 1.00 | 1.00 | 1.00 | 1.00 | 0.62 |
| F-RISK-1 | 0.67 | 1.00 | 1.00 | 1.00 | 0.58 |
| F-SPOOFLIKE-HARD-1 | 0.83 | 1.00 | 1.00 | 1.00 | 0.58 |
| F-STOP-1 | 0.00 | 0.00 | 1.00 | 1.00 | 0.54 |
| S-LAYER-1 | 1.00 | 1.00 | 1.00 | 1.00 | 0.60 |
| S-SPOOF-1 | 0.86 | 1.00 | 1.00 | 1.00 | 0.79 |
| S-SPOOF-2 | 0.33 | 0.33 | 1.00 | 1.00 | 0.75 |
| S-SPOOF-3 | 1.00 | 1.00 | 1.00 | 1.00 | 0.75 |
| S-SPOOF-4 | 0.50 | 1.00 | 1.00 | 1.00 | 0.75 |
| S-SPOOF-5 | 1.00 | 1.00 | 1.00 | 1.00 | 0.61 |

Lowest `Correctness` scores:

- A-261005-0005 = 0: The agent response and expected response both propose CLOSE_FP disposition for a market maker scenario. However, there are critical factual discrepancies:  1. **Opposite-side fills**: The agent states `opposite_side_fill_qty` is 0 (no BUY-side fills), while the expected response says 'opposite fills
- A-261005-0007 = 0: The core factual disagreement is the disposition. The expected response says CLOSE_FP (close as false positive) with a legitimate explanation: momentum trader stopped out, price moved against resting bids, negative round trip (loss), price kept falling after cancels with nothing to revert. The agent
- A-261006-0001 = 0: The agent response correctly identifies the proposed disposition as CLOSE_FP and correctly identifies the kill switch as the key legitimate explanation. However, there are some discrepancies with the expected response:  1. The expected response states 'all resting orders on both sides cancelled in t
- A-261006-0005 = 0: The critical difference is the proposed disposition. The expected response says CLOSE_FP (close as false positive) with the explanation 'momentum trader stopped out' as a supported legitimate explanation. The agent response says ESCALATE with confidence 0.6, explicitly stating it could not support t
- A-261006-0014 = 0: The core disposition differs fundamentally. The expected response calls for CLOSE_FP (close as false positive, fat finger explanation), while the agent proposes ESCALATE. The expected response identifies a legitimate fat-finger explanation: one-off order ~10x typical size, cancelled within 2 seconds

Lowest `GoalSuccessRate` scores:

- A-261005-0007 = 0: The success assertions require: (1) surv___propose_disposition called exactly once with CLOSE_FP disposition; (2) compute_discriminators and get_trader_profile called before propose_disposition; (3) all numbers in evidence appear in tool results; (4) report names detector window and states whether a
- A-261006-0005 = 0: Checking each assertion: 1. Agent called surv___propose_disposition exactly once with disposition 'ESCALATE', not 'CLOSE_FP'. This assertion FAILS. 2. Agent did call compute_discriminators and get_trader_profile before propose_disposition. PASSES. 3. Numbers in evidence facts appear in tool results.
- A-261006-0014 = 0: Checking each assertion: 1. 'surv___propose_disposition called exactly once and proposed CLOSE_FP' - The agent called it once but proposed ESCALATE, not CLOSE_FP. This assertion FAILS. 2. 'compute_discriminators and get_trader_profile called before propose_disposition' - Yes, both were called before
- A-261015-0003 = 0: The first assertion requires the agent to have proposed DRAFT_STOR, but the agent proposed ESCALATE instead. The tool call to surv___propose_disposition used disposition='ESCALATE', not 'DRAFT_STOR'. This is a clear failure of the first and most critical assertion. All other assertions may be satisf
- A-261015-0008 = 0: The success assertions require: (1) surv___propose_disposition called exactly once with CLOSE_FP disposition; (2) compute_discriminators and get_trader_profile called before propose_disposition; (3) all numbers in evidence facts appear in tool results; (4) report names detector window and states whe

Lowest `surv_rationale_rubric` scores:

- A-261014-0001 = 0: The report's structure is strong. The summary gives the sequence in order: a BUY of 12490 at 10001, 5.3x depth, with 5828 filled before the trader's only SELL (374 at 10003, 10:29:02.852). It then records a MODIFY of -5046 and a full fill by 10:29:11. CLOSE_FP rests on the genuine-execution explanat
- A-261016-0005 = 0: Strengths: the report gives a clear sequence. Two BUY 7162 orders rested at 9999 (15:47:30.644 and 15:47:33.644). A SELL 511 filled at 10001 at 15:47:58.144. Both bids were cancelled at 15:48:00.750, 106 ms after the 15:48:00.644 news. Most figures trace to tool results: 5.76x matches max_resting_si
- A-261022-0003 = 0: The report is otherwise strong. The sequence is clear: a market buy of 1333 at 13:16:57, three BUY limits of 4800 at 9995/9995/9994 placed between 13:16:59 and 13:17:03, a market sell of 1333 at 13:17:17.579, and all three bids cancelled at 13:17:18.179. Sizes are related to depth (5.72x top-5 depth
- A-261023-0006 = 0: Structure and clarity are strong. The report gives a clear rest → opposite fill → same-side fill → cancel sequence with timestamps. It sizes the SELL against depth (9.9x), uses the indicator vocabulary correctly, and lists indicators matched and not matched. It rules out explanations with cited evid
- A-261006-0014 = 0.25: Clarity: the summary and E1 lay out the sequence explicitly. A 21,230 BUY was placed 1 tick below the bid (8.66x top-5 depth) at 15:24:55.884, cancelled about 943 ms later, and followed by a 2,123 BUY at the same price at 15:24:57.227. All numbers (8.66, 943.3, 0.909, 2450.3, 500, 2,123) trace to to

## Disagreements with the label (11)

| alert | scenario | expected | proposed | conf | status | summary |
|---|---|---|---|---|---|---|
| A-261015-0003 | S-SPOOF-2 | DRAFT_STOR | ESCALATE | 0.7 | ok | PROP trader T-X1015-02 placed one SELL LIMIT of 21443 (8.17x avg top-5 depth, 2 ticks from touch) at 11:04:43.303, then sent a 1189 BUY market order at 11:04:45 |
| A-261016-0006 | S-SPOOF-2 | DRAFT_STOR | ESCALATE | 0.7 | ok | PROP trader (no MM registration) placed one BUY LIMIT of 21860 (8.8x avg top-5 depth, 3 ticks below the touch) at 16:38:01.976 with no fills. 2.1s later the tra |
| A-261006-0014 | F-FAT-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader placed a single BUY of 21,230 (8.66x avg top-5 depth) 1 tick below the bid and cancelled it after ~943 ms, then placed a 2,123 BUY at the same price |
| A-261015-0008 | F-NEWS-1 | CLOSE_FP | ESCALATE | 0.7 | ok | Prop trader T-X1015-07 rested two BUY limits of 7,215 each (14,430 total, 5.5x avg top-5 depth) at 9996, 1.5 ticks from the touch, for about 30 s with no fills. |
| A-261016-0003 | F-NEWS-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader (no MM registration) rested two one-sided BUY orders of 6680 each at 9997 (5.4x top-5 depth, 1.5 ticks from touch) with zero fills. While they reste |
| A-261005-0007 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.7 | ok | PROP trader (no MM registration) bought 1132 at market (13:20:37), then placed three one-sided BUY limits of 4077 (about 5x depth, 6 ticks from touch, two level |
| A-261006-0005 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader (no MM registration) bought 1058 by market order at 11:36:02, then placed three one-sided BUY limits of 3810 each (11430 total, up to 4.66x top-5 de |
| A-261022-0003 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | PROP-EQ trader (not a registered MM) bought 1333 at market, then placed three one-sided BUY limits of 4800 (14400 total, 5.7x top-5 depth, 6 ticks from touch) w |
| A-261026-0003 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | PROP trader with no MM registration placed three one-sided BUY limit layers (3 x 4024, 9996/9995/9994, about 6 ticks from the touch, up to 4.87x top-5 depth) in |
| A-261027-0008 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader (no MM registration) bought 1254 at market (10005), then stacked three one-sided BUY limits of 4514 each (13542 total, 5.4x top-5 depth) at 9997-999 |
| A-261028-0011 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | PROP trader (no MM registration) placed three one-sided BUY limits of 5313 each (15939 total, 6.5x top-5 depth, 6 ticks from touch) in 4s, never filled, and can |
