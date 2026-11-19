# Dataset run `20261118T1610-variance-v20`

- Dataset `seed7`, 110 alerts (35 TRUE_ABUSE, 75 FALSE_POSITIVE); backend `runtime`, model `eu.anthropic.claude-sonnet-5-5`, analyst `L1`, mode `investigate`, memory on, bundle none (code defaults), concurrency 2.
- Started 2026-11-18T16:10:17+00:00, finished 2026-11-18T16:38:10+00:00 (27.9 min).
- Notes: run-to-run variance on Runtime v20 with one analyst per worker: the 22 alerts of 20261116T1924-variance-v5, 22 x 5; the subset is enriched with F-STOP-1/F-NEWS-1/F-FAT-1 on purpose, so its safe close is not the full-set number

## Headline

| metric | value |
|---|---|
| gate | **holds** (0 TRUE_ABUSE proposed CLOSE_FP) |
| safe close rate | 70.7% (53 of 75 false positives closed) |
| escalation precision | 61.4% (57 ESCALATE/DRAFT_STOR) |
| strong-call precision | 100.0% (3 DRAFT_STOR) |
| agreement with label (exact disposition) | 72.7% |
| **override rate** (1 - agreement) | **27.3%** |
| direction agreement (close vs not-close) | 80.0% |
| proposals | {'CLOSE_FP': 53, 'ESCALATE': 54, 'DRAFT_STOR': 3} |
| run status | {'ok': 110} |
| configuration bundle reported by the agent | none |
| latency, agent p50 / p95 | 23.5 s / 29.4 s (wall p50 29.6 s) |
| tokens per alert, in / out (mean) | 11 / 3174 (max in 14) |
| prompt cache, per alert | read 46304 / write 14712 / full price 11 tokens; hit rate 0.759 of 61026 prompt tokens |
| tool calls per alert (mean / median) | 10.0 / 10.0 |
| estimated model cost | $8.56 total, $0.078 per alert (assumed $2.0/$10.0 per M tokens in/out; cache read 0.1x, write 1.25x of input; not verified against the pricing page) |

## Against the baselines (same alerts)

| scorer | gate | safe close rate | raw safe close | escalation precision | agreement | override rate |
|---|---|---|---|---|---|---|
| agent (this run) | holds | 70.7% | 70.7% | 61.4% | 72.7% | 27.3% |
| threshold baseline (detector rules) | 1 missed | n/a | 93.3% | 85.7% | 90.9% | 9.1% |
| escalate everything | holds | 0.0% | 0.0% | 31.8% | 27.3% | 72.7% |
| close everything (the gate at work) | 7 missed | n/a | 100.0% | n/a | 68.2% | 31.8% |

## Confusion: expected (rows) x proposed (columns)

| expected \ proposed | CLOSE_FP | ESCALATE | DRAFT_STOR | none |
|---|---|---|---|---|
| CLOSE_FP | 53 | 22 | 0 | 0 |
| ESCALATE | 0 | 27 | 3 | 0 |
| DRAFT_STOR | 0 | 5 | 0 | 0 |

## Per scenario

