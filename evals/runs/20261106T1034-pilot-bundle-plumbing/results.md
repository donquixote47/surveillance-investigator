# Dataset run `20261106T1034-pilot-bundle-plumbing`

- Dataset `seed7`, 1 alerts (0 TRUE_ABUSE, 1 FALSE_POSITIVE); backend `runtime`, model `eu.anthropic.claude-sonnet-5-5`, analyst `L1`, mode `investigate`, memory on, bundle v1-current (surv_v1_current-HXLr7b3ctV:9ba88538-087f-4a74-b54f-ceb5cfc9fd16), concurrency 2.
- Started 2026-11-06T10:34:44+00:00, finished 2026-11-06T10:35:25+00:00 (0.7 min).
- Notes: does the baggage header reach the agent? (after the Gateway role grant)

## Headline

| metric | value |
|---|---|
| gate | **holds** (0 TRUE_ABUSE proposed CLOSE_FP) |
| safe close rate | 100.0% (1 of 1 false positives closed) |
| escalation precision | n/a (0 ESCALATE/DRAFT_STOR) |
| strong-call precision | n/a (0 DRAFT_STOR) |
| agreement with label (exact disposition) | 100.0% |
| **override rate** (1 - agreement) | **0.0%** |
| direction agreement (close vs not-close) | 100.0% |
| proposals | {'CLOSE_FP': 1} |
| run status | {'ok': 1} |
| configuration bundle reported by the agent | surv_v1_current-HXLr7b3ctV:9ba88538-087f-4a74-b54f-ceb5cfc9fd16 |
| latency, agent p50 / p95 | 33.0 s / 33.0 s (wall p50 39.7 s) |
| tokens per alert, in / out (mean) | 91665 / 3110 (max in 91665) |
| tool calls per alert (mean / median) | 10 / 10 |
| estimated model cost | $0.21 total, $0.214 per alert (assumed $2.0/$10.0 per M tokens in/out; not verified against the pricing page) |

## Against the baselines (same alerts)

| scorer | gate | safe close rate | raw safe close | escalation precision | agreement | override rate |
|---|---|---|---|---|---|---|
| agent (this run) | holds | 100.0% | 100.0% | n/a | 100.0% | 0.0% |
| threshold baseline (detector rules) | holds | 100.0% | 100.0% | n/a | 100.0% | 0.0% |
| escalate everything | holds | 0.0% | 0.0% | 0.0% | 0.0% | 100.0% |
| close everything (the gate at work) | holds | 100.0% | 100.0% | n/a | 100.0% | 0.0% |

## Confusion: expected (rows) x proposed (columns)

| expected \ proposed | CLOSE_FP | ESCALATE | DRAFT_STOR | none |
|---|---|---|---|---|
| CLOSE_FP | 1 | 0 | 0 | 0 |
| ESCALATE | 0 | 0 | 0 | 0 |
| DRAFT_STOR | 0 | 0 | 0 | 0 |

## Per scenario

| scenario | truth | expected | n | CLOSE_FP | ESCALATE | DRAFT_STOR | none | agreement | mean conf | gate misses |
|---|---|---|---|---|---|---|---|---|---|---|
| F-MM-1 | FALSE_POSITIVE | CLOSE_FP | 1 | 1 | 0 | 0 | 0 | 100% | 0.9 | - |

## Regression against the previous run

Previous run: `20261106T0906-sonnet-v2`. Verdict: **PASS (offline promotion rule, faithfulness pending)**.

- [x] gate holds
- [x] safe close rate not down by more than 2 points
- [x] no false-positive scenario regressed to 0% close (none)

| delta | value |
|---|---|
| raw_safe_close_rate | +11.5 pts |
| agreement | +11.4 pts |
| direction_agreement | +9.6 pts |
| gate misses | +0 |

## Disagreements with the label (0)

| alert | scenario | expected | proposed | conf | status | summary |
|---|---|---|---|---|---|---|
