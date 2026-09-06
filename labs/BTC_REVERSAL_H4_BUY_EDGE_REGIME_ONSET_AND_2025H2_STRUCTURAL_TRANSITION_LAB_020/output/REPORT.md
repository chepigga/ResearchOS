# BTC_REVERSAL_H4_BUY_EDGE_REGIME_ONSET_AND_2025H2_STRUCTURAL_TRANSITION_LAB_020

**Verdict: FAIL_NO_CAUSAL_REGIME_ONSET_SUPPORT — 4/5**

## Part A — BUY outcome change point

- Best split: **2025-07-02 04:15:00+00:00**
- Pre: N=24, mean -0.384R, PF 0.527, DD 12.88R
- Post: N=13, mean +0.850R, PF 5.619, DD 1.22R
- Mean shift: +1.234R/fill
- Episode-bootstrap best-split in Apr-Oct 2025: **57.5%** (valid=5000); IQR 2025-02-27 00:15:00+00:00 .. 2025-07-02 04:15:00+00:00

## Part B — stable causal state shifts

| Feature | Cliff H1→H2 | Cliff hist→recent | Stable | Structural |
|---|---:|---:|---|---|
| parent_range_pct | -0.879 | -0.497 | YES | yes |
| ret_24h | +0.363 | +0.189 | no | yes |
| ret_72h | +0.615 | +0.228 | no | yes |
| ret_7d | +0.055 | +0.107 | no | yes |
| range_pos_7d | -0.176 | -0.028 | no | yes |
| range_pos_30d | +0.143 | -0.084 | no | yes |
| rv_ratio_24h_7d | -0.385 | -0.124 | no | yes |
| range_ratio_24h_7d | -0.242 | -0.052 | no | yes |
| parent_body_frac | -0.198 | +0.010 | no | yes |
| parent_reclaim_frac | +0.121 | +0.130 | no | yes |
| router_conf | +0.396 | -0.091 | no | no |
| child_latency_h | -0.016 | +0.074 | no | no |
| child_parent_range_ratio | +0.440 | +0.173 | no | no |
| prior_virtual_fills | +0.385 | +0.252 | no | no |
| episode_age_h | +0.220 | +0.351 | no | no |

Stable shifts: **1**, structural: **1**.

## Part C — H2-regime similarity transfer
Frozen threshold = median H2-2025 training score = **0.383**.

| Window | Regime-like | Opps | Real fills | CumR | MeanR | PF | DD |
|---|---|---:|---:|---:|---:|---:|---:|
| 2026_JAN_JUL | YES | 2 | 1 | +1.08 | +1.078 | inf | 0.00 |
| 2026_JAN_JUL | no | 15 | 5 | +4.05 | +0.810 | 4.458 | 1.17 |
| AUG2026_REUSED_AUDIT | YES | 2 | 2 | -2.92 | -1.461 | 0.000 | 2.92 |
| AUG2026_REUSED_AUDIT | no | 2 | 0 | +0.00 | — | — | 0.00 |

### Strongest period-fingerprint coefficients

| Feature | Standardized coefficient |
|---|---:|
| parent_range_pct | -2.018 |
| ret_72h | +0.842 |
| rv_ratio_24h_7d | +0.480 |
| range_pos_30d | -0.451 |
| episode_age_h | +0.415 |
| ret_24h | +0.414 |
| prior_virtual_fills | +0.370 |
| range_ratio_24h_7d | -0.364 |

## Gates
- PASS — `best_change_point_near_2025H2`
- PASS — `post_split_mean_gt_pre`
- FAIL — `stable_shifts_ge_3`
- PASS — `structural_stable_shift_ge_1`
- PASS — `2026_similarity_transfer_supportive`

## Guardrail
This LAB is diagnostic. No calendar date, classifier threshold or feature cutoff is promoted to live trading. Any regime router must be separately preregistered and replicated. Live allocation remains **0**.
