# GC_XAU_REV2_FLOW_IMPULSE_VOLUME_QUALITY_LAB009

Status: REV2_QUALITY_DISCOVERY_NOT_OOS

## Base by confirmation clock

| Clock | Period | N | +2ATR | +3ATR | Fixed5m EV ATR |
|---:|---|---:|---:|---:|---:|
| 0s | TRAIN | 54 | 20.4% | 7.4% | 0.194 |
| 0s | VALID | 74 | 23.0% | 9.5% | -0.042 |
| 0s | POST_CHECK | 45 | 24.4% | 17.8% | 0.103 |
| 5s | TRAIN | 53 | 17.0% | 5.7% | 0.195 |
| 5s | VALID | 74 | 25.7% | 8.1% | 0.002 |
| 5s | POST_CHECK | 45 | 26.7% | 17.8% | 0.190 |
| 15s | TRAIN | 54 | 18.5% | 7.4% | 0.171 |
| 15s | VALID | 72 | 27.8% | 6.9% | 0.016 |
| 15s | POST_CHECK | 44 | 27.3% | 18.2% | 0.094 |
| 30s | TRAIN | 54 | 22.2% | 9.3% | 0.240 |
| 30s | VALID | 74 | 29.7% | 5.4% | 0.028 |
| 30s | POST_CHECK | 45 | 24.4% | 20.0% | 0.157 |

## Frozen TRAIN-tail tests

