# Dataset run `20261106T1126-sonnet-v3-nomem`

- Dataset `seed7`, 167 alerts (28 TRUE_ABUSE, 139 FALSE_POSITIVE); backend `runtime`, model `eu.anthropic.claude-sonnet-5-5`, analyst `L1`, mode `investigate`, memory OFF, bundle none (code defaults), concurrency 1.
- Started 2026-11-06T11:26:24+00:00, finished 2026-11-07T19:53:14+00:00 (1716.0 min).
- Notes: Memory OFF arm of v3 (data doc 4.5.1): recall_memory hidden from the agent, everything else identical to sonnet-v3, run concurrently with it

## Headline

| metric | value |
|---|---|
| gate | **holds** (0 TRUE_ABUSE proposed CLOSE_FP) |
| safe close rate | 92.8% (129 of 139 false positives closed) |
| escalation precision | 73.7% (38 ESCALATE/DRAFT_STOR) |
| strong-call precision | 100.0% (2 DRAFT_STOR) |
| agreement with label (exact disposition) | 92.2% |
| **override rate** (1 - agreement) | **7.8%** |
| direction agreement (close vs not-close) | 94.0% |
| proposals | {'CLOSE_FP': 129, 'ESCALATE': 36, 'DRAFT_STOR': 2} |
| run status | {'ok': 167} |
| alerts with a disposition recorded before this run (visible to the agent through history and Memory) | 3: A-261005-0003, A-261009-0003, A-261016-0003 |
| configuration bundle reported by the agent | none |
| latency, agent p50 / p95 | 24.0 s / 34.6 s (wall p50 29.8 s) |
| tokens per alert, in / out (mean) | 60052 / 3091 (max in 151561) |
| tool calls per alert (mean / median) | 9.2 / 9 |
| estimated model cost | $25.22 total, $0.151 per alert (assumed $2.0/$10.0 per M tokens in/out; not verified against the pricing page) |

## Against the baselines (same alerts)

| scorer | gate | safe close rate | raw safe close | escalation precision | agreement | override rate |
|---|---|---|---|---|---|---|
| agent (this run) | holds | 92.8% | 92.8% | 73.7% | 92.2% | 7.8% |
| threshold baseline (detector rules) | 6 missed | n/a | 95.7% | 78.6% | 92.8% | 7.2% |
| escalate everything | holds | 0.0% | 0.0% | 16.8% | 15.0% | 85.0% |
| close everything (the gate at work) | 28 missed | n/a | 100.0% | n/a | 83.2% | 16.8% |

## Confusion: expected (rows) x proposed (columns)

| expected \ proposed | CLOSE_FP | ESCALATE | DRAFT_STOR | none |
|---|---|---|---|---|
| CLOSE_FP | 129 | 10 | 0 | 0 |
| ESCALATE | 0 | 24 | 1 | 0 |
| DRAFT_STOR | 0 | 2 | 1 | 0 |

## Per scenario

| scenario | truth | expected | n | CLOSE_FP | ESCALATE | DRAFT_STOR | none | agreement | mean conf | gate misses |
|---|---|---|---|---|---|---|---|---|---|---|
| S-LAYER-1 | TRUE_ABUSE | ESCALATE | 5 | 0 | 4 | 1 | 0 | 80% | 0.69 | - |
| S-SPOOF-1 | TRUE_ABUSE | ESCALATE | 7 | 0 | 7 | 0 | 0 | 100% | 0.7 | - |
| S-SPOOF-2 | TRUE_ABUSE | DRAFT_STOR | 3 | 0 | 2 | 1 | 0 | 33% | 0.72 | - |
| S-SPOOF-3 | TRUE_ABUSE | ESCALATE | 4 | 0 | 4 | 0 | 0 | 100% | 0.71 | - |
| S-SPOOF-4 | TRUE_ABUSE | ESCALATE | 2 | 0 | 2 | 0 | 0 | 100% | 0.71 | - |
| S-SPOOF-5 | TRUE_ABUSE | ESCALATE | 7 | 0 | 7 | 0 | 0 | 100% | 0.71 | - |
| BACKGROUND | FALSE_POSITIVE | CLOSE_FP | 52 | 52 | 0 | 0 | 0 | 100% | 0.89 | - |
| F-ALGO-1 | FALSE_POSITIVE | CLOSE_FP | 24 | 24 | 0 | 0 | 0 | 100% | 0.84 | - |
| F-FAT-1 | FALSE_POSITIVE | CLOSE_FP | 3 | 2 | 1 | 0 | 0 | 67% | 0.68 | - |
| F-ICE-1 | FALSE_POSITIVE | CLOSE_FP | 9 | 9 | 0 | 0 | 0 | 100% | 0.81 | - |
| F-MM-1 | FALSE_POSITIVE | CLOSE_FP | 24 | 24 | 0 | 0 | 0 | 100% | 0.89 | - |
| F-NEWS-1 | FALSE_POSITIVE | CLOSE_FP | 4 | 1 | 3 | 0 | 0 | 25% | 0.63 | - |
| F-PARTIAL-1 | FALSE_POSITIVE | CLOSE_FP | 8 | 8 | 0 | 0 | 0 | 100% | 0.75 | - |
| F-RISK-1 | FALSE_POSITIVE | CLOSE_FP | 3 | 3 | 0 | 0 | 0 | 100% | 0.62 | - |
| F-SPOOFLIKE-HARD-1 | FALSE_POSITIVE | CLOSE_FP | 6 | 6 | 0 | 0 | 0 | 100% | 0.78 | - |
| F-STOP-1 | FALSE_POSITIVE | CLOSE_FP | 6 | 0 | 6 | 0 | 0 | 0% | 0.62 | - |

