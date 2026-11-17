# Dataset run `20261117T2154-gap-slice`

- Dataset `seed7`, 29 alerts (7 TRUE_ABUSE, 22 FALSE_POSITIVE); backend `runtime`, model `eu.anthropic.claude-sonnet-5-5`, analyst `L1`, mode `investigate`, memory on, bundle none (code defaults), concurrency 2.
- Started 2026-11-17T21:54:29+00:00, finished 2026-11-17T22:02:15+00:00 (7.8 min).
- Notes: 30-alert slice after the 2026-11-17 control-gap deploy: policies 03a/03b/04 match output.alert_id, two Cognito clients, Runtime v18 on DEFAULT (v17 + boto3 1.44.5)

## Headline

| metric | value |
|---|---|
| gate | **holds** (0 TRUE_ABUSE proposed CLOSE_FP) |
| safe close rate | 90.9% (20 of 22 false positives closed) |
| escalation precision | 77.8% (9 ESCALATE/DRAFT_STOR) |
| strong-call precision | n/a (0 DRAFT_STOR) |
| agreement with label (exact disposition) | 89.7% |
| **override rate** (1 - agreement) | **10.3%** |
| direction agreement (close vs not-close) | 93.1% |
| proposals | {'CLOSE_FP': 20, 'ESCALATE': 9} |
| run status | {'ok': 29} |
| alerts an analyst had decided before this run: not investigated (a decided case takes no proposal), not scored, not in any number above or below | 1: A-261009-0003 |
| configuration bundle reported by the agent | none |
| latency, agent p50 / p95 | 24.1 s / 33.3 s (wall p50 30.8 s) |
| tokens per alert, in / out (mean) | 11 / 2966 (max in 12) |
| prompt cache, per alert | read 49166 / write 17973 / full price 11 tokens; hit rate 0.732 of 67149 prompt tokens |
| tool calls per alert (mean / median) | 10 / 10 |
| estimated model cost | $2.45 total, $0.084 per alert (assumed $2.0/$10.0 per M tokens in/out; cache read 0.1x, write 1.25x of input; not verified against the pricing page) |

## Against the baselines (same alerts)

| scorer | gate | safe close rate | raw safe close | escalation precision | agreement | override rate |
|---|---|---|---|---|---|---|
| agent (this run) | holds | 90.9% | 90.9% | 77.8% | 89.7% | 10.3% |
| threshold baseline (detector rules) | 1 missed | n/a | 95.5% | 85.7% | 93.1% | 6.9% |
| escalate everything | holds | 0.0% | 0.0% | 24.1% | 20.7% | 79.3% |
| close everything (the gate at work) | 7 missed | n/a | 100.0% | n/a | 75.9% | 24.1% |

## Confusion: expected (rows) x proposed (columns)

| expected \ proposed | CLOSE_FP | ESCALATE | DRAFT_STOR | none |
|---|---|---|---|---|
| CLOSE_FP | 20 | 2 | 0 | 0 |
| ESCALATE | 0 | 6 | 0 | 0 |
| DRAFT_STOR | 0 | 1 | 0 | 0 |

## Per scenario

