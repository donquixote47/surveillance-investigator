# Dataset run `20261112T1409-v16-slice`

- Dataset `seed7`, 30 alerts (7 TRUE_ABUSE, 23 FALSE_POSITIVE); backend `runtime`, model `eu.anthropic.claude-sonnet-5-5`, analyst `L1`, mode `investigate`, memory on, bundle none (code defaults), concurrency 2.
- Started 2026-11-12T14:09:09+00:00, finished 2026-11-12T14:18:01+00:00 (8.9 min).
- Notes: Runtime v16 (v14 code + draft_stor mode) regression slice on the investigate path: same 30 alerts as the iteration-3 and effort slices (seed 7); expected no change against v4

## Headline

| metric | value |
|---|---|
| gate | **holds** (0 TRUE_ABUSE proposed CLOSE_FP) |
| safe close rate | 91.3% (21 of 23 false positives closed) |
| escalation precision | 77.8% (9 ESCALATE/DRAFT_STOR) |
| strong-call precision | n/a (0 DRAFT_STOR) |
| agreement with label (exact disposition) | 90.0% |
| **override rate** (1 - agreement) | **10.0%** |
| direction agreement (close vs not-close) | 93.3% |
| proposals | {'CLOSE_FP': 21, 'ESCALATE': 9} |
| run status | {'ok': 30} |
| alerts with a disposition recorded before this run (visible to the agent through history and Memory) | 1: A-261009-0003 |
| configuration bundle reported by the agent | none |
| latency, agent p50 / p95 | 27.9 s / 34.4 s (wall p50 34.2 s) |
| tokens per alert, in / out (mean) | 11 / 3114 (max in 12) |
| prompt cache, per alert | read 48494 / write 17816 / full price 11 tokens; hit rate 0.731 of 66322 prompt tokens |
| tool calls per alert (mean / median) | 10 / 10.0 |
| estimated model cost | $2.56 total, $0.085 per alert (assumed $2.0/$10.0 per M tokens in/out; cache read 0.1x, write 1.25x of input; not verified against the pricing page) |

## Against the baselines (same alerts)

| scorer | gate | safe close rate | raw safe close | escalation precision | agreement | override rate |
|---|---|---|---|---|---|---|
| agent (this run) | holds | 91.3% | 91.3% | 77.8% | 90.0% | 10.0% |
| threshold baseline (detector rules) | 1 missed | n/a | 95.7% | 85.7% | 93.3% | 6.7% |
| escalate everything | holds | 0.0% | 0.0% | 23.3% | 20.0% | 80.0% |
| close everything (the gate at work) | 7 missed | n/a | 100.0% | n/a | 76.7% | 23.3% |

## Confusion: expected (rows) x proposed (columns)

| expected \ proposed | CLOSE_FP | ESCALATE | DRAFT_STOR | none |
|---|---|---|---|---|
| CLOSE_FP | 21 | 2 | 0 | 0 |
| ESCALATE | 0 | 6 | 0 | 0 |
| DRAFT_STOR | 0 | 1 | 0 | 0 |

## Per scenario

| scenario | truth | expected | n | CLOSE_FP | ESCALATE | DRAFT_STOR | none | agreement | mean conf | gate misses |
|---|---|---|---|---|---|---|---|---|---|---|
| S-LAYER-1 | TRUE_ABUSE | ESCALATE | 2 | 0 | 2 | 0 | 0 | 100% | 0.7 | - |
| S-SPOOF-1 | TRUE_ABUSE | ESCALATE | 1 | 0 | 1 | 0 | 0 | 100% | 0.7 | - |
| S-SPOOF-2 | TRUE_ABUSE | DRAFT_STOR | 1 | 0 | 1 | 0 | 0 | 0% | 0.65 | - |
| S-SPOOF-3 | TRUE_ABUSE | ESCALATE | 1 | 0 | 1 | 0 | 0 | 100% | 0.7 | - |
| S-SPOOF-4 | TRUE_ABUSE | ESCALATE | 1 | 0 | 1 | 0 | 0 | 100% | 0.7 | - |
| S-SPOOF-5 | TRUE_ABUSE | ESCALATE | 1 | 0 | 1 | 0 | 0 | 100% | 0.75 | - |
| BACKGROUND | FALSE_POSITIVE | CLOSE_FP | 8 | 8 | 0 | 0 | 0 | 100% | 0.89 | - |
| F-ALGO-1 | FALSE_POSITIVE | CLOSE_FP | 3 | 3 | 0 | 0 | 0 | 100% | 0.86 | - |
| F-FAT-1 | FALSE_POSITIVE | CLOSE_FP | 2 | 2 | 0 | 0 | 0 | 100% | 0.72 | - |
| F-ICE-1 | FALSE_POSITIVE | CLOSE_FP | 2 | 2 | 0 | 0 | 0 | 100% | 0.8 | - |
| F-MM-1 | FALSE_POSITIVE | CLOSE_FP | 2 | 2 | 0 | 0 | 0 | 100% | 0.89 | - |
| F-NEWS-1 | FALSE_POSITIVE | CLOSE_FP | 1 | 0 | 1 | 0 | 0 | 0% | 0.6 | - |
| F-PARTIAL-1 | FALSE_POSITIVE | CLOSE_FP | 2 | 2 | 0 | 0 | 0 | 100% | 0.75 | - |
| F-RISK-1 | FALSE_POSITIVE | CLOSE_FP | 1 | 1 | 0 | 0 | 0 | 100% | 0.6 | - |
| F-SPOOFLIKE-HARD-1 | FALSE_POSITIVE | CLOSE_FP | 1 | 1 | 0 | 0 | 0 | 100% | 0.85 | - |
| F-STOP-1 | FALSE_POSITIVE | CLOSE_FP | 1 | 0 | 1 | 0 | 0 | 0% | 0.6 | - |

## Regression against the previous run

Previous run: `20261110T1833-sonnet-v4`. Verdict: **FAIL**.

- [x] gate holds
- [ ] safe close rate not down by more than 2 points
- [ ] no false-positive scenario regressed to 0% close (F-STOP-1; within noise: F-NEWS-1 (1/4 -> 0/1, below the floor))

| delta | value |
|---|---|
| raw_safe_close_rate | -3.7 pts |
| agreement | -4.6 pts |
| escalation_precision | -2.2 pts |
| direction_agreement | -2.5 pts |
| true_abuse_recall | +0.0 pts |
| gate misses | +0 |

| scenario | agreement delta | close-rate delta |
|---|---|---|
| S-SPOOF-2 | -33 pts | +0 pts |
| F-STOP-1 | -33 pts | -33 pts |
| F-NEWS-1 | -25 pts | -25 pts |

## Disagreements with the label (3)

| alert | scenario | expected | proposed | conf | status | summary |
|---|---|---|---|---|---|---|
| A-261015-0003 | S-SPOOF-2 | DRAFT_STOR | ESCALATE | 0.65 | ok | PROP trader (no MM registration) placed a one-sided SELL of 21443 (8.2x avg top-5 depth) 2 ticks from the touch, bought 1189 by market order 2.4s later, and can |
| A-261015-0008 | F-NEWS-1 | CLOSE_FP | ESCALATE | 0.6 | ok | PROP-EQ trader (no MM registration) rested two BUY limits of 7,215 each (14,430 total, 5.5x avg top-5 depth) at 9996, 1.5 ticks off the touch. The trader sold 5 |
| A-261027-0008 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader bought 1,254 at market (10005) at 13:50:44, then layered three one-sided BUY limits of 4,514 each (13,542 total, 5.4x top-5 depth, 6 ticks below tou |
