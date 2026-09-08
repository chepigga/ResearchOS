# BTC_SHORT_PERSISTENT_FAILURE_EXIT_NOW_VS_REACCEPTANCE_OCO_LAB_054

**Verdict: FAIL_WAIT_OCO_DOES_NOT_BEAT_EXIT_NOW — 13/20**

- Parent N **327**; ADVERSE_FIRST **145**; PERSISTENT **59**; OCO resolved **52** (REACCEPT 13, EXTENSION 39).
- Parent parity **2.220e-16**; EXIT_NOW parity **2.220e-16**.

## Full economics

| Policy | EV 5bps | PF | CumR | MaxDD R | DD @0.25% | EV/original | EV 10bps |
|---|---:|---:|---:|---:|---:|---:|---:|
| PARENT_HOLD | +0.086 | 1.176 | +28.22 | 11.44 | 2.86% | +0.059 | +0.024 |
| EXIT_NOW | +0.101 | 1.228 | +33.17 | 9.79 | 2.45% | +0.070 | +0.040 |
| WAIT_REACCEPT_OCO | +0.090 | 1.190 | +29.45 | 13.07 | 3.27% | +0.062 | +0.028 |

WAIT−EXIT paired delta **-0.011R/trade**, 7d bootstrap 95% CI **[-0.037, +0.018]**.
WAIT−PARENT paired delta **+0.004R/trade**, 95% CI **[-0.020, +0.024]**.

## Transfer

| Slice | Parent EV/orig | EXIT NOW | WAIT OCO | WAIT−EXIT |
|---|---:|---:|---:|---:|
| 2021 | +0.180 | +0.207 | +0.186 | -0.020 |
| 2022 | -0.025 | +0.014 | -0.020 | -0.034 |
| 2023 | -0.004 | -0.015 | -0.021 | -0.007 |
| 2024 | +0.057 | +0.058 | +0.059 | +0.001 |
| 2025_H1 | -0.080 | -0.038 | -0.066 | -0.028 |
| 2025_H2 | +0.088 | +0.151 | +0.120 | -0.031 |
| 2026_JAN_JUL | +0.216 | +0.127 | +0.206 | +0.079 |
| BAD_POOLED | -0.045 | -0.005 | -0.037 | -0.032 |
| RECENT_POOLED | +0.154 | +0.138 | +0.164 | +0.026 |

## Gates
- PASS — `exact_parent_n327`
- PASS — `exact_adverse_n145`
- PASS — `exact_persistent_n59`
- PASS — `path_coverage_ge99pct`
- PASS — `parent_parity_le1e9`
- PASS — `exit_now_parity_le1e9`
- PASS — `oco_resolved_n_ge30`
- PASS — `reaccept_n_ge10`
- PASS — `extension_n_ge10`
- FAIL — `wait_full_ev_gt_exit`
- FAIL — `wait_full_pf_gt_exit`
- FAIL — `wait_cumr_gt_exit`
- FAIL — `wait_dd_le_exit`
- FAIL — `paired_wait_exit_delta_gt0`
- FAIL — `paired_wait_exit_boot_lower_gt0`
- PASS — `2026_wait_evorig_gt_exit`
- FAIL — `bad_wait_not_worse_than_exit_minus002`
- PASS — `recent_wait_evorig_positive`
- PASS — `wait_10bps_ev_positive`
- PASS — `no_august_no_new_threshold`

## Guardrail
Final reused-sample post-failure management decision LAB. No further sequence refinement is promoted from this lineage. Not fresh OOS. Live allocation = **0**.