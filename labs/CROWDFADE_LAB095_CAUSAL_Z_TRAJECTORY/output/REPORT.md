# LAB095 — CAUSAL Z TRAJECTORY / PEAK-TROUGH

{
  "lab": "LAB095_CAUSAL_Z_TRAJECTORY_PEAK_TROUGH",
  "hypothesis": "Trajectory / peak-trough reversal in Z may time crowd traps better than a fixed absolute Z gate.",
  "causal_definition": "For trade side, transform u=crowd_dir*Z. Use only observations strictly before decision time to find trailing directional peak. Trigger when current u has pulled back from that peak by >= pullback, peak prominence >= prominence, and peak age <= max_age.",
  "grid": {
    "lookback_min": [
      30,
      60,
      120
    ],
    "pullback_Z": [
      0.1,
      0.2,
      0.3,
      0.5
    ],
    "prominence_Z": [
      0.5,
      0.75,
      1.0,
      1.5
    ],
    "max_peak_age_min": [
      10,
      20,
      30
    ]
  },
  "absolute_Z_gate": "NONE for trajectory variants",
  "benchmark": "Frozen LAB093 with |Z|>=2.5",
  "frozen_other_logic": "LAB089 base excluding Z + LAB093 BUY ANY2 / SELL PRICE_LS + existing MARKET outcomes from LAB094",
  "benchmark_rows": [
    {
      "kind": "BENCH_Z2P5",
      "dataset": "historical",
      "lookback_min": NaN,
      "pullback": NaN,
      "prominence": NaN,
      "max_age": NaN,
      "N": 1347,
      "EV_R": 0.3014722605753926,
      "PF": 1.565106279831263,
      "SumR": 406.08313499505385,
      "MaxDD_R": 21.119207753318733,
      "WR": 0.44766146993318484,
      "trades_per_month": 22.45,
      "positive_months": 50,
      "negative_months": 10,
      "avg_month_R": 6.768052249917565
    },
    {
      "kind": "BENCH_Z2P5",
      "dataset": "forward_2026",
      "lookback_min": NaN,
      "pullback": NaN,
      "prominence": NaN,
      "max_age": NaN,
      "N": 119,
      "EV_R": 0.29686185997575926,
      "PF": 1.5790089541323942,
      "SumR": 35.32656133711535,
      "MaxDD_R": 11.347582306820339,
      "WR": 0.4369747899159664,
      "trades_per_month": 19.833333333333332,
      "positive_months": 6,
      "negative_months": 0,
      "avg_month_R": 5.887760222852556
    }
  ],
  "methodology_note": "Candidate selection must be based on historical rows; 2026 is reused diagnostic transfer only and is not pristine OOS.",
  "limitations": [
    "Multiple trajectory combinations are discovery and require freeze + future OOS.",
    "2026 Mar-Aug is reused diagnostic data.",
    "Trajectory test currently sits on the same non-Z LAB089 base universe: dLS>0, dOI>0.02%, price rejection>0.10ATR.",
    "Execution outcomes are inherited from LAB094 Binance 1m proxy."
  ]
}

## Top historical-selected candidates + forward check

