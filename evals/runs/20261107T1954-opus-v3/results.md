# Dataset run `20261107T1954-opus-v3`

- Dataset `seed7`, 167 alerts (28 TRUE_ABUSE, 139 FALSE_POSITIVE); backend `runtime`, model `eu.anthropic.claude-opus-5-5`, analyst `L1`, mode `investigate`, memory on, bundle opus (surv_opus-Pm3GdiCh5N:5305b644-4586-41ea-8ad0-0336862c4f5f), concurrency 2.
- Started 2026-11-07T19:54:49+00:00, finished 2026-11-08T11:44:30+00:00 (111.8 min).
- Notes: model-comparison arm (data doc 4.3): bundle surv_opus = the same prompt, eu.anthropic.claude-opus-5-5, effort medium; iteration-2 procedures, Memory on, ENFORCE, l1.analyst

## Headline

| metric | value |
|---|---|
| gate | **holds** (0 TRUE_ABUSE proposed CLOSE_FP) |
| safe close rate | 94.2% (131 of 139 false positives closed) |
| escalation precision | 77.8% (36 ESCALATE/DRAFT_STOR) |
| strong-call precision | 100.0% (2 DRAFT_STOR) |
| agreement with label (exact disposition) | 93.4% |
| **override rate** (1 - agreement) | **6.6%** |
| direction agreement (close vs not-close) | 95.2% |
| proposals | {'CLOSE_FP': 131, 'ESCALATE': 34, 'DRAFT_STOR': 2} |
| run status | {'ok': 167} |
| alerts with a disposition recorded before this run (visible to the agent through history and Memory) | 3: A-261005-0003, A-261009-0003, A-261016-0003 |
| configuration bundle reported by the agent | surv_opus-Pm3GdiCh5N:5305b644-4586-41ea-8ad0-0336862c4f5f |
| latency, agent p50 / p95 | 51.4 s / 63.5 s (wall p50 57.0 s) |
| tokens per alert, in / out (mean) | 147343 / 4355 (max in 309728) |
| tool calls per alert (mean / median) | 10.1 / 10 |
| estimated model cost | $112.97 total, $0.676 per alert (assumed $4.0/$20.0 per M tokens in/out; not verified against the pricing page) |

## Against the baselines (same alerts)

| scorer | gate | safe close rate | raw safe close | escalation precision | agreement | override rate |
|---|---|---|---|---|---|---|
| agent (this run) | holds | 94.2% | 94.2% | 77.8% | 93.4% | 6.6% |
| threshold baseline (detector rules) | 6 missed | n/a | 95.7% | 78.6% | 92.8% | 7.2% |
| escalate everything | holds | 0.0% | 0.0% | 16.8% | 15.0% | 85.0% |
| close everything (the gate at work) | 28 missed | n/a | 100.0% | n/a | 83.2% | 16.8% |

## Confusion: expected (rows) x proposed (columns)

| expected \ proposed | CLOSE_FP | ESCALATE | DRAFT_STOR | none |
|---|---|---|---|---|
| CLOSE_FP | 131 | 8 | 0 | 0 |
| ESCALATE | 0 | 24 | 1 | 0 |
| DRAFT_STOR | 0 | 2 | 1 | 0 |

## Per scenario

