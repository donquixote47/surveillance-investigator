# Dataset run `20261118T1343-two-analysts-slice`

- Dataset `seed7`, 29 alerts (7 TRUE_ABUSE, 22 FALSE_POSITIVE); backend `runtime`, model `eu.anthropic.claude-sonnet-5-5`, analyst `L1`, mode `investigate`, memory on, bundle none (code defaults), concurrency 2.
- Started 2026-11-18T13:43:35+00:00, finished 2026-11-18T13:51:18+00:00 (7.7 min).
- Notes: 30-alert slice on Runtime v20 with one analyst per worker (l1.analyst, l1.analyst2), limits rested for 25 minutes: does a run still meet the write limit?

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
| latency, agent p50 / p95 | 23.9 s / 30.5 s (wall p50 30.4 s) |
| tokens per alert, in / out (mean) | 11 / 3006 (max in 12) |
| prompt cache, per alert | read 50057 / write 18244 / full price 11 tokens; hit rate 0.733 of 68312 prompt tokens |
| tool calls per alert (mean / median) | 10 / 10 |
| estimated model cost | $2.49 total, $0.086 per alert (assumed $2.0/$10.0 per M tokens in/out; cache read 0.1x, write 1.25x of input; not verified against the pricing page) |

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
| S-LAYER-1 | TRUE_ABUSE | ESCALATE | 2 | 0 | 2 | 0 | 0 | 100% | 0.65 | - |
| S-SPOOF-1 | TRUE_ABUSE | ESCALATE | 1 | 0 | 1 | 0 | 0 | 100% | 0.75 | - |
| S-SPOOF-2 | TRUE_ABUSE | DRAFT_STOR | 1 | 0 | 1 | 0 | 0 | 0% | 0.7 | - |
| S-SPOOF-3 | TRUE_ABUSE | ESCALATE | 1 | 0 | 1 | 0 | 0 | 100% | 0.75 | - |
| S-SPOOF-4 | TRUE_ABUSE | ESCALATE | 1 | 0 | 1 | 0 | 0 | 100% | 0.72 | - |
| S-SPOOF-5 | TRUE_ABUSE | ESCALATE | 1 | 0 | 1 | 0 | 0 | 100% | 0.72 | - |
| BACKGROUND | FALSE_POSITIVE | CLOSE_FP | 8 | 8 | 0 | 0 | 0 | 100% | 0.91 | - |
| F-ALGO-1 | FALSE_POSITIVE | CLOSE_FP | 3 | 3 | 0 | 0 | 0 | 100% | 0.86 | - |
| F-FAT-1 | FALSE_POSITIVE | CLOSE_FP | 2 | 2 | 0 | 0 | 0 | 100% | 0.7 | - |
| F-ICE-1 | FALSE_POSITIVE | CLOSE_FP | 2 | 2 | 0 | 0 | 0 | 100% | 0.85 | - |
| F-MM-1 | FALSE_POSITIVE | CLOSE_FP | 1 | 1 | 0 | 0 | 0 | 100% | 0.88 | - |
| F-NEWS-1 | FALSE_POSITIVE | CLOSE_FP | 1 | 0 | 1 | 0 | 0 | 0% | 0.6 | - |
| F-PARTIAL-1 | FALSE_POSITIVE | CLOSE_FP | 2 | 2 | 0 | 0 | 0 | 100% | 0.78 | - |
| F-RISK-1 | FALSE_POSITIVE | CLOSE_FP | 1 | 1 | 0 | 0 | 0 | 100% | 0.65 | - |
| F-SPOOFLIKE-HARD-1 | FALSE_POSITIVE | CLOSE_FP | 1 | 1 | 0 | 0 | 0 | 100% | 0.85 | - |
| F-STOP-1 | FALSE_POSITIVE | CLOSE_FP | 1 | 0 | 1 | 0 | 0 | 0% | 0.6 | - |

## Regression against the previous run

Previous run: `20261118T1204-sonnet-v7`. Verdict: **FAIL**.

- [x] gate holds
- [ ] safe close rate not down by more than 2 points
- [ ] no false-positive scenario regressed to 0% close (F-NEWS-1, F-STOP-1)

| delta | value |
|---|---|
| raw_safe_close_rate | -4.8 pts |
| agreement | -5.5 pts |
| escalation_precision | -4.6 pts |
| direction_agreement | -3.3 pts |
| true_abuse_recall | +0.0 pts |
| gate misses | +0 |

| scenario | agreement delta | close-rate delta |
|---|---|---|
| F-NEWS-1 | -50 pts | -50 pts |
| S-SPOOF-2 | -33 pts | +0 pts |
| F-STOP-1 | -33 pts | -33 pts |

## Disagreements with the label (3)

| alert | scenario | expected | proposed | conf | status | summary |
|---|---|---|---|---|---|---|
| A-261015-0003 | S-SPOOF-2 | DRAFT_STOR | ESCALATE | 0.7 | ok | PROP trader placed one SELL limit of 21443 (8.17x avg top-5 depth) 2 ticks from the touch, with nothing resting on the other side. 2.4s later the trader bought  |
| A-261015-0008 | F-NEWS-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader rested two identical BUY 7215 orders at 9996 (combined 5.5x depth, 1.5 ticks from touch), never executed. While they rested, a SELL 515 filled at 10 |
| A-261027-0008 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | PROP trader (no MM registration) placed three one-sided BUY limits of 4514 each (13542 total, 5.4x depth) at 9997-9998, 6 ticks from the touch, over 13:50:46-50 |
