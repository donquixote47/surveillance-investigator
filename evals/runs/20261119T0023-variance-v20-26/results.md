# Dataset run `20261119T0023-variance-v20-26`

- Dataset `seed7`, 130 alerts (35 TRUE_ABUSE, 95 FALSE_POSITIVE); backend `runtime`, model `eu.anthropic.claude-sonnet-5-5`, analyst `L1`, mode `investigate`, memory on, bundle none (code defaults), concurrency 2.
- Started 2026-11-19T00:23:56+00:00, finished 2026-11-19T00:56:48+00:00 (32.9 min).
- Notes: run-to-run variance on Runtime v20 with one analyst per worker, enlarged set: the 22 alerts of 20261116T1924-variance-v5 plus the two F-STOP-1 and the two F-NEWS-1 alerts it lacked (all six and all four now), 26 x 5; the baseline for judging the two borderline scenarios; the subset is enriched on purpose, so its safe close is not the full-set number

## Headline

| metric | value |
|---|---|
| gate | **holds** (0 TRUE_ABUSE proposed CLOSE_FP) |
| safe close rate | 56.8% (54 of 95 false positives closed) |
| escalation precision | 46.1% (76 ESCALATE/DRAFT_STOR) |
| strong-call precision | 100.0% (3 DRAFT_STOR) |
| agreement with label (exact disposition) | 62.3% |
| **override rate** (1 - agreement) | **37.7%** |
| direction agreement (close vs not-close) | 68.5% |
| proposals | {'CLOSE_FP': 54, 'ESCALATE': 73, 'DRAFT_STOR': 3} |
| run status | {'ok': 130} |
| configuration bundle reported by the agent | none |
| latency, agent p50 / p95 | 23.6 s / 29.0 s (wall p50 29.9 s) |
| tokens per alert, in / out (mean) | 11 / 3226 (max in 12) |
| prompt cache, per alert | read 45336 / write 14266 / full price 11 tokens; hit rate 0.761 of 59613 prompt tokens |
| tool calls per alert (mean / median) | 10 / 10.0 |
| estimated model cost | $10.01 total, $0.077 per alert (assumed $2.0/$10.0 per M tokens in/out; cache read 0.1x, write 1.25x of input; not verified against the pricing page) |

## Against the baselines (same alerts)

| scorer | gate | safe close rate | raw safe close | escalation precision | agreement | override rate |
|---|---|---|---|---|---|---|
| agent (this run) | holds | 56.8% | 56.8% | 46.1% | 62.3% | 37.7% |
| threshold baseline (detector rules) | 1 missed | n/a | 94.7% | 85.7% | 92.3% | 7.7% |
| escalate everything | holds | 0.0% | 0.0% | 26.9% | 23.1% | 76.9% |
| close everything (the gate at work) | 7 missed | n/a | 100.0% | n/a | 73.1% | 26.9% |

## Confusion: expected (rows) x proposed (columns)

| expected \ proposed | CLOSE_FP | ESCALATE | DRAFT_STOR | none |
|---|---|---|---|---|
| CLOSE_FP | 54 | 41 | 0 | 0 |
| ESCALATE | 0 | 27 | 3 | 0 |
| DRAFT_STOR | 0 | 5 | 0 | 0 |

## Per scenario

