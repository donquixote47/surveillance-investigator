# Dataset run `20261117T2346-sonnet-v6`

- Dataset `seed7`, 167 alerts (28 TRUE_ABUSE, 139 FALSE_POSITIVE); backend `runtime`, model `eu.anthropic.claude-sonnet-5-5`, analyst `L1`, mode `investigate`, memory on, bundle none (code defaults), concurrency 2.
- Started 2026-11-17T23:46:01+00:00, finished 2026-11-18T00:41:07+00:00 (55.1 min).
- Notes: full seed7 run on Runtime v19 (DEFAULT): v17's packages locked, tests out of the bundle, guard counts an evidence tool only when its answer names the alert; back end and policies of 2026-11-17

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
| configuration bundle reported by the agent | none |
| latency, agent p50 / p95 | 25.0 s / 36.1 s (wall p50 31.2 s) |
| tokens per alert, in / out (mean) | 11 / 2981 (max in 12) |
| prompt cache, per alert | read 54078 / write 21086 / full price 11 tokens; hit rate 0.719 of 75175 prompt tokens |
| tool calls per alert (mean / median) | 10 / 10 |
| estimated model cost | $15.59 total, $0.093 per alert (assumed $2.0/$10.0 per M tokens in/out; cache read 0.1x, write 1.25x of input; not verified against the pricing page) |

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
| S-LAYER-1 | TRUE_ABUSE | ESCALATE | 5 | 0 | 5 | 0 | 0 | 100% | 0.71 | - |
| S-SPOOF-1 | TRUE_ABUSE | ESCALATE | 7 | 0 | 7 | 0 | 0 | 100% | 0.71 | - |
| S-SPOOF-2 | TRUE_ABUSE | DRAFT_STOR | 3 | 0 | 2 | 1 | 0 | 33% | 0.73 | - |
| S-SPOOF-3 | TRUE_ABUSE | ESCALATE | 4 | 0 | 4 | 0 | 0 | 100% | 0.73 | - |
| S-SPOOF-4 | TRUE_ABUSE | ESCALATE | 2 | 0 | 2 | 0 | 0 | 100% | 0.71 | - |
| S-SPOOF-5 | TRUE_ABUSE | ESCALATE | 7 | 0 | 7 | 0 | 0 | 100% | 0.73 | - |
| BACKGROUND | FALSE_POSITIVE | CLOSE_FP | 52 | 52 | 0 | 0 | 0 | 100% | 0.89 | - |
| F-ALGO-1 | FALSE_POSITIVE | CLOSE_FP | 24 | 24 | 0 | 0 | 0 | 100% | 0.85 | - |
| F-FAT-1 | FALSE_POSITIVE | CLOSE_FP | 3 | 3 | 0 | 0 | 0 | 100% | 0.74 | - |
| F-ICE-1 | FALSE_POSITIVE | CLOSE_FP | 9 | 9 | 0 | 0 | 0 | 100% | 0.81 | - |
| F-MM-1 | FALSE_POSITIVE | CLOSE_FP | 24 | 24 | 0 | 0 | 0 | 100% | 0.89 | - |
| F-NEWS-1 | FALSE_POSITIVE | CLOSE_FP | 4 | 2 | 2 | 0 | 0 | 50% | 0.62 | - |
| F-PARTIAL-1 | FALSE_POSITIVE | CLOSE_FP | 8 | 8 | 0 | 0 | 0 | 100% | 0.76 | - |
| F-RISK-1 | FALSE_POSITIVE | CLOSE_FP | 3 | 3 | 0 | 0 | 0 | 100% | 0.65 | - |
| F-SPOOFLIKE-HARD-1 | FALSE_POSITIVE | CLOSE_FP | 6 | 6 | 0 | 0 | 0 | 100% | 0.78 | - |
| F-STOP-1 | FALSE_POSITIVE | CLOSE_FP | 6 | 1 | 5 | 0 | 0 | 17% | 0.62 | - |

## Regression against the previous run

Previous run: `20261116T1828-sonnet-v5`. Verdict: **PASS (offline promotion rule)**.

- [x] gate holds
- [x] safe close rate not down by more than 2 points
- [x] no false-positive scenario regressed to 0% close (none)
- [x] evidence faithfulness at least 99% and not down by more than 0.5 points (99.83% of 4112 numbers, previous 99.72%; 100.00% of 593 categorical claims)

| delta | value |
|---|---|
| raw_safe_close_rate | +0.7 pts |
| agreement | +0.6 pts |
| escalation_precision | +2.2 pts |
| direction_agreement | +0.6 pts |
| true_abuse_recall | +0.0 pts |
| gate misses | +0 |

| scenario | agreement delta | close-rate delta |
|---|---|---|
| F-NEWS-1 | +25 pts | +25 pts |