| scenario | truth | expected | n | CLOSE_FP | ESCALATE | DRAFT_STOR | none | agreement | mean conf | gate misses |
|---|---|---|---|---|---|---|---|---|---|---|
| S-LAYER-1 | TRUE_ABUSE | ESCALATE | 10 | 0 | 7 | 3 | 0 | 70% | 0.68 | - |
| S-SPOOF-1 | TRUE_ABUSE | ESCALATE | 5 | 0 | 5 | 0 | 0 | 100% | 0.72 | - |
| S-SPOOF-2 | TRUE_ABUSE | DRAFT_STOR | 5 | 0 | 5 | 0 | 0 | 0% | 0.7 | - |
| S-SPOOF-3 | TRUE_ABUSE | ESCALATE | 5 | 0 | 5 | 0 | 0 | 100% | 0.71 | - |
| S-SPOOF-4 | TRUE_ABUSE | ESCALATE | 5 | 0 | 5 | 0 | 0 | 100% | 0.72 | - |
| S-SPOOF-5 | TRUE_ABUSE | ESCALATE | 5 | 0 | 5 | 0 | 0 | 100% | 0.74 | - |
| BACKGROUND | FALSE_POSITIVE | CLOSE_FP | 5 | 5 | 0 | 0 | 0 | 100% | 0.89 | - |
| F-ALGO-1 | FALSE_POSITIVE | CLOSE_FP | 5 | 5 | 0 | 0 | 0 | 100% | 0.85 | - |
| F-FAT-1 | FALSE_POSITIVE | CLOSE_FP | 10 | 10 | 0 | 0 | 0 | 100% | 0.74 | - |
| F-ICE-1 | FALSE_POSITIVE | CLOSE_FP | 5 | 5 | 0 | 0 | 0 | 100% | 0.8 | - |
| F-MM-1 | FALSE_POSITIVE | CLOSE_FP | 5 | 5 | 0 | 0 | 0 | 100% | 0.9 | - |
| F-NEWS-1 | FALSE_POSITIVE | CLOSE_FP | 10 | 4 | 6 | 0 | 0 | 40% | 0.6 | - |
| F-PARTIAL-1 | FALSE_POSITIVE | CLOSE_FP | 5 | 5 | 0 | 0 | 0 | 100% | 0.71 | - |
| F-RISK-1 | FALSE_POSITIVE | CLOSE_FP | 5 | 5 | 0 | 0 | 0 | 100% | 0.66 | - |
| F-SPOOFLIKE-HARD-1 | FALSE_POSITIVE | CLOSE_FP | 5 | 5 | 0 | 0 | 0 | 100% | 0.82 | - |
| F-STOP-1 | FALSE_POSITIVE | CLOSE_FP | 20 | 4 | 16 | 0 | 0 | 20% | 0.6 | - |

## Disagreements with the label (30)

