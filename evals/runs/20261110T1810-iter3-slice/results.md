# Dataset run `20261110T1810-iter3-slice`

- Dataset `seed7`, 30 alerts (7 TRUE_ABUSE, 23 FALSE_POSITIVE); backend `local`, model `eu.anthropic.claude-sonnet-5-5`, analyst `L1`, mode `investigate`, memory on, bundle none (code defaults), concurrency 2.
- Started 2026-11-10T18:10:03+00:00, finished 2026-11-10T18:17:43+00:00 (7.7 min).
- Notes: iteration 3 slice: ruled_out alias + prompt caching (CacheConfig auto, tools_ttl), local backend, cache on

## Headline

| metric | value |
|---|---|
| gate | **holds** (0 TRUE_ABUSE proposed CLOSE_FP) |
| safe close rate | 87.0% (20 of 23 false positives closed) |
| escalation precision | 70.0% (10 ESCALATE/DRAFT_STOR) |
| strong-call precision | 100.0% (1 DRAFT_STOR) |
| agreement with label (exact disposition) | 83.3% |
| **override rate** (1 - agreement) | **16.7%** |
| direction agreement (close vs not-close) | 90.0% |
| proposals | {'CLOSE_FP': 20, 'ESCALATE': 9, 'DRAFT_STOR': 1} |
| run status | {'ok': 30} |
| alerts with a disposition recorded before this run (visible to the agent through history and Memory) | 1: A-261009-0003 |
| configuration bundle reported by the agent | none |
| latency, agent p50 / p95 | 29.2 s / 34.2 s (wall p50 29.2 s) |
| tokens per alert, in / out (mean) | 11 / 3100 (max in 12) |
| prompt cache, per alert | read 47560 / write 17115 / full price 11 tokens; hit rate 0.735 of 64686 prompt tokens |
| tool calls per alert (mean / median) | 10 / 10.0 |
| estimated model cost | $2.5 total, $0.083 per alert (assumed $2.0/$10.0 per M tokens in/out; cache read 0.1x, write 1.25x of input; not verified against the pricing page) |

## Against the baselines (same alerts)

| scorer | gate | safe close rate | raw safe close | escalation precision | agreement | override rate |
|---|---|---|---|---|---|---|
| agent (this run) | holds | 87.0% | 87.0% | 70.0% | 83.3% | 16.7% |
| threshold baseline (detector rules) | 1 missed | n/a | 95.7% | 85.7% | 93.3% | 6.7% |
| escalate everything | holds | 0.0% | 0.0% | 23.3% | 20.0% | 80.0% |
| close everything (the gate at work) | 7 missed | n/a | 100.0% | n/a | 76.7% | 23.3% |

## Confusion: expected (rows) x proposed (columns)

| expected \ proposed | CLOSE_FP | ESCALATE | DRAFT_STOR | none |
|---|---|---|---|---|
| CLOSE_FP | 20 | 3 | 0 | 0 |
| ESCALATE | 0 | 5 | 1 | 0 |
| DRAFT_STOR | 0 | 1 | 0 | 0 |

## Per scenario

