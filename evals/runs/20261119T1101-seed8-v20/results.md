# Dataset run `20261119T1101-seed8-v20`

- Dataset `seed8`, 100 alerts (24 TRUE_ABUSE, 76 FALSE_POSITIVE); backend `runtime`, model `eu.anthropic.claude-sonnet-5-5`, analyst `L1`, mode `investigate`, memory on, bundle none (code defaults), concurrency 2.
- Started 2026-11-19T11:01:05+00:00, finished 2026-11-19T11:25:41+00:00 (24.6 min).
- Notes: generalisation on the release: Runtime v20 (v0.4.0-alpha) with one analyst per worker on seed8, the dataset no configuration was tuned against (100 alerts, 24 true abuse); compared with the v17 run 20261116T2028-seed8-v17

## Headline

| metric | value |
|---|---|
| gate | **holds** (0 TRUE_ABUSE proposed CLOSE_FP) |
| safe close rate | 90.8% (69 of 76 false positives closed) |
| escalation precision | 77.4% (31 ESCALATE/DRAFT_STOR) |
| strong-call precision | 100.0% (2 DRAFT_STOR) |
| agreement with label (exact disposition) | 90.0% |
| **override rate** (1 - agreement) | **10.0%** |
| direction agreement (close vs not-close) | 93.0% |
| proposals | {'CLOSE_FP': 69, 'ESCALATE': 29, 'DRAFT_STOR': 2} |
| run status | {'ok': 100} |
| configuration bundle reported by the agent | none |
| latency, agent p50 / p95 | 22.9 s / 27.5 s (wall p50 29.3 s) |
| tokens per alert, in / out (mean) | 11 / 3045 (max in 12) |
| prompt cache, per alert | read 52239 / write 20139 / full price 11 tokens; hit rate 0.722 of 72389 prompt tokens |
| tool calls per alert (mean / median) | 10 / 10.0 |
| estimated model cost | $9.13 total, $0.091 per alert (assumed $2.0/$10.0 per M tokens in/out; cache read 0.1x, write 1.25x of input; not verified against the pricing page) |

## Against the baselines (same alerts)

| scorer | gate | safe close rate | raw safe close | escalation precision | agreement | override rate |
|---|---|---|---|---|---|---|
| agent (this run) | holds | 90.8% | 90.8% | 77.4% | 90.0% | 10.0% |
| threshold baseline (detector rules) | 1 missed | n/a | 90.8% | 76.7% | 92.0% | 8.0% |
| escalate everything | holds | 0.0% | 0.0% | 24.0% | 19.0% | 81.0% |
| close everything (the gate at work) | 24 missed | n/a | 100.0% | n/a | 76.0% | 24.0% |

## Confusion: expected (rows) x proposed (columns)

| expected \ proposed | CLOSE_FP | ESCALATE | DRAFT_STOR | none |
|---|---|---|---|---|
| CLOSE_FP | 69 | 7 | 0 | 0 |
| ESCALATE | 0 | 19 | 0 | 0 |
| DRAFT_STOR | 0 | 3 | 2 | 0 |

## Per scenario

| scenario | truth | expected | n | CLOSE_FP | ESCALATE | DRAFT_STOR | none | agreement | mean conf | gate misses |
|---|---|---|---|---|---|---|---|---|---|---|
| S-LAYER-1 | TRUE_ABUSE | ESCALATE | 3 | 0 | 3 | 0 | 0 | 100% | 0.68 | - |
| S-SPOOF-1 | TRUE_ABUSE | ESCALATE | 11 | 0 | 11 | 0 | 0 | 100% | 0.72 | - |
| S-SPOOF-2 | TRUE_ABUSE | DRAFT_STOR | 5 | 0 | 3 | 2 | 0 | 40% | 0.67 | - |
| S-SPOOF-3 | TRUE_ABUSE | ESCALATE | 3 | 0 | 3 | 0 | 0 | 100% | 0.7 | - |
| S-SPOOF-4 | TRUE_ABUSE | ESCALATE | 2 | 0 | 2 | 0 | 0 | 100% | 0.72 | - |
| BACKGROUND | FALSE_POSITIVE | CLOSE_FP | 1 | 1 | 0 | 0 | 0 | 100% | 0.92 | - |
| F-ALGO-1 | FALSE_POSITIVE | CLOSE_FP | 22 | 22 | 0 | 0 | 0 | 100% | 0.85 | - |
| F-FAT-1 | FALSE_POSITIVE | CLOSE_FP | 3 | 3 | 0 | 0 | 0 | 100% | 0.73 | - |
| F-ICE-1 | FALSE_POSITIVE | CLOSE_FP | 6 | 6 | 0 | 0 | 0 | 100% | 0.84 | - |
| F-MM-1 | FALSE_POSITIVE | CLOSE_FP | 17 | 17 | 0 | 0 | 0 | 100% | 0.88 | - |
| F-NEWS-1 | FALSE_POSITIVE | CLOSE_FP | 6 | 4 | 2 | 0 | 0 | 67% | 0.62 | - |
| F-PARTIAL-1 | FALSE_POSITIVE | CLOSE_FP | 5 | 5 | 0 | 0 | 0 | 100% | 0.79 | - |
| F-RISK-1 | FALSE_POSITIVE | CLOSE_FP | 4 | 3 | 1 | 0 | 0 | 75% | 0.63 | - |
| F-SPOOFLIKE-HARD-1 | FALSE_POSITIVE | CLOSE_FP | 7 | 7 | 0 | 0 | 0 | 100% | 0.79 | - |
| F-STOP-1 | FALSE_POSITIVE | CLOSE_FP | 5 | 1 | 4 | 0 | 0 | 20% | 0.6 | - |

## Regression against the previous run

