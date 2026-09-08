# BTC_SHORT_ACCEPT25_ATR_NONLINEAR_SHAPE_AND_LEAVE_ONE_PERIOD_OUT_STABILITY_LAB_049

**Verdict: FAIL_ATR_NONLINEAR_SHAPE_PERIOD_DEPENDENT — 15/18**

## Frozen full-sample shape

| Band | N | EV | PF | CumR |
|---|---:|---:|---:|---:|
| LOW_BAND | 111 | -0.090 | 0.847 | -9.97 |
| MID_SPIKE | 67 | +0.244 | 1.557 | +16.35 |
| DEAD_MID | 79 | +0.002 | 1.003 | +0.12 |
| TOP_BAND | 70 | +0.310 | 1.765 | +21.71 |

TOP-LOW gap: **+0.400R**, 7d bootstrap 95% CI **[+0.085, +0.718]**
MID_SPIKE-LOW gap: **+0.334R**, bootstrap **[-0.030, +0.665]**

## Leave-one-period-out stability

| Left out | N | TOP EV | LOW EV | TOP-LOW | Boot 95% CI | MID EV | MID-LOW |
|---|---:|---:|---:|---:|---|---:|---:|
| 2021 | 265 | +0.210 | -0.092 | +0.302 | [-0.055, +0.646] | +0.206 | +0.298 |
| 2022 | 278 | +0.337 | -0.059 | +0.396 | [+0.039, +0.744] | +0.213 | +0.272 |
| 2023 | 275 | +0.335 | -0.089 | +0.425 | [+0.042, +0.801] | +0.216 | +0.305 |
| 2024 | 263 | +0.410 | -0.102 | +0.512 | [+0.153, +0.852] | +0.199 | +0.301 |
| 2025_H1 | 295 | +0.354 | -0.075 | +0.429 | [+0.092, +0.774] | +0.290 | +0.366 |
| 2025_H2 | 294 | +0.303 | -0.080 | +0.383 | [+0.019, +0.745] | +0.287 | +0.367 |
| 2026_JAN_JUL | 292 | +0.241 | -0.128 | +0.369 | [+0.009, +0.718] | +0.291 | +0.419 |

Primary bootstrap lower >0 in **6/7** LOPO samples; LOW_BAND <=0 in **7/7**.

## Period stress and MID_SPIKE concentration

| Period | N | TOP n | LOW n | TOP EV | LOW EV | TOP-LOW | MID n | MID EV | MID CumR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2021 | 62 | 10 | 23 | +0.913 | -0.080 | +0.994 | 14 | +0.389 | +5.45 |
| 2022 | 49 | 5 | 26 | -0.034 | -0.190 | +0.156 | 10 | +0.423 | +4.23 |
| 2023 | 52 | 14 | 14 | +0.209 | -0.094 | +0.303 | 8 | +0.449 | +3.60 |
| 2024 | 64 | 22 | 12 | +0.093 | +0.013 | +0.081 | 10 | +0.500 | +5.00 |
| 2025_H1 | 32 | 4 | 14 | -0.417 | -0.191 | -0.226 | 7 | -0.154 | -1.08 |
| 2025_H2 | 33 | 8 | 8 | +0.366 | -0.221 | +0.586 | 7 | -0.124 | -0.87 |
| 2026_JAN_JUL | 35 | 7 | 14 | +0.930 | +0.173 | +0.757 | 11 | +0.002 | +0.03 |

Combined 2022+2025_H1 TOP-LOW: **-0.014R**, bootstrap **[-0.862, +0.885]**
MID_SPIKE maximum single-period share of absolute CumR contribution: **26.9%**

## Gates
- PASS — `exact_frozen_accept25_n327`
- PASS — `atr_rank_coverage_ge99pct`
- PASS — `full_top_minus_low_gap_gt_025r`
- PASS — `full_top_minus_low_boot_lower_gt0`
- PASS — `top_band_ev_positive_all_7_lopo`
- PASS — `low_band_ev_nonpositive_at_least_6_of_7_lopo`
- PASS — `top_minus_low_gap_positive_all_7_lopo`
- PASS — `top_minus_low_boot_lower_gt0_at_least_5_of_7_lopo`
- FAIL — `combined_2022_2025h1_top_minus_low_positive`
- FAIL — `combined_bad_boot_lower_gt0`
- PASS — `leave_2025h2_out_top_minus_low_positive`
- PASS — `leave_2026_out_top_minus_low_positive`
- PASS — `2022_top_minus_low_positive`
- FAIL — `2025h1_top_minus_low_positive`
- PASS — `mid_spike_ev_positive_all_7_lopo`
- PASS — `mid_spike_minus_low_positive_all_7_lopo`
- PASS — `mid_spike_no_single_period_gt50pct_abs_contribution`
- PASS — `august_not_used_for_selection`

## Guardrail
No new ATR cutoff/router was searched or promoted. Exact frozen execution/payoff and absolute LAB048 bands only. Reused historical lineage; not fresh OOS. Live allocation = **0**.