## Evidence faithfulness

167 reports checked against their sessions' tool results (`evals/faithfulness.py`): **95.8% of reports** have every number grounded; 4105 of 4112 numbers matched (99.8%). Categorical claims (roles, desks, order types, registration): 593 of 593 matched (100.0%).

| alert | scenario | proposed | source | unmatched | fact |
|---|---|---|---|---|---|
| A-261006-0005 | F-STOP-1 | ESCALATE | get_instrument_stats | 1.55 | avg_depth_top5 2450; the layers are 3810 each, 1.55x depth individually. |
| A-261006-0013 | BACKGROUND | CLOSE_FP | get_order_events | 1.755 | Each cycle cancels and re-places a 391 BUY and a 391 SELL together at the same timestamp with prices stepping 10000/10001 (bid) and 10004/10005 (ask). The 143 fill was a PARTIAL_FILL on SELL O-00031053 at 10003 (remainin |
| A-261016-0006 | S-SPOOF-2 | ESCALATE | get_order_events | 645 | SELL MARKET O-00037888 qty 1329 at 16:38:04.112, filled at 10002 (645), 9999 (529), 9998 (155) |
| A-261020-0003 | F-ICE-1 | CLOSE_FP | get_order_events | 10004 | BUY ICEBERG placed 15:34:28.400 at 10003 (1 tick below the 10004 touch reference, distance -1), with 17 partial fills from 15:34:29 before the SELL 609 filled at 15:34:53.400; cancel at 15:34:55.400 |
| A-261022-0001 | F-ALGO-1 | CLOSE_FP | get_order_events | 0.1 | All orders are PEGGED with parent ids P-T-X1022-01-B / P-T-X1022-01-S. Bid and ask are cancelled and re-posted in pairs within about 0.1-0.3 s as the touch moves (10000/10001). |
| A-261022-0003 | F-STOP-1 | ESCALATE | compute_discriminators | 1.9 | price_move_ticks -2.0; post_cancel_move_ticks -1.5; reversion_ticks 0.0; round_trip_ticks -5.42; repetitions_in_session 0; large_orders empty (each order ~1.9x depth). |
| A-261023-0001 | F-NEWS-1 | CLOSE_FP | get_market_events | 148 | NEWS on SYN.A 'issuer announces unscheduled trading update' at 09:38:30.051, 148 ms before the cancels. |

## Disagreements with the label (9)

| alert | scenario | expected | proposed | conf | status | summary |
|---|---|---|---|---|---|---|
| A-261015-0003 | S-SPOOF-2 | DRAFT_STOR | ESCALATE | 0.7 | ok | PROP-EQ trader (no registered MM on SYN.A) placed one SELL LIMIT of 21443 (8.17x avg top-5 depth), 2 ticks from the touch. About 2.4s later they bought 1189 by  |
| A-261016-0006 | S-SPOOF-2 | DRAFT_STOR | ESCALATE | 0.7 | ok | PROP trader placed one BUY LIMIT of 21860 (8.8x depth, 3 ticks below the touch) with no other resting orders. About 2.1s later a SELL MARKET order of 1329 execu |
| A-261015-0008 | F-NEWS-1 | CLOSE_FP | ESCALATE | 0.6 | ok | PROP trader placed two BUY 7,215 LIMIT orders at 9996 (combined 5.5x depth, 1.5 ticks from touch) at 15:12:52 and 15:12:55. About 25s later the trader sold 515  |
| A-261016-0003 | F-NEWS-1 | CLOSE_FP | ESCALATE | 0.62 | ok | Prop trader placed two BUY LIMIT orders of 6,680 each at 9997 (combined 5.37x depth, 1.5 ticks from touch, one-sided, no fills). While they rested the bid rose, |
| A-261005-0007 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader bought 1132 by market order at 13:20:37, then rested three one-sided BUY limits of 4077 each (12231 total, about 5.0x depth in aggregate, 6 ticks fr |
| A-261006-0005 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.7 | ok | Prop trader bought 1058 at market (10002-10005), then placed three one-sided BUY limits of 3810 each (9994/9993/9992, 6 ticks from touch, 11430 total, 4.66x dep |
| A-261022-0003 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader bought 1333 by market order at 13:16:57, then placed three 4,800 BUY limits (14,400 total, ~5.7x depth, 5-6 ticks below the touch) at 13:16:59-13:17 |
| A-261027-0008 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | PROP trader (no MM registration) stacked three one-sided BUY limits (3 x 4514 = 13542, 5.4x avg top-5 depth) 5-8 ticks below the touch over 4s, never executed a |
| A-261028-0011 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader bought 1476 by market order at 10005-10006, then placed three one-sided BUY limits of 5313 each (15939 total, 6.55x depth) 6 ticks off the touch, wi |
