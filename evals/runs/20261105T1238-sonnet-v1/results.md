# Dataset run `20261105T1238-sonnet-v1`

- Dataset `seed7`, 167 alerts (28 TRUE_ABUSE, 139 FALSE_POSITIVE); backend `runtime`, model `eu.anthropic.claude-sonnet-5-5`, analyst `L1`, mode `investigate`, concurrency 2.
- Started 2026-11-05T12:38:34+00:00, finished 2026-11-05T13:35:21+00:00 (56.8 min).
- Notes: first full run: Runtime v8, Sonnet 5.5 effort medium, Memory on, policies ENFORCE, as l1.analyst

## Headline

| metric | value |
|---|---|
| gate | **holds** (0 TRUE_ABUSE proposed CLOSE_FP) |
| safe close rate | 79.9% (111 of 139 false positives closed) |
| escalation precision | 50.0% (56 ESCALATE/DRAFT_STOR) |
| strong-call precision | 100.0% (2 DRAFT_STOR) |
| agreement with label (exact disposition) | 81.4% |
| **override rate** (1 - agreement) | **18.6%** |
| direction agreement (close vs not-close) | 83.2% |
| proposals | {'CLOSE_FP': 111, 'ESCALATE': 54, 'DRAFT_STOR': 2} |
| run status | {'ok': 167} |
| alerts with a disposition recorded before this run (visible to the agent through history and Memory) | 3: A-261005-0003, A-261009-0003, A-261016-0003 |
| latency, agent p50 / p95 | 31.9 s / 47.9 s (wall p50 37.8 s) |
| tokens per alert, in / out (mean) | 81529 / 4097 (max in 163204) |
| tool calls per alert (mean / median) | 10.4 / 10 |
| estimated model cost | $34.07 total, $0.204 per alert (assumed $2.0/$10.0 per M tokens in/out; not verified against the pricing page) |

## Against the baselines (same alerts)

| scorer | gate | safe close rate | raw safe close | escalation precision | agreement | override rate |
|---|---|---|---|---|---|---|
| agent (this run) | holds | 79.9% | 79.9% | 50.0% | 81.4% | 18.6% |
| threshold baseline (detector rules) | 6 missed | n/a | 95.7% | 78.6% | 92.8% | 7.2% |
| escalate everything | holds | 0.0% | 0.0% | 16.8% | 15.0% | 85.0% |
| close everything (the gate at work) | 28 missed | n/a | 100.0% | n/a | 83.2% | 16.8% |

## Confusion: expected (rows) x proposed (columns)

| expected \ proposed | CLOSE_FP | ESCALATE | DRAFT_STOR | none |
|---|---|---|---|---|
| CLOSE_FP | 111 | 28 | 0 | 0 |
| ESCALATE | 0 | 24 | 1 | 0 |
| DRAFT_STOR | 0 | 2 | 1 | 0 |

## Per scenario

| scenario | truth | expected | n | CLOSE_FP | ESCALATE | DRAFT_STOR | none | agreement | mean conf | gate misses |
|---|---|---|---|---|---|---|---|---|---|---|
| S-LAYER-1 | TRUE_ABUSE | ESCALATE | 5 | 0 | 4 | 1 | 0 | 80% | 0.67 | - |
| S-SPOOF-1 | TRUE_ABUSE | ESCALATE | 7 | 0 | 7 | 0 | 0 | 100% | 0.7 | - |
| S-SPOOF-2 | TRUE_ABUSE | DRAFT_STOR | 3 | 0 | 2 | 1 | 0 | 33% | 0.63 | - |
| S-SPOOF-3 | TRUE_ABUSE | ESCALATE | 4 | 0 | 4 | 0 | 0 | 100% | 0.7 | - |
| S-SPOOF-4 | TRUE_ABUSE | ESCALATE | 2 | 0 | 2 | 0 | 0 | 100% | 0.7 | - |
| S-SPOOF-5 | TRUE_ABUSE | ESCALATE | 7 | 0 | 7 | 0 | 0 | 100% | 0.7 | - |
| BACKGROUND | FALSE_POSITIVE | CLOSE_FP | 52 | 50 | 2 | 0 | 0 | 96% | 0.79 | - |
| F-ALGO-1 | FALSE_POSITIVE | CLOSE_FP | 24 | 24 | 0 | 0 | 0 | 100% | 0.78 | - |
| F-FAT-1 | FALSE_POSITIVE | CLOSE_FP | 3 | 3 | 0 | 0 | 0 | 100% | 0.7 | - |
| F-ICE-1 | FALSE_POSITIVE | CLOSE_FP | 9 | 1 | 8 | 0 | 0 | 11% | 0.62 | - |
| F-MM-1 | FALSE_POSITIVE | CLOSE_FP | 24 | 24 | 0 | 0 | 0 | 100% | 0.83 | - |
| F-NEWS-1 | FALSE_POSITIVE | CLOSE_FP | 4 | 1 | 3 | 0 | 0 | 25% | 0.66 | - |
| F-PARTIAL-1 | FALSE_POSITIVE | CLOSE_FP | 8 | 0 | 8 | 0 | 0 | 0% | 0.66 | - |
| F-RISK-1 | FALSE_POSITIVE | CLOSE_FP | 3 | 2 | 1 | 0 | 0 | 67% | 0.64 | - |
| F-SPOOFLIKE-HARD-1 | FALSE_POSITIVE | CLOSE_FP | 6 | 6 | 0 | 0 | 0 | 100% | 0.7 | - |
| F-STOP-1 | FALSE_POSITIVE | CLOSE_FP | 6 | 0 | 6 | 0 | 0 | 0% | 0.6 | - |