| Clock | Feature | Tail | Thr | Train N | T lift | T EV | Valid N | V lift | V EV | Post lift | Post EV | Gate |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 5s | post_impulse_efficiency | Q5 | 0.0246 | 10 | 1.15x | -0.247 | 9 | 1.81x | 0.907 | 2.73x | 2.076 | FAIL |
| 0s | abs_attack2_delta_frac | Q1 | 0.0483 | 11 | 0.89x | 0.082 | 10 | 1.74x | 0.262 | 0.00x | -0.930 | FAIL |
| 5s | post_signed_impulse_atr | Q5 | 0.1707 | 10 | 2.30x | 0.564 | 16 | 1.53x | 0.490 | 1.82x | 0.993 | FAIL |
| 5s | post_opposite_volume | Q5 | 11.0000 | 10 | 1.15x | 2.058 | 11 | 1.48x | -0.117 | 0.73x | 0.489 | FAIL |
| 30s | post_impulse_efficiency | Q5 | 0.0169 | 11 | 0.80x | -0.467 | 7 | 1.44x | 0.415 | 2.45x | 1.452 | FAIL |
| 5s | gc_xau_lead_gap | Q5 | 0.0940 | 10 | 1.15x | -0.182 | 17 | 1.44x | 0.246 | 1.56x | 1.160 | FAIL |
| 30s | volume_acceleration | Q5 | 1.9083 | 11 | 1.61x | 0.685 | 17 | 1.39x | 0.665 | 0.74x | 0.219 | FAIL |
| 15s | post_aligned_share | Q1 | 0.2316 | 11 | 0.48x | -0.500 | 8 | 1.36x | -0.665 | 0.73x | -0.315 | FAIL |
| 15s | post_aligned_delta_frac | Q1 | -0.5368 | 11 | 0.48x | -0.500 | 8 | 1.36x | -0.665 | 0.73x | -0.315 | FAIL |
| 30s | post_opposite_volume | Q5 | 47.6000 | 11 | 1.61x | 0.789 | 20 | 1.35x | 0.449 | 0.58x | 0.571 | FAIL |
| 30s | post_volume | Q5 | 80.8000 | 11 | 2.01x | 2.409 | 23 | 1.32x | 0.312 | 0.45x | 0.367 | FAIL |
| 5s | xau_signed_move_confirm_atr | Q5 | 0.1530 | 11 | 2.68x | 0.404 | 15 | 1.30x | 0.214 | 1.61x | 0.483 | FAIL |
| 5s | post_volume | Q5 | 17.0000 | 10 | 1.15x | 2.312 | 13 | 1.25x | 0.077 | 1.21x | 0.698 | FAIL |
| 30s | post_aligned_volume | Q5 | 36.0000 | 12 | 1.84x | 2.541 | 26 | 1.16x | 0.280 | 0.68x | 0.212 | FAIL |
| 0s | impact_deterioration | Q1 | 0.1770 | 11 | 1.34x | 0.025 | 15 | 1.16x | 0.105 | 0.91x | -0.134 | FAIL |
| 15s | post_impulse_efficiency | Q1 | -0.0072 | 11 | 0.96x | -1.345 | 19 | 1.15x | -0.117 | 0.46x | -0.239 | FAIL |
| 15s | gc_xau_lead_gap | Q5 | 0.1089 | 11 | 1.45x | -0.264 | 13 | 1.12x | -0.438 | 1.10x | 0.416 | FAIL |
| 0s | volume_ratio_2_to_1 | Q1 | 0.4595 | 11 | 1.34x | 0.129 | 16 | 1.09x | -0.138 | 1.02x | -0.197 | FAIL |
| 15s | aligned_delta_acceleration | Q1 | -0.4951 | 11 | 0.47x | -0.519 | 14 | 1.08x | -0.188 | 1.30x | 0.336 | FAIL |
| 0s | attack2_delta_frac_aligned | Q1 | -0.2970 | 11 | 0.89x | -0.385 | 21 | 1.04x | -0.079 | 1.46x | -0.155 | FAIL |
| 0s | rev2_aligned_aggr_share | Q1 | 0.3515 | 11 | 0.89x | -0.385 | 21 | 1.04x | -0.079 | 1.46x | -0.155 | FAIL |
| 0s | attack2_volume | Q5 | 86.0000 | 11 | 1.79x | 0.462 | 17 | 1.02x | 0.240 | 1.82x | 1.534 | FAIL |
| 15s | post_volume | Q5 | 39.0000 | 12 | 1.32x | 1.589 | 25 | 1.02x | 0.481 | 1.33x | 0.462 | FAIL |
| 5s | post_aligned_volume | Q5 | 7.0000 | 11 | 1.57x | 2.403 | 16 | 1.02x | 0.118 | 0.91x | 0.001 | FAIL |
| 0s | attack1_delta_frac_aligned | Q1 | -0.4485 | 11 | 0.45x | -0.114 | 13 | 1.00x | -0.180 | 1.57x | 0.194 | FAIL |
| 15s | post_aligned_volume | Q5 | 13.6000 | 11 | 2.41x | 2.671 | 29 | 1.00x | 0.499 | 1.05x | 0.165 | FAIL |
| 30s | xau_signed_move_confirm_atr | Q1 | -0.4147 | 11 | 1.23x | -0.073 | 16 | 0.84x | -0.813 | 1.02x | 0.927 | FAIL |
| 15s | post_signed_impulse_atr | Q1 | -0.1412 | 11 | 1.45x | -0.975 | 22 | 0.83x | -0.014 | 0.65x | -0.022 | FAIL |
| 15s | post_opposite_volume | Q5 | 27.6000 | 11 | 1.45x | 0.443 | 18 | 0.81x | 0.058 | 1.05x | 0.347 | FAIL |
| 30s | post_signed_impulse_atr | Q1 | -0.2895 | 11 | 1.20x | 0.399 | 18 | 0.75x | -0.845 | 0.82x | 0.434 | FAIL |
| 0s | attack2_signed_impact | Q1 | -0.3552 | 11 | 0.89x | 0.063 | 6 | 0.73x | -0.186 | 0.00x | -0.328 | FAIL |
| 5s | post_aligned_share | Q1 | 0.1000 | 10 | 1.15x | -0.544 | 12 | 0.68x | -0.441 | 1.04x | 0.184 | FAIL |
| 5s | post_aligned_delta_frac | Q1 | -0.8000 | 10 | 1.15x | -0.544 | 12 | 0.68x | -0.441 | 1.04x | 0.184 | FAIL |
| 15s | xau_signed_move_confirm_atr | Q1 | -0.1933 | 11 | 1.47x | -0.716 | 22 | 0.65x | -0.489 | 0.73x | 0.038 | FAIL |
| 15s | volume_acceleration | Q5 | 2.8889 | 11 | 1.89x | 1.061 | 12 | 0.63x | 0.489 | 1.17x | -0.002 | FAIL |
| 30s | post_aligned_share | Q1 | 0.3279 | 11 | 1.20x | 0.206 | 11 | 0.61x | -0.846 | 0.58x | -0.298 | FAIL |
| 30s | post_aligned_delta_frac | Q1 | -0.3441 | 11 | 1.20x | 0.206 | 11 | 0.61x | -0.846 | 0.58x | -0.298 | FAIL |
| 0s | attack1_volume | Q1 | 14.6000 | 11 | 1.34x | -0.267 | 9 | 0.48x | -1.092 | 1.36x | -0.183 | FAIL |
| 30s | aligned_delta_acceleration | Q1 | -0.1380 | 11 | 1.20x | 0.401 | 8 | 0.42x | -0.752 | 0.58x | -0.051 | FAIL |
| 30s | gc_xau_lead_gap | Q5 | 0.1469 | 11 | 1.20x | -0.647 | 8 | 0.42x | -1.564 | 2.45x | 1.319 | FAIL |

Survivors: NONE

Delayed 5s/15s/30s features are evaluated only from their confirmation-end clock; no future leakage from REV2 t0.
