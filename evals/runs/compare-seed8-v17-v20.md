# seed8 on v17 vs seed8 on v20

100 shared alerts on dataset `seed8` (A has 100, B has 100).

| metric | seed8 on v17 | seed8 on v20 |
|---|---|---|
| gate | holds | holds |
| safe close rate | 88.2% | 90.8% |
| escalation precision | 72.7% | 77.4% |
| agreement / override rate | 88.0% / 12.0% | 90.0% / 10.0% |
| proposals | {'CLOSE_FP': 67, 'ESCALATE': 31, 'DRAFT_STOR': 2} | {'CLOSE_FP': 69, 'ESCALATE': 29, 'DRAFT_STOR': 2} |
| run status | {'ok': 100} | {'ok': 100} |
| recall_memory called / reports citing memory_used | 100 / 91 | 100 / 91 |
| agent p50 / p95 | 23.9 s / 35.8 s | 22.9 s / 27.5 s |
| tokens in / out per alert (mean) | 11 / 3049 | 11 / 3045 |
| tool calls per alert (mean) | 10.0 | 10 |
| estimated model cost (assumed prices) | $8.93 | $9.13 |
| mean confidence | 0.774 | 0.774 |

## Paired changes (4 of 100 alerts proposed differently)

| seed8 on v17 -> seed8 on v20 | n |
|---|---|
| ESCALATE -> CLOSE_FP | 2 |
| DRAFT_STOR -> ESCALATE | 1 |
| ESCALATE -> DRAFT_STOR | 1 |

| alert | scenario | expected | seed8 on v17 | seed8 on v20 | who is right |
|---|---|---|---|---|---|
| A-261118-0001 | S-SPOOF-2 | DRAFT_STOR | DRAFT_STOR (0.6) | ESCALATE (0.7) | A |
| A-261119-0001 | S-SPOOF-2 | DRAFT_STOR | ESCALATE (0.7) | DRAFT_STOR (0.6) | B |
| A-261105-0005 | F-NEWS-1 | CLOSE_FP | ESCALATE (0.6) | CLOSE_FP (0.6) | B |
| A-261116-0003 | F-RISK-1 | CLOSE_FP | ESCALATE (0.6) | CLOSE_FP (0.62) | B |

## Per scenario (agreement with the label)

| scenario | truth | n | seed8 on v17 | seed8 on v20 |
|---|---|---|---|---|
| S-LAYER-1 | TRUE_ABUSE | 3 | 3/3 | 3/3 |
| S-SPOOF-1 | TRUE_ABUSE | 11 | 11/11 | 11/11 |
| S-SPOOF-2 | TRUE_ABUSE | 5 | 2/5 | 2/5 |
| S-SPOOF-3 | TRUE_ABUSE | 3 | 3/3 | 3/3 |
| S-SPOOF-4 | TRUE_ABUSE | 2 | 2/2 | 2/2 |
| BACKGROUND | FALSE_POSITIVE | 1 | 1/1 | 1/1 |
| F-ALGO-1 | FALSE_POSITIVE | 22 | 22/22 | 22/22 |
| F-FAT-1 | FALSE_POSITIVE | 3 | 3/3 | 3/3 |
| F-ICE-1 | FALSE_POSITIVE | 6 | 6/6 | 6/6 |
| F-MM-1 | FALSE_POSITIVE | 17 | 17/17 | 17/17 |
| F-NEWS-1 | FALSE_POSITIVE | 6 | 3/6 | 4/6 |
| F-PARTIAL-1 | FALSE_POSITIVE | 5 | 5/5 | 5/5 |
| F-RISK-1 | FALSE_POSITIVE | 4 | 2/4 | 3/4 |
| F-SPOOFLIKE-HARD-1 | FALSE_POSITIVE | 7 | 7/7 | 7/7 |
| F-STOP-1 | FALSE_POSITIVE | 5 | 1/5 | 1/5 |