Previous run: `20261116T2028-seed8-v17`. Verdict: **PASS (offline promotion rule)**.

- [x] gate holds
- [x] safe close rate not down by more than 2 points
- [x] no false-positive scenario regressed to 0% close (none)
- [x] evidence faithfulness at least 99% and not down by more than 0.5 points (99.71% of 2395 numbers, previous 99.84%; 100.00% of 372 categorical claims)

| delta | value |
|---|---|
| raw_safe_close_rate | +2.6 pts |
| agreement | +2.0 pts |
| escalation_precision | +4.7 pts |
| direction_agreement | +2.0 pts |
| true_abuse_recall | +0.0 pts |
| gate misses | +0 |

| scenario | agreement delta | close-rate delta |
|---|---|---|
| F-NEWS-1 | +17 pts | +17 pts |
| F-RISK-1 | +25 pts | +25 pts |

## Evidence faithfulness

100 reports checked against their sessions' tool results (`evals/faithfulness.py`): **94.0% of reports** have every number grounded; 2388 of 2395 numbers matched (99.7%). Categorical claims (roles, desks, order types, registration): 372 of 372 matched (100.0%).

| alert | scenario | proposed | source | unmatched | fact |
|---|---|---|---|---|---|
| A-261103-0003 | F-STOP-1 | ESCALATE | get_order_events | 1274 | Earlier BUY market order O-00029590 filled 1274 at 10007 to 10009 at 14:55:43. The later SELL of 863 filled at 10003/10002, a loss. |
| A-261104-0006 | F-ALGO-1 | CLOSE_FP | get_order_events | 0.1, 0.2 | Each SELL cancel/replace pairs with a BUY cancel/replace within about 0.1-0.2s, at the touch, same size 2298 (= typical_order_size 2298) |
| A-261113-0003 | F-ICE-1 | CLOSE_FP | get_order_events | 540,527,540,527,540,185 | O-00014991 BUY ICEBERG 14416 @9997 placed 12:04:05.382 under parent C-T-X1113-02-A; seven partial fills (540,527,540,527,540,185,72) between 12:04:09 and 12:04:28 before any SELL |
| A-261117-0001 | F-NEWS-1 | ESCALATE | compute_discriminators | 2.4 | cancel_symmetry 0.0, same_side_fill_qty 0, opposite_side_fill_qty 430, max_resting_size_vs_depth 4.81, distance_from_touch_ticks 1.5, price_move_ticks 0.5, post_cancel_move_ticks -6.5, reversion_ticks 6.5, otr 5.0, repet |
| A-261120-0004 | F-NEWS-1 | CLOSE_FP | get_order_events | 192 | Both BUY orders cancelled at 17:05:03.283, 192 ms after the news; the SELL 544 filled at 17:05:00.591, before the news |
| A-261126-0004 | F-NEWS-1 | ESCALATE | get_order_events | 2.6 | Both BUYs cancelled at 12:51:09.833, after the news and 2.6s after the SELL fill; the SELL was placed at 12:51:05.756, before the news |

## Disagreements with the label (10)

| alert | scenario | expected | proposed | conf | status | summary |
|---|---|---|---|---|---|---|
| A-261106-0006 | S-SPOOF-2 | DRAFT_STOR | ESCALATE | 0.7 | ok | Prop trader (no MM registration) placed one SELL LIMIT of 24907 (10.3x depth, 3 ticks from touch) at 13:45:54.608 and had no fills on it. It bought 696 by marke |
| A-261118-0001 | S-SPOOF-2 | DRAFT_STOR | ESCALATE | 0.7 | ok | Prop trader placed a one-sided SELL limit of 23295 (9.2x top-5 depth, 2 ticks from the touch). 1.4s later the trader sent a 1026 MARKET BUY. The SELL was cancel |
| A-261126-0007 | S-SPOOF-2 | DRAFT_STOR | ESCALATE | 0.6 | ok | Prop trader placed one SELL limit of 20229 (7.85x avg top-5 depth), 4 ticks above the touch, with nothing resting on the buy side. 1.7s later a BUY market order |
| A-261117-0001 | F-NEWS-1 | CLOSE_FP | ESCALATE | 0.6 | ok | PROP trader (no MM registration) rested two identical one-sided BUY limits of 6031 at 9996 (combined 4.8x depth, about 12x typical size 500). Both were 1.5 tick |
| A-261126-0004 | F-NEWS-1 | CLOSE_FP | ESCALATE | 0.6 | ok | PROP trader placed two one-sided BUY limits of 7806 each (3.03x depth) at 1 and 2 ticks from the touch, resting 27-30s with no fills. While they rested, a 557 S |
| A-261124-0004 | F-RISK-1 | CLOSE_FP | ESCALATE | 0.62 | ok | Three BUY limit orders of 3,966 each (11,898 total, about 5.2x top-5 depth) were stacked at 10000/10001/9999 over 10s. A SELL of 594 filled at 10005 at 15:42:20 |
| A-261103-0003 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.62 | ok | Prop trader bought 1354 at market (14:55:43), then layered three BUY limits of 4876 each at 10001/10000/9999 (gross 14628, about 6x avg top-5 depth) with no fil |
| A-261104-0009 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader (no MM registration) bought 979 by market order at 10006-10007, then placed three one-sided BUY limits of 3526 (10578 total, 4.5x depth) at 9997-999 |
| A-261109-0001 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader bought 1413 at market (09:23:05), then placed three one-sided BUY limits of 5086 each at 9995/9994/9993 (total 15258, 5.9x depth, 5-7 ticks from tou |
| A-261116-0004 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | PROP trader (no MM registration) placed three non-executing BUY limits of 4305 each (12915 total, ~4.95x depth, 5-6 ticks below touch) at 16:36:44-48, then sold |