| scenario | truth | expected | n | CLOSE_FP | ESCALATE | DRAFT_STOR | none | agreement | mean conf | gate misses |
|---|---|---|---|---|---|---|---|---|---|---|
| S-LAYER-1 | TRUE_ABUSE | ESCALATE | 5 | 0 | 4 | 1 | 0 | 80% | 0.74 | - |
| S-SPOOF-1 | TRUE_ABUSE | ESCALATE | 7 | 0 | 7 | 0 | 0 | 100% | 0.78 | - |
| S-SPOOF-2 | TRUE_ABUSE | DRAFT_STOR | 3 | 0 | 2 | 1 | 0 | 33% | 0.74 | - |
| S-SPOOF-3 | TRUE_ABUSE | ESCALATE | 4 | 0 | 4 | 0 | 0 | 100% | 0.78 | - |
| S-SPOOF-4 | TRUE_ABUSE | ESCALATE | 2 | 0 | 2 | 0 | 0 | 100% | 0.78 | - |
| S-SPOOF-5 | TRUE_ABUSE | ESCALATE | 7 | 0 | 7 | 0 | 0 | 100% | 0.79 | - |
| BACKGROUND | FALSE_POSITIVE | CLOSE_FP | 52 | 52 | 0 | 0 | 0 | 100% | 0.87 | - |
| F-ALGO-1 | FALSE_POSITIVE | CLOSE_FP | 24 | 24 | 0 | 0 | 0 | 100% | 0.86 | - |
| F-FAT-1 | FALSE_POSITIVE | CLOSE_FP | 3 | 3 | 0 | 0 | 0 | 100% | 0.84 | - |
| F-ICE-1 | FALSE_POSITIVE | CLOSE_FP | 9 | 9 | 0 | 0 | 0 | 100% | 0.85 | - |
| F-MM-1 | FALSE_POSITIVE | CLOSE_FP | 24 | 24 | 0 | 0 | 0 | 100% | 0.88 | - |
| F-NEWS-1 | FALSE_POSITIVE | CLOSE_FP | 4 | 1 | 3 | 0 | 0 | 25% | 0.66 | - |
| F-PARTIAL-1 | FALSE_POSITIVE | CLOSE_FP | 8 | 8 | 0 | 0 | 0 | 100% | 0.78 | - |
| F-RISK-1 | FALSE_POSITIVE | CLOSE_FP | 3 | 2 | 1 | 0 | 0 | 67% | 0.67 | - |
| F-SPOOFLIKE-HARD-1 | FALSE_POSITIVE | CLOSE_FP | 6 | 6 | 0 | 0 | 0 | 100% | 0.79 | - |
| F-STOP-1 | FALSE_POSITIVE | CLOSE_FP | 6 | 2 | 4 | 0 | 0 | 33% | 0.66 | - |

## Regression against the previous run

Previous run: `20261106T1126-sonnet-v3`. Verdict: **PASS (offline promotion rule)**.

- [x] gate holds
- [x] safe close rate not down by more than 2 points
- [x] no false-positive scenario regressed to 0% close (none)

| delta | value |
|---|---|
| raw_safe_close_rate | +0.7 pts |
| agreement | +0.0 pts |
| escalation_precision | +2.1 pts |
| direction_agreement | +0.6 pts |
| true_abuse_recall | +0.0 pts |
| gate misses | +0 |

| scenario | agreement delta | close-rate delta |
|---|---|---|
| F-RISK-1 | -33 pts | -33 pts |
| F-NEWS-1 | -25 pts | -25 pts |
| S-LAYER-1 | -20 pts | +0 pts |
| F-FAT-1 | +33 pts | +33 pts |
| F-STOP-1 | +33 pts | +33 pts |

## Evidence faithfulness

167 reports checked against their sessions' tool results (`evals/faithfulness.py`): **93.4% of reports** have every number grounded; 9084 of 9095 numbers matched (99.9%).

| alert | scenario | proposed | source | unmatched | fact |
|---|---|---|---|---|---|
| A-261005-0001 | F-MM-1 | CLOSE_FP | get_order_events | -489 | Every cycle is a paired BUY and SELL NEW of 2092 one tick apart (e.g. BUY 9993 / SELL 9994 at 09:59:19.487-489), both cancelled at the same timestamp (e.g. 09:59:21.728) and re-posted within ~15ms; the quote pair moved t |
| A-261005-0009 | F-ICE-1 | CLOSE_FP | get_order_events | 816,816,404,816,816,518,816,816 | O-00030261 NEW BUY 21768 at 10002, order_type ICEBERG, parent C-T-X1005-05-A at 15:08:53.881; nine PARTIAL_FILLs (816,816,404,816,816,518,816,816,17) between 15:08:57.881 and 15:09:09.881 left 15933 remaining |
| A-261015-0005 | F-MM-1 | CLOSE_FP | get_order_events | -126 | 174 events, all LIMIT; every cycle is a BUY and SELL of 3808 placed within ms of each other one tick apart (e.g. BUY 9994 / SELL 9995 at 12:49:59.125-126), both cancelled at the same timestamp and immediately re-quoted;  |
| A-261015-0008 | F-NEWS-1 | ESCALATE | get_market_events | 142 | NEWS 15:13:22.998 SYN.A 'issuer announces unscheduled trading update' (62.5 s after window start), i.e. after the 15:13:20.498 sale and about 142 ms before the 15:13:23.140 cancel. |
| A-261016-0003 | F-NEWS-1 | ESCALATE | get_market_events | 187 | NEWS 12:02:12.731 SYN.A 'issuer announces unscheduled trading update', i.e. 2.5 s after the sale fill and 187 ms before the cancels |
| A-261021-0001 | BACKGROUND | CLOSE_FP | get_market_events | 21.4 | Only event: SYN.A OPEN at 09:00:00.000, 21.4s before window start. |
| A-261021-0007 | F-MM-1 | CLOSE_FP | compute_discriminators | 0.0005 | price_move_ticks 0.0; reversion_ticks 0.0; post_cancel_move_ticks 1.5; round_trip_ticks -0.42; opposite_side_fill_qty 3213; same_side_fill_qty 62 (all after the opposite trade, share 0.0005) |
| A-261023-0001 | F-NEWS-1 | CLOSE_FP | get_market_events | 148 | NEWS on SYN.A at 09:38:30.051: 'issuer announces unscheduled trading update'. That is 148 ms before the 09:38:30.199 cancels and about 3 s after the 09:38:27 sale |
| A-261023-0010 | S-LAYER-1 | ESCALATE | get_order_events | 575 | SELL MARKET O-00038932 qty 1334 at 16:41:32.389 (best bid 10000) filled 331 @10000, 575 @9999, 428 @9998. |
| A-261027-0003 | BACKGROUND | CLOSE_FP | get_market_events | 40.9 | Only event: market-wide scheduled macro print at 10:30:49, 40.9s before window start |
| A-261030-0002 | F-MM-1 | CLOSE_FP | get_order_events | -510 | Paired orders of 2260 at bid/ask (e.g. BUY 9999 / SELL 10000 at 11:44:40.497-510); each buy cancelled at the same timestamp as its sell and re-quoted within ~5-15 ms; SELL O-00013389 at 10000 partially filled 30 then 285 |

