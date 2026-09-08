# BTC_SHORT_ACCEPT25_ATR_X_72H_EXTENSION_FAILURE_INTERACTION_LAB_050

**Verdict: FAIL_NO_ATR_X_EXTENSION_INTERACTION — 8/15**

## Frozen continuous interaction
- ATR main coefficient: **-0.1055R** per full rank move
- EXT72 main coefficient: **-0.0184R per ATR of prior extension**
- ATR×EXT72 interaction: **+0.0395R**
- 7d cluster bootstrap interaction 95% CI: **[-0.0214, +0.0961]**, clusters=197

## Frozen ATR-band extension diagnostics

| Band | N | EV | PF | EXT mean | EXT rho->R | EXT slope |
|---|---:|---:|---:|---:|---:|---:|
| LOW_BAND | 111 | -0.090 | 0.847 | 14.55 | -0.169 | -0.0158 |
| MID_SPIKE | 67 | +0.244 | 1.557 | 11.13 | +0.165 | +0.0207 |
| DEAD_MID | 79 | +0.002 | 1.003 | 10.22 | -0.021 | +0.0062 |
| TOP_BAND | 70 | +0.310 | 1.765 | 8.82 | +0.181 | +0.0155 |

## Leave-one-period-out interaction

| Left out | N | Interaction | ATR main | EXT main |
|---|---:|---:|---:|---:|
| 2021 | 265 | +0.0369 | -0.1790 | -0.0182 |
| 2022 | 278 | +0.0528 | -0.1691 | -0.0162 |
| 2023 | 275 | +0.0422 | -0.0654 | -0.0153 |
| 2024 | 263 | +0.0237 | +0.1400 | -0.0197 |
| 2025_H1 | 295 | +0.0355 | -0.0575 | -0.0227 |
| 2025_H2 | 294 | +0.0404 | -0.1077 | -0.0102 |
| 2026_JAN_JUL | 292 | +0.0422 | -0.2389 | -0.0239 |

Negative interaction sign in **0/7** LOPO samples.

## Period stress

| Period | N | EV | ATR mean | EXT mean | TOP n | TOP EV | TOP EXT mean | Marginal ATR effect @ period EXT |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2021 | 62 | +0.238 | 0.509 | 9.37 | 10 | +0.913 | 9.36 | +0.265 |
| 2022 | 49 | -0.040 | 0.422 | 14.48 | 5 | -0.034 | 13.85 | +0.466 |
| 2023 | 52 | -0.006 | 0.606 | 10.73 | 14 | +0.209 | 7.33 | +0.318 |
| 2024 | 64 | +0.084 | 0.657 | 10.24 | 22 | +0.093 | 8.82 | +0.299 |
| 2025_H1 | 32 | -0.114 | 0.459 | 12.61 | 4 | -0.417 | 5.64 | +0.392 |
| 2025_H2 | 33 | +0.117 | 0.596 | 13.99 | 8 | +0.366 | 9.02 | +0.447 |
| 2026_JAN_JUL | 35 | +0.290 | 0.494 | 11.92 | 7 | +0.930 | 8.97 | +0.365 |

2025_H1 TOP mean EXT72: **5.64 ATR**; pooled profitable TOP periods: **8.61 ATR**

## Gates
- PASS — `exact_frozen_n327`
- PASS — `atr_coverage_ge99pct`
- PASS — `ext72_coverage_ge99pct`
- FAIL — `interaction_beta_negative`
- FAIL — `interaction_boot_upper_lt0`
- FAIL — `interaction_negative_at_least_5_of_7_lopo`
- FAIL — `top_band_ext_slope_negative`
- FAIL — `top_band_ext_rho_negative`
- FAIL — `2025h1_top_ext_gt_profitable_top_ext`
- PASS — `2025h2_and_2026_top_positive`
- FAIL — `period_fixed_atr_main_positive`
- PASS — `period_fixed_ext_main_nonpositive`
- PASS — `2022_marginal_atr_effect_nonnegative`
- PASS — `no_new_cutoff_router_searched`
- PASS — `august_not_used_for_selection`

## Guardrail
Interaction audit only. No extension cutoff, ATR cutoff, stop, target, entry, or time-exit was searched or promoted. Reused historical lineage; not fresh OOS. Live allocation = **0**.
