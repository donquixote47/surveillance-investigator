# Dataset run `20261117T1255-seed9-mm`

- Dataset `seed9`, 48 alerts (12 TRUE_ABUSE, 36 FALSE_POSITIVE); backend `runtime`, model `eu.anthropic.claude-sonnet-5-5`, analyst `L1`, mode `investigate`, memory on, bundle none (code defaults), concurrency 2.
- Started 2026-11-17T12:55:29+00:00, finished 2026-11-17T13:11:18+00:00 (15.8 min).
- Notes: the registered-market-maker question on the release (Runtime v17, v0.3.0-alpha): seed9, a focused set of 48 alerts, twelve each of S-SPOOF-6 (a registered market maker who spoofs), its innocent twin F-MM-LARGE-1, F-MM-1 and F-SPOOFLIKE-HARD-1; headline numbers are not comparable with seed7 or seed8; the reading is per scenario

## Headline

| metric | value |
|---|---|
| gate | **holds** (0 TRUE_ABUSE proposed CLOSE_FP) |
| safe close rate | 100.0% (36 of 36 false positives closed) |
| escalation precision | 100.0% (12 ESCALATE/DRAFT_STOR) |
| strong-call precision | n/a (0 DRAFT_STOR) |
| agreement with label (exact disposition) | 100.0% |
| **override rate** (1 - agreement) | **0.0%** |
| direction agreement (close vs not-close) | 100.0% |
| proposals | {'CLOSE_FP': 36, 'ESCALATE': 12} |
| run status | {'ok': 48} |
| configuration bundle reported by the agent | none |
| latency, agent p50 / p95 | 25.3 s / 29.7 s (wall p50 31.1 s) |
| tokens per alert, in / out (mean) | 11 / 3152 (max in 12) |
| prompt cache, per alert | read 58463 / write 25401 / full price 11 tokens; hit rate 0.697 of 83875 prompt tokens |
| tool calls per alert (mean / median) | 10 / 10.0 |
| estimated model cost | $5.12 total, $0.107 per alert (assumed $2.0/$10.0 per M tokens in/out; cache read 0.1x, write 1.25x of input; not verified against the pricing page) |

## Against the baselines (same alerts)

| scorer | gate | safe close rate | raw safe close | escalation precision | agreement | override rate |
|---|---|---|---|---|---|---|
| agent (this run) | holds | 100.0% | 100.0% | 100.0% | 100.0% | 0.0% |
| threshold baseline (detector rules) | 12 missed | n/a | 69.4% | 0.0% | 52.1% | 47.9% |
| escalate everything | holds | 0.0% | 0.0% | 25.0% | 25.0% | 75.0% |
| close everything (the gate at work) | 12 missed | n/a | 100.0% | n/a | 75.0% | 25.0% |

## Confusion: expected (rows) x proposed (columns)

| expected \ proposed | CLOSE_FP | ESCALATE | DRAFT_STOR | none |
|---|---|---|---|---|
| CLOSE_FP | 36 | 0 | 0 | 0 |
| ESCALATE | 0 | 12 | 0 | 0 |
| DRAFT_STOR | 0 | 0 | 0 | 0 |

## Per scenario

| scenario | truth | expected | n | CLOSE_FP | ESCALATE | DRAFT_STOR | none | agreement | mean conf | gate misses |
|---|---|---|---|---|---|---|---|---|---|---|
| S-SPOOF-6 | TRUE_ABUSE | ESCALATE | 12 | 0 | 12 | 0 | 0 | 100% | 0.72 | - |
| F-MM-1 | FALSE_POSITIVE | CLOSE_FP | 12 | 12 | 0 | 0 | 0 | 100% | 0.88 | - |
| F-MM-LARGE-1 | FALSE_POSITIVE | CLOSE_FP | 12 | 12 | 0 | 0 | 0 | 100% | 0.74 | - |
| F-SPOOFLIKE-HARD-1 | FALSE_POSITIVE | CLOSE_FP | 12 | 12 | 0 | 0 | 0 | 100% | 0.8 | - |

## Regression against the previous run

Previous run: `20261116T1828-sonnet-v5`. Verdict: **n/a: different datasets (seed7 -> seed9); the promotion rule applies on one fixed dataset, the deltas below are mix-dependent (gate check still meaningful: holds)**.

- [x] gate holds
- [x] safe close rate not down by more than 2 points
- [x] no false-positive scenario regressed to 0% close (none)
- [x] evidence faithfulness at least 99% and not down by more than 0.5 points (99.84% of 1286 numbers, previous 99.72%; 100.00% of 158 categorical claims)

| delta | value |
|---|---|
| raw_safe_close_rate | +5.8 pts |
| agreement | +6.0 pts |
| escalation_precision | +22.2 pts |
| direction_agreement | +4.8 pts |
| true_abuse_recall | +0.0 pts |
| gate misses | +0 |

## Evidence faithfulness

48 reports checked against their sessions' tool results (`evals/faithfulness.py`): **95.8% of reports** have every number grounded; 1284 of 1286 numbers matched (99.8%). Categorical claims (roles, desks, order types, registration): 158 of 158 matched (100.0%).

| alert | scenario | proposed | source | unmatched | fact |
|---|---|---|---|---|---|
| A-260917-0004 | F-SPOOFLIKE-HARD-1 | CLOSE_FP | get_instrument_stats | 0.26 | avg_depth_top5 2894.7, so the 756 bid is about 0.26x depth and the 3784 offer about 1.3x depth |
| A-260918-0004 | F-SPOOFLIKE-HARD-1 | CLOSE_FP | get_order_events | 2445 | SELL 4311 and BUY 862 LIMIT quotes were placed within ms of each other and cancelled together at the same timestamp, then re-placed one tick lower as the touch fell from 10001 to 9994. The SELL orders had many partial fi |

## Disagreements with the label (0)

| alert | scenario | expected | proposed | conf | status | summary |
|---|---|---|---|---|---|---|
