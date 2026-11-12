# Dataset run `20261111T1326-seed8-generalisation`

- Dataset `seed8`, 100 alerts (24 TRUE_ABUSE, 76 FALSE_POSITIVE); backend `runtime`, model `eu.anthropic.claude-sonnet-5-5`, analyst `L1`, mode `investigate`, memory on, bundle none (code defaults), concurrency 2.
- Started 2026-11-11T13:26:36+00:00, finished 2026-11-11T13:58:44+00:00 (32.1 min).
- Notes: generalisation: the promoted configuration (Runtime v15 = v14 code, iteration-2 procedures, memory on) on a dataset no configuration was tuned against: seed 8, November 2026 dates, detector K=4 (tuning report), 100 alerts, 24 true abuse, 1 background; compared with v4 on seed7 (different alerts, same scenarios)

## Headline

| metric | value |
|---|---|
| gate | **holds** (0 TRUE_ABUSE proposed CLOSE_FP) |
| safe close rate | 86.8% (66 of 76 false positives closed) |
| escalation precision | 70.6% (34 ESCALATE/DRAFT_STOR) |
| strong-call precision | 100.0% (3 DRAFT_STOR) |
| agreement with label (exact disposition) | 88.0% |
| **override rate** (1 - agreement) | **12.0%** |
| direction agreement (close vs not-close) | 90.0% |
| proposals | {'CLOSE_FP': 66, 'ESCALATE': 31, 'DRAFT_STOR': 3} |
| run status | {'ok': 100} |
| configuration bundle reported by the agent | none |
| latency, agent p50 / p95 | 27.7 s / 34.7 s (wall p50 33.8 s) |
| tokens per alert, in / out (mean) | 12 / 3153 (max in 14) |
| prompt cache, per alert | read 51090 / write 18685 / full price 12 tokens; hit rate 0.732 of 69787 prompt tokens |
| tool calls per alert (mean / median) | 10.0 / 10.0 |
| estimated model cost | $8.85 total, $0.088 per alert (assumed $2.0/$10.0 per M tokens in/out; cache read 0.1x, write 1.25x of input; not verified against the pricing page) |

## Against the baselines (same alerts)

| scorer | gate | safe close rate | raw safe close | escalation precision | agreement | override rate |
|---|---|---|---|---|---|---|
| agent (this run) | holds | 86.8% | 86.8% | 70.6% | 88.0% | 12.0% |
| threshold baseline (detector rules) | 1 missed | n/a | 90.8% | 76.7% | 92.0% | 8.0% |
| escalate everything | holds | 0.0% | 0.0% | 24.0% | 19.0% | 81.0% |
| close everything (the gate at work) | 24 missed | n/a | 100.0% | n/a | 76.0% | 24.0% |

## Confusion: expected (rows) x proposed (columns)

| expected \ proposed | CLOSE_FP | ESCALATE | DRAFT_STOR | none |
|---|---|---|---|---|
| CLOSE_FP | 66 | 10 | 0 | 0 |
| ESCALATE | 0 | 19 | 0 | 0 |
| DRAFT_STOR | 0 | 2 | 3 | 0 |

## Per scenario

| scenario | truth | expected | n | CLOSE_FP | ESCALATE | DRAFT_STOR | none | agreement | mean conf | gate misses |
|---|---|---|---|---|---|---|---|---|---|---|
| S-LAYER-1 | TRUE_ABUSE | ESCALATE | 3 | 0 | 3 | 0 | 0 | 100% | 0.72 | - |
| S-SPOOF-1 | TRUE_ABUSE | ESCALATE | 11 | 0 | 11 | 0 | 0 | 100% | 0.7 | - |
| S-SPOOF-2 | TRUE_ABUSE | DRAFT_STOR | 5 | 0 | 2 | 3 | 0 | 60% | 0.66 | - |
| S-SPOOF-3 | TRUE_ABUSE | ESCALATE | 3 | 0 | 3 | 0 | 0 | 100% | 0.7 | - |
| S-SPOOF-4 | TRUE_ABUSE | ESCALATE | 2 | 0 | 2 | 0 | 0 | 100% | 0.7 | - |
| BACKGROUND | FALSE_POSITIVE | CLOSE_FP | 1 | 1 | 0 | 0 | 0 | 100% | 0.9 | - |
| F-ALGO-1 | FALSE_POSITIVE | CLOSE_FP | 22 | 22 | 0 | 0 | 0 | 100% | 0.84 | - |
| F-FAT-1 | FALSE_POSITIVE | CLOSE_FP | 3 | 1 | 2 | 0 | 0 | 33% | 0.63 | - |
| F-ICE-1 | FALSE_POSITIVE | CLOSE_FP | 6 | 6 | 0 | 0 | 0 | 100% | 0.83 | - |
| F-MM-1 | FALSE_POSITIVE | CLOSE_FP | 17 | 17 | 0 | 0 | 0 | 100% | 0.87 | - |
| F-NEWS-1 | FALSE_POSITIVE | CLOSE_FP | 6 | 4 | 2 | 0 | 0 | 67% | 0.64 | - |
| F-PARTIAL-1 | FALSE_POSITIVE | CLOSE_FP | 5 | 5 | 0 | 0 | 0 | 100% | 0.79 | - |
| F-RISK-1 | FALSE_POSITIVE | CLOSE_FP | 4 | 3 | 1 | 0 | 0 | 75% | 0.64 | - |
| F-SPOOFLIKE-HARD-1 | FALSE_POSITIVE | CLOSE_FP | 7 | 7 | 0 | 0 | 0 | 100% | 0.76 | - |
| F-STOP-1 | FALSE_POSITIVE | CLOSE_FP | 5 | 0 | 5 | 0 | 0 | 0% | 0.6 | - |

