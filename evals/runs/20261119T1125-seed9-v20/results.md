# Dataset run `20261119T1125-seed9-v20`

- Dataset `seed9`, 48 alerts (12 TRUE_ABUSE, 36 FALSE_POSITIVE); backend `runtime`, model `eu.anthropic.claude-sonnet-5-5`, analyst `L1`, mode `investigate`, memory on, bundle none (code defaults), concurrency 2.
- Started 2026-11-19T11:25:42+00:00, finished 2026-11-19T11:37:40+00:00 (12.0 min).
- Notes: the registered-market-maker question on the release: Runtime v20 (v0.4.0-alpha) with one analyst per worker on seed9, the focused set of 48 alerts (twelve each of S-SPOOF-6, its innocent twin F-MM-LARGE-1, F-MM-1 and F-SPOOFLIKE-HARD-1); compared with the v17 run 20261117T1255-seed9-mm

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
| latency, agent p50 / p95 | 23.6 s / 26.0 s (wall p50 29.6 s) |
| tokens per alert, in / out (mean) | 11 / 3149 (max in 12) |
| prompt cache, per alert | read 57995 / write 25469 / full price 11 tokens; hit rate 0.695 of 83474 prompt tokens |
| tool calls per alert (mean / median) | 10 / 10.0 |
| estimated model cost | $5.13 total, $0.107 per alert (assumed $2.0/$10.0 per M tokens in/out; cache read 0.1x, write 1.25x of input; not verified against the pricing page) |

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
| F-MM-LARGE-1 | FALSE_POSITIVE | CLOSE_FP | 12 | 12 | 0 | 0 | 0 | 100% | 0.75 | - |
| F-SPOOFLIKE-HARD-1 | FALSE_POSITIVE | CLOSE_FP | 12 | 12 | 0 | 0 | 0 | 100% | 0.8 | - |

## Regression against the previous run

Previous run: `20261117T1255-seed9-mm`. Verdict: **PASS (offline promotion rule)**.

- [x] gate holds
- [x] safe close rate not down by more than 2 points
- [x] no false-positive scenario regressed to 0% close (none)
- [x] evidence faithfulness at least 99% and not down by more than 0.5 points (100.00% of 1290 numbers, previous 99.84%; 100.00% of 163 categorical claims)

| delta | value |
|---|---|
| raw_safe_close_rate | +0.0 pts |
| agreement | +0.0 pts |
| escalation_precision | +0.0 pts |
| direction_agreement | +0.0 pts |
| true_abuse_recall | +0.0 pts |
| gate misses | +0 |

## Evidence faithfulness

48 reports checked against their sessions' tool results (`evals/faithfulness.py`): **100.0% of reports** have every number grounded; 1290 of 1290 numbers matched (100.0%). Categorical claims (roles, desks, order types, registration): 163 of 163 matched (100.0%).

## Disagreements with the label (0)

| alert | scenario | expected | proposed | conf | status | summary |
|---|---|---|---|---|---|---|
