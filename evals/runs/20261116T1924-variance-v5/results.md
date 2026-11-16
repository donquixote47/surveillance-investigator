# Dataset run `20261116T1924-variance-v5`

- Dataset `seed7`, 110 alerts (35 TRUE_ABUSE, 75 FALSE_POSITIVE); backend `runtime`, model `eu.anthropic.claude-sonnet-5-5`, analyst `L1`, mode `investigate`, memory on, bundle none (code defaults), concurrency 2.
- Started 2026-11-16T19:24:55+00:00, finished 2026-11-16T19:59:46+00:00 (34.9 min).
- Notes: run-to-run variance on Runtime v17 with the tools and the standard of 2026-11-16: the 21 alerts of 20261111T0950-variance-v4 (one per scenario plus the alerts that had moved) and A-261022-0003, which moved between v4 and v5; 22 x 5; the subset is enriched with F-STOP-1/F-NEWS-1/F-FAT-1 on purpose, so its safe close is not the full-set number

## Headline

| metric | value |
|---|---|
| gate | **holds** (0 TRUE_ABUSE proposed CLOSE_FP) |
| safe close rate | 70.7% (53 of 75 false positives closed) |
| escalation precision | 61.4% (57 ESCALATE/DRAFT_STOR) |
| strong-call precision | 100.0% (2 DRAFT_STOR) |
| agreement with label (exact disposition) | 73.6% |
| **override rate** (1 - agreement) | **26.4%** |
| direction agreement (close vs not-close) | 80.0% |
| proposals | {'CLOSE_FP': 53, 'ESCALATE': 55, 'DRAFT_STOR': 2} |
| run status | {'ok': 110} |
| configuration bundle reported by the agent | none |
| latency, agent p50 / p95 | 28.9 s / 47.2 s (wall p50 34.5 s) |
| tokens per alert, in / out (mean) | 10 / 3155 (max in 12) |
| prompt cache, per alert | read 45221 / write 14576 / full price 10 tokens; hit rate 0.756 of 59807 prompt tokens |
| tool calls per alert (mean / median) | 10 / 10.0 |
| estimated model cost | $8.48 total, $0.077 per alert (assumed $2.0/$10.0 per M tokens in/out; cache read 0.1x, write 1.25x of input; not verified against the pricing page) |

## Against the baselines (same alerts)

| scorer | gate | safe close rate | raw safe close | escalation precision | agreement | override rate |
|---|---|---|---|---|---|---|
| agent (this run) | holds | 70.7% | 70.7% | 61.4% | 73.6% | 26.4% |
| threshold baseline (detector rules) | 1 missed | n/a | 93.3% | 85.7% | 90.9% | 9.1% |
| escalate everything | holds | 0.0% | 0.0% | 31.8% | 27.3% | 72.7% |
| close everything (the gate at work) | 7 missed | n/a | 100.0% | n/a | 68.2% | 31.8% |

## Confusion: expected (rows) x proposed (columns)

| expected \ proposed | CLOSE_FP | ESCALATE | DRAFT_STOR | none |
|---|---|---|---|---|
| CLOSE_FP | 53 | 22 | 0 | 0 |
| ESCALATE | 0 | 28 | 2 | 0 |
| DRAFT_STOR | 0 | 5 | 0 | 0 |

## Per scenario