| scenario | truth | expected | n | CLOSE_FP | ESCALATE | DRAFT_STOR | none | agreement | mean conf | gate misses |
|---|---|---|---|---|---|---|---|---|---|---|
| S-LAYER-1 | TRUE_ABUSE | ESCALATE | 2 | 0 | 1 | 1 | 0 | 50% | 0.66 | - |
| S-SPOOF-1 | TRUE_ABUSE | ESCALATE | 1 | 0 | 1 | 0 | 0 | 100% | 0.7 | - |
| S-SPOOF-2 | TRUE_ABUSE | DRAFT_STOR | 1 | 0 | 1 | 0 | 0 | 0% | 0.72 | - |
| S-SPOOF-3 | TRUE_ABUSE | ESCALATE | 1 | 0 | 1 | 0 | 0 | 100% | 0.7 | - |
| S-SPOOF-4 | TRUE_ABUSE | ESCALATE | 1 | 0 | 1 | 0 | 0 | 100% | 0.7 | - |
| S-SPOOF-5 | TRUE_ABUSE | ESCALATE | 1 | 0 | 1 | 0 | 0 | 100% | 0.7 | - |
| BACKGROUND | FALSE_POSITIVE | CLOSE_FP | 8 | 8 | 0 | 0 | 0 | 100% | 0.88 | - |
| F-ALGO-1 | FALSE_POSITIVE | CLOSE_FP | 3 | 3 | 0 | 0 | 0 | 100% | 0.85 | - |
| F-FAT-1 | FALSE_POSITIVE | CLOSE_FP | 2 | 1 | 1 | 0 | 0 | 50% | 0.7 | - |
| F-ICE-1 | FALSE_POSITIVE | CLOSE_FP | 2 | 2 | 0 | 0 | 0 | 100% | 0.8 | - |
| F-MM-1 | FALSE_POSITIVE | CLOSE_FP | 2 | 2 | 0 | 0 | 0 | 100% | 0.9 | - |
| F-NEWS-1 | FALSE_POSITIVE | CLOSE_FP | 1 | 0 | 1 | 0 | 0 | 0% | 0.7 | - |
| F-PARTIAL-1 | FALSE_POSITIVE | CLOSE_FP | 2 | 2 | 0 | 0 | 0 | 100% | 0.72 | - |
| F-RISK-1 | FALSE_POSITIVE | CLOSE_FP | 1 | 1 | 0 | 0 | 0 | 100% | 0.7 | - |
| F-SPOOFLIKE-HARD-1 | FALSE_POSITIVE | CLOSE_FP | 1 | 1 | 0 | 0 | 0 | 100% | 0.85 | - |
| F-STOP-1 | FALSE_POSITIVE | CLOSE_FP | 1 | 0 | 1 | 0 | 0 | 0% | 0.62 | - |

## Regression against the previous run

Previous run: `20261106T1126-sonnet-v3`. Verdict: **FAIL**.

- [x] gate holds
- [ ] safe close rate not down by more than 2 points
- [ ] no false-positive scenario regressed to 0% close (F-NEWS-1)

| delta | value |
|---|---|
| raw_safe_close_rate | -6.6 pts |
| agreement | -10.1 pts |
| escalation_precision | -5.7 pts |
| direction_agreement | -4.6 pts |
| true_abuse_recall | +0.0 pts |
| gate misses | +0 |

| scenario | agreement delta | close-rate delta |
|---|---|---|
| S-LAYER-1 | -50 pts | +0 pts |
| F-NEWS-1 | -50 pts | -50 pts |
| S-SPOOF-2 | -33 pts | +0 pts |
| F-FAT-1 | -17 pts | -17 pts |

## Disagreements with the label (5)

| alert | scenario | expected | proposed | conf | status | summary |
|---|---|---|---|---|---|---|
| A-261013-0003 | S-LAYER-1 | ESCALATE | DRAFT_STOR | 0.6 | ok | Prop trader placed five BUY limit orders of 4340 each (21700 gross, 8.7x top-5 depth) on five levels 3 ticks from the touch, with no same-side fills. About 2 s  |
| A-261015-0003 | S-SPOOF-2 | DRAFT_STOR | ESCALATE | 0.72 | ok | PROP trader placed a single one-sided SELL limit of 21443 (8.17x avg top-5 depth) at 10000, 2 ticks from the touch, with no same-side fills. 2.4s later a BUY ma |
| A-261009-0007 | F-FAT-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader T-X1009-05 (no registered MM on SYN.A, typical size 500) placed a one-sided BUY of 18930 (7.9x top-5 depth) 1 tick below the best bid and cancelled  |
| A-261015-0008 | F-NEWS-1 | CLOSE_FP | ESCALATE | 0.7 | ok | PROP trader (no MM registration) rested two BUY limits of 7215 each at 9996 (about 5.5x average top-5 depth, 1.5 ticks from the touch), one-sided, with zero fil |
| A-261027-0008 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.62 | ok | PROP-EQ trader (no MM registration) rested three one-sided BUY limits of 4514 each (13542 total, max 5.4x top-5 depth, 6 ticks from touch) for ~14-16s with zero |
