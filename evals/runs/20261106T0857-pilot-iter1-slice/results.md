# Dataset run `20261106T0857-pilot-iter1-slice`

- Dataset `seed7`, 24 alerts (7 TRUE_ABUSE, 17 FALSE_POSITIVE); backend `runtime`, model `eu.anthropic.claude-sonnet-5-5`, analyst `L1`, mode `investigate`, concurrency 2.
- Started 2026-11-06T08:57:26+00:00, finished 2026-11-06T09:05:02+00:00 (7.6 min).
- Notes: iteration 1 check: fill-sequencing discriminators + closure standard genuine-execution rule; Lambda and target redeployed, procedures re-ingested

## Headline

| metric | value |
|---|---|
| gate | **holds** (0 TRUE_ABUSE proposed CLOSE_FP) |
| safe close rate | 100.0% (17 of 17 false positives closed) |
| escalation precision | 100.0% (7 ESCALATE/DRAFT_STOR) |
| strong-call precision | n/a (0 DRAFT_STOR) |
| agreement with label (exact disposition) | 100.0% |
| **override rate** (1 - agreement) | **0.0%** |
| direction agreement (close vs not-close) | 100.0% |
| proposals | {'CLOSE_FP': 17, 'ESCALATE': 7} |
| run status | {'ok': 24} |
| latency, agent p50 / p95 | 30.9 s / 40.7 s (wall p50 36.9 s) |
| tokens per alert, in / out (mean) | 55702 / 3558 (max in 80451) |
| tool calls per alert (mean / median) | 10.3 / 10.0 |
| estimated model cost | $3.53 total, $0.147 per alert (assumed $2.0/$10.0 per M tokens in/out; not verified against the pricing page) |

## Against the baselines (same alerts)

| scorer | gate | safe close rate | raw safe close | escalation precision | agreement | override rate |
|---|---|---|---|---|---|---|
| agent (this run) | holds | 100.0% | 100.0% | 100.0% | 100.0% | 0.0% |
| threshold baseline (detector rules) | 6 missed | n/a | 100.0% | 100.0% | 75.0% | 25.0% |
| escalate everything | holds | 0.0% | 0.0% | 29.2% | 29.2% | 70.8% |
| close everything (the gate at work) | 7 missed | n/a | 100.0% | n/a | 70.8% | 29.2% |

## Confusion: expected (rows) x proposed (columns)

| expected \ proposed | CLOSE_FP | ESCALATE | DRAFT_STOR | none |
|---|---|---|---|---|
| CLOSE_FP | 17 | 0 | 0 | 0 |
| ESCALATE | 0 | 7 | 0 | 0 |
| DRAFT_STOR | 0 | 0 | 0 | 0 |

## Per scenario

| scenario | truth | expected | n | CLOSE_FP | ESCALATE | DRAFT_STOR | none | agreement | mean conf | gate misses |
|---|---|---|---|---|---|---|---|---|---|---|
| S-SPOOF-5 | TRUE_ABUSE | ESCALATE | 7 | 0 | 7 | 0 | 0 | 100% | 0.71 | - |
| F-ICE-1 | FALSE_POSITIVE | CLOSE_FP | 9 | 9 | 0 | 0 | 0 | 100% | 0.82 | - |
| F-PARTIAL-1 | FALSE_POSITIVE | CLOSE_FP | 8 | 8 | 0 | 0 | 0 | 100% | 0.76 | - |

## Regression against the previous run

Previous run: `20261105T1238-sonnet-v1`. Verdict: **PASS (offline promotion rule, faithfulness pending)**.

- [x] gate holds
- [x] safe close rate not down by more than 2 points
- [x] no false-positive scenario regressed to 0% close (none)

| delta | value |
|---|---|
| raw_safe_close_rate | +20.1 pts |
| agreement | +18.6 pts |
| escalation_precision | +50.0 pts |
| direction_agreement | +16.8 pts |
| true_abuse_recall | +0.0 pts |
| gate misses | +0 |

| scenario | agreement delta | close-rate delta |
|---|---|---|
| F-ICE-1 | +89 pts | +89 pts |
| F-PARTIAL-1 | +100 pts | +100 pts |

## Disagreements with the label (0)

| alert | scenario | expected | proposed | conf | status | summary |
|---|---|---|---|---|---|---|