| scenario | truth | expected | n | CLOSE_FP | ESCALATE | DRAFT_STOR | none | agreement | mean conf | gate misses |
|---|---|---|---|---|---|---|---|---|---|---|
| S-LAYER-1 | TRUE_ABUSE | ESCALATE | 10 | 0 | 8 | 2 | 0 | 80% | 0.7 | - |
| S-SPOOF-1 | TRUE_ABUSE | ESCALATE | 5 | 0 | 5 | 0 | 0 | 100% | 0.7 | - |
| S-SPOOF-2 | TRUE_ABUSE | DRAFT_STOR | 5 | 0 | 5 | 0 | 0 | 0% | 0.7 | - |
| S-SPOOF-3 | TRUE_ABUSE | ESCALATE | 5 | 0 | 5 | 0 | 0 | 100% | 0.7 | - |
| S-SPOOF-4 | TRUE_ABUSE | ESCALATE | 5 | 0 | 5 | 0 | 0 | 100% | 0.73 | - |
| S-SPOOF-5 | TRUE_ABUSE | ESCALATE | 5 | 0 | 5 | 0 | 0 | 100% | 0.77 | - |
| BACKGROUND | FALSE_POSITIVE | CLOSE_FP | 5 | 5 | 0 | 0 | 0 | 100% | 0.9 | - |
| F-ALGO-1 | FALSE_POSITIVE | CLOSE_FP | 5 | 5 | 0 | 0 | 0 | 100% | 0.84 | - |
| F-FAT-1 | FALSE_POSITIVE | CLOSE_FP | 10 | 10 | 0 | 0 | 0 | 100% | 0.72 | - |
| F-ICE-1 | FALSE_POSITIVE | CLOSE_FP | 5 | 5 | 0 | 0 | 0 | 100% | 0.82 | - |
| F-MM-1 | FALSE_POSITIVE | CLOSE_FP | 5 | 5 | 0 | 0 | 0 | 100% | 0.9 | - |
| F-NEWS-1 | FALSE_POSITIVE | CLOSE_FP | 10 | 2 | 8 | 0 | 0 | 20% | 0.6 | - |
| F-PARTIAL-1 | FALSE_POSITIVE | CLOSE_FP | 5 | 5 | 0 | 0 | 0 | 100% | 0.71 | - |
| F-RISK-1 | FALSE_POSITIVE | CLOSE_FP | 5 | 5 | 0 | 0 | 0 | 100% | 0.66 | - |
| F-SPOOFLIKE-HARD-1 | FALSE_POSITIVE | CLOSE_FP | 5 | 5 | 0 | 0 | 0 | 100% | 0.82 | - |
| F-STOP-1 | FALSE_POSITIVE | CLOSE_FP | 20 | 6 | 14 | 0 | 0 | 30% | 0.61 | - |

## Disagreements with the label (29)