## Regression against the previous run

Previous run: `20261105T1238-sonnet-v1`. Verdict: **PASS (offline promotion rule)**.

- [x] gate holds
- [x] safe close rate not down by more than 2 points
- [x] no false-positive scenario regressed to 0% close (none)

| delta | value |
|---|---|
| raw_safe_close_rate | +0.0 pts |
| agreement | +0.0 pts |
| escalation_precision | +0.0 pts |
| direction_agreement | +0.0 pts |
| true_abuse_recall | +0.0 pts |
| gate misses | +0 |

## AgentCore Evaluations

167 sessions scored against ground truth generated from the labels (`evals/ground_truth.py`); 0 evaluator error(s). Pass = score 1.0.

| evaluator | n | mean | pass rate | judge tokens in / out |
|---|---|---|---|---|
| Correctness | 167 | 0.80 | 80% | 154,943 / 40,114 |
| GoalSuccessRate | 167 | 0.81 | 81% | 2,659,664 / 61,660 |
| TrajectoryAnyOrderMatch | 167 | 1.00 | 100% | programmatic |
| TrajectoryInOrderMatch | 167 | 1.00 | 100% | programmatic |
| surv_rationale_rubric | 167 | 0.55 | 0% | 3,635,382 / 262,040 |

| scenario | Correctness | GoalSuccessRate | TrajectoryAnyOrderMatch | TrajectoryInOrderMatch | surv_rationale_rubric |
|---|---|---|---|---|---|
| BACKGROUND | 0.96 | 0.96 | 1.00 | 1.00 | 0.52 |
| F-ALGO-1 | 1.00 | 1.00 | 1.00 | 1.00 | 0.47 |
| F-FAT-1 | 1.00 | 1.00 | 1.00 | 1.00 | 0.42 |
| F-ICE-1 | 0.11 | 0.11 | 1.00 | 1.00 | 0.61 |
| F-MM-1 | 1.00 | 1.00 | 1.00 | 1.00 | 0.53 |
| F-NEWS-1 | 0.25 | 0.25 | 1.00 | 1.00 | 0.69 |
| F-PARTIAL-1 | 0.00 | 0.00 | 1.00 | 1.00 | 0.62 |
| F-RISK-1 | 0.67 | 0.67 | 1.00 | 1.00 | 0.42 |
| F-SPOOFLIKE-HARD-1 | 1.00 | 1.00 | 1.00 | 1.00 | 0.54 |
| F-STOP-1 | 0.00 | 0.00 | 1.00 | 1.00 | 0.46 |
| S-LAYER-1 | 0.80 | 0.80 | 1.00 | 1.00 | 0.70 |
| S-SPOOF-1 | 0.86 | 1.00 | 1.00 | 1.00 | 0.71 |
| S-SPOOF-2 | 0.33 | 0.33 | 1.00 | 1.00 | 0.67 |
| S-SPOOF-3 | 1.00 | 1.00 | 1.00 | 1.00 | 0.75 |
| S-SPOOF-4 | 0.50 | 1.00 | 1.00 | 1.00 | 0.75 |
| S-SPOOF-5 | 1.00 | 1.00 | 1.00 | 1.00 | 0.64 |

