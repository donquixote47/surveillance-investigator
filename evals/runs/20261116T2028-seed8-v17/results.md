# Dataset run `20261116T2028-seed8-v17`

- Dataset `seed8`, 100 alerts (24 TRUE_ABUSE, 76 FALSE_POSITIVE); backend `runtime`, model `eu.anthropic.claude-sonnet-5-5`, analyst `L1`, mode `investigate`, memory on, bundle none (code defaults), concurrency 2.
- Started 2026-11-16T20:28:34+00:00, finished 2026-11-16T21:00:24+00:00 (31.8 min).
- Notes: generalisation on the release: Runtime v17 with the tools and the standard of 2026-11-16 (v0.3.0-alpha) on seed8, the dataset no configuration was tuned against (100 alerts, 24 true abuse); compared with the v14 run 20261111T1326-seed8-generalisation on the same alerts; the one alert with a recorded test decision (A-261126-0001) reopened for the run and restored after

## Headline

| metric | value |
|---|---|
| gate | **holds** (0 TRUE_ABUSE proposed CLOSE_FP) |
| safe close rate | 88.2% (67 of 76 false positives closed) |
| escalation precision | 72.7% (33 ESCALATE/DRAFT_STOR) |
| strong-call precision | 100.0% (2 DRAFT_STOR) |
| agreement with label (exact disposition) | 88.0% |
| **override rate** (1 - agreement) | **12.0%** |
| direction agreement (close vs not-close) | 91.0% |
| proposals | {'CLOSE_FP': 67, 'ESCALATE': 31, 'DRAFT_STOR': 2} |
| run status | {'ok': 100} |
| configuration bundle reported by the agent | none |
| latency, agent p50 / p95 | 23.9 s / 35.8 s (wall p50 29.7 s) |
| tokens per alert, in / out (mean) | 11 / 3049 (max in 14) |
| prompt cache, per alert | read 53665 / write 19211 / full price 11 tokens; hit rate 0.736 of 72887 prompt tokens |
| tool calls per alert (mean / median) | 10.0 / 10.0 |
| estimated model cost | $8.93 total, $0.089 per alert (assumed $2.0/$10.0 per M tokens in/out; cache read 0.1x, write 1.25x of input; not verified against the pricing page) |

## Against the baselines (same alerts)

| scorer | gate | safe close rate | raw safe close | escalation precision | agreement | override rate |
|---|---|---|---|---|---|---|
| agent (this run) | holds | 88.2% | 88.2% | 72.7% | 88.0% | 12.0% |
| threshold baseline (detector rules) | 1 missed | n/a | 90.8% | 76.7% | 92.0% | 8.0% |
| escalate everything | holds | 0.0% | 0.0% | 24.0% | 19.0% | 81.0% |
| close everything (the gate at work) | 24 missed | n/a | 100.0% | n/a | 76.0% | 24.0% |

## Confusion: expected (rows) x proposed (columns)

| expected \ proposed | CLOSE_FP | ESCALATE | DRAFT_STOR | none |
|---|---|---|---|---|
| CLOSE_FP | 67 | 9 | 0 | 0 |
| ESCALATE | 0 | 19 | 0 | 0 |
| DRAFT_STOR | 0 | 3 | 2 | 0 |

## Per scenario

| scenario | truth | expected | n | CLOSE_FP | ESCALATE | DRAFT_STOR | none | agreement | mean conf | gate misses |
|---|---|---|---|---|---|---|---|---|---|---|
| S-LAYER-1 | TRUE_ABUSE | ESCALATE | 3 | 0 | 3 | 0 | 0 | 100% | 0.72 | - |
| S-SPOOF-1 | TRUE_ABUSE | ESCALATE | 11 | 0 | 11 | 0 | 0 | 100% | 0.73 | - |
| S-SPOOF-2 | TRUE_ABUSE | DRAFT_STOR | 5 | 0 | 3 | 2 | 0 | 40% | 0.68 | - |
| S-SPOOF-3 | TRUE_ABUSE | ESCALATE | 3 | 0 | 3 | 0 | 0 | 100% | 0.73 | - |
| S-SPOOF-4 | TRUE_ABUSE | ESCALATE | 2 | 0 | 2 | 0 | 0 | 100% | 0.7 | - |
| BACKGROUND | FALSE_POSITIVE | CLOSE_FP | 1 | 1 | 0 | 0 | 0 | 100% | 0.93 | - |
| F-ALGO-1 | FALSE_POSITIVE | CLOSE_FP | 22 | 22 | 0 | 0 | 0 | 100% | 0.84 | - |
| F-FAT-1 | FALSE_POSITIVE | CLOSE_FP | 3 | 3 | 0 | 0 | 0 | 100% | 0.72 | - |
| F-ICE-1 | FALSE_POSITIVE | CLOSE_FP | 6 | 6 | 0 | 0 | 0 | 100% | 0.83 | - |
| F-MM-1 | FALSE_POSITIVE | CLOSE_FP | 17 | 17 | 0 | 0 | 0 | 100% | 0.88 | - |
| F-NEWS-1 | FALSE_POSITIVE | CLOSE_FP | 6 | 3 | 3 | 0 | 0 | 50% | 0.62 | - |
| F-PARTIAL-1 | FALSE_POSITIVE | CLOSE_FP | 5 | 5 | 0 | 0 | 0 | 100% | 0.81 | - |
| F-RISK-1 | FALSE_POSITIVE | CLOSE_FP | 4 | 2 | 2 | 0 | 0 | 50% | 0.6 | - |
| F-SPOOFLIKE-HARD-1 | FALSE_POSITIVE | CLOSE_FP | 7 | 7 | 0 | 0 | 0 | 100% | 0.78 | - |
| F-STOP-1 | FALSE_POSITIVE | CLOSE_FP | 5 | 1 | 4 | 0 | 0 | 20% | 0.6 | - |