| alert | scenario | expected | proposed | conf | status | summary |
|---|---|---|---|---|---|---|
| A-261013-0003 | S-LAYER-1 | ESCALATE | DRAFT_STOR | 0.6 | ok | PROP trader placed five one-sided BUY limit orders of 4340 each (21700 total, 8.7x depth) at 9988-9992 within 60 ms, 1-5 ticks below the touch of 9993. About 2  |
| A-261013-0003 | S-LAYER-1 | ESCALATE | DRAFT_STOR | 0.6 | ok | PROP trader placed five BUY limit orders of 4,340 each (21,700 total, about 8.7x top-5 depth) at 9988-9992, 1-5 ticks below the 9993 bid, with nothing on the ot |
| A-261015-0003 | S-SPOOF-2 | DRAFT_STOR | ESCALATE | 0.7 | ok | PROP trader placed a single one-sided SELL limit of 21443 (8.2x depth, 2 ticks from touch) at 11:04:43.303. It was never executed. Two seconds later the trader  |
| A-261015-0003 | S-SPOOF-2 | DRAFT_STOR | ESCALATE | 0.7 | ok | PROP trader placed one SELL limit of 21443 (8.17x avg top-5 depth) 2 ticks from the touch. 2.4s later a BUY market order of 1189 executed, and the SELL was full |
| A-261015-0003 | S-SPOOF-2 | DRAFT_STOR | ESCALATE | 0.72 | ok | PROP trader T-X1015-02 placed one SELL LIMIT of 21443 (8.17x avg top-5 depth, 2 ticks from the touch) on SYN.A. Two seconds later a BUY MARKET of 1189 executed. |
| A-261015-0003 | S-SPOOF-2 | DRAFT_STOR | ESCALATE | 0.7 | ok | PROP trader placed a one-sided SELL limit of 21,443 (8.17x depth, 2 ticks from touch, typical size 500) at 11:04:43.303. It never executed. 2.4s later the trade |
| A-261015-0003 | S-SPOOF-2 | DRAFT_STOR | ESCALATE | 0.7 | ok | Prop trader T-X1015-02 placed one SELL LIMIT of 21443 (8.17x depth, 2 ticks from touch) at 11:04:43.303 with nothing on the bid. 2.4s later a BUY market order o |
| A-261015-0008 | F-NEWS-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader rested two identical one-sided BUY orders (2 x 7,215 at 9996, about 5.5x depth combined, 1.5 ticks from touch). Both were up for about 30 s with no  |
| A-261015-0008 | F-NEWS-1 | CLOSE_FP | ESCALATE | 0.6 | ok | PROP trader placed two BUY 7,215 limit orders (14,430 total, about 5.5x top-5 depth, 14x typical size 500) at 9996, 1.5 ticks behind the touch. While they reste |
| A-261015-0008 | F-NEWS-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader placed two BUY limits of 7,215 each (14,430 total, 5.5x avg top-5 depth) at 9996, 1.5 ticks from the touch. Neither order filled. About 2.6s before  |
| A-261015-0008 | F-NEWS-1 | CLOSE_FP | ESCALATE | 0.6 | ok | PROP trader (no MM registration) rested two identical BUY 7,215 orders at 9996 (14,430 total, 5.5x depth, 1.5 ticks from touch, one level) for about 25-28s with |
| A-261015-0008 | F-NEWS-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader placed two BUY limits of 7215 each (14430 total, 5.5x avg top-5 depth) at 9996, 1.5 ticks from the touch, with no same-side fills. About 25s later a |
| A-261016-0005 | F-NEWS-1 | CLOSE_FP | ESCALATE | 0.6 | ok | PROP trader (no MM registration) rested two identical BUY 7162 LIMIT orders at 9999 (combined 5.76x depth, one-sided, 1.5 ticks from touch) for about 25-30s wit |
| A-261016-0005 | F-NEWS-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader placed two identical BUY 7162 limit orders at 9999 (1.5 ticks from touch, 5.76x depth combined) and kept them resting about 27s with no fills. Meanw |
| A-261016-0005 | F-NEWS-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader rested two BUY orders of 7,162 at 9999 (14,324 combined, 5.76x depth; each below the 3x single-order threshold) with no fills. A 511 SELL filled at  |
| A-261022-0003 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader T-X1022-03 bought 1333 by market order at 10003-10004 at 13:16:57, then rested three one-sided BUY limits of 4800 each (14400 total, max 5.7x depth, |
| A-261022-0003 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | PROP trader bought 1333 by market order at 10003-10004 (13:16:57), then stacked three 4800 BUY limits (14400 total, up to 5.7x depth) at 9995/9994, 6 ticks from |
| A-261022-0003 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | PROP trader (no MM registration) bought 1333 at market (10003-10004) at 13:16:57, then placed three one-sided BUY limits of 4800 each (14400 total, 5.7x depth,  |
| A-261022-0003 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader placed three one-sided BUY limits (3x4800 = 14400, about 5.7x top-5 depth, 6 ticks from the touch, none filled). The trader sold 1333 at market, and |
| A-261026-0003 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader bought 1118 at market (12:36:13), then placed three one-sided BUY limits of 4024 each (12,072 total, 4.87x depth) at 9996/9995/9994, 6 ticks from th |
| A-261026-0003 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.65 | ok | PROP trader (no MM registration) bought 1118 at market (12:36:13), then placed three BUY limits of 4024 each at 9996/9995/9994 (6 ticks from touch, 12072 total, |
| A-261026-0003 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader placed three BUY limits of 4024 each (12072 total, 4.87x depth) at 9996/9995/9994, 5-7 ticks below the touch, and they never executed. The trader th |
| A-261027-0008 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | PROP trader bought 1254 at market (10005), then rested three one-sided BUY limits of 4514 each (13542 total, about 5.4x depth) 6 ticks from the touch. About 15  |
| A-261027-0008 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader (not a registered MM) bought 1254 at market (10005), then rested three BUY limits of 4514 each (13542 total, 5.4x depth, 6 ticks off touch, 9998/999 |
| A-261027-0008 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader bought 1254 at market (10005), then stacked three one-sided BUY limits of 4514 each (13542 total, 5.4x depth) 3-6 ticks below the touch. None execut |
| A-261027-0008 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader bought 1254 at market (10005), then placed three one-sided BUY limits of 4514 each (13542 total, 3 to 6 ticks below touch, 2 levels), none filled. A |
| A-261027-0008 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.7 | ok | Prop trader bought 1254 at market (10005), then rested three one-sided BUY limits of 4514 each (13542 total, 5.4x depth, 6 ticks from touch) over ~4s. Starting  |
| A-261028-0011 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader bought 1476 by market order at 16:57:25, then placed three one-sided BUY limits of 5313 (15939 total, 6.5x depth, 6 ticks from the touch) at 16:57:2 |
| A-261028-0011 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader (no MM registration) bought 1476 by market order at 10005-10006, then rested three one-sided BUY limits of 5313 each (15939 total, 6.5x depth) at 99 |

## Run-to-run variance

22 alerts, each investigated 5 times with nothing changed (110 investigations). An alert is *stable* when every repetition proposed the same disposition.

| measure | value |
|---|---|
| stable alerts | 17 of 22 (77.3%) |
| true-abuse alerts proposed CLOSE_FP in any repetition | **none** |
| safe close rate across the 5 pseudo-runs | 60.0% to 86.7% (mean 70.7%, sd 9.0 pts) |
| agreement with the label across pseudo-runs | 68.2% to 81.8% |

| pseudo-run | gate | safe close | agreement | escalation precision |
|---|---|---|---|---|
| repeat 0 | holds | 60.0% | 68.2% | 53.8% |
| repeat 1 | holds | 86.7% | 81.8% | 77.8% |
| repeat 2 | holds | 66.7% | 72.7% | 58.3% |
| repeat 3 | holds | 66.7% | 68.2% | 58.3% |
| repeat 4 | holds | 73.3% | 77.3% | 63.6% |

| scenario | alerts | unstable | flips / repetitions | flip rate |
|---|---|---|---|---|
| BACKGROUND | 1 | 0 | 0 / 5 | 0.0% |
| F-ALGO-1 | 1 | 0 | 0 / 5 | 0.0% |
| F-FAT-1 | 2 | 0 | 0 / 10 | 0.0% |
| F-ICE-1 | 1 | 0 | 0 / 5 | 0.0% |
| F-MM-1 | 1 | 0 | 0 / 5 | 0.0% |
| F-NEWS-1 | 2 | 1 | 2 / 10 | 20.0% |
| F-PARTIAL-1 | 1 | 0 | 0 / 5 | 0.0% |
| F-RISK-1 | 1 | 0 | 0 / 5 | 0.0% |
| F-SPOOFLIKE-HARD-1 | 1 | 0 | 0 / 5 | 0.0% |
| F-STOP-1 | 4 | 3 | 5 / 20 | 25.0% |
| S-LAYER-1 | 2 | 1 | 2 / 10 | 20.0% |
| S-SPOOF-1 | 1 | 0 | 0 / 5 | 0.0% |
| S-SPOOF-2 | 1 | 0 | 0 / 5 | 0.0% |
| S-SPOOF-3 | 1 | 0 | 0 / 5 | 0.0% |
| S-SPOOF-4 | 1 | 0 | 0 / 5 | 0.0% |
| S-SPOOF-5 | 1 | 0 | 0 / 5 | 0.0% |

## Unstable alerts

| alert | scenario | expected | sequence | confidence |
|---|---|---|---|---|
| A-261013-0003 | S-LAYER-1 | ESCALATE | ESCALATE , DRAFT_STOR , ESCALATE , DRAFT_STOR , ESCALATE | 0.6 to 0.8 |
| A-261016-0005 | F-NEWS-1 | CLOSE_FP | ESCALATE , CLOSE_FP , CLOSE_FP , ESCALATE , ESCALATE | 0.6 to 0.6 |
| A-261022-0003 | F-STOP-1 | CLOSE_FP | ESCALATE , CLOSE_FP , ESCALATE , ESCALATE , ESCALATE | 0.6 to 0.6 |
| A-261026-0003 | F-STOP-1 | CLOSE_FP | ESCALATE , CLOSE_FP , ESCALATE , ESCALATE , CLOSE_FP | 0.6 to 0.65 |
| A-261028-0011 | F-STOP-1 | CLOSE_FP | ESCALATE , CLOSE_FP , ESCALATE , CLOSE_FP , CLOSE_FP | 0.6 to 0.6 |
