# BTC_RETAIL_FLOW_REACCEPTANCE_EXTENSION050_VS_SECOND_FAILURE_FIRST_PASSAGE_LAB_032

**Verdict: WATCH_EXTENSION050_POSITIVE_TRANSFER_INCOMPLETE — 11/14**

- FULL_REACCEPT total: **703**, pre-Aug: **701**

## First-passage states by window

| Window | N | Ext050 first | Ext residual | PF | Win | Second fail first | Second residual | Gap | Ambig | None |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2021 | 154 | 134 | 0.201 | 1.182 | 0.500 | 18 | -0.289 | 0.490 | 0 | 2 |
| 2022 | 109 | 93 | 0.605 | 1.600 | 0.559 | 13 | 1.317 | -0.712 | 0 | 3 |
| 2023 | 125 | 101 | 1.058 | 1.695 | 0.554 | 17 | -0.710 | 1.769 | 0 | 7 |
| 2024 | 122 | 106 | 0.570 | 1.437 | 0.519 | 16 | -0.723 | 1.293 | 0 | 0 |
| 2025_H1 | 59 | 54 | 0.476 | 1.403 | 0.537 | 5 | 1.418 | -0.942 | 0 | 0 |
| 2025_H2 | 66 | 56 | -0.140 | 0.921 | 0.482 | 8 | 0.261 | -0.401 | 0 | 2 |
| 2026_JAN_JUL | 66 | 56 | 1.316 | 2.063 | 0.571 | 8 | -0.883 | 2.199 | 0 | 2 |
| AUG2026_REUSED_AUDIT | 2 | 2 | -8.285 | 0.000 | 0.000 | 0 | — | — | 0 | 0 |
| HIST | 569 | 488 | 0.566 | 1.462 | 0.531 | 69 | -0.067 | 0.633 | 0 | 12 |
| RECENT | 132 | 112 | 0.588 | 1.391 | 0.527 | 16 | -0.311 | 0.899 | 0 | 4 |
| ALL_PRE_AUG | 701 | 600 | 0.570 | 1.447 | 0.530 | 85 | -0.113 | 0.683 | 0 | 16 |

## By side pre-Aug

| Side | N | Ext050 first | Ext residual | Second residual | Gap | PF | Win |
|---|---:|---:|---:|---:|---:|---:|---:|
| LONG | 325 | 278 | 0.311 | -0.514 | 0.825 | 1.236 | 0.493 |
| SHORT | 376 | 322 | 0.793 | 0.227 | 0.566 | 1.640 | 0.562 |

## 7d cluster bootstrap
- clusters: **267**, draws: **5000**
- EXTENSION050_FIRST minus SECOND_FAIL_FIRST residual: **0.683 ATR**, 95% CI **[-0.206, 1.668]**

## Anatomy
- median reaccept→extension classification: **0.250 h**
- EXTENSION050 post-class median MAE/MFE: **1.770 / 2.718 ATR**

## Gates
- PASS — `exact_lab030_full_reaccept_lineage_ge_690`
- PASS — `extension050_n_ge_200`
- PASS — `second_fail_n_ge_50`
- PASS — `ambiguous_rate_le_10pct`
- PASS — `extension050_residual_positive`
- PASS — `second_fail_residual_lt_extension`
- PASS — `residual_gap_ge_0_50atr`
- FAIL — `bootstrap_ci_lower_gt_zero`
- PASS — `recent_extension_n_ge_40`
- PASS — `recent_extension_residual_positive`
- FAIL — `2025h2_and_2026_extension_positive`
- PASS — `2022_short_extension_n15_residual_positive`
- PASS — `long_and_short_extension_positive`
- FAIL — `extension_win_rate_gt_55pct`

## Guardrail
Extension threshold is frozen at exactly +0.5 ATR beyond the acceptance entry. Same-bar extension/second-failure is AMBIGUOUS and excluded. No threshold/horizon/side rescue. August 2026 reused audit only. Live allocation = **0**.
