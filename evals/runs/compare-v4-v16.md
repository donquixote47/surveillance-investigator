# v4 (v14) vs v16 slice

30 shared alerts (A has 167, B has 30).

| metric | v4 (v14) | v16 slice |
|---|---|---|
| gate | holds | holds |
| safe close rate | 91.3% | 91.3% |
| escalation precision | 77.8% | 77.8% |
| agreement / override rate | 90.0% / 10.0% | 90.0% / 10.0% |
| proposals | {'CLOSE_FP': 21, 'ESCALATE': 9} | {'CLOSE_FP': 21, 'ESCALATE': 9} |
| run status | {'ok': 30} | {'ok': 30} |
| recall_memory called / reports citing memory_used | 30 / 27 | 30 / 27 |
| agent p50 / p95 | 26.9 s / 32.9 s | 27.9 s / 34.4 s |
| tokens in / out per alert (mean) | 12 / 3172 | 11 / 3114 |
| tool calls per alert (mean) | 10.1 | 10 |
| estimated model cost (assumed prices) | $2.47 | $2.56 |
| mean confidence | 0.787 | 0.786 |

## Paired changes (0 of 30 alerts proposed differently)

## Per scenario (agreement with the label)

| scenario | truth | n | v4 (v14) | v16 slice |
|---|---|---|---|---|
| S-LAYER-1 | TRUE_ABUSE | 2 | 2/2 | 2/2 |
| S-SPOOF-1 | TRUE_ABUSE | 1 | 1/1 | 1/1 |
| S-SPOOF-2 | TRUE_ABUSE | 1 | 0/1 | 0/1 |
| S-SPOOF-3 | TRUE_ABUSE | 1 | 1/1 | 1/1 |
| S-SPOOF-4 | TRUE_ABUSE | 1 | 1/1 | 1/1 |
| S-SPOOF-5 | TRUE_ABUSE | 1 | 1/1 | 1/1 |
| BACKGROUND | FALSE_POSITIVE | 8 | 8/8 | 8/8 |
| F-ALGO-1 | FALSE_POSITIVE | 3 | 3/3 | 3/3 |
| F-FAT-1 | FALSE_POSITIVE | 2 | 2/2 | 2/2 |
| F-ICE-1 | FALSE_POSITIVE | 2 | 2/2 | 2/2 |
| F-MM-1 | FALSE_POSITIVE | 2 | 2/2 | 2/2 |
| F-NEWS-1 | FALSE_POSITIVE | 1 | 0/1 | 0/1 |
| F-PARTIAL-1 | FALSE_POSITIVE | 2 | 2/2 | 2/2 |
| F-RISK-1 | FALSE_POSITIVE | 1 | 1/1 | 1/1 |
| F-SPOOFLIKE-HARD-1 | FALSE_POSITIVE | 1 | 1/1 | 1/1 |
| F-STOP-1 | FALSE_POSITIVE | 1 | 0/1 | 0/1 |