Lowest `Correctness` scores:

- A-261005-0002 = 0: The expected response calls for CLOSE_FP (false positive) with the trader identified as a market maker, and the key reasoning being legitimate market-making activity. The agent response instead proposes ESCALATE with confidence 0.5, explicitly stating the disposition is NOT CLOSE_FP. This is a funda
- A-261005-0007 = 0: The critical difference is in the proposed disposition. The expected response clearly states 'CLOSE_FP' (Close as False Positive) with the explanation that this is a legitimate momentum trader who was stopped out - price moved against resting bids, trader sold at a loss, and there was nothing to rev
- A-261005-0009 = 0: The agent proposed ESCALATE with confidence 0.62, while the expected response calls for CLOSE_FP (Close as False Positive). These are fundamentally opposite dispositions. The expected response identifies a legitimate explanation: the iceberg order was for one client (agency role) and the sale was fo
- A-261006-0001 = 0: The critical difference is the proposed disposition. The expected response says CLOSE_FP (close as false positive), while the agent response says ESCALATE. This is a fundamental contradiction on the core question of the investigation.  The expected response identifies the kill switch as a legitimate
- A-261006-0005 = 0: The core disposition differs fundamentally. The expected response calls for CLOSE_FP (close as false positive) with a legitimate explanation of a momentum trader being stopped out at a loss. The agent response proposes ESCALATE with confidence 0.6, treating the activity as potentially suspicious spo

Lowest `GoalSuccessRate` scores:

