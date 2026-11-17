# Dataset run `20261117T1454-seed9-variance`

- Dataset `seed9`, 72 alerts (36 TRUE_ABUSE, 36 FALSE_POSITIVE); backend `runtime`, model `eu.anthropic.claude-sonnet-5-5`, analyst `L1`, mode `investigate`, memory on, bundle none (code defaults), concurrency 1.
- Started 2026-11-17T14:54:33+00:00, finished 2026-11-17T15:32:42+00:00 (38.1 min).
- Notes: run-to-run stability of the registered-market-maker result on the release (Runtime v17): the 12 S-SPOOF-6 and the 12 F-MM-LARGE-1 alerts of seed9, three times each (72 investigations), one at a time because two short investigations in parallel sit at the Gateway request limit

## Headline

| metric | value |
|---|---|
| gate | **holds** (0 TRUE_ABUSE proposed CLOSE_FP) |
| safe close rate | 100.0% (36 of 36 false positives closed) |
| escalation precision | 100.0% (36 ESCALATE/DRAFT_STOR) |
| strong-call precision | n/a (0 DRAFT_STOR) |
| agreement with label (exact disposition) | 100.0% |
| **override rate** (1 - agreement) | **0.0%** |
| direction agreement (close vs not-close) | 100.0% |
| proposals | {'CLOSE_FP': 36, 'ESCALATE': 36} |
| run status | {'ok': 72} |
| configuration bundle reported by the agent | none |
| latency, agent p50 / p95 | 25.6 s / 28.5 s (wall p50 31.6 s) |
| tokens per alert, in / out (mean) | 11 / 3289 (max in 12) |
| prompt cache, per alert | read 56296 / write 22591 / full price 11 tokens; hit rate 0.714 of 78898 prompt tokens |
| tool calls per alert (mean / median) | 10 / 10.0 |
| estimated model cost | $7.25 total, $0.101 per alert (assumed $2.0/$10.0 per M tokens in/out; cache read 0.1x, write 1.25x of input; not verified against the pricing page) |

## Against the baselines (same alerts)

| scorer | gate | safe close rate | raw safe close | escalation precision | agreement | override rate |
|---|---|---|---|---|---|---|
| agent (this run) | holds | 100.0% | 100.0% | 100.0% | 100.0% | 0.0% |
| threshold baseline (detector rules) | 12 missed | n/a | 100.0% | n/a | 50.0% | 50.0% |
| escalate everything | holds | 0.0% | 0.0% | 50.0% | 50.0% | 50.0% |
| close everything (the gate at work) | 12 missed | n/a | 100.0% | n/a | 50.0% | 50.0% |

## Confusion: expected (rows) x proposed (columns)

| expected \ proposed | CLOSE_FP | ESCALATE | DRAFT_STOR | none |
|---|---|---|---|---|
| CLOSE_FP | 36 | 0 | 0 | 0 |
| ESCALATE | 0 | 36 | 0 | 0 |
| DRAFT_STOR | 0 | 0 | 0 | 0 |

## Per scenario

| scenario | truth | expected | n | CLOSE_FP | ESCALATE | DRAFT_STOR | none | agreement | mean conf | gate misses |
|---|---|---|---|---|---|---|---|---|---|---|
| S-SPOOF-6 | TRUE_ABUSE | ESCALATE | 36 | 0 | 36 | 0 | 0 | 100% | 0.73 | - |
| F-MM-LARGE-1 | FALSE_POSITIVE | CLOSE_FP | 36 | 36 | 0 | 0 | 0 | 100% | 0.75 | - |

## Disagreements with the label (0)

| alert | scenario | expected | proposed | conf | status | summary |
|---|---|---|---|---|---|---|

## Run-to-run variance

24 alerts, each investigated 3 times with nothing changed (72 investigations). An alert is *stable* when every repetition proposed the same disposition.

| measure | value |
|---|---|
| stable alerts | 24 of 24 (100.0%) |
| true-abuse alerts proposed CLOSE_FP in any repetition | **none** |
| safe close rate across the 3 pseudo-runs | 100.0% to 100.0% (mean 100.0%, sd 0.0 pts) |
| agreement with the label across pseudo-runs | 100.0% to 100.0% |

| pseudo-run | gate | safe close | agreement | escalation precision |
|---|---|---|---|---|
| repeat 0 | holds | 100.0% | 100.0% | 100.0% |
| repeat 1 | holds | 100.0% | 100.0% | 100.0% |
| repeat 2 | holds | 100.0% | 100.0% | 100.0% |

| scenario | alerts | unstable | flips / repetitions | flip rate |
|---|---|---|---|---|
| F-MM-LARGE-1 | 12 | 0 | 0 / 36 | 0.0% |
| S-SPOOF-6 | 12 | 0 | 0 / 36 | 0.0% |