## Regression against the previous run

Previous run: `20261106T0906-sonnet-v2`. Verdict: **PASS (offline promotion rule, faithfulness pending)**.

- [x] gate holds
- [x] safe close rate not down by more than 2 points
- [x] no false-positive scenario regressed to 0% close (none; within noise: F-STOP-1 (1/6 -> 0/6, below the floor))

| delta | value |
|---|---|
| raw_safe_close_rate | +4.3 pts |
| agreement | +3.6 pts |
| escalation_precision | +10.1 pts |
| direction_agreement | +3.6 pts |
| true_abuse_recall | +0.0 pts |
| gate misses | +0 |

| scenario | agreement delta | close-rate delta |
|---|---|---|
| F-STOP-1 | -17 pts | -17 pts |
| BACKGROUND | +8 pts | +8 pts |
| F-ALGO-1 | +12 pts | +12 pts |

## Disagreements with the label (13)

| alert | scenario | expected | proposed | conf | status | summary |
|---|---|---|---|---|---|---|
| A-261013-0003 | S-LAYER-1 | ESCALATE | DRAFT_STOR | 0.65 | ok | PROP trader placed five BUY limit orders of 4,340 each (21,700 total, 8.7x avg top-5 depth) on five levels 1-5 ticks below the bid, then sold 799 at market at t |
| A-261015-0003 | S-SPOOF-2 | DRAFT_STOR | ESCALATE | 0.7 | ok | Prop trader placed one SELL LIMIT of 21443 (8.17x avg top-5 depth) at 10000, 2 ticks from the touch, with no same-side fills. 2.4s later a BUY market order of 1 |
| A-261016-0006 | S-SPOOF-2 | DRAFT_STOR | ESCALATE | 0.7 | ok | PROP trader placed a single one-sided BUY LIMIT of 21860 (8.8x avg top-5 depth) 3 ticks below the touch. About 2.1s later a SELL MARKET of 1329 executed while t |
| A-261009-0007 | F-FAT-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader T-X1009-05 placed one BUY LIMIT of 18930 on SYN.A at 9997 (7.9x avg top-5 depth, 1 tick behind the touch) and cancelled it 803 ms later with no fill |
| A-261015-0008 | F-NEWS-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader T-X1015-07 rested two BUY LIMIT orders of 7215 each (14430 total, 5.5x avg top-5 depth) at 9996, 1.5 ticks from the touch. The trader sold 515 at 10 |
| A-261016-0003 | F-NEWS-1 | CLOSE_FP | ESCALATE | 0.72 | ok | PROP trader placed two BUY LIMIT orders of 6680 each at 9997 (13360 total, 5.37x avg top-5 depth, 1.5 ticks from touch, one side only). While they rested, the t |
| A-261016-0005 | F-NEWS-1 | CLOSE_FP | ESCALATE | 0.6 | ok | PROP trader placed two one-sided BUY limits of 7162 each (14324 total, ~5.8x avg top-5 depth) at 9999, 1.5 ticks from the touch, about 25-28s before cancelling  |
| A-261005-0007 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.65 | ok | PROP trader placed three one-sided BUY limit orders of 4077 each (12231 total, 5.04x top-5 depth, 6 ticks from touch) at 13:20:39-43, then sold 961 at market at |
| A-261006-0005 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.65 | ok | PROP trader placed three BUY limit layers of 3810 each (11430 total, 4.66x top-5 depth, 6 ticks from touch) at 9994/9993/9992, none filled, then sold 1058 at ma |
| A-261022-0003 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | PROP trader with no MM registration placed three one-sided BUY limits (3x4800 = 14400, up to 5.72x top-5 depth, 6 ticks from touch) between 13:16:59 and 13:17:0 |
| A-261026-0003 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader (no MM registration) bought 1118 at market (12:36:13), then rested three BUY limits of 4024 each (12072 total, 4.87x top-5 depth) at 9996/9995/9994, |
| A-261027-0008 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.62 | ok | Prop trader placed three one-sided BUY limits (3 x 4514 = 13542, up to 5.4x avg top-5 depth, ~6 ticks from touch) between 13:50:46 and 13:50:50, then sold 700 a |
| A-261028-0011 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | Prop trader bought 1476 by market order at 10005-10006, then placed three one-sided BUY limits of 5313 each (15939 total, 6.5x top-5 depth, 6 ticks from touch,  |
