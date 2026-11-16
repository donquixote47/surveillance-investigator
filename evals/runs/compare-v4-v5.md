# v4 vs v5

167 shared alerts (A has 167, B has 167).

| metric | v4 | v5 |
|---|---|---|
| gate | holds | holds |
| safe close rate | 95.0% | 94.2% |
| escalation precision | 80.0% | 77.8% |
| agreement / override rate | 94.6% / 5.4% | 94.0% / 6.0% |
| proposals | {'CLOSE_FP': 132, 'ESCALATE': 34, 'DRAFT_STOR': 1} | {'CLOSE_FP': 131, 'ESCALATE': 35, 'DRAFT_STOR': 1} |
| run status | {'ok': 167} | {'ok': 167} |
| recall_memory called / reports citing memory_used | 167 / 154 | 167 / 154 |
| agent p50 / p95 | 27.9 s / 35.3 s | 28.5 s / 41.5 s |
| tokens in / out per alert (mean) | 11 / 3125 | 11 / 2961 |
| tool calls per alert (mean) | 10.0 | 10 |
| estimated model cost (assumed prices) | $15.25 | $15.84 |
| mean confidence | 0.813 | 0.818 |

## Paired changes (3 of 167 alerts proposed differently)

| v4 -> v5 | n |
|---|---|
| CLOSE_FP -> ESCALATE | 2 |
| ESCALATE -> CLOSE_FP | 1 |

| alert | scenario | expected | v4 | v5 | who is right |
|---|---|---|---|---|---|
| A-261022-0003 | F-STOP-1 | CLOSE_FP | ESCALATE (0.6) | CLOSE_FP (0.6) | B |
| A-261026-0003 | F-STOP-1 | CLOSE_FP | CLOSE_FP (0.65) | ESCALATE (0.6) | A |
| A-261028-0011 | F-STOP-1 | CLOSE_FP | CLOSE_FP (0.62) | ESCALATE (0.6) | A |

## Per scenario (agreement with the label)

| scenario | truth | n | v4 | v5 |
|---|---|---|---|---|
| S-LAYER-1 | TRUE_ABUSE | 5 | 5/5 | 5/5 |
| S-SPOOF-1 | TRUE_ABUSE | 7 | 7/7 | 7/7 |
| S-SPOOF-2 | TRUE_ABUSE | 3 | 1/3 | 1/3 |
| S-SPOOF-3 | TRUE_ABUSE | 4 | 4/4 | 4/4 |
| S-SPOOF-4 | TRUE_ABUSE | 2 | 2/2 | 2/2 |
| S-SPOOF-5 | TRUE_ABUSE | 7 | 7/7 | 7/7 |
| BACKGROUND | FALSE_POSITIVE | 52 | 52/52 | 52/52 |
| F-ALGO-1 | FALSE_POSITIVE | 24 | 24/24 | 24/24 |
| F-FAT-1 | FALSE_POSITIVE | 3 | 3/3 | 3/3 |
| F-ICE-1 | FALSE_POSITIVE | 9 | 9/9 | 9/9 |
| F-MM-1 | FALSE_POSITIVE | 24 | 24/24 | 24/24 |
| F-NEWS-1 | FALSE_POSITIVE | 4 | 1/4 | 1/4 |
| F-PARTIAL-1 | FALSE_POSITIVE | 8 | 8/8 | 8/8 |
| F-RISK-1 | FALSE_POSITIVE | 3 | 3/3 | 3/3 |
| F-SPOOFLIKE-HARD-1 | FALSE_POSITIVE | 6 | 6/6 | 6/6 |
| F-STOP-1 | FALSE_POSITIVE | 6 | 2/6 | 1/6 |