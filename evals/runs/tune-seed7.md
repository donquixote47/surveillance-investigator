# Detector threshold re-tuning on `seed7`

Grid of 60 parameter sets over K (size vs depth), P (cancel percent) and C (cancel window), W fixed at 60 s; 142 s. Recall is on injected TRUE_ABUSE scenarios and must be 1.0; precision is TRUE_ABUSE alerts over all alerts.

| | K | P | C | alerts | TRUE_ABUSE | false positives | background | precision | injection recall |
|---|---|---|---|---|---|---|---|---|---|
| current (used for the evaluated dataset) | 3.25 | 70 | 5 | 167 | 28 | 139 | 52 | 16.8% | 1.0 |
| best at 100% recall | 6 | 60 | 2 | 97.0 | 28.0 | 69.0 | 0.0 | 28.9% | 1.0 |

K alone (P=70, C=5):

| K | alerts | precision | injection recall | missed true injections |
|---|---|---|---|---|
| 2.5 | 491 | 5.7% | 1.0 | 0 |
| 3.25 | 167 | 16.8% | 1.0 | 0 |
| 4 | 119 | 23.5% | 1.0 | 0 |
| 5 | 110 | 25.4% | 1.0 | 0 |
| 6 | 99 | 28.3% | 1.0 | 0 |

Top parameter sets that keep recall at 1.0:

| K | P | C | alerts | precision |
|---|---|---|---|---|
| 6 | 60 | 2 | 97 | 28.9% |
| 6 | 70 | 2 | 97 | 28.9% |
| 6 | 80 | 2 | 97 | 28.9% |
| 6 | 60 | 5 | 99 | 28.3% |
| 6 | 60 | 10 | 99 | 28.3% |
| 6 | 70 | 5 | 99 | 28.3% |
| 6 | 70 | 10 | 99 | 28.3% |
| 6 | 80 | 5 | 99 | 28.3% |

Applies to the next dataset build only (`scripts/build_dataset.py --k-depth ...`); the evaluated dataset keeps its parameters so that run-to-run comparisons stay on the same 167 alerts.