| alert | scenario | expected | proposed | conf | status | summary |
|---|---|---|---|---|---|---|
| A-261013-0003 | S-LAYER-1 | ESCALATE | DRAFT_STOR | 0.62 | ok | Five BUY limit orders of 4340 each (21700 gross, 8.7x average top-5 depth) were placed on five levels, 3 to 7 ticks below the ask, within 60 ms. About 2 s later |
| A-261013-0003 | S-LAYER-1 | ESCALATE | DRAFT_STOR | 0.6 | ok | PROP trader placed five BUY limit orders of 4,340 each (21,700 total, about 8.7x average depth) on five levels 3 to 7 ticks below the touch within 60 ms. About  |
| A-261022-0002 | S-LAYER-1 | ESCALATE | DRAFT_STOR | 0.6 | ok | PROP trader with no market-making registration stacked five SELL limits of 4,734 (23,670 gross, about 9.4x average top-5 depth) over four price levels (10006-10 |
| A-261015-0003 | S-SPOOF-2 | DRAFT_STOR | ESCALATE | 0.72 | ok | PROP trader placed a single one-sided SELL limit of 21443 (8.17x depth, 2 ticks from touch) at 11:04:43.303. It had no fills. 2.4s later the trader bought 1189  |
| A-261015-0003 | S-SPOOF-2 | DRAFT_STOR | ESCALATE | 0.7 | ok | PROP trader placed a one-sided SELL limit of 21443 (8.17x avg top-5 depth, 2 ticks from touch) at 11:04:43.303, then 2.4s later bought 1189 by market order, and |
| A-261015-0003 | S-SPOOF-2 | DRAFT_STOR | ESCALATE | 0.7 | ok | PROP trader with no registered MM obligations placed a one-sided SELL of 21443 (8.17x depth, 2 ticks from touch) at 11:04:43.303. Two seconds later the trader b |
| A-261015-0003 | S-SPOOF-2 | DRAFT_STOR | ESCALATE | 0.7 | ok | PROP trader (no registered MM on SYN.A) placed one SELL limit of 21443 (8.17x depth, 2 ticks from touch) at 11:04:43.303. 2.4s later he bought 1189 by market or |
| A-261015-0003 | S-SPOOF-2 | DRAFT_STOR | ESCALATE | 0.7 | ok | PROP trader T-X1015-02 placed one SELL limit of 21,443 (8.17x avg top-5 depth) 2 ticks from the touch, with nothing on the bid. 2.4s later they bought 1,189 by  |
| A-261015-0008 | F-NEWS-1 | CLOSE_FP | ESCALATE | 0.6 | ok | PROP trader placed two BUY 7215 LIMIT orders at 9996 (combined 14430 = 5.5x top-5 depth, 1.5 ticks from touch) at 15:12:52.998 and 15:12:55.998. No fills on the |
| A-261015-0008 | F-NEWS-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader placed two BUY 7,215 limit orders at 9996 (14,430 total, 5.5x depth, 1.5 ticks from touch) at 15:12:53 and 15:12:56. They had no fills. Roughly 28 s |
| A-261015-0008 | F-NEWS-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader placed two BUY 7215 LIMIT orders at 9996 (14430 total, 5.5x depth, 1.5 ticks from the touch) at 15:12:52 and 15:12:55, then sold 515 at 10001 at 15: |
| A-261015-0008 | F-NEWS-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader rested two identical one-sided BUY orders (2 x 7215 at 9996, 5.5x avg depth combined) for about 25-28s with no fills, sold 515 at 10001 while they r |
| A-261015-0008 | F-NEWS-1 | CLOSE_FP | ESCALATE | 0.6 | ok | PROP trader placed two BUY 7215 LIMIT orders at 9996 (about 2.75x depth each, 5.5x combined; 14430 total) at 15:12:52.998 and 15:12:55.998. About 25 s later the |
| A-261016-0005 | F-NEWS-1 | CLOSE_FP | ESCALATE | 0.6 | ok | PROP trader (no MM registration) rested two BUY LIMIT orders of 7,162 each at 9999 (14,324 combined, 5.76x depth, 1.5 ticks from the touch, ~14x typical size 50 |
| A-261022-0003 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | PROP trader bought 1333 by market order at 13:16:57, then placed three 4,800 BUY limits (14,400 total, 5.7x top-5 depth, 4-6 ticks below the touch) at 13:16:59- |
| A-261022-0003 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Three one-sided BUY limit orders of 4800 (14400 total, 5.7x top-5 depth) were placed 13:16:59-13:17:03 at 9995/9995/9994, about 6 ticks from the touch. The trad |
| A-261022-0003 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader bought 1333 by market order at 13:16:57, then stacked three one-sided BUY limits of 4800 (14400 total, 5.7x depth) at 9995/9995/9994, 5-6 ticks from |
| A-261022-0003 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | PROP trader bought 1333 at market (13:16:57), then placed three one-sided BUY limits of 4800 (14400 total, 5.7x depth, 5-6 ticks below touch) over 4s. At 13:17: |
| A-261026-0003 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | PROP trader (no MM registration) put three one-sided BUY limits of 4024 each (12072 total, 4.87x depth) at 9996/9995/9994, 6 ticks below the touch. About 14s la |
| A-261026-0003 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Three BUY limit orders of 4024 each (12072 total, 4.87x depth) were placed at 9996/9995/9994 and rested 6 ticks from the touch with no fills. They were all canc |
| A-261026-0003 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader (not a registered MM) placed three one-sided BUY limit orders of 4024 each (12072 total, 3 levels, 6 ticks from touch, 4.9x depth in aggregate) afte |
| A-261026-0003 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader (no MM registration) rested three BUY limits of 4,024 each (12,072 total, 4.87x depth) at 6, 5 and 4 ticks below the touch, with no fills. They sold |
| A-261026-0003 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader bought 1118 by market order at 12:36:13, then placed three one-sided BUY limits of 4024 each (12072 total, 4.87x depth) at 9996/9995/9994, 5-7 ticks |
| A-261027-0008 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | PROP trader (no MM registration) bought 1254 at market (13:50:44), then stacked three one-sided BUY limits of 4514 each (13,542 total, 5.4x depth) 4-6 ticks bel |
| A-261027-0008 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.65 | ok | Prop trader bought 1254 at market (10005), then placed three one-sided BUY limits of 4514 each (13542 total, about 5.4x depth, 6 ticks from the touch, two price |
| A-261027-0008 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader bought 1254 at market, then placed three 4514 BUY limits (13542 total, 5.4x depth, 2 levels, ~6 ticks from touch) over 4s, with no fills. 14s later  |
| A-261027-0008 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | PROP trader (no MM registration) bought 1254 by market at 10005 at 13:50:44, then stacked three one-sided bids of 4514 each (13542 total, 5.4x depth) 6 ticks of |
| A-261027-0008 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | PROP trader bought 1254 at market (10005), then rested three BUY limits of 4514 each (13542 total, 5.4x depth, 2 levels, 6 ticks off the touch) with no fills. A |
| A-261028-0011 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader bought 1476 by market order at 10005-10006, then placed three BUY limits (5313 each, 15939 total = 6.55x top-5 depth, 6 ticks below touch, 2 levels) |
| A-261028-0011 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | PROP trader bought 1476 by market order, then placed three one-sided LIMIT bids of 5313 each (15939 total, 6.5x top-5 depth, 6 ticks below the touch, 2 price le |

## Run-to-run variance

22 alerts, each investigated 5 times with nothing changed (110 investigations). An alert is *stable* when every repetition proposed the same disposition.

| measure | value |
|---|---|
| stable alerts | 17 of 22 (77.3%) |
| true-abuse alerts proposed CLOSE_FP in any repetition | **none** |
| safe close rate across the 5 pseudo-runs | 66.7% to 73.3% (mean 70.7%, sd 3.3 pts) |
| agreement with the label across pseudo-runs | 68.2% to 77.3% |

| pseudo-run | gate | safe close | agreement | escalation precision |
|---|---|---|---|---|
| repeat 0 | holds | 66.7% | 68.2% | 58.3% |
| repeat 1 | holds | 66.7% | 72.7% | 58.3% |
| repeat 2 | holds | 73.3% | 72.7% | 63.6% |
| repeat 3 | holds | 73.3% | 77.3% | 63.6% |
| repeat 4 | holds | 73.3% | 72.7% | 63.6% |

| scenario | alerts | unstable | flips / repetitions | flip rate |
|---|---|---|---|---|
| BACKGROUND | 1 | 0 | 0 / 5 | 0.0% |
| F-ALGO-1 | 1 | 0 | 0 / 5 | 0.0% |
| F-FAT-1 | 2 | 0 | 0 / 10 | 0.0% |
| F-ICE-1 | 1 | 0 | 0 / 5 | 0.0% |
| F-MM-1 | 1 | 0 | 0 / 5 | 0.0% |
| F-NEWS-1 | 2 | 1 | 1 / 10 | 10.0% |
| F-PARTIAL-1 | 1 | 0 | 0 / 5 | 0.0% |
| F-RISK-1 | 1 | 0 | 0 / 5 | 0.0% |
| F-SPOOFLIKE-HARD-1 | 1 | 0 | 0 / 5 | 0.0% |
| F-STOP-1 | 4 | 2 | 3 / 20 | 15.0% |
| S-LAYER-1 | 2 | 2 | 3 / 10 | 30.0% |
| S-SPOOF-1 | 1 | 0 | 0 / 5 | 0.0% |
| S-SPOOF-2 | 1 | 0 | 0 / 5 | 0.0% |
| S-SPOOF-3 | 1 | 0 | 0 / 5 | 0.0% |
| S-SPOOF-4 | 1 | 0 | 0 / 5 | 0.0% |
| S-SPOOF-5 | 1 | 0 | 0 / 5 | 0.0% |

## Unstable alerts

| alert | scenario | expected | sequence | confidence |
|---|---|---|---|---|
| A-261013-0003 | S-LAYER-1 | ESCALATE | DRAFT_STOR , ESCALATE , ESCALATE , ESCALATE , DRAFT_STOR | 0.6 to 0.72 |
| A-261016-0005 | F-NEWS-1 | CLOSE_FP | CLOSE_FP , ESCALATE , CLOSE_FP , CLOSE_FP , CLOSE_FP | 0.6 to 0.6 |
| A-261022-0002 | S-LAYER-1 | ESCALATE | ESCALATE , ESCALATE , DRAFT_STOR , ESCALATE , ESCALATE | 0.6 to 0.8 |
| A-261022-0003 | F-STOP-1 | CLOSE_FP | ESCALATE , ESCALATE , ESCALATE , ESCALATE , CLOSE_FP | 0.6 to 0.6 |
| A-261028-0011 | F-STOP-1 | CLOSE_FP | ESCALATE , CLOSE_FP , CLOSE_FP , CLOSE_FP , ESCALATE | 0.6 to 0.6 |
