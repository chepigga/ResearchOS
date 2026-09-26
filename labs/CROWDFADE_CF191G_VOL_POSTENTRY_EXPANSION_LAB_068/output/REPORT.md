# LAB068 — VOLATILITY × POST-ENTRY EXPANSION / DIRECTIONAL PERSISTENCE

## Entry-vol regime → early 15m state

| period       | vol_bucket   |    N |       EV_R |       PF |      SumR |   MaxDD_R |   mean_expansion15_atr |   median_expansion15_atr |   mean_eff15 |   mean_persist15 |   expansion_persistent_share |   failed_early_share |   active15_share |   right_tail_share |
|:-------------|:-------------|-----:|-----------:|---------:|----------:|----------:|-----------------------:|-------------------------:|-------------:|-----------------:|-----------------------------:|---------------------:|-----------------:|-------------------:|
| historical   | P0_20        | 1223 |  0.174641  | 1.2835   | 213.585   |  19.111   |             0.0234707  |               -0.0259259 |   -0.0142734 |         0.485255 |                     0.123467 |             0.514309 |         0.910875 |           0.212592 |
| historical   | P20_40       | 1232 |  0.165381  | 1.27423  | 203.749   |  29.3016  |             0.0321721  |               -0.011872  |   -0.0128503 |         0.490476 |                     0.129058 |             0.511364 |         0.931006 |           0.209416 |
| historical   | P40_60       | 1076 |  0.0480104 | 1.07815  |  51.6592  |  35.8252  |            -0.0174728  |               -0.0652897 |   -0.0231291 |         0.48259  |                     0.1171   |             0.541822 |         0.947955 |           0.170074 |
| historical   | P60_80       |  969 |  0.177121  | 1.32338  | 171.631   |  21.4446  |            -0.0234955  |               -0.04811   |   -0.0237775 |         0.48882  |                     0.100103 |             0.534572 |         0.941176 |           0.185759 |
| historical   | P80_100      |  776 |  0.0735524 | 1.14125  |  57.0766  |  37.1768  |            -0.00557915 |               -0.0607943 |   -0.0211726 |         0.486254 |                     0.119845 |             0.536082 |         0.95232  |           0.150773 |
| forward_2026 | P0_20        |  125 |  0.12046   | 1.19488  |  15.0575  |  13.225   |            -0.00410972 |               -0.0408308 |   -0.0155709 |         0.453333 |                     0.08     |             0.512    |         0.936    |           0.216    |
| forward_2026 | P20_40       |  130 | -0.025224  | 0.963474 |  -3.27912 |  24.3457  |            -0.0425752  |                0.0196591 |   -0.0244509 |         0.492821 |                     0.130769 |             0.484615 |         0.915385 |           0.176923 |
| forward_2026 | P40_60       |  105 |  0.253729  | 1.45621  |  26.6416  |   6.70587 |            -0.0313725  |               -0.0449188 |   -0.0388747 |         0.466667 |                     0.133333 |             0.561905 |         0.942857 |           0.247619 |
| forward_2026 | P60_80       |   99 | -0.0216207 | 0.964752 |  -2.14045 |  12.1041  |            -0.0481238  |               -0.03671   |   -0.0313946 |         0.491582 |                     0.111111 |             0.515152 |         0.949495 |           0.171717 |
| forward_2026 | P80_100      |   63 | -0.128277  | 0.788647 |  -8.08144 |  12.365   |            -0.0157592  |               -0.116593  |   -0.0210105 |         0.50582  |                     0.142857 |             0.571429 |         0.952381 |           0.126984 |

## MID/HIGH × early state — all entries