- A-261005-0002 = 0: Let me check each assertion:  1. 'The agent called surv___propose_disposition exactly once and proposed CLOSE_FP.' - The agent proposed ESCALATE, not CLOSE_FP. This assertion FAILS.  2. 'The agent called surv___compute_discriminators and surv___get_trader_profile before surv___propose_disposition.' 
- A-261005-0007 = 0: Checking each assertion: 1. 'Agent called surv___propose_disposition exactly once and proposed CLOSE_FP' - The agent called surv___propose_disposition once but proposed ESCALATE, not CLOSE_FP. This assertion FAILS. 2. 'Agent called surv___compute_discriminators and surv___get_trader_profile before s
- A-261005-0009 = 0: The first assertion requires the agent to call surv___propose_disposition exactly once and propose CLOSE_FP. However, the agent proposed ESCALATE, not CLOSE_FP. This is a clear failure of the first assertion. Additionally, the report does not mark any legitimate explanation as supported (all are eit
- A-261006-0001 = 0: The agent proposed ESCALATE, not CLOSE_FP. The first assertion requires the agent to have called surv___propose_disposition exactly once and proposed CLOSE_FP. The agent instead proposed ESCALATE. This is a clear failure of the first assertion.  Additionally, the report does not mark the kill-switch
- A-261006-0005 = 0: The success assertions require: (1) surv___propose_disposition called exactly once with CLOSE_FP disposition; (2) compute_discriminators and get_trader_profile called before propose_disposition; (3) all numbers in evidence appear in tool results; (4) report names detector window and states whether a

Lowest `surv_rationale_rubric` scores:

- A-261009-0007 = 0: The report is readable and its structure is good. It gives the sequence NEW, CANCEL, re-entry, rules out market making (empty registered_mm_instruments), risk (risk_limit_events_total 0) and news (no market events), and gives the right reason for absent feature (b): no fills. CLOSE_FP on an entry-er
- A-261027-0008 = 0: The report is clearly structured. It gives the sequence of market buy 1254 at 10005, three BUY limits of 4514 at 13:50:46–50, market sell at 13:51:04.003 and cancels 600 ms later. Most figures trace to tool results: 5.40x depth, the 700 opposite fill (286+156+133+125 = 700) at 9999–10001, price_move
- A-261005-0001 = 0.25: All numbers trace to tool results: 2092, 0.974, 0.0/0.0, 1.23, 1.5, 0.86, 10.0, 40, 4441, 532, the fills 79/46/322/85, and 2426/2.78. The market-making explanation fits the tape: the trader is a registered market maker on SYN.A, quotes two-sided at desk-typical size, and cancels symmetrically. Even 
- A-261005-0006 = 0.25: All cited numbers trace to tool results: 0.995 symmetry, 0.15x depth, 0.38 ticks, 3126, 0.0/0.0, 3.85, 8.625 vs 14.4, 0.815, 2 and 317. The report still has serious problems.  (1) Consistency with the closure standard: that standard defines a positive round trip as feature (b), a benefit. The report
- A-261005-0012 = 0.25: Clarity and grounding: The report is readable. It shows two pegged parents re-posting 1927-lot children about every 3s at the touch. The figures it cites (cancel_symmetry 0.9959, otr 31.33, cancel_ratio 0.950, 559/201 fills, round_trip 3.0, depth 2426) all appear in the tool results, and the roughly

## Disagreements with the label (31)

| alert | scenario | expected | proposed | conf | status | summary |
|---|---|---|---|---|---|---|
| A-261022-0002 | S-LAYER-1 | ESCALATE | DRAFT_STOR | 0.6 | ok | Prop trader placed five one-sided SELL limit orders of 4,734 each (23,670 total, 9.4x avg top-5 depth, about 9x typical size 500) at 10006-10009, 2-5 ticks off  |
| A-261015-0003 | S-SPOOF-2 | DRAFT_STOR | ESCALATE | 0.7 | ok | PROP-EQ trader (no MM registration) placed a single SELL LIMIT of 21443 (8.2x avg top-5 depth) 2 ticks above the touch at 11:04:43.303, bought 1189 by MARKET or |
| A-261016-0006 | S-SPOOF-2 | DRAFT_STOR | ESCALATE | 0.6 | ok | PROP-EQ trader placed one BUY LIMIT of 21860 (8.8x avg top-5 depth, 3 ticks below the touch, typical size 500), sold 1329 at market 2.1s later, and cancelled th |
| A-261005-0002 | BACKGROUND | CLOSE_FP | ESCALATE | 0.5 | ok | T-MM-01 is a registered market maker on SYN.A and the tape looks like two-sided quoting: 364 lots per side, refreshed every 1-7s, cancel symmetry 0.996, resting |
| A-261029-0004 | BACKGROUND | CLOSE_FP | ESCALATE | 0.55 | ok | T-MM-02, a registered market maker on SYN.A, quoted both sides every 1-5s at a constant 381 (0.15x depth) at or next to the touch. Most features point to market |
| A-261005-0009 | F-ICE-1 | CLOSE_FP | ESCALATE | 0.62 | ok | Agency trader T-X1005-05 placed an ICEBERG BUY of 21768 on SYN.A (about 9x top-5 depth, against a typical size of 800). It was partly executed (5835), then the  |
| A-261007-0002 | F-ICE-1 | CLOSE_FP | ESCALATE | 0.6 | ok | AGENCY trader (no MM registration) rested a 19,992 BUY ICEBERG at 9998 (8.07x top-5 depth, 1 tick from touch). About 5,740 executed on it, but after a separate- |
| A-261014-0002 | F-ICE-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Agency trader placed a 20000 BUY ICEBERG at 9997, 8.49x average top-5 depth and far above the 800 typical size. It partly executed (5724) in 6-second slices. At |
| A-261019-0005 | F-ICE-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Agency trader T-X1019-04 placed a 22,280 BUY iceberg at 10001 (8.65x avg top-5 depth) under parent C-T-X1019-04-A. 12,197 executed on that order, which points t |
| A-261019-0009 | F-ICE-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Agency trader placed a 22,256 BUY ICEBERG at the touch (9999), 8.6x top-5 depth and about 28x typical size. It executed 4,941 over 16s in regular slices. Bid th |
| A-261020-0003 | F-ICE-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Agency trader T-X1020-03 rested a 24,368 BUY ICEBERG at 10003 (child of parent C-T-X1020-03-A), 9.1x average top-5 depth and about 30x typical size. The order w |
| A-261028-0007 | F-ICE-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Agency trader placed a 17528 BUY iceberg at the touch (7.2x top-5 depth). About 2990 executed on it. A separate-parent SELL of 438 filled 2s before the 14538 re |
| A-261029-0014 | F-ICE-1 | CLOSE_FP | ESCALATE | 0.62 | ok | Agency trader (no MM registration) rested a 21408 ICEBERG BUY at the touch (9999), 8.4x average top-5 depth and far above the typical size of 800. It executed 5 |
| A-261015-0008 | F-NEWS-1 | CLOSE_FP | ESCALATE | 0.62 | ok | Prop trader placed two BUY 7,215 limit orders at 9996 (about 5.5x avg top-5 depth, 1.5 ticks from touch, vs typical size 500). While they rested, the bid moved  |
| A-261016-0003 | F-NEWS-1 | CLOSE_FP | ESCALATE | 0.7 | ok | Prop trader (not a registered MM) rested two BUY LIMITs of 6680 at 9997 (about 5.4x avg top-5 depth, 1.5 ticks from touch) for ~30s. At 12:02:10.231 he SOLD 477 |
| A-261016-0005 | F-NEWS-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader placed two BUY LIMITs of 7,162 at 9999 (combined 14,324, about 5.8x avg top-5 depth, 1.5 ticks from the touch). They rested about 30s with no fills. |
| A-261006-0009 | F-PARTIAL-1 | CLOSE_FP | ESCALATE | 0.6 | ok | PROP trader (no MM registration) rested a 12,210 BUY LIMIT at the touch (9999), about 5x top-5 depth. About 7,952 executed on it. The trader sold 366 at 10001 a |
| A-261014-0001 | F-PARTIAL-1 | CLOSE_FP | ESCALATE | 0.6 | ok | PROP-EQ trader (no MM registration) placed a 12,490 BUY limit at 10001, one tick inside the 10000/10004 spread, 5.3x avg top-5 depth. It executed steadily (7,03 |
| A-261016-0004 | F-PARTIAL-1 | CLOSE_FP | ESCALATE | 0.7 | ok | PROP trader placed a BUY of 15555 (6.25x top-5 depth, ~31x typical size 500) one tick inside the touch. After 3195 executed, the trader sold 466 at 10006 after  |
| A-261020-0002 | F-PARTIAL-1 | CLOSE_FP | ESCALATE | 0.7 | ok | PROP-EQ trader (typical size 500, no MM registration) rested a 12,140 BUY at 10002 on SYN.A (4.56x top-5 depth). 1,931 executed on it; then a 364 SELL at 10005  |
| A-261021-0004 | F-PARTIAL-1 | CLOSE_FP | ESCALATE | 0.7 | ok | PROP trader placed a 11565 BUY limit at 10003 (4.6x top-5 depth, about 23x typical size 500). The bid was partly executed (2786 same-side), then the trader sold |
| A-261023-0004 | F-PARTIAL-1 | CLOSE_FP | ESCALATE | 0.7 | ok | PROP-EQ trader (no MM registration, typical size 500) rested a single BUY of 19570 (~8x top-5 depth) at 9996. Partial fills of 3568 hit it. The trader then sold |
| A-261023-0009 | F-PARTIAL-1 | CLOSE_FP | ESCALATE | 0.7 | ok | PROP-EQ trader (no MM registration) placed a 9680 BUY at 9996 (about 3.9x top-5 depth, about 19x typical size 500) that improved the bid. 1602 executed, then a  |
| A-261028-0004 | F-PARTIAL-1 | CLOSE_FP | ESCALATE | 0.6 | ok | PROP-EQ trader (not a registered MM) placed an 11,185 BUY limit at 10001 (4.6x top-5 depth; typical size 500). 2,585 executed on it, then the trader sold 335 at |
| A-261006-0001 | F-RISK-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader (no MM registration) stacked three BUY limits of 4614 each (2 levels, 9995-9996, up to 5.6x top-5 depth, ~9x typical size) over 15s, then sold 692 a |
| A-261005-0007 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | PROP-EQ trader (no MM registration) bought 1132 at market (13:20:37), then placed three BUY limits of 4077 each (12231 total, about 5x top-5 depth) 6 ticks from |
| A-261006-0005 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | PROP-EQ trader (no MM registration) bought 1058 by market order at 11:36:02, then stacked three BUY limits of 3810 each (11430 total, 4.66x top-5 depth) at 6 ti |
| A-261022-0003 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | PROP-EQ trader (no MM registration) bought 1333 at market at 13:16:57, then placed three BUY limits of 4,800 each (14,400 total, 5.7x top-5 depth, ~28x typical  |
| A-261026-0003 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader T-X1026-03 bought 1118 by market order (12:36:13), then placed three BUY limits of 4024 each at 9996/9995/9994 (6 ticks from touch, 4.87x top-5 dept |
| A-261027-0008 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | PROP-EQ trader bought 1254 at market (10005), then placed three BUY limits of 4514 each (13542 total, 5.4x avg top-5 depth) 4-8 ticks below the touch, none fill |
| A-261028-0011 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | PROP-EQ trader (no MM registration) bought 1476 by market order at 10005-10006, then placed three 5313 BUY limits (15939 total, 6.5x top-5 depth) at 9997-9998,  |
