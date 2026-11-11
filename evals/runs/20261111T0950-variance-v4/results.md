# Dataset run `20261111T0950-variance-v4`

- Dataset `seed7`, 105 alerts (35 TRUE_ABUSE, 70 FALSE_POSITIVE); backend `runtime`, model `eu.anthropic.claude-sonnet-5-5`, analyst `L1`, mode `investigate`, memory on, bundle none (code defaults), concurrency 2.
- Started 2026-11-11T09:50:46+00:00, finished 2026-11-11T10:24:38+00:00 (33.9 min).
- Notes: run-to-run variance on the promoted configuration (Runtime v15 = v14 code): 21 alerts x 5, one per scenario plus the alerts that moved between v3, v4 and the iteration-3 slice; the subset is enriched with F-STOP-1/F-NEWS-1/F-FAT-1 on purpose, so its safe close is not the full-set number

## Headline

| metric | value |
|---|---|
| gate | **holds** (0 TRUE_ABUSE proposed CLOSE_FP) |
| safe close rate | 67.1% (47 of 70 false positives closed) |
| escalation precision | 60.3% (58 ESCALATE/DRAFT_STOR) |
| strong-call precision | 100.0% (3 DRAFT_STOR) |
| agreement with label (exact disposition) | 70.5% |
| **override rate** (1 - agreement) | **29.5%** |
| direction agreement (close vs not-close) | 78.1% |
| proposals | {'CLOSE_FP': 47, 'ESCALATE': 55, 'DRAFT_STOR': 3} |
| run status | {'ok': 105} |
| alerts with a disposition recorded before this run (visible to the agent through history and Memory) | 5: A-261009-0003, A-261009-0003, A-261009-0003, A-261009-0003, A-261009-0003 |
| configuration bundle reported by the agent | none |
| latency, agent p50 / p95 | 28.0 s / 36.0 s (wall p50 33.5 s) |
| tokens per alert, in / out (mean) | 12 / 3289 (max in 14) |
| prompt cache, per alert | read 45055 / write 13461 / full price 12 tokens; hit rate 0.77 of 58528 prompt tokens |
| tool calls per alert (mean / median) | 10.0 / 10 |
| estimated model cost | $7.94 total, $0.076 per alert (assumed $2.0/$10.0 per M tokens in/out; cache read 0.1x, write 1.25x of input; not verified against the pricing page) |

## Against the baselines (same alerts)

| scorer | gate | safe close rate | raw safe close | escalation precision | agreement | override rate |
|---|---|---|---|---|---|---|
| agent (this run) | holds | 67.1% | 67.1% | 60.3% | 70.5% | 29.5% |
| threshold baseline (detector rules) | 1 missed | n/a | 92.9% | 85.7% | 90.5% | 9.5% |
| escalate everything | holds | 0.0% | 0.0% | 33.3% | 28.6% | 71.4% |
| close everything (the gate at work) | 7 missed | n/a | 100.0% | n/a | 66.7% | 33.3% |

## Confusion: expected (rows) x proposed (columns)

| expected \ proposed | CLOSE_FP | ESCALATE | DRAFT_STOR | none |
|---|---|---|---|---|
| CLOSE_FP | 47 | 23 | 0 | 0 |
| ESCALATE | 0 | 27 | 3 | 0 |
| DRAFT_STOR | 0 | 5 | 0 | 0 |

## Per scenario

