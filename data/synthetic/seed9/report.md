# Dataset seed9

seed 9, 12 sessions 2026-09-14..2026-09-29, generator market-sim-0.1 (scenario catalogue 3), detector spoof-naive-v1 {"cancel_pct": 70.0, "cancel_within_s": 5.0, "cooldown_s": 900.0, "k_depth": 4.0, "large_quick_k": 6.0, "large_quick_within_s": 10.0, "layering_min_levels": 3, "window_s": 60.0}

FOCUSED SET: every session injects exactly S-SPOOF-6, F-MM-LARGE-1, F-MM-1, F-SPOOFLIKE-HARD-1; nothing is sampled. Its headline numbers are not comparable with a sampled dataset's.

- order events: 1,086,930; trades: 83,447; traders: 70
- alerts: 48 (12 TRUE_ABUSE = 25%; 0 background)
- detector recall on injected abuse: 100%; precision: 25%
- missed injections: 0

## Coverage per scenario (injected vs alerts attributed)

                    injected  alerts  missed_injections
F-MM-1                    12      12                  0
F-MM-LARGE-1              12      12                  0
F-SPOOFLIKE-HARD-1        12      12                  0
S-SPOOF-6                 12      12                  0

## Threshold baseline (no LLM)

- gate: 12 TRUE_ABUSE alerts proposed CLOSE_FP -> GATE FAILED; safe close rate reported as n/a
- safe close rate: n/a (gate failed) (raw 69%)

Share proposed CLOSE_FP per scenario:

                    close_fp_share  alerts
injected_scenario                         
F-MM-1                    1.000000      12
F-MM-LARGE-1              1.000000      12
F-SPOOFLIKE-HARD-1        0.083333      12
S-SPOOF-6                 1.000000      12

Gate failures:

     alert_id injected_scenario    baseline_rule
A-260914-0003         S-SPOOF-6 R1-registered-mm
A-260915-0001         S-SPOOF-6 R1-registered-mm
A-260916-0004         S-SPOOF-6 R1-registered-mm
A-260917-0002         S-SPOOF-6 R1-registered-mm
A-260918-0003         S-SPOOF-6 R1-registered-mm
A-260921-0001         S-SPOOF-6 R1-registered-mm
A-260922-0002         S-SPOOF-6 R1-registered-mm
A-260923-0002         S-SPOOF-6 R1-registered-mm
A-260924-0001         S-SPOOF-6 R1-registered-mm
A-260925-0004         S-SPOOF-6 R1-registered-mm
A-260928-0004         S-SPOOF-6 R1-registered-mm
A-260929-0002         S-SPOOF-6 R1-registered-mm

timing: simulate 7.2s, detect 1.4s, discriminators+baseline 0.7s