## Regression against the previous run

Previous run: `20261110T1833-sonnet-v4`. Verdict: **FAIL**.

- [x] gate holds
- [ ] safe close rate not down by more than 2 points
- [ ] no false-positive scenario regressed to 0% close (F-STOP-1)

| delta | value |
|---|---|
| raw_safe_close_rate | -8.1 pts |
| agreement | -6.6 pts |
| escalation_precision | -9.4 pts |
| direction_agreement | -5.8 pts |
| true_abuse_recall | +0.0 pts |
| gate misses | +0 |

| scenario | agreement delta | close-rate delta |
|---|---|---|
| F-FAT-1 | -67 pts | -67 pts |
| F-STOP-1 | -33 pts | -33 pts |
| F-RISK-1 | -25 pts | -25 pts |
| S-SPOOF-2 | +27 pts | +0 pts |
| F-NEWS-1 | +42 pts | +42 pts |

## Evidence faithfulness

100 reports checked against their sessions' tool results (`evals/faithfulness.py`): **96.0% of reports** have every number grounded; 2462 of 2466 numbers matched (99.8%). Categorical claims (roles, desks, order types, registration): 384 of 384 matched (100.0%).

| alert | scenario | proposed | source | unmatched | fact |
|---|---|---|---|---|---|
| A-261103-0003 | F-STOP-1 | ESCALATE | get_order_events | 1274 | SELL MARKET 1354 at 14:56:03.778 filled 863 at 10003/10002 as the bid dropped from 10003 to 10001; earlier BUY MARKET 1354 at 14:55:43 filled 1274 at 10007-10009 |
| A-261105-0005 | F-NEWS-1 | CLOSE_FP | get_market_events | 166 | NEWS 'issuer announces unscheduled trading update' at 15:34:43.834, 166 ms before the cancels and after the sale |
| A-261111-0002 | F-NEWS-1 | CLOSE_FP | get_order_events | 190 | SELL 500 filled 11:52:54.823 (before news); BUY cancels at 11:52:57.513, 190 ms after the news |
| A-261120-0004 | F-NEWS-1 | CLOSE_FP | get_order_events | 192 | Both BUY orders cancelled at 17:05:03.283 (192 ms after the news); the SELL 544 was placed at 17:04:59.091 and filled at 17:05:00.591, before the news; 20 partial fills on O-00039369 from 17:04:43.825 |

## Disagreements with the label (12)

| alert | scenario | expected | proposed | conf | status | summary |
|---|---|---|---|---|---|---|
| A-261106-0006 | S-SPOOF-2 | DRAFT_STOR | ESCALATE | 0.7 | ok | PROP trader placed one SELL limit of 24907 (10.3x avg top-5 depth, 3 ticks from touch) at 13:45:54.608, then 2.2s later bought 696 by market order at 10005, and |
| A-261126-0007 | S-SPOOF-2 | DRAFT_STOR | ESCALATE | 0.6 | ok | Prop trader T-X1126-07 placed a single SELL LIMIT of 20229 (7.85x avg top-5 depth) at 4 ticks from the touch, bought 1258 by MARKET order at the ask 323 ms befo |
| A-261106-0009 | F-FAT-1 | CLOSE_FP | ESCALATE | 0.6 | ok | PROP trader T-X1106-11 placed one BUY 22140 at 9994 (9.1x avg top-5 depth, about 44x typical size 500), 1 tick below the best bid of 9995, and cancelled it afte |
| A-261109-0004 | F-FAT-1 | CLOSE_FP | ESCALATE | 0.6 | ok | PROP-EQ trader placed one BUY LIMIT of 24,250 (9.4x avg top-5 depth, about 48x typical size 500) at 9994, 1 tick behind the touch, and cancelled it after about  |
| A-261117-0001 | F-NEWS-1 | CLOSE_FP | ESCALATE | 0.6 | ok | PROP trader placed two BUY limits of 6031 each (12062 total, 4.8x avg top-5 depth) at 9996, 1.5 ticks from the touch, with no fills on them. At 09:29:52-53 a SE |
| A-261126-0004 | F-NEWS-1 | CLOSE_FP | ESCALATE | 0.6 | ok | PROP trader placed two one-sided BUY limits of 7806 each (about 6x average top-5 depth, 15x typical size) at 1.5 ticks from the touch. About 2.6s before the can |
| A-261124-0004 | F-RISK-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader placed three one-sided BUY limit orders (3966 each, 11898 total, 5.19x top-5 depth) at 3 levels 5s apart, then sold 594 at 10005 after the touch had |
| A-261103-0003 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader (no MM registration) placed three one-sided BUY limit orders of 4,876 each (14,628 total, ~6x top-5 depth) at 10001/10000/9999, 5-7 ticks below the  |
| A-261104-0009 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | PROP trader bought 979 at market (~10006) at 15:48:19, then placed three one-sided BUY limits of 3526 each (10578 total, 4.5x top-5 depth, 6 ticks from touch, 2 |
| A-261109-0001 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | PROP trader bought 1413 at market at 09:23:05, then placed three BUY limit layers of 5086 each (9995/9994/9993, 6 ticks from touch, 5.9x top-5 depth) over 4 s,  |
| A-261110-0006 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | PROP-EQ trader bought 1087 at market (15:56:29), then placed three one-sided BUY limits of 3913 each (11739 total, about 4.8x top-5 depth) 6 ticks below the tou |
| A-261116-0004 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | PROP trader (no MM registration) rested three one-sided BUY limits of 4305 each (12915 total, about 5x top-5 depth, 6 ticks from touch) with no fills, then sold |