## Regression against the previous run

Previous run: `20261111T1326-seed8-generalisation`. Verdict: **PASS (offline promotion rule)**.

- [x] gate holds
- [x] safe close rate not down by more than 2 points
- [x] no false-positive scenario regressed to 0% close (none)
- [x] evidence faithfulness at least 99% and not down by more than 0.5 points (99.84% of 2427 numbers, previous 99.84%; 100.00% of 367 categorical claims)

| delta | value |
|---|---|
| raw_safe_close_rate | +1.3 pts |
| agreement | +0.0 pts |
| escalation_precision | +2.1 pts |
| direction_agreement | +1.0 pts |
| true_abuse_recall | +0.0 pts |
| gate misses | +0 |

| scenario | agreement delta | close-rate delta |
|---|---|---|
| F-RISK-1 | -25 pts | -25 pts |
| S-SPOOF-2 | -20 pts | +0 pts |
| F-NEWS-1 | -17 pts | -17 pts |
| F-STOP-1 | +20 pts | +20 pts |
| F-FAT-1 | +67 pts | +67 pts |

## Evidence faithfulness

100 reports checked against their sessions' tool results (`evals/faithfulness.py`): **96.0% of reports** have every number grounded; 2423 of 2427 numbers matched (99.8%). Categorical claims (roles, desks, order types, registration): 367 of 367 matched (100.0%).

| alert | scenario | proposed | source | unmatched | fact |
|---|---|---|---|---|---|
| A-261103-0003 | F-STOP-1 | ESCALATE | get_order_events | 1274 | Earlier, at 14:55:43.778, a market BUY of 1354 was filled 1274 at 10007-10009 with 80 cancelled. The market SELL of 1354 was filled 863 at 10003/10002 with 491 cancelled. |
| A-261111-0002 | F-NEWS-1 | CLOSE_FP | get_market_events | 190 | NEWS 'issuer announces unscheduled trading update' at 11:52:57.323, 190 ms before the cancels. |
| A-261117-0001 | F-NEWS-1 | ESCALATE | get_market_events | 74 | NEWS 09:29:56.006: issuer announces unscheduled trading update, 74 ms before the cancels |
| A-261120-0004 | F-NEWS-1 | CLOSE_FP | get_order_events | 192 | Both BUY orders cancelled at 17:05:03.283, 192 ms after the news; SELL 544 placed 17:04:59.091 and filled 17:05:00.591, before the news |

## Disagreements with the label (12)

| alert | scenario | expected | proposed | conf | status | summary |
|---|---|---|---|---|---|---|
| A-261106-0006 | S-SPOOF-2 | DRAFT_STOR | ESCALATE | 0.7 | ok | PROP trader placed one-sided SELL limit of 24907 (10.26x depth, 3 ticks from touch) at 13:45:54.608. Zero fills on it. A BUY market order was executed 2.2s late |
| A-261119-0001 | S-SPOOF-2 | DRAFT_STOR | ESCALATE | 0.7 | ok | Prop trader placed a one-sided SELL limit of 28,359 (11.9x avg top-5 depth) 3 ticks from the touch. 2.5s later a BUY market order of 1,247 executed. The SELL wa |
| A-261126-0007 | S-SPOOF-2 | DRAFT_STOR | ESCALATE | 0.7 | ok | PROP trader placed a one-sided SELL limit of 20229 (7.85x avg top-5 depth, 4 ticks from touch) at 16:27:40.050. 1.7s later a BUY market order of 1258 executed a |
| A-261105-0005 | F-NEWS-1 | CLOSE_FP | ESCALATE | 0.6 | ok | PROP trader (no MM registration) rested two BUY LIMIT orders of 6325 each (12650 total, ~5x depth) at 10003, 1.5 ticks from the touch, with no executions. While |
| A-261117-0001 | F-NEWS-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader placed two BUY LIMIT orders of 6,031 each (12,062 combined, 4.8x avg top-5 depth of 2,508; typical order size 500) at 9996, 1.5 ticks off the touch. |
| A-261126-0004 | F-NEWS-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader (not a registered MM) rested two BUY limits of 7806 each (3.03x depth, 1-2 ticks from touch) for 27-30s with zero fills, sold 557 at the ask (10003) |
| A-261116-0003 | F-RISK-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader laid three BUY limit orders of 5112 each (15336 total, about 5.9x average top-5 depth, 10x typical size 500) at 9999/9998/9997 over 15s. The touch w |
| A-261124-0004 | F-RISK-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Three BUY limit orders of 3966 each (11898 gross, 5.2x depth) were placed 5s apart at 10000/10001/9999. None executed. The trader sold 594 at 10005 at 15:42:20. |
| A-261103-0003 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | PROP trader placed three one-sided BUY limit layers (3 x 4,876 = 14,628, about 6x average depth) 6 ticks from the touch. None filled. About 600 ms after a marke |
| A-261104-0009 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | PROP trader (no MM registration) bought 979 by market order at 10006-10007, then placed three one-sided BUY limits of 3526 each (10578 total, 4.5x depth) at 999 |
| A-261109-0001 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader bought 1413 at market (to 10003), then stacked three BUY limits of 5086 each at 9995/9994/9993 (15258 total, 5.9x depth, 5-7 ticks below the ask). 1 |
| A-261116-0004 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader (no MM registration) bought 1196 by market order at 10003, then stacked three one-sided BUY limits of 4305 each (12915 total, 4.95x depth) at 9995/9 |
