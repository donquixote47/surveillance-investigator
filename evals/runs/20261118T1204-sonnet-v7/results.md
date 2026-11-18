# Dataset run `20261118T1204-sonnet-v7`

- Dataset `seed7`, 167 alerts (28 TRUE_ABUSE, 139 FALSE_POSITIVE); backend `runtime`, model `eu.anthropic.claude-sonnet-5-5`, analyst `L1`, mode `investigate`, memory on, bundle none (code defaults), concurrency 2.
- Started 2026-11-18T12:04:30+00:00, finished 2026-11-18T12:58:22+00:00 (53.9 min).
- Notes: full seed7 run on Runtime v20 (DEFAULT): v19 with a Gateway retry that outlasts the per-minute limits (2, 4, 8, 16, 32 s with jitter); limits as released: 60 requests a minute, 3 proposals a minute per analyst

## Headline

| metric | value |
|---|---|
| gate | **holds** (0 TRUE_ABUSE proposed CLOSE_FP) |
| safe close rate | 95.7% (133 of 139 false positives closed) |
| escalation precision | 82.4% (34 ESCALATE/DRAFT_STOR) |
| strong-call precision | 100.0% (1 DRAFT_STOR) |
| agreement with label (exact disposition) | 95.2% |
| **override rate** (1 - agreement) | **4.8%** |
| direction agreement (close vs not-close) | 96.4% |
| proposals | {'CLOSE_FP': 133, 'ESCALATE': 33, 'DRAFT_STOR': 1} |
| run status | {'ok': 167} |
| configuration bundle reported by the agent | none |
| latency, agent p50 / p95 | 24.9 s / 53.0 s (wall p50 31.4 s) |
| tokens per alert, in / out (mean) | 11 / 2974 (max in 12) |
| prompt cache, per alert | read 54142 / write 21270 / full price 11 tokens; hit rate 0.718 of 75423 prompt tokens |
| tool calls per alert (mean / median) | 10.0 / 10 |
| estimated model cost | $15.66 total, $0.094 per alert (assumed $2.0/$10.0 per M tokens in/out; cache read 0.1x, write 1.25x of input; not verified against the pricing page) |

## Against the baselines (same alerts)

| scorer | gate | safe close rate | raw safe close | escalation precision | agreement | override rate |
|---|---|---|---|---|---|---|
| agent (this run) | holds | 95.7% | 95.7% | 82.4% | 95.2% | 4.8% |
| threshold baseline (detector rules) | 6 missed | n/a | 95.7% | 78.6% | 92.8% | 7.2% |
| escalate everything | holds | 0.0% | 0.0% | 16.8% | 15.0% | 85.0% |
| close everything (the gate at work) | 28 missed | n/a | 100.0% | n/a | 83.2% | 16.8% |

## Confusion: expected (rows) x proposed (columns)

| expected \ proposed | CLOSE_FP | ESCALATE | DRAFT_STOR | none |
|---|---|---|---|---|
| CLOSE_FP | 133 | 6 | 0 | 0 |
| ESCALATE | 0 | 25 | 0 | 0 |
| DRAFT_STOR | 0 | 2 | 1 | 0 |

## Per scenario

| scenario | truth | expected | n | CLOSE_FP | ESCALATE | DRAFT_STOR | none | agreement | mean conf | gate misses |
|---|---|---|---|---|---|---|---|---|---|---|
| S-LAYER-1 | TRUE_ABUSE | ESCALATE | 5 | 0 | 5 | 0 | 0 | 100% | 0.68 | - |
| S-SPOOF-1 | TRUE_ABUSE | ESCALATE | 7 | 0 | 7 | 0 | 0 | 100% | 0.71 | - |
| S-SPOOF-2 | TRUE_ABUSE | DRAFT_STOR | 3 | 0 | 2 | 1 | 0 | 33% | 0.73 | - |
| S-SPOOF-3 | TRUE_ABUSE | ESCALATE | 4 | 0 | 4 | 0 | 0 | 100% | 0.72 | - |
| S-SPOOF-4 | TRUE_ABUSE | ESCALATE | 2 | 0 | 2 | 0 | 0 | 100% | 0.7 | - |
| S-SPOOF-5 | TRUE_ABUSE | ESCALATE | 7 | 0 | 7 | 0 | 0 | 100% | 0.75 | - |
| BACKGROUND | FALSE_POSITIVE | CLOSE_FP | 52 | 52 | 0 | 0 | 0 | 100% | 0.89 | - |
| F-ALGO-1 | FALSE_POSITIVE | CLOSE_FP | 24 | 24 | 0 | 0 | 0 | 100% | 0.85 | - |
| F-FAT-1 | FALSE_POSITIVE | CLOSE_FP | 3 | 3 | 0 | 0 | 0 | 100% | 0.73 | - |
| F-ICE-1 | FALSE_POSITIVE | CLOSE_FP | 9 | 9 | 0 | 0 | 0 | 100% | 0.81 | - |
| F-MM-1 | FALSE_POSITIVE | CLOSE_FP | 24 | 24 | 0 | 0 | 0 | 100% | 0.89 | - |
| F-NEWS-1 | FALSE_POSITIVE | CLOSE_FP | 4 | 2 | 2 | 0 | 0 | 50% | 0.63 | - |
| F-PARTIAL-1 | FALSE_POSITIVE | CLOSE_FP | 8 | 8 | 0 | 0 | 0 | 100% | 0.78 | - |
| F-RISK-1 | FALSE_POSITIVE | CLOSE_FP | 3 | 3 | 0 | 0 | 0 | 100% | 0.65 | - |
| F-SPOOFLIKE-HARD-1 | FALSE_POSITIVE | CLOSE_FP | 6 | 6 | 0 | 0 | 0 | 100% | 0.78 | - |
| F-STOP-1 | FALSE_POSITIVE | CLOSE_FP | 6 | 2 | 4 | 0 | 0 | 33% | 0.65 | - |