| scenario | truth | expected | n | CLOSE_FP | ESCALATE | DRAFT_STOR | none | agreement | mean conf | gate misses |
|---|---|---|---|---|---|---|---|---|---|---|
| S-LAYER-1 | TRUE_ABUSE | ESCALATE | 10 | 0 | 7 | 3 | 0 | 70% | 0.65 | - |
| S-SPOOF-1 | TRUE_ABUSE | ESCALATE | 5 | 0 | 5 | 0 | 0 | 100% | 0.71 | - |
| S-SPOOF-2 | TRUE_ABUSE | DRAFT_STOR | 5 | 0 | 5 | 0 | 0 | 0% | 0.7 | - |
| S-SPOOF-3 | TRUE_ABUSE | ESCALATE | 5 | 0 | 5 | 0 | 0 | 100% | 0.7 | - |
| S-SPOOF-4 | TRUE_ABUSE | ESCALATE | 5 | 0 | 5 | 0 | 0 | 100% | 0.68 | - |
| S-SPOOF-5 | TRUE_ABUSE | ESCALATE | 5 | 0 | 5 | 0 | 0 | 100% | 0.71 | - |
| BACKGROUND | FALSE_POSITIVE | CLOSE_FP | 5 | 5 | 0 | 0 | 0 | 100% | 0.89 | - |
| F-ALGO-1 | FALSE_POSITIVE | CLOSE_FP | 5 | 5 | 0 | 0 | 0 | 100% | 0.85 | - |
| F-FAT-1 | FALSE_POSITIVE | CLOSE_FP | 10 | 9 | 1 | 0 | 0 | 90% | 0.7 | - |
| F-ICE-1 | FALSE_POSITIVE | CLOSE_FP | 5 | 5 | 0 | 0 | 0 | 100% | 0.76 | - |
| F-MM-1 | FALSE_POSITIVE | CLOSE_FP | 5 | 5 | 0 | 0 | 0 | 100% | 0.91 | - |
| F-NEWS-1 | FALSE_POSITIVE | CLOSE_FP | 10 | 3 | 7 | 0 | 0 | 30% | 0.62 | - |
| F-PARTIAL-1 | FALSE_POSITIVE | CLOSE_FP | 5 | 5 | 0 | 0 | 0 | 100% | 0.7 | - |
| F-RISK-1 | FALSE_POSITIVE | CLOSE_FP | 5 | 5 | 0 | 0 | 0 | 100% | 0.65 | - |
| F-SPOOFLIKE-HARD-1 | FALSE_POSITIVE | CLOSE_FP | 5 | 5 | 0 | 0 | 0 | 100% | 0.84 | - |
| F-STOP-1 | FALSE_POSITIVE | CLOSE_FP | 15 | 0 | 15 | 0 | 0 | 0% | 0.61 | - |

## Disagreements with the label (31)

