# BTC_RETAIL_FLOW_REACCEPTANCE_EXTENSION_SEQUENCE_LATENCY_AND_CYCLE_DURATION_REGIME_SPLIT_LAB_033

**Verdict: FAIL_NO_CAUSAL_SEQUENCE_REGIME_SPLIT — 6/12**

## Lineage / parity
- EXTENSION050 pre-Aug: **600**; 2025H2 **56**, 2026 Jan-Jul **56**
- Clock ordering: **100.000%**
- First failure timestamp parity: **93.039%**
- Full reaccept timestamp parity: **100.000%**

## Fixed feature tests: 2026 vs 2025H2

| Feature | Med 2025H2 | Med 2026 | RBC | p | BH q | rho→residual | p(rho) | Aligned |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| signal_to_accept_h | 0.250 | 0.250 | -0.067 | 0.433 | 0.712 | -0.045 | 0.268 | no |
| accept_to_failure_h | 1.250 | 1.000 | -0.073 | 0.507 | 0.712 | -0.012 | 0.762 | no |
| failure_to_origin_reclaim_h | 0.750 | 0.750 | 0.005 | 0.962 | 0.962 | -0.001 | 0.983 | no |
| failure_to_full_reaccept_h | 1.500 | 1.250 | -0.051 | 0.640 | 0.712 | -0.005 | 0.897 | no |
| reaccept_to_extension_h | 0.250 | 0.250 | 0.040 | 0.609 | 0.712 | -0.018 | 0.658 | no |
| signal_to_extension_h | 4.875 | 3.500 | -0.124 | 0.257 | 0.712 | 0.007 | 0.858 | no |
| accept_to_extension_h | 4.500 | 3.250 | -0.115 | 0.293 | 0.712 | 0.010 | 0.802 | no |
| extra_bad_closes_before_reaccept | 2.000 | 3.000 | -0.070 | 0.525 | 0.712 | -0.020 | 0.631 | no |
| cycle_count_accept_to_extension | 1.000 | 1.000 | -0.018 | 0.326 | 0.712 | -0.063 | 0.121 | no |
| origin_bad_close_count_accept_to_extension | 6.000 | 5.000 | -0.056 | 0.611 | 0.712 | -0.030 | 0.469 | no |

## Aligned-feature 7d cluster bootstrap

| Feature | 2026-2025H2 median diff | 95% CI |
|---|---:|---:|
| none | — | — |

## Side composition
- 2025H2 LONG/SHORT: **23/33**
- 2026 LONG/SHORT: **26/30**

## Gates
- PASS — `exact_lab032_extension050_pre_aug_ge_590`
- PASS — `2025h2_n45_and_2026_n45`
- PASS — `clock_ordering_ge_99pct`
- FAIL — `reconstructed_failure_parity_ge_99pct`
- PASS — `reconstructed_reaccept_parity_ge_99pct`
- FAIL — `at_least_one_feature_bh_q_le_0_10`
- FAIL — `at_least_one_feature_abs_rbc_ge_0_30`
- FAIL — `at_least_one_full_aligned_feature`
- FAIL — `aligned_feature_cluster_boot_ci_excludes_zero`
- FAIL — `aligned_feature_same_direction_within_side`
- PASS — `no_more_than_2_features_gt10pct_missing`
- PASS — `august_not_used_for_selection`

## Guardrail
This is a regime-mechanism audit only. No sequence cutoff/router is promoted from reused data. August 2026 is audit-only. Live allocation = **0**.