## Regression against the previous run

Previous run: `20261117T2346-sonnet-v6`. Verdict: **PASS (offline promotion rule)**.

- [x] gate holds
- [x] safe close rate not down by more than 2 points
- [x] no false-positive scenario regressed to 0% close (none)
- [x] evidence faithfulness at least 99% and not down by more than 0.5 points (99.90% of 3940 numbers, previous 99.83%; 100.00% of 601 categorical claims)

| delta | value |
|---|---|
| raw_safe_close_rate | +0.7 pts |
| agreement | +0.6 pts |
| escalation_precision | +2.4 pts |
| direction_agreement | +0.6 pts |
| true_abuse_recall | +0.0 pts |
| gate misses | +0 |

| scenario | agreement delta | close-rate delta |
|---|---|---|
| F-STOP-1 | +17 pts | +17 pts |

## Evidence faithfulness

167 reports checked against their sessions' tool results (`evals/faithfulness.py`): **97.6% of reports** have every number grounded; 3936 of 3940 numbers matched (99.9%). Categorical claims (roles, desks, order types, registration): 601 of 601 matched (100.0%).

| alert | scenario | proposed | source | unmatched | fact |
|---|---|---|---|---|---|
| A-261005-0007 | F-STOP-1 | ESCALATE | compute_discriminators | 1.7 | gross_submitted_dominant BUY 12231, other side 0; max_resting_size_vs_depth 5.04; distance_from_touch_ticks 6.0; distinct_price_levels 2; cancel_ratio 1.0; cancel_symmetry 0.0; large_orders empty (each order is 4077, abo |
| A-261012-0001 | F-RISK-1 | CLOSE_FP | get_instrument_stats | 2.1 | SYN.A average top-5 depth is 2338, so each 4932 order is about 2.1x depth. |
| A-261015-0008 | F-NEWS-1 | ESCALATE | get_market_events | 142 | NEWS 'issuer announces unscheduled trading update' at 15:13:22.998, which is 142 ms before the cancels and 2.5 s after the sale fill. |
| A-261023-0001 | F-NEWS-1 | CLOSE_FP | get_market_events | 148 | NEWS: issuer announces unscheduled trading update at 09:38:30.051, 148ms before the cancels |

## Disagreements with the label (8)

| alert | scenario | expected | proposed | conf | status | summary |
|---|---|---|---|---|---|---|
| A-261015-0003 | S-SPOOF-2 | DRAFT_STOR | ESCALATE | 0.7 | ok | PROP trader placed a single one-sided SELL limit of 21,443 (8.17x avg top-5 depth, 2 ticks from touch) at 11:04:43.303. 2.4s later a BUY market order of 1,189 e |
| A-261016-0006 | S-SPOOF-2 | DRAFT_STOR | ESCALATE | 0.7 | ok | PROP trader (no registered MM) placed a one-sided BUY LIMIT of 21860 (8.79x depth, 3 ticks below touch) at 16:38:01.976. 2.1s later a SELL MARKET of 1329 execut |
| A-261015-0008 | F-NEWS-1 | CLOSE_FP | ESCALATE | 0.62 | ok | Prop trader rested two BUY LIMIT orders of 7,215 each (14,430 total, 5.5x depth) at 9996, 1.5 ticks off the touch. Neither order executed. The trader sold 515 a |
| A-261016-0003 | F-NEWS-1 | CLOSE_FP | ESCALATE | 0.7 | ok | Prop trader (no MM registration) rested two one-sided BUY orders of 6680 each at 9997 (combined 5.37x depth, 1.5 ticks from the touch). He then SOLD 477 at 1000 |
| A-261005-0007 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.65 | ok | PROP trader with no registered MM, no parent orders and no risk event bought 1132 at market, then rested three BUY limits of 4077 each (12231 total, about 5x de |
| A-261006-0005 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.7 | ok | Prop trader bought 1058 by market order at 11:36:02, then placed three BUY limits of 3810 each (9994/9993/9992, 6 ticks from touch, 4.66x depth in total) with n |
| A-261027-0008 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.65 | ok | Prop trader (no MM registration) bought 1254 at market at 10005, then stacked three one-sided BUY limits of 4514 each (13542 total, 5.4x depth) 6 ticks from the |
| A-261028-0011 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.7 | ok | Prop trader bought 1476 by market order at 10005-10006, then placed three one-sided BUY limits of 5313 each (15939 total, 6.5x depth) at 9997-9998, 6 ticks off  |
