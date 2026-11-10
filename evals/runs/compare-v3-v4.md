# v3 (Runtime v12) vs v4 (Runtime v14, alias + cache)

167 shared alerts (A has 167, B has 167).

| metric | v3 (Runtime v12) | v4 (Runtime v14, alias + cache) |
|---|---|---|
| gate | holds | holds |
| safe close rate | 93.5% | 95.0% |
| escalation precision | 75.7% | 80.0% |
| agreement / override rate | 93.4% / 6.6% | 94.6% / 5.4% |
| proposals | {'CLOSE_FP': 130, 'ESCALATE': 36, 'DRAFT_STOR': 1} | {'CLOSE_FP': 132, 'ESCALATE': 34, 'DRAFT_STOR': 1} |
| run status | {'ok': 167} | {'ok': 167} |
| recall_memory called / reports citing memory_used | 167 / 154 | 167 / 154 |
| agent p50 / p95 | 27.4 s / 37.9 s | 27.9 s / 35.3 s |
| tokens in / out per alert (mean) | 76679 / 3384 | 11 / 3125 |
| tool calls per alert (mean) | 10.1 | 10.0 |
| estimated model cost (assumed prices) | $31.26 | $15.25 |
| mean confidence | 0.811 | 0.813 |

## Paired changes (4 of 167 alerts proposed differently)

| v3 (Runtime v12) -> v4 (Runtime v14, alias + cache) | n |
|---|---|
| ESCALATE -> CLOSE_FP | 3 |
| CLOSE_FP -> ESCALATE | 1 |

| alert | scenario | expected | v3 (Runtime v12) | v4 (Runtime v14, alias + cache) | who is right |
|---|---|---|---|---|---|
| A-261006-0014 | F-FAT-1 | CLOSE_FP | ESCALATE (0.6) | CLOSE_FP (0.7) | B |
| A-261016-0005 | F-NEWS-1 | CLOSE_FP | CLOSE_FP (0.6) | ESCALATE (0.6) | A |
| A-261026-0003 | F-STOP-1 | CLOSE_FP | ESCALATE (0.6) | CLOSE_FP (0.65) | B |
| A-261028-0011 | F-STOP-1 | CLOSE_FP | ESCALATE (0.6) | CLOSE_FP (0.62) | B |

## Per scenario (agreement with the label)

| scenario | truth | n | v3 (Runtime v12) | v4 (Runtime v14, alias + cache) |
|---|---|---|---|---|
| S-LAYER-1 | TRUE_ABUSE | 5 | 5/5 | 5/5 |
| S-SPOOF-1 | TRUE_ABUSE | 7 | 7/7 | 7/7 |
| S-SPOOF-2 | TRUE_ABUSE | 3 | 1/3 | 1/3 |
| S-SPOOF-3 | TRUE_ABUSE | 4 | 4/4 | 4/4 |
| S-SPOOF-4 | TRUE_ABUSE | 2 | 2/2 | 2/2 |
| S-SPOOF-5 | TRUE_ABUSE | 7 | 7/7 | 7/7 |
| BACKGROUND | FALSE_POSITIVE | 52 | 52/52 | 52/52 |
| F-ALGO-1 | FALSE_POSITIVE | 24 | 24/24 | 24/24 |
| F-FAT-1 | FALSE_POSITIVE | 3 | 2/3 | 3/3 |
| F-ICE-1 | FALSE_POSITIVE | 9 | 9/9 | 9/9 |
| F-MM-1 | FALSE_POSITIVE | 24 | 24/24 | 24/24 |
| F-NEWS-1 | FALSE_POSITIVE | 4 | 2/4 | 1/4 |
| F-PARTIAL-1 | FALSE_POSITIVE | 8 | 8/8 | 8/8 |
| F-RISK-1 | FALSE_POSITIVE | 3 | 3/3 | 3/3 |
| F-SPOOFLIKE-HARD-1 | FALSE_POSITIVE | 6 | 6/6 | 6/6 |
| F-STOP-1 | FALSE_POSITIVE | 6 | 0/6 | 2/6 |