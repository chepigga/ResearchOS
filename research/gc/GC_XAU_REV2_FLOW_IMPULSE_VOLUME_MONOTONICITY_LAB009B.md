# GC_XAU_REV2_FLOW_IMPULSE_VOLUME_MONOTONICITY_LAB009B

Status: MONOTONICITY_AUDIT_NOT_OOS

| Clock | Feature | Period | LOW N/+2/EV | MID N/+2/EV | HIGH N/+2/EV | Train monotonic | Valid H>L | Strong |
|---:|---|---|---|---|---|---|---|---|
| 5s | post_signed_impulse_atr | TRAIN | 28/7.1%/-0.432 | 2/0.0%/-0.909 | 16/37.5%/1.384 | False | True | False |
| 5s | post_signed_impulse_atr | VALID | 36/16.7%/-0.352 | 5/40.0%/0.705 | 20/35.0%/0.567 | False | True | False |
| 5s | post_signed_impulse_atr | POST_CHECK | 26/23.1%/0.008 | 4/25.0%/0.628 | 10/40.0%/0.650 | False | True | False |
| 30s | volume_acceleration | TRAIN | 18/22.2%/-0.171 | 17/11.8%/-0.499 | 18/33.3%/1.436 | False | True | False |
| 30s | volume_acceleration | VALID | 22/27.3%/0.216 | 22/27.3%/-0.611 | 30/33.3%/0.359 | False | True | False |
| 30s | volume_acceleration | POST_CHECK | 13/30.8%/0.326 | 10/30.0%/0.605 | 22/18.2%/-0.147 | False | True | False |
| 30s | post_volume | TRAIN | 18/16.7%/-0.729 | 17/11.8%/-0.098 | 18/38.9%/1.615 | False | True | False |
| 30s | post_volume | VALID | 24/25.0%/-0.076 | 20/30.0%/-0.271 | 30/33.3%/0.311 | False | True | False |
| 30s | post_volume | POST_CHECK | 13/38.5%/0.457 | 13/7.7%/-0.491 | 19/26.3%/0.395 | False | True | False |
| 30s | post_aligned_volume | TRAIN | 20/15.0%/-0.736 | 15/13.3%/-0.010 | 18/38.9%/1.620 | False | True | False |
| 30s | post_aligned_volume | VALID | 24/29.2%/-0.045 | 14/14.3%/-0.499 | 36/36.1%/0.282 | False | True | False |
| 30s | post_aligned_volume | POST_CHECK | 14/21.4%/-0.063 | 9/22.2%/-0.292 | 22/27.3%/0.481 | False | True | False |
| 0s | attack2_volume | TRAIN | 18/16.7%/-0.025 | 18/16.7%/0.397 | 18/27.8%/0.210 | False | False | False |
| 0s | attack2_volume | VALID | 26/26.9%/-0.050 | 16/31.2%/0.318 | 32/15.6%/-0.215 | False | False | False |
| 0s | attack2_volume | POST_CHECK | 20/30.0%/0.210 | 12/8.3%/-0.832 | 13/30.8%/0.802 | False | False | False |

Strong candidates: NONE

Thresholds are TRAIN-only terciles and remain frozen in VALID/POST. No combinations or execution optimization.