| scenario | truth | expected | n | CLOSE_FP | ESCALATE | DRAFT_STOR | none | agreement | mean conf | gate misses |
|---|---|---|---|---|---|---|---|---|---|---|
| S-LAYER-1 | TRUE_ABUSE | ESCALATE | 10 | 0 | 7 | 3 | 0 | 70% | 0.67 | - |
| S-SPOOF-1 | TRUE_ABUSE | ESCALATE | 5 | 0 | 5 | 0 | 0 | 100% | 0.71 | - |
| S-SPOOF-2 | TRUE_ABUSE | DRAFT_STOR | 5 | 0 | 5 | 0 | 0 | 0% | 0.7 | - |
| S-SPOOF-3 | TRUE_ABUSE | ESCALATE | 5 | 0 | 5 | 0 | 0 | 100% | 0.68 | - |
| S-SPOOF-4 | TRUE_ABUSE | ESCALATE | 5 | 0 | 5 | 0 | 0 | 100% | 0.72 | - |
| S-SPOOF-5 | TRUE_ABUSE | ESCALATE | 5 | 0 | 5 | 0 | 0 | 100% | 0.72 | - |
| BACKGROUND | FALSE_POSITIVE | CLOSE_FP | 5 | 5 | 0 | 0 | 0 | 100% | 0.9 | - |
| F-ALGO-1 | FALSE_POSITIVE | CLOSE_FP | 5 | 5 | 0 | 0 | 0 | 100% | 0.84 | - |
| F-FAT-1 | FALSE_POSITIVE | CLOSE_FP | 10 | 9 | 1 | 0 | 0 | 90% | 0.72 | - |
| F-ICE-1 | FALSE_POSITIVE | CLOSE_FP | 5 | 5 | 0 | 0 | 0 | 100% | 0.8 | - |
| F-MM-1 | FALSE_POSITIVE | CLOSE_FP | 5 | 5 | 0 | 0 | 0 | 100% | 0.9 | - |
| F-NEWS-1 | FALSE_POSITIVE | CLOSE_FP | 20 | 9 | 11 | 0 | 0 | 45% | 0.63 | - |
| F-PARTIAL-1 | FALSE_POSITIVE | CLOSE_FP | 5 | 5 | 0 | 0 | 0 | 100% | 0.72 | - |
| F-RISK-1 | FALSE_POSITIVE | CLOSE_FP | 5 | 5 | 0 | 0 | 0 | 100% | 0.69 | - |
| F-SPOOFLIKE-HARD-1 | FALSE_POSITIVE | CLOSE_FP | 5 | 5 | 0 | 0 | 0 | 100% | 0.81 | - |
| F-STOP-1 | FALSE_POSITIVE | CLOSE_FP | 30 | 1 | 29 | 0 | 0 | 3% | 0.61 | - |

## Disagreements with the label (49)

