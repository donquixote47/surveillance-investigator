# Dataset seed7

seed 7, 20 sessions 2026-10-05..2026-10-30, generator market-sim-0.1, detector spoof-naive-v1 {"cancel_pct": 70.0, "cancel_within_s": 5.0, "cooldown_s": 900.0, "k_depth": 3.25, "large_quick_k": 6.0, "large_quick_within_s": 10.0, "layering_min_levels": 3, "window_s": 60.0}

- order events: 1,821,634; trades: 139,652; traders: 137
- alerts: 167 (28 TRUE_ABUSE = 17%; 52 background)
- detector recall on injected abuse: 100%; precision: 17%
- missed injections: 0

## Coverage per scenario (injected vs alerts attributed)

                    injected  alerts  missed_injections
F-ALGO-1                  24      24                  0
F-FAT-1                    3       3                  0
F-ICE-1                    9       9                  0
F-MM-1                    24      24                  0
F-NEWS-1                   4       4                  0
F-PARTIAL-1                8       8                  0
F-RISK-1                   3       3                  0
F-SPOOFLIKE-HARD-1         6       6                  0
F-STOP-1                   6       6                  0
S-LAYER-1                  5       5                  0
S-SPOOF-1                  7       7                  0
S-SPOOF-2                  3       3                  0
S-SPOOF-3                  4       4                  0
S-SPOOF-4                  2       2                  0
S-SPOOF-5                  7       7                  0

## Threshold baseline (no LLM)

- gate: 6 TRUE_ABUSE alerts proposed CLOSE_FP -> GATE FAILED; safe close rate reported as n/a
- safe close rate: n/a (gate failed) (raw 96%)

Share proposed CLOSE_FP per scenario:

                    close_fp_share  alerts
injected_scenario                         
BACKGROUND                1.000000      52
F-ALGO-1                  1.000000      24
F-FAT-1                   1.000000       3
F-ICE-1                   1.000000       9
F-MM-1                    1.000000      24
F-NEWS-1                  1.000000       4
F-PARTIAL-1               1.000000       8
F-RISK-1                  1.000000       3
F-SPOOFLIKE-HARD-1        0.000000       6
F-STOP-1                  1.000000       6
S-LAYER-1                 0.000000       5
S-SPOOF-1                 0.000000       7
S-SPOOF-2                 0.000000       3
S-SPOOF-3                 0.000000       4
S-SPOOF-4                 0.000000       2
S-SPOOF-5                 0.857143       7

Gate failures:

     alert_id injected_scenario        baseline_rule
A-261006-0015         S-SPOOF-5 R5-genuine-execution
A-261008-0001         S-SPOOF-5 R5-genuine-execution
A-261008-0002         S-SPOOF-5 R5-genuine-execution
A-261021-0003         S-SPOOF-5 R5-genuine-execution
A-261027-0001         S-SPOOF-5 R5-genuine-execution
A-261030-0001         S-SPOOF-5 R5-genuine-execution

timing: simulate 11.0s, detect 2.1s, discriminators+baseline 1.4s