| scenario | truth | expected | n | CLOSE_FP | ESCALATE | DRAFT_STOR | none | agreement | mean conf | gate misses |
|---|---|---|---|---|---|---|---|---|---|---|
| S-LAYER-1 | TRUE_ABUSE | ESCALATE | 2 | 0 | 2 | 0 | 0 | 100% | 0.71 | - |
| S-SPOOF-1 | TRUE_ABUSE | ESCALATE | 1 | 0 | 1 | 0 | 0 | 100% | 0.72 | - |
| S-SPOOF-2 | TRUE_ABUSE | DRAFT_STOR | 1 | 0 | 1 | 0 | 0 | 0% | 0.7 | - |
| S-SPOOF-3 | TRUE_ABUSE | ESCALATE | 1 | 0 | 1 | 0 | 0 | 100% | 0.75 | - |
| S-SPOOF-4 | TRUE_ABUSE | ESCALATE | 1 | 0 | 1 | 0 | 0 | 100% | 0.7 | - |
| S-SPOOF-5 | TRUE_ABUSE | ESCALATE | 1 | 0 | 1 | 0 | 0 | 100% | 0.72 | - |
| BACKGROUND | FALSE_POSITIVE | CLOSE_FP | 8 | 8 | 0 | 0 | 0 | 100% | 0.9 | - |
| F-ALGO-1 | FALSE_POSITIVE | CLOSE_FP | 3 | 3 | 0 | 0 | 0 | 100% | 0.83 | - |
| F-FAT-1 | FALSE_POSITIVE | CLOSE_FP | 2 | 2 | 0 | 0 | 0 | 100% | 0.7 | - |
| F-ICE-1 | FALSE_POSITIVE | CLOSE_FP | 2 | 2 | 0 | 0 | 0 | 100% | 0.82 | - |
| F-MM-1 | FALSE_POSITIVE | CLOSE_FP | 1 | 1 | 0 | 0 | 0 | 100% | 0.85 | - |
| F-NEWS-1 | FALSE_POSITIVE | CLOSE_FP | 1 | 0 | 1 | 0 | 0 | 0% | 0.6 | - |
| F-PARTIAL-1 | FALSE_POSITIVE | CLOSE_FP | 2 | 2 | 0 | 0 | 0 | 100% | 0.76 | - |
| F-RISK-1 | FALSE_POSITIVE | CLOSE_FP | 1 | 1 | 0 | 0 | 0 | 100% | 0.7 | - |
| F-SPOOFLIKE-HARD-1 | FALSE_POSITIVE | CLOSE_FP | 1 | 1 | 0 | 0 | 0 | 100% | 0.85 | - |
| F-STOP-1 | FALSE_POSITIVE | CLOSE_FP | 1 | 0 | 1 | 0 | 0 | 0% | 0.6 | - |

## Regression against the previous run

Previous run: `20261116T1828-sonnet-v5`. Verdict: **FAIL**.

- [x] gate holds
- [ ] safe close rate not down by more than 2 points
- [x] no false-positive scenario regressed to 0% close (none; within noise: F-NEWS-1 (1/4 -> 0/1, below the floor), F-STOP-1 (1/6 -> 0/1, below the floor))

| delta | value |
|---|---|
| raw_safe_close_rate | -3.3 pts |
| agreement | -4.4 pts |
| escalation_precision | +0.0 pts |
| direction_agreement | -2.1 pts |
| true_abuse_recall | +0.0 pts |
| gate misses | +0 |

| scenario | agreement delta | close-rate delta |
|---|---|---|
| S-SPOOF-2 | -33 pts | +0 pts |
| F-NEWS-1 | -25 pts | -25 pts |
| F-STOP-1 | -17 pts | -17 pts |

## Disagreements with the label (3)

| alert | scenario | expected | proposed | conf | status | summary |
|---|---|---|---|---|---|---|
| A-261015-0003 | S-SPOOF-2 | DRAFT_STOR | ESCALATE | 0.7 | ok | PROP-EQ trader (no MM registration) placed one SELL LIMIT of 21,443 (8.17x depth, 2 ticks from touch) at 11:04:43.303, bought 1,189 by market order 2.4s later,  |
| A-261015-0008 | F-NEWS-1 | CLOSE_FP | ESCALATE | 0.6 | ok | PROP trader placed two BUY LIMIT orders of 7,215 each (14,430 total, about 5.5x depth) at 9996, 1.5 ticks off the touch, about 27s before selling 515 at 10001.  |
| A-261027-0008 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader bought 1254 at market (10005), then layered three one-sided bids of 4514 each (13542 total, 5.4x depth) at 9997-9998, about 5-6 ticks below the touc |