| period       | active_only   | vol_bucket   | early_state          |   N |       EV_R |       PF |       SumR |   mean_ret15_to_60_atr |   mean_post15_mfe_to_60_atr |   mean_post15_mae_to_60_atr |   right_tail_share |   initial_stop_share |
|:-------------|:--------------|:-------------|:---------------------|----:|-----------:|---------:|-----------:|-----------------------:|----------------------------:|----------------------------:|-------------------:|---------------------:|
| historical   | False         | P40_60       | EXPANSION_PERSISTENT | 126 |  1.09145   | 4.44152  |  137.523   |              0.23884   |                    1.4448   |                    1.08201  |          0.428571  |             0.309524 |
| historical   | False         | P40_60       | MIXED                | 367 |  0.30124   | 1.5949   |  110.555   |              0.033385  |                    1.08779  |                    0.965703 |          0.190736  |             0.476839 |
| historical   | False         | P40_60       | FAILED_EARLY         | 583 | -0.33691   | 0.548684 | -196.418   |              0.0554058 |                    1.06872  |                    0.912318 |          0.101201  |             0.722127 |
| historical   | False         | P80_100      | EXPANSION_PERSISTENT |  93 |  0.816512  | 3.60008  |   75.9356  |              0.137019  |                    1.224    |                    0.88501  |          0.322581  |             0.27957  |
| historical   | False         | P80_100      | MIXED                | 267 |  0.35119   | 1.8752   |   93.7678  |              0.0628425 |                    0.922319 |                    0.78124  |          0.179775  |             0.385768 |
| historical   | False         | P80_100      | FAILED_EARLY         | 416 | -0.270737  | 0.579357 | -112.627   |              0.0782799 |                    0.967305 |                    0.745939 |          0.09375   |             0.584135 |
| forward_2026 | False         | P40_60       | EXPANSION_PERSISTENT |  14 |  1.05889   | 4.40571  |   14.8245  |              0.0666478 |                    1.13832  |                    1.09827  |          0.571429  |             0.285714 |
| forward_2026 | False         | P40_60       | MIXED                |  32 |  0.450837  | 1.94213  |   14.4268  |             -0.0279095 |                    1.1406   |                    0.963268 |          0.28125   |             0.5      |
| forward_2026 | False         | P40_60       | FAILED_EARLY         |  59 | -0.0442319 | 0.932623 |   -2.60968 |              0.0987888 |                    1.10942  |                    0.981302 |          0.152542  |             0.644068 |
| forward_2026 | False         | P80_100      | EXPANSION_PERSISTENT |   9 |  0.855327  | 3.54758  |    7.69794 |              0.143372  |                    1.00072  |                    0.708616 |          0.444444  |             0.333333 |
| forward_2026 | False         | P80_100      | MIXED                |  18 | -0.0562153 | 0.900026 |   -1.01188 |              0.0920321 |                    0.848676 |                    0.621165 |          0.111111  |             0.5      |
| forward_2026 | False         | P80_100      | FAILED_EARLY         |  36 | -0.410208  | 0.411502 |  -14.7675  |             -0.168627  |                    0.715874 |                    1.07399  |          0.0555556 |             0.666667 |

## MID/HIGH × early state — active at 15m only

| period       | active_only   | vol_bucket   | early_state          |   N |       EV_R |       PF |       SumR |   mean_ret15_to_60_atr |   mean_post15_mfe_to_60_atr |   mean_post15_mae_to_60_atr |   right_tail_share |   initial_stop_share |
|:-------------|:--------------|:-------------|:---------------------|----:|-----------:|---------:|-----------:|-----------------------:|----------------------------:|----------------------------:|-------------------:|---------------------:|
| historical   | True          | P40_60       | EXPANSION_PERSISTENT | 120 |  1.04171   | 4.12826  |  125.005   |              0.24776   |                    1.44074  |                    1.05733  |          0.408333  |             0.325    |
| historical   | True          | P40_60       | MIXED                | 362 |  0.286009  | 1.56021  |  103.535   |              0.0301423 |                    1.07831  |                    0.949597 |          0.185083  |             0.480663 |
| historical   | True          | P40_60       | FAILED_EARLY         | 538 | -0.29033   | 0.600265 | -156.197   |              0.0288932 |                    1.01146  |                    0.858829 |          0.107807  |             0.698885 |
| historical   | True          | P80_100      | EXPANSION_PERSISTENT |  90 |  0.754694  | 3.3257   |   67.9225  |              0.115165  |                    1.20818  |                    0.900195 |          0.3       |             0.288889 |
| historical   | True          | P80_100      | MIXED                | 266 |  0.344134  | 1.8544   |   91.5396  |              0.0668081 |                    0.925542 |                    0.778318 |          0.176692  |             0.387218 |
| historical   | True          | P80_100      | FAILED_EARLY         | 383 | -0.207324  | 0.661425 |  -79.4051  |              0.0525955 |                    0.932231 |                    0.7076   |          0.101828  |             0.548303 |
| forward_2026 | True          | P40_60       | EXPANSION_PERSISTENT |  13 |  0.932519  | 3.78503  |   12.1227  |             -0.0446483 |                    1.06871  |                    1.07522  |          0.538462  |             0.307692 |
| forward_2026 | True          | P40_60       | MIXED                |  32 |  0.450837  | 1.94213  |   14.4268  |             -0.0279095 |                    1.1406   |                    0.963268 |          0.28125   |             0.5      |
| forward_2026 | True          | P40_60       | FAILED_EARLY         |  54 |  0.0455102 | 1.073    |    2.45755 |              0.0253127 |                    1.02041  |                    1.01691  |          0.166667  |             0.611111 |
| forward_2026 | True          | P80_100      | EXPANSION_PERSISTENT |   9 |  0.855327  | 3.54758  |    7.69794 |              0.143372  |                    1.00072  |                    0.708616 |          0.444444  |             0.333333 |
| forward_2026 | True          | P80_100      | MIXED                |  18 | -0.0562153 | 0.900026 |   -1.01188 |              0.0920321 |                    0.848676 |                    0.621165 |          0.111111  |             0.5      |
| forward_2026 | True          | P80_100      | FAILED_EARLY         |  33 | -0.355793  | 0.467935 |  -11.7412  |             -0.220977  |                    0.724842 |                    1.00635  |          0.0606061 |             0.636364 |

