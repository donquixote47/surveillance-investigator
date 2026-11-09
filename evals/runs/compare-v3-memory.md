# memory on vs memory off

167 shared alerts (A has 167, B has 167).

| metric | memory on | memory off |
|---|---|---|
| gate | holds | holds |
| safe close rate | 93.5% | 92.8% |
| escalation precision | 75.7% | 73.7% |
| agreement / override rate | 93.4% / 6.6% | 92.2% / 7.8% |
| proposals | {'CLOSE_FP': 130, 'ESCALATE': 36, 'DRAFT_STOR': 1} | {'CLOSE_FP': 129, 'ESCALATE': 36, 'DRAFT_STOR': 2} |
| run status | {'ok': 167} | {'ok': 167} |
| recall_memory called / reports citing memory_used | 167 / 154 | 0 / 1 |
| agent p50 / p95 | 27.4 s / 37.9 s | 24.0 s / 34.6 s |
| tokens in / out per alert (mean) | 76679 / 3384 | 60052 / 3091 |
| tool calls per alert (mean) | 10.1 | 9.2 |
| estimated model cost (assumed prices) | $31.26 | $25.22 |
| mean confidence | 0.811 | 0.812 |

## Paired changes (4 of 167 alerts proposed differently)

| memory on -> memory off | n |
|---|---|
| CLOSE_FP -> ESCALATE | 2 |
| ESCALATE -> CLOSE_FP | 1 |
| ESCALATE -> DRAFT_STOR | 1 |

| alert | scenario | expected | memory on | memory off | who is right |
|---|---|---|---|---|---|
| A-261013-0003 | S-LAYER-1 | ESCALATE | ESCALATE (0.72) | DRAFT_STOR (0.65) | A |
| A-261006-0014 | F-FAT-1 | CLOSE_FP | ESCALATE (0.6) | CLOSE_FP (0.7) | B |
| A-261009-0007 | F-FAT-1 | CLOSE_FP | CLOSE_FP (0.7) | ESCALATE (0.6) | A |
| A-261016-0005 | F-NEWS-1 | CLOSE_FP | CLOSE_FP (0.6) | ESCALATE (0.6) | A |

## Per scenario (agreement with the label)

| scenario | truth | n | memory on | memory off |
|---|---|---|---|---|
| S-LAYER-1 | TRUE_ABUSE | 5 | 5/5 | 4/5 |
| S-SPOOF-1 | TRUE_ABUSE | 7 | 7/7 | 7/7 |
| S-SPOOF-2 | TRUE_ABUSE | 3 | 1/3 | 1/3 |
| S-SPOOF-3 | TRUE_ABUSE | 4 | 4/4 | 4/4 |
| S-SPOOF-4 | TRUE_ABUSE | 2 | 2/2 | 2/2 |
| S-SPOOF-5 | TRUE_ABUSE | 7 | 7/7 | 7/7 |
| BACKGROUND | FALSE_POSITIVE | 52 | 52/52 | 52/52 |
| F-ALGO-1 | FALSE_POSITIVE | 24 | 24/24 | 24/24 |
| F-FAT-1 | FALSE_POSITIVE | 3 | 2/3 | 2/3 |
| F-ICE-1 | FALSE_POSITIVE | 9 | 9/9 | 9/9 |
| F-MM-1 | FALSE_POSITIVE | 24 | 24/24 | 24/24 |
| F-NEWS-1 | FALSE_POSITIVE | 4 | 2/4 | 1/4 |
| F-PARTIAL-1 | FALSE_POSITIVE | 8 | 8/8 | 8/8 |
| F-RISK-1 | FALSE_POSITIVE | 3 | 3/3 | 3/3 |
| F-SPOOFLIKE-HARD-1 | FALSE_POSITIVE | 6 | 6/6 | 6/6 |
| F-STOP-1 | FALSE_POSITIVE | 6 | 0/6 | 0/6 |