| alert | scenario | expected | proposed | conf | status | summary |
|---|---|---|---|---|---|---|
| A-261013-0003 | S-LAYER-1 | ESCALATE | DRAFT_STOR | 0.6 | ok | Prop trader (no MM registration) placed five BUY limit orders of 4,340 each (21,700 total, 8.69x avg top-5 depth) on consecutive bid levels 3+ ticks below the t |
| A-261013-0003 | S-LAYER-1 | ESCALATE | DRAFT_STOR | 0.6 | ok | Prop trader placed five BUY limit orders of 4340 each (21700 total, 8.69x avg top-5 depth) on five levels 9988-9992 within ~60 ms, 1-5 ticks below the 9993 bid. |
| A-261013-0003 | S-LAYER-1 | ESCALATE | DRAFT_STOR | 0.6 | ok | PROP-EQ trader (no MM registration) placed five BUY limits at 9988-9992 (4340 each, 21700 total, 8.7x top-5 depth) within ~60 ms, 1-5 ticks below the touch. Abo |
| A-261015-0003 | S-SPOOF-2 | DRAFT_STOR | ESCALATE | 0.7 | ok | PROP trader T-X1015-02 (no registered MM on SYN.A) placed one SELL limit of 21443 (8.17x avg top-5 depth) at 10000, 2 ticks from the touch. About 2.4s later the |
| A-261015-0003 | S-SPOOF-2 | DRAFT_STOR | ESCALATE | 0.7 | ok | PROP trader placed a single one-sided SELL limit of 21443 (8.2x avg top-5 depth, 2 ticks from touch) at 11:04:43.303, bought 1189 by market order at 11:04:45.73 |
| A-261015-0003 | S-SPOOF-2 | DRAFT_STOR | ESCALATE | 0.7 | ok | Prop trader (no MM registration) placed a single one-sided SELL of 21443 (8.17x avg top-5 depth) 2 ticks from the touch, then 2.4s later bought 1189 by market o |
| A-261015-0003 | S-SPOOF-2 | DRAFT_STOR | ESCALATE | 0.7 | ok | PROP trader placed a single one-sided SELL limit of 21443 (8.17x avg top-5 depth, 2 ticks from touch) at 11:04:43.303, bought 1189 by market order at 11:04:45.7 |
| A-261015-0003 | S-SPOOF-2 | DRAFT_STOR | ESCALATE | 0.7 | ok | PROP trader placed a single one-sided SELL of 21443 (8.17x avg top-5 depth) 2 ticks above the touch at 11:04:43.303, bought 1189 by market order at 11:04:45.731 |
| A-261009-0007 | F-FAT-1 | CLOSE_FP | ESCALATE | 0.6 | ok | PROP-EQ trader (not a registered MM) placed a one-sided BUY of 18930 (7.9x top-5 depth) at 9997, 1 tick behind the bid, and cancelled it after about 0.8s with n |
| A-261015-0008 | F-NEWS-1 | CLOSE_FP | ESCALATE | 0.65 | ok | PROP-EQ trader (not a registered MM) rested two BUY LIMIT orders of 7,215 each at 9996 (5.5x avg top-5 depth, one side only, no fills) from 15:12:52 and 15:12:5 |
| A-261015-0008 | F-NEWS-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader (no MM registration) rested two identical one-sided BUY limits of 7,215 each (peak 5.5x top-5 depth, 1.5 ticks from touch) for about 28 s. A 515 SEL |
| A-261015-0008 | F-NEWS-1 | CLOSE_FP | ESCALATE | 0.65 | ok | Prop trader T-X1015-07 rested two BUY LIMIT orders of 7,215 each (14,430 total, 5.5x average top-5 depth) at 9996, 1.5 ticks from the touch. The bid rose 1.5 ti |
| A-261015-0008 | F-NEWS-1 | CLOSE_FP | ESCALATE | 0.65 | ok | PROP trader placed two BUY LIMIT orders of 7,215 each (14,430 total, 5.5x avg top-5 depth) at 9996, 1.5 ticks from the touch. They rested about 25-30s with no f |
| A-261015-0008 | F-NEWS-1 | CLOSE_FP | ESCALATE | 0.68 | ok | PROP trader T-X1015-07 rested two identical one-sided BUY orders (7215 each, 14430 total, 5.5x average top-5 depth) at 9996 for about 30s. Meanwhile the bid ros |
| A-261016-0005 | F-NEWS-1 | CLOSE_FP | ESCALATE | 0.6 | ok | PROP trader placed two BUY LIMIT orders of 7,162 each at 9999 (about 5.76x avg top-5 depth, 1.5 ticks from the touch), one-sided, no fills on them. A 511 SELL f |
| A-261016-0005 | F-NEWS-1 | CLOSE_FP | ESCALATE | 0.6 | ok | PROP trader (no MM registration) rested two BUY LIMITs of 7162 at 9999 (14324 total, 5.76x top-5 depth, 1.5 ticks from touch) for ~27-30s, sold 511 at 10001 at  |
| A-261026-0003 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | PROP trader with no MM registration bought 1118 at market (12:36:13), then placed three 4024-lot BUY limits at 9996/9995/9994 (6 ticks from the touch, 4.87x top |
| A-261026-0003 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader bought 1118 by market order at 12:36:13 (lifting the ask from 10003 to 10007), then placed three one-sided BUY limits of 4024 each at 9996/9995/9994 |
| A-261026-0003 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader bought 1118 at market (sweeping asks 10003-10007), then placed three one-sided BUY limits of 4024 each at 9996/9995/9994 (6 ticks from touch, up to  |
| A-261026-0003 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.7 | ok | PROP trader with no MM registration placed three one-sided BUY limits of 4,024 each (12,072 total, up to 4.87x top-5 depth, 6 ticks from touch) at 9996/9995/999 |
| A-261026-0003 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.65 | ok | PROP trader bought 1118 at market (sweeping 10003 to 10007), then placed three one-sided BUY limits of 4024 each at 9996/9995/9994 (6 ticks from touch, max 4.87 |
| A-261027-0008 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader T-X1027-05 (not a registered MM on SYN.A) bought 1254 by market order at 10005 at 13:50:44, then stacked three one-sided BUY limits of 4514 each (13 |
| A-261027-0008 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | PROP trader (no MM registration) bought 1254 at market (10005), then placed three one-sided BUY limits of 4514 each (13542 gross, 5.4x top-5 depth, 6 ticks from |
| A-261027-0008 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | PROP trader bought 1254 at market (10005), then placed three one-sided LIMIT bids of 4514 (13542 total, 5.4x top-5 depth, 6 ticks from touch) over 13:50:46-50,  |
| A-261027-0008 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | PROP trader with no registered market making placed three one-sided BUY limit orders of 4514 each (13542 total, 5.4x average top-5 depth) 6 ticks from the touch |
| A-261027-0008 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | PROP trader with no registered MM on SYN.A placed three one-sided BUY limits of 4,514 each (13,542 total, 5.4x avg top-5 depth) 4-6 ticks below the touch, never |
| A-261028-0011 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.65 | ok | PROP trader, not a registered MM, bought 1476 at market (16:57:25), then placed three one-sided BUY limits of 5313 each (15939 total, 6.5x top-5 depth, 6 ticks  |
| A-261028-0011 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | PROP trader (no MM registration) placed three one-sided BUY limits of 5313 each (15939 total, 6.5x top-5 depth) 5-6 ticks below the touch, with no fills. About  |
| A-261028-0011 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.62 | ok | PROP trader (not a registered MM on SYN.A) rested three one-sided BUY limits of 5,313 each (15,939 total, 6.5x avg top-5 depth) 5-6 ticks below the touch. About |
| A-261028-0011 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | PROP trader bought 1476 by market order, then placed three one-sided BUY limits of 5313 (about 6.5x top-5 depth, 6 ticks from the touch) over 4 s, sold 1476 at  |
| A-261028-0011 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | PROP trader (no MM registration) rested three one-sided BUY limits of 5313 each (15939 total, 6.5x top-5 depth, 6 ticks below touch) and cancelled all 600 ms af |

## Run-to-run variance

21 alerts, each investigated 5 times with nothing changed (105 investigations). An alert is *stable* when every repetition proposed the same disposition.

| measure | value |
|---|---|
| stable alerts | 18 of 21 (85.7%) |
| true-abuse alerts proposed CLOSE_FP in any repetition | **none** |
| safe close rate across the 5 pseudo-runs | 57.1% to 71.4% (mean 67.1%, sd 5.7 pts) |
| agreement with the label across pseudo-runs | 61.9% to 76.2% |

| pseudo-run | gate | safe close | agreement | escalation precision |
|---|---|---|---|---|
| repeat 0 | holds | 71.4% | 71.4% | 63.6% |
| repeat 1 | holds | 64.3% | 71.4% | 58.3% |
| repeat 2 | holds | 57.1% | 61.9% | 53.8% |
| repeat 3 | holds | 71.4% | 76.2% | 63.6% |
| repeat 4 | holds | 71.4% | 71.4% | 63.6% |

| scenario | alerts | unstable | flips / repetitions | flip rate |
|---|---|---|---|---|
| BACKGROUND | 1 | 0 | 0 / 5 | 0.0% |
| F-ALGO-1 | 1 | 0 | 0 / 5 | 0.0% |
| F-FAT-1 | 2 | 1 | 1 / 10 | 10.0% |
| F-ICE-1 | 1 | 0 | 0 / 5 | 0.0% |
| F-MM-1 | 1 | 0 | 0 / 5 | 0.0% |
| F-NEWS-1 | 2 | 1 | 2 / 10 | 20.0% |
| F-PARTIAL-1 | 1 | 0 | 0 / 5 | 0.0% |
| F-RISK-1 | 1 | 0 | 0 / 5 | 0.0% |
| F-SPOOFLIKE-HARD-1 | 1 | 0 | 0 / 5 | 0.0% |
| F-STOP-1 | 3 | 0 | 0 / 15 | 0.0% |
| S-LAYER-1 | 2 | 1 | 2 / 10 | 20.0% |
| S-SPOOF-1 | 1 | 0 | 0 / 5 | 0.0% |
| S-SPOOF-2 | 1 | 0 | 0 / 5 | 0.0% |
| S-SPOOF-3 | 1 | 0 | 0 / 5 | 0.0% |
| S-SPOOF-4 | 1 | 0 | 0 / 5 | 0.0% |
| S-SPOOF-5 | 1 | 0 | 0 / 5 | 0.0% |

## Unstable alerts

| alert | scenario | expected | sequence | confidence |
|---|---|---|---|---|
| A-261009-0007 | F-FAT-1 | CLOSE_FP | CLOSE_FP , CLOSE_FP , ESCALATE , CLOSE_FP , CLOSE_FP | 0.6 to 0.8 |
| A-261013-0003 | S-LAYER-1 | ESCALATE | DRAFT_STOR , ESCALATE , DRAFT_STOR , ESCALATE , DRAFT_STOR | 0.6 to 0.72 |
| A-261016-0005 | F-NEWS-1 | CLOSE_FP | CLOSE_FP , ESCALATE , ESCALATE , CLOSE_FP , CLOSE_FP | 0.6 to 0.6 |
