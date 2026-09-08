# BTC_RETAIL_FLOW_REACCEPTANCE_POST_RECOVERY_PERSISTENCE_AND_SECOND_FAILURE_LAB_031

**Verdict: WATCH_PERSISTENCE_DISCRIMINATIVE_TRANSFER_INCOMPLETE — 10/14**

## Frozen lineage
- FULL_REACCEPT total: **703**, pre-Aug: **701**

## Post-reaccept states by window

| Window | N | Persist2 | Rate | Persist residual | PF | Win | Second fail | Second residual | Gap | Unresolved |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2021 | 154 | 74 | 0.481 | -0.427 | 0.696 | 0.432 | 57 | 0.593 | -1.021 | 23 |
| 2022 | 107 | 56 | 0.523 | 0.338 | 1.321 | 0.571 | 35 | 0.635 | -0.297 | 16 |
| 2023 | 122 | 58 | 0.475 | 0.046 | 1.023 | 0.483 | 39 | 0.180 | -0.134 | 25 |
| 2024 | 122 | 56 | 0.459 | 1.305 | 2.941 | 0.607 | 50 | -0.543 | 1.848 | 16 |
| 2025_H1 | 59 | 33 | 0.559 | -0.527 | 0.677 | 0.455 | 17 | 0.246 | -0.773 | 9 |
| 2025_H2 | 65 | 33 | 0.508 | -0.769 | 0.628 | 0.485 | 21 | -0.016 | -0.753 | 11 |
| 2026_JAN_JUL | 65 | 33 | 0.508 | 1.213 | 2.165 | 0.545 | 24 | 0.107 | 1.105 | 8 |
| AUG2026_REUSED_AUDIT | 2 | 1 | 0.500 | -12.702 | 0.000 | 0.000 | 1 | -0.955 | -11.747 | 0 |
| HIST | 564 | 277 | 0.491 | 0.165 | 1.123 | 0.509 | 198 | 0.202 | -0.038 | 89 |
| RECENT | 130 | 66 | 0.508 | 0.222 | 1.143 | 0.515 | 45 | 0.050 | 0.172 | 19 |
| ALL_PRE_AUG | 694 | 343 | 0.494 | 0.176 | 1.127 | 0.510 | 243 | 0.174 | 0.002 | 108 |

## By side pre-Aug

| Side | N | Persist2 | Persist residual | Second residual | Gap | PF | Win |
|---|---:|---:|---:|---:|---:|---:|---:|
| LONG | 320 | 148 | 0.033 | -0.109 | 0.142 | 1.023 | 0.459 |
| SHORT | 374 | 195 | 0.284 | 0.433 | -0.149 | 1.209 | 0.549 |

## 7d cluster bootstrap
- clusters: **260**, draws: **5000**
- PERSIST2 minus SECOND_FAIL residual: **0.002 ATR**, 95% CI **[-0.777, 0.756]**

## Primary anatomy
- pre-Aug median reaccept→PERSIST2 classification: **0.500 h**
- PERSIST2 median post-class MAE/MFE: **1.914 / 2.546 ATR**

## Secondary first-passage audit
- +0.5 ATR first: **600**
- SECOND_FAIL first: **85**

## Gates
- PASS — `exact_lab030_full_reaccept_lineage_ge_690`
- PASS — `persist2_n_ge_150`
- PASS — `second_fail_n_ge_80`
- PASS — `persist2_residual_positive`
- PASS — `second_fail_residual_lt_persist2`
- FAIL — `residual_gap_ge_0_50atr`
- FAIL — `bootstrap_ci_lower_gt_zero`
- PASS — `recent_persist2_n_ge_30`
- PASS — `recent_persist2_residual_positive`
- PASS — `recent_persist_gt_second_fail`
- FAIL — `2025h2_and_2026_persist_positive`
- PASS — `2022_short_persist_n15_residual_positive`
- PASS — `long_and_short_persist_positive`
- FAIL — `persist_win_rate_gt_55pct`

## Guardrail
PERSIST2 uses only the first two completed M15 closes after FULL_REACCEPT. No later qualifying pair can rescue it. No threshold/horizon/side optimization. August 2026 reused audit only. Live allocation = **0**.