## Disagreements with the label (11)

| alert | scenario | expected | proposed | conf | status | summary |
|---|---|---|---|---|---|---|
| A-261013-0003 | S-LAYER-1 | ESCALATE | DRAFT_STOR | 0.6 | ok | PROP trader T-X1013-03 (no market-making registration) placed five BUY limit orders of 4,340 each (21,700 total, 8.69x avg top-5 depth of 2,498; typical order s |
| A-261015-0003 | S-SPOOF-2 | DRAFT_STOR | ESCALATE | 0.78 | ok | PROP trader T-X1015-02 (no market-making registration) placed a single one-sided SELL limit of 21443 on SYN.A at 11:04:43.303 (8.17x avg top-5 depth of 2624, ab |
| A-261016-0006 | S-SPOOF-2 | DRAFT_STOR | ESCALATE | 0.75 | ok | PROP trader T-X1016-06 (PROP-EQ, not a registered market maker on SYN.A, typical order size 500) placed a single one-sided BUY LIMIT of 21,860 (8.79x avg top-5  |
| A-261015-0008 | F-NEWS-1 | CLOSE_FP | ESCALATE | 0.75 | ok | PROP trader T-X1015-07 (desk PROP-EQ, no market-making registration, typical order size 500) placed two BUY limits of 7215 each at 9996 (15:12:52.998 and 15:12: |
| A-261016-0003 | F-NEWS-1 | CLOSE_FP | ESCALATE | 0.6 | ok | PROP trader T-X1016-03 (no MM registration) placed two BUY limits of 6,680 each at 9997 (12:01:42.731 and 12:01:45.731), a one-sided 13,360 resting at 5.37x avg |
| A-261016-0005 | F-NEWS-1 | CLOSE_FP | ESCALATE | 0.6 | ok | PROP trader T-X1016-05 (desk PROP-EQ, no market-making registration) rested two BUY limits of 7,162 at 9999 (14,324 gross, 5.76x avg top-5 depth of 2,487; typic |
| A-261006-0001 | F-RISK-1 | CLOSE_FP | ESCALATE | 0.7 | ok | PROP trader T-X1006-01 (PROP-EQ, no MM registration, typical order size 500) placed three one-sided BUY limits of 4614 each (13842 gross, max_resting_size_vs_de |
| A-261005-0007 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.7 | ok | PROP trader T-X1005-04 (no market-making registration, typical order size 500) bought 1132 SYN.A at market at 13:20:37.412, then placed three one-sided BUY limi |
| A-261006-0005 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | PROP trader T-X1006-03 (no MM registration on SYN.A) bought 947 at market at 11:36:02.890 (10002-10005), then placed three one-sided BUY limits of 3810 each at  |
| A-261026-0003 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.6 | ok | T-X1026-03 (PROP-EQ, no MM registration) bought 1118 SYN.A with a market order at 12:36:13.062, sweeping 10003-10007. Over the next 2-6 s it placed three one-si |
| A-261028-0011 | F-STOP-1 | CLOSE_FP | ESCALATE | 0.65 | ok | T-X1028-10 (PROP, PROP-EQ, no market-making registration) bought 1476 SYN.A at market at 16:57:25.851 (10005-10006). Over the next 4 seconds it placed three BUY |