| alert | scenario | expected | proposed | conf | status | summary |
|---|---|---|---|---|---|---|
| A-261013-0003 | S-LAYER-1 | ESCALATE | DRAFT_STOR | 0.62 | ok | PROP trader (no MM registration, typical order size 500) placed five one-sided BUY limits of 4340 each (21,700 total, 8.69x depth) at 9988-9992, 1-5 ticks below |
| A-261013-0003 | S-LAYER-1 | ESCALATE | DRAFT_STOR | 0.6 | ok | Prop trader placed five BUY limit orders of 4340 each (21700 total, 8.7x average top-5 depth) at five levels, 3 to 7 ticks below the ask. About 2 s later a SELL |
| A-261013-0003 | S-LAYER-1 | ESCALATE | DRAFT_STOR | 0.6 | ok | Prop trader (not a registered MM, typical order 500) placed five BUY limit orders of 4,340 each (21,700 total, up to 8.7x depth) on five levels 1-5 ticks below  |
| A-261015-0003 | S-SPOOF-2 | DRAFT_STOR | ESCALATE | 0.7 | ok | PROP-EQ trader (no MM registration) placed a single one-sided SELL limit of 21443 (8.17x avg top-5 depth) 2 ticks from the touch at 11:04:43.303, bought 1189 by |
| A-261015-0003 | S-SPOOF-2 | DRAFT_STOR | ESCALATE | 0.7 | ok | Prop trader placed one SELL limit of 21443 (8.2x avg top-5 depth), 2 ticks from the touch, with nothing on the buy side. 2.4s later a BUY market order of 1189 e |
| A-261015-0003 | S-SPOOF-2 | DRAFT_STOR | ESCALATE | 0.7 | ok | PROP trader placed one SELL limit of 21443 (8.17x avg top-5 depth) 2 ticks from the touch, bought 1189 by market order 2.4s later, and cancelled the whole SELL  |
| A-261015-0003 | S-SPOOF-2 | DRAFT_STOR | ESCALATE | 0.7 | ok | Prop trader placed a one-sided SELL limit of 21443 (8.17x avg top-5 depth) at 10000, 2 ticks from the touch. About 2.4s later the trader bought 1189 by market o |
| A-261015-0003 | S-SPOOF-2 | DRAFT_STOR | ESCALATE | 0.7 | ok | Prop trader placed a one-sided SELL limit of 21443 (8.17x depth, 2 ticks from touch, no resting BUY).2.4s later they bought 1189 by market order. The SELL was c |
| A-261009-0007 | F-FAT-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader placed a single BUY of 18,930 (7.94x avg top-5 depth) 1 tick below the bid and cancelled it after 803 ms with no fills. There was no opposite-side e |
| A-261015-0008 | F-NEWS-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader placed two BUY limits of 7215 each at 9996 (about 5.5x depth combined, 1.5 ticks from the touch), both one-sided with no fills. The bid rose from 99 |
| A-261015-0008 | F-NEWS-1 | CLOSE_FP | ESCALATE | 0.6 | ok | PROP trader (no MM registration) rested two BUY LIMIT orders of 7,215 each (14,430 total, 5.5x avg top-5 depth) at 9996, never filled. Mid-rest the trader sold  |
| A-261015-0008 | F-NEWS-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader (no MM registration) rested two identical BUY 7,215 limit orders at 9996 (total 14,430, 5.5x depth, 1.5 ticks from touch) for about 28s with no fill |
| A-261015-0008 | F-NEWS-1 | CLOSE_FP | ESCALATE | 0.6 | ok | PROP trader placed two BUY 7,215 orders at 9996 (combined 5.5x depth, one-sided, never filled), sold 515 at 10001 after the bid had risen from 9997 to 10000, th |
| A-261015-0008 | F-NEWS-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader placed two BUY limits of 7,215 each at 9996 (about 5.5x depth in total, 1.5 ticks from the touch). The bid rose while they rested. The trader then s |
| A-261016-0003 | F-NEWS-1 | CLOSE_FP | ESCALATE | 0.7 | ok | PROP trader (no MM registration) rested two identical BUY 6680 LIMIT orders at 9997 (combined 5.37x depth, 1.5 ticks from touch) for about 27-30s with zero fill |
| A-261016-0003 | F-NEWS-1 | CLOSE_FP | ESCALATE | 0.68 | ok | Prop trader with no market-making registration rested two identical one-sided BUY orders (2 x 6680 at 9997, 5.37x depth combined, 1.5 ticks from touch) for abou |
| A-261016-0003 | F-NEWS-1 | CLOSE_FP | ESCALATE | 0.7 | ok | PROP trader (no MM registration) rested two one-sided BUY orders of 6680 each at 9997 (13360 total, 5.37x depth), 30-ish seconds, with zero fills on them. While |
| A-261016-0003 | F-NEWS-1 | CLOSE_FP | ESCALATE | 0.7 | ok | Two one-sided BUY orders of 6,680 each (13,360 total, 5.37x avg top-5 depth) rested at 9997, about 1.5 ticks from the touch, with no fills. The trader sold 477  |
| A-261016-0003 | F-NEWS-1 | CLOSE_FP | ESCALATE | 0.7 | ok | Prop trader placed two one-sided BUY limit orders of 6680 each (about 5.4x depth) at 9997, then sold 477 at 10003 while both rested. Both bids were cancelled 18 |
| A-261016-0005 | F-NEWS-1 | CLOSE_FP | ESCALATE | 0.55 | ok | PROP trader with no MM registration rested two BUY LIMITs of 7,162 each at 9999 (14,324 together, 5.76x depth, about 29x typical size of 500), with no fills. Ab |
| A-261005-0007 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader with no market-making registration bought 1132 at market (13:20:37), then placed three one-sided BUY limits of 4077 each (12231 total, 5.04x depth)  |
| A-261005-0007 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Three one-sided BUY limit orders (3 x 4077 = 12231, about 5x average depth, 6 ticks from the touch) were placed over 4s. None executed. At 13:20:57.412 the trad |
| A-261005-0007 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader T-X1005-04 (not a registered MM) rested three BUY limits of 4077 each (12231 total, 5.04x depth, 6 ticks from touch, 2 price levels) from 13:20:39 t |
| A-261005-0007 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.62 | ok | Prop trader bought 1132 by market order at 13:20:37, then layered three BUY limits of 4077 (12231 total, 5.04x depth) at 9993/9994, 6 ticks from the touch. At 1 |
| A-261005-0007 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.65 | ok | Prop trader with no MM registration bought 1132 at market (13:20:37), then placed three 4077 BUY limits (12231 total, 5.04x depth) 6 ticks from the touch at 999 |
| A-261006-0005 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | PROP trader (no registered MM) bought 1058 at market at 11:36:02, then placed three one-sided BUY limit layers of 3810 each (total 11430, 4.66x depth, 6 ticks f |
| A-261006-0005 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader bought 1058 at market (11:36:02), then layered three BUY limits of 3810 (9994/9993/9992, 11430 total, 4.66x depth, 6 ticks from touch) over ~4s, sol |
| A-261006-0005 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | PROP trader (no registered MM) rested three BUY limit orders of 3810 each (11430 total, 4.66x depth) at 9994/9993/9992, 6 ticks off the touch. They were placed  |
| A-261006-0005 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.62 | ok | Prop trader bought 1058 at market (11:36:02), then placed three BUY limits of 3810 each at 9994/9993/9992 (11430 total, 4.66x depth, 6 ticks from touch) over 4  |
| A-261006-0005 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | PROP trader bought 1058 at market (10002-10005), then placed three one-sided BUY limits of 3810 each at 9994/9993/9992 (11430 total, 4.66x depth, 6 ticks from t |
| A-261022-0003 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader bought 1333 at market (13:16:57), then stacked three one-sided BUY limits of 4800 (14400 total, 5.7x depth) at 9994-9995, 5-6 ticks from the touch.  |
| A-261022-0003 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader bought 1333 by market order, then placed three one-sided BUY limits of 4800 (14400 total, 5.7x depth, 6 ticks from touch, 2 levels), sold 1333 at ma |
| A-261022-0003 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Three one-sided BUY limit orders of 4,800 (14,400 total, 5.7x top-5 depth) rested 6 ticks below the touch, with no executions. They were all cancelled together  |
| A-261022-0003 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | PROP trader bought 1333 by market order at 10003-10004 (13:16:57), then placed three one-sided BUY limits of 4800 each (14400 total, 5.7x depth) 5-6 ticks below |
| A-261022-0003 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader bought 1333 by market order at 10003-10004 (13:16:57), then placed three one-sided BUY limits of 4800 (14400 total, 5.7x depth) at 9994-9995, 5-6 ti |
| A-261026-0003 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader bought 1118 by market order (fills 10003-10007), then placed three BUY limit layers of 4024 each (12072 total, 4.87x depth, 6 ticks from touch, 9996 |
| A-261026-0003 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader bought 1118 by market order (12:36:13), then placed three bid LIMITs of 4024 each (12,072 total, 4.87x depth, 6 ticks below touch, 3 levels) and nev |
| A-261026-0003 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader placed three one-sided BUY limits of 4,024 each (12,072 total, 4.87x depth) at 9996/9995/9994, 5-7 ticks below the touch. None filled. Seconds later |
| A-261026-0003 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader bought 1118 by market order at 12:36:13 (sweeping the ask from 10003 to 10007), then placed three BUY limit orders of 4024 each at 9996/9995/9994 (1 |
| A-261027-0008 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader bought 1254 at market (10005), then stacked three one-sided BUY limits of 4514 each (13542 total, 5.4x depth) 5-8 ticks below the touch over 4s. Abo |
| A-261027-0008 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader bought 1254 at market at 10005 (13:50:44), then placed three one-sided BUY limits of 4514 each (13,542 total, 5.4x depth) 6 ticks from the touch. At |
| A-261027-0008 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.7 | ok | PROP trader bought 1254 at market (13:50:44), then placed three one-sided BUY limits of 4514 each (13542 total, 5.4x depth) 4-8 ticks below the touch. The bid r |
| A-261027-0008 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader bought 1254 at market (13:50:44), then placed three one-sided BUY limits of 4514 each (13542 total, 5.4x avg depth 2506) 5-6 ticks below the touch w |
| A-261027-0008 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader bought 1254 at market (10005), then stacked three BUY limits of 4514 (13542 total, 5.4x depth, 6 ticks from touch, 2 levels) with no fills. At 13:51 |
| A-261028-0011 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | PROP trader (no MM registration) bought 1476 at market (16:57:25), then placed three one-sided BUY limits of 5313 each (15939 total, 6.5x depth) 6 ticks below t |
| A-261028-0011 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | PROP trader (no MM registration) bought 1476 by market order at 10005-10006, then placed three one-sided BUY limits of 5313 (15939 total, 6.5x depth) at 9997-99 |
| A-261028-0011 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader bought 1476 by market order at 16:57:25, then stacked three one-sided BUY limits of 5313 (15939 total, 6.5x depth) 6 ticks from the touch. At 16:57: |
| A-261028-0011 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader bought 1476 by market order (16:57:25.851, filled 10005-10006), then placed three away-from-touch BUY limits of 5313 each (15939 total, 6.5x avg top |
| A-261028-0011 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.65 | ok | Prop trader (no MM registration) rested three one-sided BUY limits (3x5313=15939, about 6.5x depth in total) 5-6 ticks below the touch. None executed, and all w |

## Run-to-run variance

26 alerts, each investigated 5 times with nothing changed (130 investigations). An alert is *stable* when every repetition proposed the same disposition.

| measure | value |
|---|---|
| stable alerts | 22 of 26 (84.6%) |
| true-abuse alerts proposed CLOSE_FP in any repetition | **none** |
| safe close rate across the 5 pseudo-runs | 52.6% to 63.2% (mean 56.8%, sd 3.9 pts) |
| agreement with the label across pseudo-runs | 57.7% to 65.4% |

| pseudo-run | gate | safe close | agreement | escalation precision |
|---|---|---|---|---|
| repeat 0 | holds | 52.6% | 61.5% | 43.8% |
| repeat 1 | holds | 52.6% | 57.7% | 43.8% |
| repeat 2 | holds | 63.2% | 65.4% | 50.0% |
| repeat 3 | holds | 57.9% | 65.4% | 46.7% |
| repeat 4 | holds | 57.9% | 61.5% | 46.7% |

| scenario | alerts | unstable | flips / repetitions | flip rate |
|---|---|---|---|---|
| BACKGROUND | 1 | 0 | 0 / 5 | 0.0% |
| F-ALGO-1 | 1 | 0 | 0 / 5 | 0.0% |
| F-FAT-1 | 2 | 1 | 1 / 10 | 10.0% |
| F-ICE-1 | 1 | 0 | 0 / 5 | 0.0% |
| F-MM-1 | 1 | 0 | 0 / 5 | 0.0% |
| F-NEWS-1 | 4 | 1 | 1 / 20 | 5.0% |
| F-PARTIAL-1 | 1 | 0 | 0 / 5 | 0.0% |
| F-RISK-1 | 1 | 0 | 0 / 5 | 0.0% |
| F-SPOOFLIKE-HARD-1 | 1 | 0 | 0 / 5 | 0.0% |
| F-STOP-1 | 6 | 1 | 1 / 30 | 3.3% |
| S-LAYER-1 | 2 | 1 | 2 / 10 | 20.0% |
| S-SPOOF-1 | 1 | 0 | 0 / 5 | 0.0% |
| S-SPOOF-2 | 1 | 0 | 0 / 5 | 0.0% |
| S-SPOOF-3 | 1 | 0 | 0 / 5 | 0.0% |
| S-SPOOF-4 | 1 | 0 | 0 / 5 | 0.0% |
| S-SPOOF-5 | 1 | 0 | 0 / 5 | 0.0% |

## Unstable alerts

| alert | scenario | expected | sequence | confidence |
|---|---|---|---|---|
| A-261009-0007 | F-FAT-1 | CLOSE_FP | CLOSE_FP , ESCALATE , CLOSE_FP , CLOSE_FP , CLOSE_FP | 0.6 to 0.8 |
| A-261013-0003 | S-LAYER-1 | ESCALATE | ESCALATE , DRAFT_STOR , DRAFT_STOR , ESCALATE , DRAFT_STOR | 0.6 to 0.7 |
| A-261016-0005 | F-NEWS-1 | CLOSE_FP | ESCALATE , CLOSE_FP , CLOSE_FP , CLOSE_FP , CLOSE_FP | 0.55 to 0.6 |
| A-261026-0003 | F-STOP-1 | CLOSE_FP | ESCALATE , ESCALATE , CLOSE_FP , ESCALATE , ESCALATE | 0.6 to 0.6 |
