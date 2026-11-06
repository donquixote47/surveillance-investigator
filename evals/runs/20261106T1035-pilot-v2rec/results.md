# Dataset run `20261106T1035-pilot-v2rec`

- Dataset `seed7`, 30 alerts (10 TRUE_ABUSE, 20 FALSE_POSITIVE); backend `runtime`, model `eu.anthropic.claude-sonnet-5-5`, analyst `L1`, mode `investigate`, memory on, bundle v2-rec (surv_v2_rec-178VZR7ZzL:4f93cfe7-95a8-4955-bb99-fd6b43189e1a), concurrency 2.
- Started 2026-11-06T10:35:47+00:00, finished 2026-11-06T10:43:08+00:00 (7.3 min).
- Notes: Optimization recommendation surv-prompt-rec-v1 as bundle surv_v2_rec, unedited, on a 30-alert stratified sample; Runtime v10, iteration-2 procedures

## Headline

| metric | value |
|---|---|
| gate | **holds** (0 TRUE_ABUSE proposed CLOSE_FP) |
| true-abuse alerts with no proposal | 10: A-261008-0002, A-261012-0003, A-261015-0003, A-261016-0002, A-261022-0002, A-261023-0006, A-261026-0002, A-261028-0001, A-261028-0009, A-261030-0005 |
| safe close rate | 0.0% (0 of 20 false positives closed) |
| escalation precision | n/a (0 ESCALATE/DRAFT_STOR) |
| strong-call precision | n/a (0 DRAFT_STOR) |
| agreement with label (exact disposition) | 0.0% |
| **override rate** (1 - agreement) | **100.0%** |
| direction agreement (close vs not-close) | 0.0% |
| proposals | {'NONE': 30} |
| run status | {'no_proposal': 30} |
| alerts with a disposition recorded before this run (visible to the agent through history and Memory) | 1: A-261016-0003 |
| configuration bundle reported by the agent | surv_v2_rec-178VZR7ZzL:4f93cfe7-95a8-4955-bb99-fd6b43189e1a |
| latency, agent p50 / p95 | 22.2 s / 26.7 s (wall p50 27.9 s) |
| tokens per alert, in / out (mean) | 57780 / 2000 (max in 102787) |
| tool calls per alert (mean / median) | 9.7 / 10.0 |
| estimated model cost | $4.07 total, $0.136 per alert (assumed $2.0/$10.0 per M tokens in/out; not verified against the pricing page) |

## Against the baselines (same alerts)

| scorer | gate | safe close rate | raw safe close | escalation precision | agreement | override rate |
|---|---|---|---|---|---|---|
| agent (this run) | holds | 0.0% | 0.0% | n/a | 0.0% | 100.0% |
| threshold baseline (detector rules) | 1 missed | n/a | 95.0% | 90.0% | 93.3% | 6.7% |
| escalate everything | holds | 0.0% | 0.0% | 33.3% | 30.0% | 70.0% |
| close everything (the gate at work) | 10 missed | n/a | 100.0% | n/a | 66.7% | 33.3% |

## Confusion: expected (rows) x proposed (columns)

| expected \ proposed | CLOSE_FP | ESCALATE | DRAFT_STOR | none |
|---|---|---|---|---|
| CLOSE_FP | 0 | 0 | 0 | 20 |
| ESCALATE | 0 | 0 | 0 | 9 |
| DRAFT_STOR | 0 | 0 | 0 | 1 |

## Per scenario

| scenario | truth | expected | n | CLOSE_FP | ESCALATE | DRAFT_STOR | none | agreement | mean conf | gate misses |
|---|---|---|---|---|---|---|---|---|---|---|
| S-LAYER-1 | TRUE_ABUSE | ESCALATE | 2 | 0 | 0 | 0 | 2 | 0% | - | - |
| S-SPOOF-1 | TRUE_ABUSE | ESCALATE | 3 | 0 | 0 | 0 | 3 | 0% | - | - |
| S-SPOOF-2 | TRUE_ABUSE | DRAFT_STOR | 1 | 0 | 0 | 0 | 1 | 0% | - | - |
| S-SPOOF-3 | TRUE_ABUSE | ESCALATE | 1 | 0 | 0 | 0 | 1 | 0% | - | - |
| S-SPOOF-4 | TRUE_ABUSE | ESCALATE | 1 | 0 | 0 | 0 | 1 | 0% | - | - |
| S-SPOOF-5 | TRUE_ABUSE | ESCALATE | 2 | 0 | 0 | 0 | 2 | 0% | - | - |
| BACKGROUND | FALSE_POSITIVE | CLOSE_FP | 4 | 0 | 0 | 0 | 4 | 0% | - | - |
| F-ALGO-1 | FALSE_POSITIVE | CLOSE_FP | 4 | 0 | 0 | 0 | 4 | 0% | - | - |
| F-FAT-1 | FALSE_POSITIVE | CLOSE_FP | 1 | 0 | 0 | 0 | 1 | 0% | - | - |
| F-ICE-1 | FALSE_POSITIVE | CLOSE_FP | 2 | 0 | 0 | 0 | 2 | 0% | - | - |
| F-MM-1 | FALSE_POSITIVE | CLOSE_FP | 3 | 0 | 0 | 0 | 3 | 0% | - | - |
| F-NEWS-1 | FALSE_POSITIVE | CLOSE_FP | 1 | 0 | 0 | 0 | 1 | 0% | - | - |
| F-PARTIAL-1 | FALSE_POSITIVE | CLOSE_FP | 1 | 0 | 0 | 0 | 1 | 0% | - | - |
| F-RISK-1 | FALSE_POSITIVE | CLOSE_FP | 1 | 0 | 0 | 0 | 1 | 0% | - | - |
| F-SPOOFLIKE-HARD-1 | FALSE_POSITIVE | CLOSE_FP | 1 | 0 | 0 | 0 | 1 | 0% | - | - |
| F-STOP-1 | FALSE_POSITIVE | CLOSE_FP | 2 | 0 | 0 | 0 | 2 | 0% | - | - |

