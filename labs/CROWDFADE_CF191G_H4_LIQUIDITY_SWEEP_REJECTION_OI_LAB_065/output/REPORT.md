# LAB065 — H4 LIQUIDITY-SWEEP / REJECTION + OI-FLUSH MAP

Footprint-free proxy inspired by the reviewed video. Diagnostic only.

## Component attrition

| period       |   h4_bars |   high_volume_bars |   sweep_rejection_bars |   oi_down_bars |   full_composite_bars |
|:-------------|----------:|-------------------:|-----------------------:|---------------:|----------------------:|
| historical   |     10955 |               2216 |                   1099 |           5299 |                   221 |
| forward_2026 |      1104 |                219 |                    102 |            568 |                    21 |

## CF191g outcome map

| period       | state      |    N |        EV_R |         PF |       SumR |         WR |   MaxDD_R |   mean_mfe15 |   mean_mae15 |   mean_mfe60 |   mean_mae60 |   initial_stop_share |   right_tail_ge_1p5R |
|:-------------|:-----------|-----:|------------:|-----------:|-----------:|-----------:|----------:|-------------:|-------------:|-------------:|-------------:|---------------------:|---------------------:|
| historical   | SUPPORTIVE |   32 |  -0.027389  |   0.949108 |  -0.876448 |   0.4375   |   4.9708  |     0.427967 |     0.500247 |     0.935484 |     0.852701 |             0.53125  |             0.125    |
| historical   | ADVERSE    |   27 |   0.527507  |   2.25819  |  14.2427   |   0.555556 |   2.94845 |     0.425684 |     0.372026 |     1.01947  |     0.770243 |             0.407407 |             0.185185 |
| historical   | NONE       | 5238 |   0.131158  |   1.22341  | 687.004    |   0.38908  |  32.9831  |     0.651753 |     0.569538 |     1.33136  |     1.13883  |             0.56491  |             0.189767 |
| historical   | NA         |    0 | nan         | nan        | nan        | nan        | nan       |   nan        |   nan        |   nan        |   nan        |           nan        |           nan        |
| forward_2026 | SUPPORTIVE |    2 |  -1.00842   |   0        |  -2.01683  |   0        |   2.01683 |     0.611758 |     0.434711 |     0.952908 |     0.523722 |             1        |             0        |
| forward_2026 | ADVERSE    |    0 | nan         | nan        | nan        | nan        | nan       |   nan        |   nan        |   nan        |   nan        |           nan        |           nan        |
| forward_2026 | NONE       |  542 |   0.0692153 |   1.11216  |  37.5147   |   0.370849 |  27.633   |     0.585739 |     0.557216 |     1.29938  |     1.2105   |             0.603321 |             0.193727 |
| forward_2026 | NA         |    0 | nan         | nan        | nan        | nan        | nan       |   nan        |   nan        |   nan        |   nan        |           nan        |           nan        |

## Checks

{
  "historical": {
    "supportive_N": 32,
    "adverse_N": 27,
    "none_N": 5238,
    "supportive_EV_gt_none": false,
    "supportive_PF_gt_none": false,
    "supportive_MFE60_gt_none": false,
    "supportive_initial_stop_lt_none": true,
    "adverse_EV_lt_supportive": false
  },
  "forward_2026": {
    "supportive_N": 2,
    "adverse_N": 0,
    "none_N": 542,
    "supportive_EV_gt_none": false,
    "supportive_PF_gt_none": false,
    "supportive_MFE60_gt_none": false,
    "supportive_initial_stop_lt_none": false,
    "adverse_EV_lt_supportive": false
  }
}

Supportive EV/PF edge repeats both periods: **False**

## Limitations
- No footprint POC/volume-at-price; OHLC rejection + H4 quote volume is only a proxy.
- Only the latest completed H4 candle is mapped to each CF191g fill.
- OI flush uses sign only; no magnitude threshold.
- Diagnostic only; no entry/exit/risk action tested.
- BTCUSDT only; 2026 Mar-Aug reused shadow/stress.