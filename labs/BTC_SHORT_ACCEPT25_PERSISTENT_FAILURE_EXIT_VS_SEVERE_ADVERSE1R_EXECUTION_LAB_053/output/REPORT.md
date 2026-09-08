# BTC_SHORT_ACCEPT25_PERSISTENT_FAILURE_EXIT_VS_SEVERE_ADVERSE1R_EXECUTION_LAB_053

**Verdict: WATCH_PERSISTENT_EXIT_ECONOMICS_IMPROVE_PROOF_OR_TRANSFER_INCOMPLETE — 18/20**

## Frozen parity
- Parent trades **327**; ADVERSE_FIRST **145**; PERSISTENT_FAILURE **59**; OCO early exits **59**.
- Parent 5bps max parity error **8.127e-14**; Severe1R-control parity error **0.000e+00**.

## Full execution economics

| Policy | Trades | Early exits | EV 5bps | PF | CumR | MaxDD R | DD @0.25% | EV/original | EV 10bps |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| PARENT_HOLD | 327 | 0 | +0.086 | 1.176 | +28.22 | 11.44 | 2.86% | +0.059 | +0.024 |
| PERSISTENT_EXIT | 327 | 59 | +0.101 | 1.228 | +33.17 | 9.79 | 2.45% | +0.070 | +0.040 |
| SEVERE_1R_CONTROL | 327 | 0 | +0.086 | 1.176 | +28.22 | 11.44 | 2.86% | +0.059 | +0.024 |
| OCO_PERSISTENT_OR_SEVERE | 327 | 59 | +0.101 | 1.228 | +33.17 | 9.79 | 2.45% | +0.070 | +0.040 |

Paired OCO−PARENT delta: **+0.015R/trade**, 7d bootstrap 95% CI **[-0.023, +0.049]**, clusters=196

## Transfer — OCO vs parent

| Slice | Orig N | Parent EV/orig | OCO EV/orig | Delta | Parent PF | OCO PF | OCO early exits |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2021 | 82 | +0.180 | +0.207 | +0.027 | 1.556 | 1.696 | 7 |
| 2022 | 79 | -0.025 | +0.014 | +0.039 | 0.930 | 1.049 | 12 |
| 2023 | 83 | -0.004 | -0.015 | -0.011 | 0.988 | 0.952 | 8 |
| 2024 | 94 | +0.057 | +0.058 | +0.001 | 1.177 | 1.193 | 16 |
| 2025_H1 | 46 | -0.080 | -0.038 | +0.042 | 0.795 | 0.891 | 4 |
| 2025_H2 | 44 | +0.088 | +0.151 | +0.063 | 1.248 | 1.519 | 4 |
| 2026_JAN_JUL | 47 | +0.216 | +0.127 | -0.089 | 1.631 | 1.384 | 8 |
| BAD_POOLED | 125 | -0.045 | -0.005 | +0.040 | 0.877 | 0.985 | 16 |
| RECENT_POOLED | 91 | +0.154 | +0.138 | -0.016 | 1.443 | 1.445 | 12 |

## Gates
- PASS — `exact_parent_n327`
- PASS — `exact_adverse_first_n145`
- PASS — `exact_persistent_failure_n59`
- PASS — `parent_5bps_parity_with_frozen_le1e9`
- PASS — `severe1r_control_parity_parent_le1e12`
- PASS — `oco_early_exit_n_ge40`
- PASS — `oco_full_ev_gt_parent`
- PASS — `oco_full_pf_gt_parent`
- PASS — `oco_cumr_gt_parent`
- PASS — `oco_maxdd_le_parent`
- PASS — `oco_ev_per_original_gt_parent`
- FAIL — `paired_delta_gt_003r_per_trade`
- FAIL — `paired_boot_lower_gt0`
- PASS — `2022_oco_evperorig_ge_parent`
- PASS — `2025h1_oco_evperorig_ge_parent`
- PASS — `bad_pooled_oco_evperorig_gt_parent`
- PASS — `recent_pooled_oco_evperorig_positive`
- PASS — `2026_degradation_no_worse_than_minus010r_per_original`
- PASS — `oco_10bps_ev_positive`
- PASS — `no_august_selection_no_new_threshold`

## Guardrail
Execution test only. Severe +1R is the frozen parent SL control. No new signal, threshold, stop, target, time exit, re-entry, sizing, or allocation rule was searched. Reused historical lineage; not fresh OOS. Live allocation = **0**.