## Regression against the previous run

Previous run: `20261106T0906-sonnet-v2`. Verdict: **FAIL**.

- [x] gate holds
- [ ] safe close rate not down by more than 2 points
- [ ] no false-positive scenario regressed to 0% close (BACKGROUND, F-ALGO-1, F-FAT-1, F-ICE-1, F-MM-1, F-NEWS-1, F-PARTIAL-1, F-RISK-1, F-SPOOFLIKE-HARD-1, F-STOP-1)

| delta | value |
|---|---|
| raw_safe_close_rate | -88.5 pts |
| agreement | -88.6 pts |
| direction_agreement | -90.4 pts |
| true_abuse_recall | +0.0 pts |
| gate misses | +0 |

| scenario | agreement delta | close-rate delta |
|---|---|---|
| S-SPOOF-1 | -100 pts | +0 pts |
| S-SPOOF-3 | -100 pts | +0 pts |
| S-SPOOF-4 | -100 pts | +0 pts |
| S-SPOOF-5 | -100 pts | +0 pts |
| F-ICE-1 | -100 pts | -100 pts |
| F-MM-1 | -100 pts | -100 pts |
| F-PARTIAL-1 | -100 pts | -100 pts |
| F-RISK-1 | -100 pts | -100 pts |
| F-SPOOFLIKE-HARD-1 | -100 pts | -100 pts |
| BACKGROUND | -92 pts | -92 pts |
| F-ALGO-1 | -88 pts | -88 pts |
| S-LAYER-1 | -80 pts | +0 pts |
| F-FAT-1 | -67 pts | -67 pts |
| S-SPOOF-2 | -33 pts | +0 pts |
| F-NEWS-1 | -25 pts | -25 pts |
| F-STOP-1 | -17 pts | -17 pts |

## Disagreements with the label (30)

| alert | scenario | expected | proposed | conf | status | summary |
|---|---|---|---|---|---|---|
| A-261022-0002 | S-LAYER-1 | ESCALATE | - | - | no_proposal |  |
| A-261028-0009 | S-LAYER-1 | ESCALATE | - | - | no_proposal |  |
| A-261012-0003 | S-SPOOF-1 | ESCALATE | - | - | no_proposal |  |
| A-261026-0002 | S-SPOOF-1 | ESCALATE | - | - | no_proposal |  |
| A-261030-0005 | S-SPOOF-1 | ESCALATE | - | - | no_proposal |  |
| A-261015-0003 | S-SPOOF-2 | DRAFT_STOR | - | - | no_proposal |  |
| A-261016-0002 | S-SPOOF-3 | ESCALATE | - | - | no_proposal |  |
| A-261028-0001 | S-SPOOF-4 | ESCALATE | - | - | no_proposal |  |
| A-261008-0002 | S-SPOOF-5 | ESCALATE | - | - | no_proposal |  |
| A-261023-0006 | S-SPOOF-5 | ESCALATE | - | - | no_proposal |  |
| A-261006-0018 | BACKGROUND | CLOSE_FP | - | - | no_proposal |  |
| A-261019-0001 | BACKGROUND | CLOSE_FP | - | - | no_proposal |  |
| A-261020-0004 | BACKGROUND | CLOSE_FP | - | - | no_proposal |  |
| A-261027-0003 | BACKGROUND | CLOSE_FP | - | - | no_proposal |  |
| A-261022-0001 | F-ALGO-1 | CLOSE_FP | - | - | no_proposal |  |
| A-261026-0006 | F-ALGO-1 | CLOSE_FP | - | - | no_proposal |  |
| A-261027-0009 | F-ALGO-1 | CLOSE_FP | - | - | no_proposal |  |
| A-261029-0001 | F-ALGO-1 | CLOSE_FP | - | - | no_proposal |  |
| A-261009-0007 | F-FAT-1 | CLOSE_FP | - | - | no_proposal |  |
| A-261020-0003 | F-ICE-1 | CLOSE_FP | - | - | no_proposal |  |
| A-261028-0007 | F-ICE-1 | CLOSE_FP | - | - | no_proposal |  |
| A-261013-0001 | F-MM-1 | CLOSE_FP | - | - | no_proposal |  |
| A-261015-0012 | F-MM-1 | CLOSE_FP | - | - | no_proposal |  |
| A-261023-0003 | F-MM-1 | CLOSE_FP | - | - | no_proposal |  |
| A-261016-0003 | F-NEWS-1 | CLOSE_FP | - | - | no_proposal |  |
| A-261016-0004 | F-PARTIAL-1 | CLOSE_FP | - | - | no_proposal |  |
| A-261030-0004 | F-RISK-1 | CLOSE_FP | - | - | no_proposal |  |
| A-261026-0005 | F-SPOOFLIKE-HARD-1 | CLOSE_FP | - | - | no_proposal |  |
| A-261027-0008 | F-STOP-1 | CLOSE_FP | - | - | no_proposal |  |
| A-261028-0011 | F-STOP-1 | CLOSE_FP | - | - | no_proposal |  |
