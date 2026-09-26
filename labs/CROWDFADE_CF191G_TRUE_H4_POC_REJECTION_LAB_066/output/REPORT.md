# LAB066 — TRUE H4 VOLUME-PROFILE / POC REJECTION

Composite H4 events: historical=221, forward_2026=21; aggTrade days=231

## Event-level true POC outcomes

| period       | profile_class   |   N |   mean_ret_1h |   median_ret_1h |   mean_ret_4h |   median_ret_4h |   mean_ret_8h |   mean_ret_12h |   mean_mfe_4h |   mean_mae_4h |   mean_poc_location |   mean_lower_third_share |   mean_upper_third_share |
|:-------------|:----------------|----:|--------------:|----------------:|--------------:|----------------:|--------------:|---------------:|--------------:|--------------:|--------------------:|-------------------------:|-------------------------:|
| historical   | POC_ALIGNED     |  66 |   0.00120484  |     0.000269313 |   0.000442734 |    -0.00150213  |  -0.000575366 |   -9.25134e-05 |    0.0127674  |    0.00979306 |            0.447316 |                 0.291304 |                 0.345088 |
| historical   | POC_MIDDLE      |  93 |   0.0010912   |    -2.32631e-05 |  -0.00130874  |    -0.00177735  |  -0.000907583 |   -0.000560464 |    0.0114059  |    0.0122879  |            0.498082 |                 0.266077 |                 0.265793 |
| historical   | POC_OPPOSITE    |  62 |   0.000706681 |    -0.000687614 |  -0.0011355   |    -0.0010176   |  -0.00312592  |   -0.00498999  |    0.00985803 |    0.0104519  |            0.465101 |                 0.326073 |                 0.347571 |
| forward_2026 | POC_ALIGNED     |  10 |  -0.000344361 |     0.000996423 |  -0.000545718 |    -0.000785321 |  -0.00309846  |   -0.00277324  |    0.0051808  |    0.00565636 |            0.502485 |                 0.363186 |                 0.271927 |
| forward_2026 | POC_MIDDLE      |   6 |  -0.000905099 |    -0.00136746  |  -0.00577447  |    -0.00643847  |  -0.00192145  |   -0.0103692   |    0.00688836 |    0.0116839  |            0.532036 |                 0.253979 |                 0.266727 |
| forward_2026 | POC_OPPOSITE    |   5 |  -0.0012532   |    -2.83968e-05 |  -0.00238686  |    -0.002508    |  -0.00852539  |   -0.00420706  |    0.00509921 |    0.00940001 |            0.827653 |                 0.267431 |                 0.392551 |

## Primary checks

{
  "historical": {
    "aligned_N": 66,
    "opposite_N": 62,
    "aligned_mean_ret4_gt_opposite": true,
    "aligned_median_ret4_gt_opposite": false,
    "aligned_mfe4_gt_opposite": true,
    "aligned_mae4_lt_opposite": true
  },
  "forward_2026": {
    "aligned_N": 10,
    "opposite_N": 5,
    "aligned_mean_ret4_gt_opposite": true,
    "aligned_median_ret4_gt_opposite": true,
    "aligned_mfe4_gt_opposite": true,
    "aligned_mae4_lt_opposite": true
  }
}

Primary POC-alignment pattern repeats both periods: **False**

## CF191g overlap

| period       | relation   | profile_class   |   N |        EV_R |         PF |       SumR |   mean_mfe60 |   mean_mae60 |
|:-------------|:-----------|:----------------|----:|------------:|-----------:|-----------:|-------------:|-------------:|
| historical   | SUPPORTIVE | POC_ALIGNED     |  10 |  -0.226952  |   0.678996 |  -2.26952  |     1.19327  |     0.821428 |
| historical   | SUPPORTIVE | POC_MIDDLE      |  16 |  -0.0516563 |   0.897242 |  -0.8265   |     0.692709 |     0.833423 |
| historical   | SUPPORTIVE | POC_OPPOSITE    |   6 |   0.369929  |   2.05273  |   2.21958  |     1.15324  |     0.956233 |
| historical   | ADVERSE    | POC_ALIGNED     |   8 |  -0.0466747 |   0.91256  |  -0.373398 |     0.871452 |     1.28766  |
| historical   | ADVERSE    | POC_MIDDLE      |   9 |   1.611     |   5.81322  |  14.499    |     0.980428 |     0.550475 |
| historical   | ADVERSE    | POC_OPPOSITE    |  10 |   0.0117083 |   1.029    |   0.117083 |     1.17303  |     0.554102 |
| forward_2026 | SUPPORTIVE | POC_ALIGNED     |   1 |  -1.00855   |   0        |  -1.00855  |     0.556988 |     0.681809 |
| forward_2026 | SUPPORTIVE | POC_MIDDLE      |   1 |  -1.00828   |   0        |  -1.00828  |     1.34883  |     0.365636 |
| forward_2026 | SUPPORTIVE | POC_OPPOSITE    |   0 | nan         | nan        | nan        |   nan        |   nan        |
| forward_2026 | ADVERSE    | POC_ALIGNED     |   0 | nan         | nan        | nan        |   nan        |   nan        |
| forward_2026 | ADVERSE    | POC_MIDDLE      |   0 | nan         | nan        | nan        |   nan        |   nan        |
| forward_2026 | ADVERSE    | POC_OPPOSITE    |   0 | nan         | nan        | nan        |   nan        |   nan        |

## Limitations
- True POC uses exact aggTrade price levels weighted by quote notional.
- q15-q85 is central 70% price mass, not standard market-profile Value Area.
- Diagnostic only; no threshold/risk/entry/exit action.
- CF191g overlap classes with N<20 historical or N<5 in 2026 are shadow-only.
- 2026 Mar-Aug is reused shadow/stress, not pristine OOS.