## Same early state: HIGH vs MID

| period       | early_state          |   mid_N |   high_N |     mid_EV |    high_EV |   mid_PF |   high_PF |   mid_post15_MFE |   high_post15_MFE |   mid_post15_MAE |   high_post15_MAE |
|:-------------|:---------------------|--------:|---------:|-----------:|-----------:|---------:|----------:|-----------------:|------------------:|-----------------:|------------------:|
| historical   | EXPANSION_PERSISTENT |     126 |       93 |  1.09145   |  0.816512  | 4.44152  |  3.60008  |          1.4448  |          1.224    |         1.08201  |          0.88501  |
| historical   | MIXED                |     367 |      267 |  0.30124   |  0.35119   | 1.5949   |  1.8752   |          1.08779 |          0.922319 |         0.965703 |          0.78124  |
| historical   | FAILED_EARLY         |     583 |      416 | -0.33691   | -0.270737  | 0.548684 |  0.579357 |          1.06872 |          0.967305 |         0.912318 |          0.745939 |
| forward_2026 | EXPANSION_PERSISTENT |      14 |        9 |  1.05889   |  0.855327  | 4.40571  |  3.54758  |          1.13832 |          1.00072  |         1.09827  |          0.708616 |
| forward_2026 | MIXED                |      32 |       18 |  0.450837  | -0.0562153 | 1.94213  |  0.900026 |          1.1406  |          0.848676 |         0.963268 |          0.621165 |
| forward_2026 | FAILED_EARLY         |      59 |       36 | -0.0442319 | -0.410208  | 0.932623 |  0.411502 |          1.10942 |          0.715874 |         0.981302 |          1.07399  |

## Regime checks

{
  "historical": {
    "mid_N": 1076,
    "high_N": 776,
    "high_expansion_lt_mid": false,
    "high_eff_lt_mid": false,
    "high_persist_lt_mid": false,
    "high_expansion_state_share_lt_mid": false,
    "high_failed_share_gt_mid": false,
    "expansion_gap_high_minus_mid": 0.011893619333427832,
    "eff_gap_high_minus_mid": 0.00195645181668715,
    "persistent_share_gap_high_minus_mid": 0.0027449890775303742
  },
  "forward_2026": {
    "mid_N": 105,
    "high_N": 63,
    "high_expansion_lt_mid": false,
    "high_eff_lt_mid": false,
    "high_persist_lt_mid": false,
    "high_expansion_state_share_lt_mid": false,
    "high_failed_share_gt_mid": true,
    "expansion_gap_high_minus_mid": 0.015613303171257652,
    "eff_gap_high_minus_mid": 0.01786418255649459,
    "persistent_share_gap_high_minus_mid": 0.009523809523809518
  }
}

Regime-shift hypothesis supported: **False**

## HIGH-vol state ordering checks

{
  "historical": {
    "persistent_N": 93,
    "failed_N": 416,
    "persistent_EV_gt_failed": true,
    "persistent_PF_gt_failed": true,
    "persistent_post15_MFE_gt_failed": true,
    "persistent_post15_MAE_lt_failed": false,
    "persistent_right_tail_gt_failed": true
  },
  "forward_2026": {
    "persistent_N": 9,
    "failed_N": 36,
    "persistent_EV_gt_failed": true,
    "persistent_PF_gt_failed": true,
    "persistent_post15_MFE_gt_failed": true,
    "persistent_post15_MAE_lt_failed": true,
    "persistent_right_tail_gt_failed": true
  }
}

Persistent > failed ordering supported both periods: **False**