# v1 vs v2

167 shared alerts (A has 167, B has 167).

| metric | v1 | v2 |
|---|---|---|
| gate | holds | holds |
| safe close rate | 79.9% | 88.5% |
| escalation precision | 50.0% | 63.6% |
| agreement / override rate | 81.4% / 18.6% | 88.6% / 11.4% |
| proposals | {'CLOSE_FP': 111, 'ESCALATE': 54, 'DRAFT_STOR': 2} | {'CLOSE_FP': 123, 'ESCALATE': 42, 'DRAFT_STOR': 2} |
| run status | {'ok': 167} | {'ok': 167} |
| recall_memory called / reports citing memory_used | 167 / 154 | 167 / 153 |
| agent p50 / p95 | 31.9 s / 47.9 s | 31.0 s / 46.2 s |
| tokens in / out per alert (mean) | 81529 / 4097 | 76279 / 3647 |
| tool calls per alert (mean) | 10.4 | 10.2 |
| estimated model cost (assumed prices) | $34.07 | $31.57 |
| mean confidence | 0.746 | 0.754 |

## Paired changes (30 of 167 alerts proposed differently)

| v1 -> v2 | n |
|---|---|
| ESCALATE -> CLOSE_FP | 20 |
| CLOSE_FP -> ESCALATE | 8 |
| ESCALATE -> DRAFT_STOR | 1 |
| DRAFT_STOR -> ESCALATE | 1 |

| alert | scenario | expected | v1 | v2 | who is right |
|---|---|---|---|---|---|
| A-261013-0003 | S-LAYER-1 | ESCALATE | ESCALATE (0.65) | DRAFT_STOR (0.6) | A |
| A-261022-0002 | S-LAYER-1 | ESCALATE | DRAFT_STOR (0.6) | ESCALATE (0.65) | B |
| A-261005-0002 | BACKGROUND | CLOSE_FP | ESCALATE (0.5) | CLOSE_FP (0.7) | B |
| A-261005-0006 | BACKGROUND | CLOSE_FP | CLOSE_FP (0.75) | ESCALATE (0.6) | A |
| A-261009-0005 | BACKGROUND | CLOSE_FP | CLOSE_FP (0.72) | ESCALATE (0.55) | A |
| A-261021-0001 | BACKGROUND | CLOSE_FP | CLOSE_FP (0.8) | ESCALATE (0.6) | A |
| A-261027-0004 | BACKGROUND | CLOSE_FP | CLOSE_FP (0.8) | ESCALATE (0.55) | A |
| A-261029-0004 | BACKGROUND | CLOSE_FP | ESCALATE (0.55) | CLOSE_FP (0.8) | B |
| A-261012-0002 | F-ALGO-1 | CLOSE_FP | CLOSE_FP (0.72) | ESCALATE (0.55) | A |
| A-261029-0015 | F-ALGO-1 | CLOSE_FP | CLOSE_FP (0.72) | ESCALATE (0.6) | A |
| A-261030-0003 | F-ALGO-1 | CLOSE_FP | CLOSE_FP (0.75) | ESCALATE (0.6) | A |
| A-261021-0009 | F-FAT-1 | CLOSE_FP | CLOSE_FP (0.72) | ESCALATE (0.6) | A |
| A-261005-0009 | F-ICE-1 | CLOSE_FP | ESCALATE (0.62) | CLOSE_FP (0.8) | B |
| A-261007-0002 | F-ICE-1 | CLOSE_FP | ESCALATE (0.6) | CLOSE_FP (0.8) | B |
| A-261014-0002 | F-ICE-1 | CLOSE_FP | ESCALATE (0.6) | CLOSE_FP (0.8) | B |
| A-261019-0005 | F-ICE-1 | CLOSE_FP | ESCALATE (0.6) | CLOSE_FP (0.8) | B |
| A-261019-0009 | F-ICE-1 | CLOSE_FP | ESCALATE (0.6) | CLOSE_FP (0.75) | B |
| A-261020-0003 | F-ICE-1 | CLOSE_FP | ESCALATE (0.6) | CLOSE_FP (0.8) | B |
| A-261028-0007 | F-ICE-1 | CLOSE_FP | ESCALATE (0.6) | CLOSE_FP (0.85) | B |
| A-261029-0014 | F-ICE-1 | CLOSE_FP | ESCALATE (0.62) | CLOSE_FP (0.8) | B |
| A-261006-0009 | F-PARTIAL-1 | CLOSE_FP | ESCALATE (0.6) | CLOSE_FP (0.8) | B |
| A-261014-0001 | F-PARTIAL-1 | CLOSE_FP | ESCALATE (0.6) | CLOSE_FP (0.8) | B |
| A-261016-0004 | F-PARTIAL-1 | CLOSE_FP | ESCALATE (0.7) | CLOSE_FP (0.7) | B |
| A-261020-0002 | F-PARTIAL-1 | CLOSE_FP | ESCALATE (0.7) | CLOSE_FP (0.7) | B |
| A-261021-0004 | F-PARTIAL-1 | CLOSE_FP | ESCALATE (0.7) | CLOSE_FP (0.75) | B |
| A-261023-0004 | F-PARTIAL-1 | CLOSE_FP | ESCALATE (0.7) | CLOSE_FP (0.7) | B |
| A-261023-0009 | F-PARTIAL-1 | CLOSE_FP | ESCALATE (0.7) | CLOSE_FP (0.7) | B |
| A-261028-0004 | F-PARTIAL-1 | CLOSE_FP | ESCALATE (0.6) | CLOSE_FP (0.8) | B |
| A-261006-0001 | F-RISK-1 | CLOSE_FP | ESCALATE (0.6) | CLOSE_FP (0.62) | B |
| A-261022-0003 | F-STOP-1 | CLOSE_FP | ESCALATE (0.6) | CLOSE_FP (0.6) | B |

## Per scenario (agreement with the label)

| scenario | truth | n | v1 | v2 |
|---|---|---|---|---|
| S-LAYER-1 | TRUE_ABUSE | 5 | 4/5 | 4/5 |
| S-SPOOF-1 | TRUE_ABUSE | 7 | 7/7 | 7/7 |
| S-SPOOF-2 | TRUE_ABUSE | 3 | 1/3 | 1/3 |
| S-SPOOF-3 | TRUE_ABUSE | 4 | 4/4 | 4/4 |
| S-SPOOF-4 | TRUE_ABUSE | 2 | 2/2 | 2/2 |
| S-SPOOF-5 | TRUE_ABUSE | 7 | 7/7 | 7/7 |
| BACKGROUND | FALSE_POSITIVE | 52 | 50/52 | 48/52 |
| F-ALGO-1 | FALSE_POSITIVE | 24 | 24/24 | 21/24 |
| F-FAT-1 | FALSE_POSITIVE | 3 | 3/3 | 2/3 |
| F-ICE-1 | FALSE_POSITIVE | 9 | 1/9 | 9/9 |
| F-MM-1 | FALSE_POSITIVE | 24 | 24/24 | 24/24 |
| F-NEWS-1 | FALSE_POSITIVE | 4 | 1/4 | 1/4 |
| F-PARTIAL-1 | FALSE_POSITIVE | 8 | 0/8 | 8/8 |
| F-RISK-1 | FALSE_POSITIVE | 3 | 2/3 | 3/3 |
| F-SPOOFLIKE-HARD-1 | FALSE_POSITIVE | 6 | 6/6 | 6/6 |
| F-STOP-1 | FALSE_POSITIVE | 6 | 0/6 | 1/6 |