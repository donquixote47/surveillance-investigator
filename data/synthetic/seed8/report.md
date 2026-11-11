# Dataset seed8

seed 8, 20 sessions 2026-11-02..2026-11-27, generator market-sim-0.1, detector spoof-naive-v1 {"cancel_pct": 70.0, "cancel_within_s": 5.0, "cooldown_s": 900.0, "k_depth": 4.0, "large_quick_k": 6.0, "large_quick_within_s": 10.0, "layering_min_levels": 3, "window_s": 60.0}

- order events: 1,813,710; trades: 141,377; traders: 123
- alerts: 100 (24 TRUE_ABUSE = 24%; 1 background)
- detector recall on injected abuse: 100%; precision: 24%
- missed injections: 2

      date scenario_id  trader_id          truth
2026-11-06    F-STOP-1 T-X1106-05 FALSE_POSITIVE
2026-11-06 F-PARTIAL-1 T-X1106-10 FALSE_POSITIVE

## Coverage per scenario (injected vs alerts attributed)

                    injected  alerts  missed_injections
F-ALGO-1                  22      22                  0
F-FAT-1                    3       3                  0
F-ICE-1                    6       6                  0
F-MM-1                    17      17                  0
F-NEWS-1                   6       6                  0
F-PARTIAL-1                6       5                  1
F-RISK-1                   4       4                  0
F-SPOOFLIKE-HARD-1         7       7                  0
F-STOP-1                   6       5                  1
S-LAYER-1                  3       3                  0
S-SPOOF-1                 11      11                  0
S-SPOOF-2                  5       5                  0
S-SPOOF-3                  3       3                  0
S-SPOOF-4                  2       2                  0

## Threshold baseline (no LLM)

- gate: 1 TRUE_ABUSE alerts proposed CLOSE_FP -> GATE FAILED; safe close rate reported as n/a
- safe close rate: n/a (gate failed) (raw 91%)

Share proposed CLOSE_FP per scenario:

                    close_fp_share  alerts
injected_scenario                         
BACKGROUND                     1.0       1
F-ALGO-1                       1.0      22
F-FAT-1                        1.0       3
F-ICE-1                        1.0       6
F-MM-1                         1.0      17
F-NEWS-1                       1.0       6
F-PARTIAL-1                    1.0       5
F-RISK-1                       1.0       4
F-SPOOFLIKE-HARD-1             0.0       7
F-STOP-1                       1.0       5
S-LAYER-1                      0.0       3
S-SPOOF-1                      0.0      11
S-SPOOF-2                      0.2       5
S-SPOOF-3                      0.0       3
S-SPOOF-4                      0.0       2

Gate failures:

     alert_id injected_scenario   baseline_rule
A-261106-0006         S-SPOOF-2 R7-adverse-move

timing: simulate 11.4s, detect 2.1s, discriminators+baseline 1.0s