| kind_hist   | dataset_hist   |   lookback_min |   pullback |   prominence |   max_age |   N_hist |   EV_R_hist |   PF_hist |   SumR_hist |   MaxDD_R_hist |   WR_hist |   trades_per_month_hist |   positive_months_hist |   negative_months_hist |   avg_month_R_hist | kind_fwd   | dataset_fwd   |   N_fwd |   EV_R_fwd |   PF_fwd |   SumR_fwd |   MaxDD_R_fwd |   WR_fwd |   trades_per_month_fwd |   positive_months_fwd |   negative_months_fwd |   avg_month_R_fwd | hist_target_20_50   | hist_pf15   |   hist_score |
|:------------|:---------------|---------------:|-----------:|-------------:|----------:|---------:|------------:|----------:|------------:|---------------:|----------:|------------------------:|-----------------------:|-----------------------:|-------------------:|:-----------|:--------------|--------:|-----------:|---------:|-----------:|--------------:|---------:|-----------------------:|----------------------:|----------------------:|------------------:|:--------------------|:------------|-------------:|
| TRAJECTORY  | historical     |             30 |        0.5 |         1.5  |        10 |      133 |    0.475025 |   1.97359 |     63.1784 |        6.75328 |  0.503759 |                 2.55769 |                     36 |                     16 |            1.21497 | TRAJECTORY | forward_2026  |       9 | -0.187174  | 0.741469 |  -1.68456  |       5.50571 | 0.222222 |                   2.25 |                     2 |                     2 |        -0.421141  | False               | True        |      117.68  |
| TRAJECTORY  | historical     |             30 |        0.5 |         1.5  |        20 |      168 |    0.424331 |   1.83708 |     71.2876 |       10.7633  |  0.488095 |                 3.05455 |                     37 |                     18 |            1.29614 | TRAJECTORY | forward_2026  |      11 | -0.336848  | 0.565951 |  -3.70533  |       7.52647 | 0.181818 |                   2.75 |                     2 |                     2 |        -0.926331  | False               | True        |      114.981 |
| TRAJECTORY  | historical     |             30 |        0.3 |         1.5  |        10 |      250 |    0.404255 |   1.81645 |    101.064  |        9.37008 |  0.496    |                 4.46429 |                     37 |                     19 |            1.80471 | TRAJECTORY | forward_2026  |      17 |  0.324406  | 1.65744  |   5.51491  |       4.5632  | 0.470588 |                   3.4  |                     4 |                     1 |         1.10298   | False               | True        |      114.825 |
| TRAJECTORY  | historical     |             30 |        0.5 |         1.5  |        30 |      172 |    0.408642 |   1.80618 |     70.2865 |       10.0793  |  0.488372 |                 3.12727 |                     37 |                     18 |            1.27794 | TRAJECTORY | forward_2026  |      13 | -0.440625  | 0.457536 |  -5.72813  |       8.53602 | 0.153846 |                   3.25 |                     1 |                     3 |        -1.43203   | False               | True        |      114.684 |
| TRAJECTORY  | historical     |             30 |        0.5 |         1    |        10 |      171 |    0.3661   |   1.70016 |     62.603  |        7.68621 |  0.467836 |                 3.05357 |                     39 |                     17 |            1.11791 | TRAJECTORY | forward_2026  |      10 |  0.0800606 | 1.12287  |   0.800606 |       3.46002 | 0.3      |                   2.5  |                     2 |                     2 |         0.200151  | False               | True        |      113.901 |
| TRAJECTORY  | historical     |             30 |        0.5 |         1    |        20 |      223 |    0.374025 |   1.71424 |     83.4076 |        9.14904 |  0.470852 |                 3.77966 |                     42 |                     17 |            1.41369 | TRAJECTORY | forward_2026  |      13 |  0.0973509 | 1.14825  |   1.26556  |       4.47381 | 0.307692 |                   3.25 |                     2 |                     2 |         0.316391  | False               | True        |      113.764 |
| TRAJECTORY  | historical     |            120 |        0.5 |         1.5  |        10 |      169 |    0.361826 |   1.68937 |     61.1486 |        8.71179 |  0.467456 |                 3.01786 |                     36 |                     20 |            1.09194 | TRAJECTORY | forward_2026  |      10 | -0.22089   | 0.686246 |  -2.2089   |       6.03005 | 0.2      |                   2.5  |                     2 |                     2 |        -0.552226  | False               | True        |      113.505 |
| TRAJECTORY  | historical     |            120 |        0.5 |         0.5  |        10 |      172 |    0.358269 |   1.67923 |     61.6223 |        8.71179 |  0.465116 |                 3.01754 |                     37 |                     20 |            1.08109 | TRAJECTORY | forward_2026  |      10 | -0.22089   | 0.686246 |  -2.2089   |       6.03005 | 0.2      |                   2.5  |                     2 |                     2 |        -0.552226  | False               | True        |      113.384 |
| TRAJECTORY  | historical     |            120 |        0.5 |         0.75 |        10 |      172 |    0.358269 |   1.67923 |     61.6223 |        8.71179 |  0.465116 |                 3.01754 |                     37 |                     20 |            1.08109 | TRAJECTORY | forward_2026  |      10 | -0.22089   | 0.686246 |  -2.2089   |       6.03005 | 0.2      |                   2.5  |                     2 |                     2 |        -0.552226  | False               | True        |      113.384 |
| TRAJECTORY  | historical     |            120 |        0.5 |         1    |        10 |      172 |    0.358269 |   1.67923 |     61.6223 |        8.71179 |  0.465116 |                 3.01754 |                     37 |                     20 |            1.08109 | TRAJECTORY | forward_2026  |      10 | -0.22089   | 0.686246 |  -2.2089   |       6.03005 | 0.2      |                   2.5  |                     2 |                     2 |        -0.552226  | False               | True        |      113.384 |
| TRAJECTORY  | historical     |             30 |        0.3 |         1    |        10 |      346 |    0.376241 |   1.74972 |    130.179  |       11.6163  |  0.488439 |                 5.86441 |                     40 |                     19 |            2.20643 | TRAJECTORY | forward_2026  |      19 |  0.383253  | 1.79961  |   7.28182  |       4.68989 | 0.473684 |                   3.8  |                     4 |                     1 |         1.45636   | False               | True        |      113.369 |
| TRAJECTORY  | historical     |             30 |        0.5 |         1    |        30 |      235 |    0.354296 |   1.6721  |     83.2596 |        9.14904 |  0.468085 |                 3.98305 |                     40 |                     19 |            1.41118 | TRAJECTORY | forward_2026  |      15 | -0.0504828 | 0.928288 |  -0.757242 |       4.47381 | 0.266667 |                   3.75 |                     1 |                     3 |        -0.189311  | False               | True        |      113.159 |
| TRAJECTORY  | historical     |             30 |        0.5 |         0.75 |        10 |      182 |    0.341734 |   1.65499 |     62.1956 |        8.71179 |  0.467033 |                 3.19298 |                     39 |                     18 |            1.09115 | TRAJECTORY | forward_2026  |      10 |  0.0800606 | 1.12287  |   0.800606 |       3.46002 | 0.3      |                   2.5  |                     2 |                     2 |         0.200151  | False               | True        |      112.932 |
| TRAJECTORY  | historical     |             30 |        0.3 |         1.5  |        30 |      295 |    0.353633 |   1.69537 |    104.322  |       10.5467  |  0.481356 |                 5.17544 |                     38 |                     19 |            1.83021 | TRAJECTORY | forward_2026  |      21 |  0.0700639 | 1.11835  |   1.47134  |       5.57699 | 0.380952 |                   4.2  |                     4 |                     1 |         0.294268  | False               | True        |      112.913 |
| TRAJECTORY  | historical     |             30 |        0.3 |         1.5  |        20 |      289 |    0.355414 |   1.694   |    102.715  |       11.3453  |  0.477509 |                 5.07018 |                     38 |                     19 |            1.80201 | TRAJECTORY | forward_2026  |      19 |  0.183902  | 1.33568  |   3.49415  |       5.57699 | 0.421053 |                   3.8  |                     4 |                     1 |         0.698829  | False               | True        |      112.742 |
| TRAJECTORY  | historical     |             30 |        0.5 |         0.5  |        10 |      192 |    0.335732 |   1.6382  |     64.4606 |        8.71179 |  0.463542 |                 3.31034 |                     39 |                     19 |            1.11139 | TRAJECTORY | forward_2026  |      13 |  0.133824  | 1.21598  |   1.73971  |       4.55961 | 0.307692 |                   3.25 |                     2 |                     2 |         0.434927  | False               | True        |      112.728 |
| TRAJECTORY  | historical     |             60 |        0.3 |         1    |        10 |      365 |    0.358652 |   1.69674 |    130.908  |       11.788   |  0.476712 |                 6.2931  |                     37 |                     21 |            2.25703 | TRAJECTORY | forward_2026  |      20 |  0.23106   | 1.43389  |   4.62119  |       4.68989 | 0.4      |                   4    |                     4 |                     1 |         0.924239  | False               | True        |      112.71  |
| TRAJECTORY  | historical     |            120 |        0.3 |         1.5  |        10 |      341 |    0.351151 |   1.68195 |    119.742  |       11.5765  |  0.478006 |                 5.87931 |                     39 |                     19 |            2.06452 | TRAJECTORY | forward_2026  |      19 |  0.113081  | 1.20196  |   2.14853  |       6.28866 | 0.368421 |                   3.8  |                     4 |                     1 |         0.429706  | False               | True        |      112.539 |
| TRAJECTORY  | historical     |             60 |        0.5 |         1    |        10 |      179 |    0.326111 |   1.60835 |     58.3739 |        8.71179 |  0.452514 |                 3.14035 |                     38 |                     19 |            1.0241  | TRAJECTORY | forward_2026  |      11 |  0.025115  | 1.03924  |   0.276265 |       3.54488 | 0.272727 |                   2.75 |                     2 |                     2 |         0.0690662 | False               | True        |      112.386 |
| TRAJECTORY  | historical     |             30 |        0.3 |         1    |        20 |      409 |    0.32913  |   1.6319  |    134.614  |        9.57791 |  0.469438 |                 6.9322  |                     40 |                     19 |            2.28159 | TRAJECTORY | forward_2026  |      21 |  0.250526  | 1.4728   |   5.26105  |       5.70368 | 0.428571 |                   4.2  |                     4 |                     1 |         1.05221   | False               | True        |      112.348 |
| TRAJECTORY  | historical     |            120 |        0.3 |         1    |        10 |      358 |    0.342461 |   1.66106 |    122.601  |       11.788   |  0.472067 |                 6.17241 |                     37 |                     21 |            2.11381 | TRAJECTORY | forward_2026  |      19 |  0.113081  | 1.20196  |   2.14853  |       6.28866 | 0.368421 |                   3.8  |                     4 |                     1 |         0.429706  | False               | True        |      112.207 |
| TRAJECTORY  | historical     |             60 |        0.5 |         0.5  |        10 |      182 |    0.323305 |   1.60058 |     58.8415 |        9.15054 |  0.450549 |                 3.19298 |                     36 |                     21 |            1.03231 | TRAJECTORY | forward_2026  |      11 |  0.025115  | 1.03924  |   0.276265 |       3.54488 | 0.272727 |                   2.75 |                     2 |                     2 |         0.0690662 | False               | True        |      112.181 |
| TRAJECTORY  | historical     |             60 |        0.5 |         0.75 |        10 |      180 |    0.318649 |   1.5915  |     57.3568 |        8.71179 |  0.45     |                 3.15789 |                     36 |                     21 |            1.00626 | TRAJECTORY | forward_2026  |      11 |  0.025115  | 1.03924  |   0.276265 |       3.54488 | 0.272727 |                   2.75 |                     2 |                     2 |         0.0690662 | False               | True        |      112.153 |
| TRAJECTORY  | historical     |            120 |        0.3 |         0.5  |        10 |      365 |    0.340386 |   1.65558 |    124.241  |       11.788   |  0.471233 |                 6.2931  |                     37 |                     21 |            2.14208 | TRAJECTORY | forward_2026  |      20 |  0.206146  | 1.38756  |   4.12292  |       4.31427 | 0.4      |                   4    |                     4 |                     1 |         0.824584  | False               | True        |      112.139 |
| TRAJECTORY  | historical     |             30 |        0.3 |         0.75 |        10 |      393 |    0.334745 |   1.65753 |    131.555  |       11.6163  |  0.478372 |                 6.66102 |                     41 |                     18 |            2.22975 | TRAJECTORY | forward_2026  |      20 |  0.46281   | 2.01642  |   9.25621  |       2.76773 | 0.5      |                   4    |                     4 |                     1 |         1.85124   | False               | True        |      112.078 |