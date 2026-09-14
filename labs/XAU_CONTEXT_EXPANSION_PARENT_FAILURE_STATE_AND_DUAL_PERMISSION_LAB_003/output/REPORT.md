# XAU_CONTEXT_EXPANSION_PARENT_FAILURE_STATE_AND_DUAL_PERMISSION_LAB_003
**Verdict: STALE_EXPANSION_FAILURE_CONFIRMED_BUT_NO_TRADABLE_FILTER**
**Winner: NONE**
**Parity: True | C0 {'trades': True, 'ev40': True, 'pf40': True, 'ddpct': True} | C1 {'trades': True, 'mean_tm': True, 'ev40': True, 'cum40': True, 'ddpct': True}**
**H1 stale-tail failure: True**

## Variant summary

| variant                                 | kind      |   qualifying_h4_all |   qualifying_h4_eval |   episodes_all |   permission_hours_eval |   permission_pct_eval |   trades |   mean_trades_month |   median_trades_month |   pct_months_ge8 |   pct_months_ge10 |   gross_expectancy_r |   commission_expectancy_r |   spread20_expectancy_r |   spread40_expectancy_r |   pf_spread40 |   cum_spread40_r |   mean_spread40_r_month |   max_dd_r |   max_dd_pct_at_025 |   max_consecutive_losses |   win_rate_net40 |   median_hold_h |   p90_hold_h |   timeout_frac |   positive_blocks |   min_block_cum_r |   top_abs_trade_share | h2_expansion_edge   | h3_dual   | target_dual   |
|:----------------------------------------|:----------|--------------------:|---------------------:|---------------:|------------------------:|----------------------:|---------:|--------------------:|----------------------:|-----------------:|------------------:|---------------------:|--------------------------:|------------------------:|------------------------:|--------------:|-----------------:|------------------------:|-----------:|--------------------:|-------------------------:|-----------------:|----------------:|-------------:|---------------:|------------------:|------------------:|----------------------:|:--------------------|:----------|:--------------|
| C0_E75_CORE                             | CONTROL   |                  62 |                   53 |             42 |                964.0000 |                0.0315 |       98 |              2.3333 |                0.0000 |           0.0952 |            0.0714 |               0.1813 |                    0.1721 |                  0.1237 |                  0.0753 |        1.1407 |           7.3792 |                  0.1757 |     7.6836 |              1.9209 |                        5 |           0.5000 |          1.3417 |       8.0000 |         0.1327 |                 3 |           -2.8042 |                0.0137 | False               | False     | False         |
| C1_EXPANSION_RAW_24H                    | CONTROL   |                 848 |                  804 |             98 |               5200.0000 |                0.1697 |      444 |             10.5714 |                9.5000 |           0.5476 |            0.5000 |               0.1510 |                    0.1410 |                  0.0861 |                  0.0312 |        1.0537 |          13.8322 |                  0.3293 |    21.5527 |              5.3882 |                        8 |           0.4685 |          1.2333 |       5.1883 |         0.0608 |                 3 |          -14.1360 |                0.0054 | False               | False     | False         |
| X1_EXP_LIVE4H                           | EXP       |                 848 |                  804 |            107 |               3216.0000 |                0.1049 |      351 |              8.3571 |                6.0000 |           0.4286 |            0.4048 |               0.1655 |                    0.1558 |                  0.1028 |                  0.0497 |        1.0874 |          17.4515 |                  0.4155 |    15.8747 |              3.9687 |                       10 |           0.4758 |          1.2667 |       5.4333 |         0.0712 |                 3 |           -5.0455 |                0.0069 | False               | False     | False         |
| X2_EXP_FORMING_LIVE4H                   | EXP       |                 270 |                  261 |             98 |               1044.0000 |                0.0341 |      176 |              4.1905 |                4.0000 |           0.2381 |            0.0476 |               0.0988 |                    0.0898 |                  0.0417 |                 -0.0064 |        0.9892 |          -1.1184 |                 -0.0266 |    15.5449 |              3.8862 |                        8 |           0.4489 |          1.3500 |       6.0917 |         0.0852 |                 3 |           -6.8036 |                0.0139 | False               | False     | False         |
| X3_EXP_MATURE_LIVE4H                    | EXP       |                 578 |                  543 |             77 |               2172.0000 |                0.0709 |      253 |              6.0238 |                4.0000 |           0.3333 |            0.2857 |               0.1728 |                    0.1638 |                  0.1144 |                  0.0650 |        1.1203 |          16.4467 |                  0.3916 |    11.1523 |              2.7881 |                        6 |           0.4822 |          1.2333 |       8.0000 |         0.1067 |                 4 |            0.5078 |                0.0076 | False               | False     | False         |
| X4_EXP_ADX_HIGH_LIVE4H                  | EXP       |                 720 |                  682 |             92 |               2728.0000 |                0.0890 |      298 |              7.0952 |                5.5000 |           0.4286 |            0.3571 |               0.1674 |                    0.1576 |                  0.1025 |                  0.0474 |        1.0829 |          14.1168 |                  0.3361 |    14.5347 |              3.6337 |                       10 |           0.4732 |          1.2167 |       5.3050 |         0.0705 |                 3 |           -1.9524 |                0.0081 | False               | False     | False         |
| X5_EXP_BREAKOUT_ACCEPT_LIVE4H           | EXP       |                 219 |                  208 |            135 |                832.0000 |                0.0271 |      156 |              3.7143 |                2.0000 |           0.2143 |            0.0952 |               0.1382 |                    0.1316 |                  0.0984 |                  0.0651 |        1.1210 |          10.1583 |                  0.2419 |    13.5828 |              3.3957 |                        8 |           0.4744 |          2.0333 |       8.0000 |         0.1282 |                 3 |          -11.5220 |                0.0161 | False               | False     | False         |
| X6_EXP_NO_G1_LIVE4H                     | EXP       |                 832 |                  788 |            107 |               3152.0000 |                0.1028 |      344 |              8.1905 |                6.0000 |           0.4286 |            0.4048 |               0.1675 |                    0.1577 |                  0.1042 |                  0.0507 |        1.0892 |          17.4383 |                  0.4152 |    15.6365 |              3.9091 |                       10 |           0.4767 |          1.2583 |       5.5033 |         0.0727 |                 3 |           -5.0455 |                0.0070 | False               | False     | False         |
| D0_CORE_PLUS_RAW_EXP24H                 | DUAL_DIAG |                 910 |                  857 |            128 |               6052.0000 |                0.1975 |      518 |             12.3333 |               10.5000 |           0.6190 |            0.5476 |               0.1509 |                    0.1411 |                  0.0874 |                  0.0337 |        1.0589 |          17.4817 |                  0.4162 |    19.3231 |              4.8308 |                        8 |           0.4730 |          1.2750 |       5.4333 |         0.0753 |                 2 |           -6.6793 |                0.0047 | False               | False     | False         |
| D1_CORE_PLUS_EXP_LIVE4H                 | DUAL      |                 910 |                  857 |            139 |               4088.0000 |                0.1334 |      429 |             10.2143 |                8.5000 |           0.5476 |            0.4762 |               0.1637 |                    0.1542 |                  0.1027 |                  0.0511 |        1.0909 |          21.9347 |                  0.5223 |    15.6365 |              3.9091 |                       10 |           0.4802 |          1.2833 |       6.0933 |         0.0862 |                 3 |           -1.4907 |                0.0057 | False               | False     | False         |
| D2_CORE_PLUS_EXP_FORMING_LIVE4H         | DUAL      |                 332 |                  314 |            130 |               1928.0000 |                0.0629 |      256 |              6.0952 |                6.0000 |           0.4048 |            0.2619 |               0.1173 |                    0.1084 |                  0.0612 |                  0.0140 |        1.0244 |           3.5748 |                  0.0851 |    13.7349 |              3.4337 |                        7 |           0.4648 |          1.3500 |       8.0000 |         0.1055 |                 2 |           -0.6879 |                0.0096 | False               | False     | False         |
| D3_CORE_PLUS_EXP_MATURE_LIVE4H          | DUAL      |                 640 |                  596 |            114 |               3124.0000 |                0.1019 |      336 |              8.0000 |                6.5000 |           0.4048 |            0.3333 |               0.1561 |                    0.1470 |                  0.0978 |                  0.0486 |        1.0880 |          16.3271 |                  0.3887 |    11.7162 |              2.9290 |                        6 |           0.4792 |          1.2500 |       8.0000 |         0.1042 |                 3 |           -1.6591 |                0.0057 | False               | False     | False         |
| D4_CORE_PLUS_EXP_ADX_HIGH_LIVE4H        | DUAL      |                 782 |                  735 |            128 |               3632.0000 |                0.1185 |      380 |              9.0476 |                8.0000 |           0.5238 |            0.4524 |               0.1462 |                    0.1365 |                  0.0834 |                  0.0302 |        1.0528 |          11.4921 |                  0.2736 |    20.5842 |              5.1460 |                       10 |           0.4711 |          1.2333 |       7.2350 |         0.0868 |                 2 |           -2.8599 |                0.0064 | False               | False     | False         |
| D5_CORE_PLUS_EXP_BREAKOUT_ACCEPT_LIVE4H | DUAL      |                 281 |                  261 |            165 |               1752.0000 |                0.0572 |      240 |              5.7143 |                5.0000 |           0.2857 |            0.2619 |               0.1467 |                    0.1393 |                  0.1011 |                  0.0629 |        1.1168 |          15.0883 |                  0.3592 |    12.2862 |              3.0715 |                        5 |           0.4833 |          1.5583 |       8.0000 |         0.1333 |                 3 |           -3.9055 |                0.0105 | False               | False     | False         |
| D6_CORE_PLUS_EXP_NO_G1_LIVE4H           | DUAL      |                 894 |                  841 |            140 |               4032.0000 |                0.1316 |      425 |             10.1190 |                8.5000 |           0.5476 |            0.4524 |               0.1688 |                    0.1593 |                  0.1075 |                  0.0558 |        1.0995 |          23.6942 |                  0.5641 |    15.6365 |              3.9091 |                       10 |           0.4824 |          1.2833 |       6.1467 |         0.0871 |                 3 |           -0.8978 |                0.0057 | False               | False     | False         |

## Staleness diagnostic

| bucket   |   trades |    ev40 |    cum40 |   pf40 |
|:---------|---------:|--------:|---------:|-------:|
| 0-4h     |      348 |  0.0620 |  21.5894 | 1.1100 |
| 4-8h     |       13 |  0.2282 |   2.9667 | 1.4499 |
| 8-12h    |       26 | -0.4520 | -11.7514 | 0.4505 |
| 12-24h   |       57 |  0.0180 |   1.0275 | 1.0310 |

## Parent feature counts

| feature         |   bars |
|:----------------|-------:|
| EXPANSION_RAW   |    848 |
| FORMING         |    270 |
| MATURE          |    578 |
| ADX_HIGH        |    720 |
| ADX_LOW         |    128 |
| BREAKOUT_ACCEPT |    219 |
| G1_TRUE         |     16 |
| G1_FALSE        |    832 |

## Calendar blocks

| block   |   n |   expectancy_net40 |   cum_net40_r | variant                                 |
|:--------|----:|-------------------:|--------------:|:----------------------------------------|
| 2023    |  22 |             0.2483 |        5.4630 | C0_E75_CORE                             |
| 2024    |  22 |             0.1112 |        2.4468 | C0_E75_CORE                             |
| 2025    |  38 |             0.0598 |        2.2737 | C0_E75_CORE                             |
| 2026H1  |  16 |            -0.1753 |       -2.8042 | C0_E75_CORE                             |
| 2023    |  80 |            -0.1767 |      -14.1360 | C1_EXPANSION_RAW_24H                    |
| 2024    | 139 |             0.0531 |        7.3868 | C1_EXPANSION_RAW_24H                    |
| 2025    | 195 |             0.0941 |       18.3575 | C1_EXPANSION_RAW_24H                    |
| 2026H1  |  30 |             0.0741 |        2.2239 | C1_EXPANSION_RAW_24H                    |
| 2023    |  60 |            -0.0841 |       -5.0455 | X1_EXP_LIVE4H                           |
| 2024    | 112 |             0.1026 |       11.4867 | X1_EXP_LIVE4H                           |
| 2025    | 153 |             0.0634 |        9.6968 | X1_EXP_LIVE4H                           |
| 2026H1  |  26 |             0.0505 |        1.3135 | X1_EXP_LIVE4H                           |
| 2023    |  29 |            -0.2346 |       -6.8036 | X2_EXP_FORMING_LIVE4H                   |
| 2024    |  61 |             0.0113 |        0.6923 | X2_EXP_FORMING_LIVE4H                   |
| 2025    |  77 |             0.0374 |        2.8766 | X2_EXP_FORMING_LIVE4H                   |
| 2026H1  |   9 |             0.2351 |        2.1163 | X2_EXP_FORMING_LIVE4H                   |
| 2023    |  45 |             0.0113 |        0.5078 | X3_EXP_MATURE_LIVE4H                    |
| 2024    |  83 |             0.0340 |        2.8186 | X3_EXP_MATURE_LIVE4H                    |
| 2025    | 105 |             0.1140 |       11.9752 | X3_EXP_MATURE_LIVE4H                    |
| 2026H1  |  20 |             0.0573 |        1.1451 | X3_EXP_MATURE_LIVE4H                    |
| 2023    |  58 |             0.0032 |        0.1854 | X4_EXP_ADX_HIGH_LIVE4H                  |
| 2024    | 100 |             0.1541 |       15.4094 | X4_EXP_ADX_HIGH_LIVE4H                  |
| 2025    | 118 |            -0.0165 |       -1.9524 | X4_EXP_ADX_HIGH_LIVE4H                  |
| 2026H1  |  22 |             0.0216 |        0.4743 | X4_EXP_ADX_HIGH_LIVE4H                  |
| 2023    |  19 |            -0.6064 |      -11.5220 | X5_EXP_BREAKOUT_ACCEPT_LIVE4H           |
| 2024    |  45 |             0.2431 |       10.9375 | X5_EXP_BREAKOUT_ACCEPT_LIVE4H           |
| 2025    |  80 |             0.0584 |        4.6704 | X5_EXP_BREAKOUT_ACCEPT_LIVE4H           |
| 2026H1  |  12 |             0.5060 |        6.0724 | X5_EXP_BREAKOUT_ACCEPT_LIVE4H           |
| 2023    |  60 |            -0.0841 |       -5.0455 | X6_EXP_NO_G1_LIVE4H                     |
| 2024    | 112 |             0.1026 |       11.4867 | X6_EXP_NO_G1_LIVE4H                     |
| 2025    | 149 |             0.0610 |        9.0906 | X6_EXP_NO_G1_LIVE4H                     |
| 2026H1  |  23 |             0.0829 |        1.9065 | X6_EXP_NO_G1_LIVE4H                     |
| 2023    |  94 |            -0.0711 |       -6.6793 | D0_CORE_PLUS_RAW_EXP24H                 |
| 2024    | 156 |             0.0632 |        9.8641 | D0_CORE_PLUS_RAW_EXP24H                 |
| 2025    | 223 |             0.0733 |       16.3457 | D0_CORE_PLUS_RAW_EXP24H                 |
| 2026H1  |  45 |            -0.0455 |       -2.0487 | D0_CORE_PLUS_RAW_EXP24H                 |
| 2023    |  74 |             0.0326 |        2.4112 | D1_CORE_PLUS_EXP_LIVE4H                 |
| 2024    | 129 |             0.1082 |       13.9640 | D1_CORE_PLUS_EXP_LIVE4H                 |
| 2025    | 184 |             0.0383 |        7.0502 | D1_CORE_PLUS_EXP_LIVE4H                 |
| 2026H1  |  42 |            -0.0355 |       -1.4907 | D1_CORE_PLUS_EXP_LIVE4H                 |
| 2023    |  44 |            -0.0136 |       -0.5968 | D2_CORE_PLUS_EXP_FORMING_LIVE4H         |
| 2024    |  78 |             0.0406 |        3.1696 | D2_CORE_PLUS_EXP_FORMING_LIVE4H         |
| 2025    | 109 |             0.0155 |        1.6899 | D2_CORE_PLUS_EXP_FORMING_LIVE4H         |
| 2026H1  |  25 |            -0.0275 |       -0.6879 | D2_CORE_PLUS_EXP_FORMING_LIVE4H         |
| 2023    |  63 |             0.0541 |        3.4081 | D3_CORE_PLUS_EXP_MATURE_LIVE4H          |
| 2024    | 100 |             0.0277 |        2.7654 | D3_CORE_PLUS_EXP_MATURE_LIVE4H          |
| 2025    | 137 |             0.0862 |       11.8127 | D3_CORE_PLUS_EXP_MATURE_LIVE4H          |
| 2026H1  |  36 |            -0.0461 |       -1.6591 | D3_CORE_PLUS_EXP_MATURE_LIVE4H          |
| 2023    |  72 |             0.1061 |        7.6421 | D4_CORE_PLUS_EXP_ADX_HIGH_LIVE4H        |
| 2024    | 118 |             0.0766 |        9.0398 | D4_CORE_PLUS_EXP_ADX_HIGH_LIVE4H        |
| 2025    | 152 |            -0.0188 |       -2.8599 | D4_CORE_PLUS_EXP_ADX_HIGH_LIVE4H        |
| 2026H1  |  38 |            -0.0613 |       -2.3299 | D4_CORE_PLUS_EXP_ADX_HIGH_LIVE4H        |
| 2023    |  37 |            -0.1056 |       -3.9055 | D5_CORE_PLUS_EXP_BREAKOUT_ACCEPT_LIVE4H |
| 2024    |  63 |             0.1949 |       12.2756 | D5_CORE_PLUS_EXP_BREAKOUT_ACCEPT_LIVE4H |
| 2025    | 112 |             0.0308 |        3.4500 | D5_CORE_PLUS_EXP_BREAKOUT_ACCEPT_LIVE4H |
| 2026H1  |  28 |             0.1167 |        3.2682 | D5_CORE_PLUS_EXP_BREAKOUT_ACCEPT_LIVE4H |
| 2023    |  74 |             0.0326 |        2.4112 | D6_CORE_PLUS_EXP_NO_G1_LIVE4H           |
| 2024    | 129 |             0.1082 |       13.9640 | D6_CORE_PLUS_EXP_NO_G1_LIVE4H           |
| 2025    | 183 |             0.0449 |        8.2167 | D6_CORE_PLUS_EXP_NO_G1_LIVE4H           |
| 2026H1  |  39 |            -0.0230 |       -0.8978 | D6_CORE_PLUS_EXP_NO_G1_LIVE4H           |

## Router composition

| source        |   trades | variant                                 |
|:--------------|---------:|:----------------------------------------|
| FVG_RETEST    |       52 | C0_E75_CORE                             |
| BOS_RETEST    |       23 | C0_E75_CORE                             |
| SWEEP_RECLAIM |       20 | C0_E75_CORE                             |
| OB_RETEST     |        3 | C0_E75_CORE                             |
| FVG_RETEST    |      202 | C1_EXPANSION_RAW_24H                    |
| BOS_RETEST    |      121 | C1_EXPANSION_RAW_24H                    |
| SWEEP_RECLAIM |      100 | C1_EXPANSION_RAW_24H                    |
| OB_RETEST     |       21 | C1_EXPANSION_RAW_24H                    |
| FVG_RETEST    |      158 | X1_EXP_LIVE4H                           |
| BOS_RETEST    |       94 | X1_EXP_LIVE4H                           |
| SWEEP_RECLAIM |       85 | X1_EXP_LIVE4H                           |
| OB_RETEST     |       14 | X1_EXP_LIVE4H                           |
| FVG_RETEST    |       68 | X2_EXP_FORMING_LIVE4H                   |
| BOS_RETEST    |       53 | X2_EXP_FORMING_LIVE4H                   |
| SWEEP_RECLAIM |       46 | X2_EXP_FORMING_LIVE4H                   |
| OB_RETEST     |        9 | X2_EXP_FORMING_LIVE4H                   |
| FVG_RETEST    |      117 | X3_EXP_MATURE_LIVE4H                    |
| BOS_RETEST    |       63 | X3_EXP_MATURE_LIVE4H                    |
| SWEEP_RECLAIM |       62 | X3_EXP_MATURE_LIVE4H                    |
| OB_RETEST     |       11 | X3_EXP_MATURE_LIVE4H                    |
| FVG_RETEST    |      134 | X4_EXP_ADX_HIGH_LIVE4H                  |
| BOS_RETEST    |       76 | X4_EXP_ADX_HIGH_LIVE4H                  |
| SWEEP_RECLAIM |       76 | X4_EXP_ADX_HIGH_LIVE4H                  |
| OB_RETEST     |       12 | X4_EXP_ADX_HIGH_LIVE4H                  |
| FVG_RETEST    |       81 | X5_EXP_BREAKOUT_ACCEPT_LIVE4H           |
| BOS_RETEST    |       49 | X5_EXP_BREAKOUT_ACCEPT_LIVE4H           |
| SWEEP_RECLAIM |       16 | X5_EXP_BREAKOUT_ACCEPT_LIVE4H           |
| OB_RETEST     |       10 | X5_EXP_BREAKOUT_ACCEPT_LIVE4H           |
| FVG_RETEST    |      156 | X6_EXP_NO_G1_LIVE4H                     |
| BOS_RETEST    |       91 | X6_EXP_NO_G1_LIVE4H                     |
| SWEEP_RECLAIM |       83 | X6_EXP_NO_G1_LIVE4H                     |
| OB_RETEST     |       14 | X6_EXP_NO_G1_LIVE4H                     |
| FVG_RETEST    |      236 | D0_CORE_PLUS_RAW_EXP24H                 |
| BOS_RETEST    |      140 | D0_CORE_PLUS_RAW_EXP24H                 |
| SWEEP_RECLAIM |      118 | D0_CORE_PLUS_RAW_EXP24H                 |
| OB_RETEST     |       24 | D0_CORE_PLUS_RAW_EXP24H                 |
| FVG_RETEST    |      196 | D1_CORE_PLUS_EXP_LIVE4H                 |
| BOS_RETEST    |      113 | D1_CORE_PLUS_EXP_LIVE4H                 |
| SWEEP_RECLAIM |      103 | D1_CORE_PLUS_EXP_LIVE4H                 |
| OB_RETEST     |       17 | D1_CORE_PLUS_EXP_LIVE4H                 |
| FVG_RETEST    |      108 | D2_CORE_PLUS_EXP_FORMING_LIVE4H         |
| BOS_RETEST    |       72 | D2_CORE_PLUS_EXP_FORMING_LIVE4H         |
| SWEEP_RECLAIM |       64 | D2_CORE_PLUS_EXP_FORMING_LIVE4H         |
| OB_RETEST     |       12 | D2_CORE_PLUS_EXP_FORMING_LIVE4H         |
| FVG_RETEST    |      163 | D3_CORE_PLUS_EXP_MATURE_LIVE4H          |
| BOS_RETEST    |       81 | D3_CORE_PLUS_EXP_MATURE_LIVE4H          |
| SWEEP_RECLAIM |       80 | D3_CORE_PLUS_EXP_MATURE_LIVE4H          |
| OB_RETEST     |       12 | D3_CORE_PLUS_EXP_MATURE_LIVE4H          |
| FVG_RETEST    |      177 | D4_CORE_PLUS_EXP_ADX_HIGH_LIVE4H        |
| BOS_RETEST    |       95 | D4_CORE_PLUS_EXP_ADX_HIGH_LIVE4H        |
| SWEEP_RECLAIM |       93 | D4_CORE_PLUS_EXP_ADX_HIGH_LIVE4H        |
| OB_RETEST     |       15 | D4_CORE_PLUS_EXP_ADX_HIGH_LIVE4H        |
| FVG_RETEST    |      123 | D5_CORE_PLUS_EXP_BREAKOUT_ACCEPT_LIVE4H |
| BOS_RETEST    |       68 | D5_CORE_PLUS_EXP_BREAKOUT_ACCEPT_LIVE4H |
| SWEEP_RECLAIM |       36 | D5_CORE_PLUS_EXP_BREAKOUT_ACCEPT_LIVE4H |
| OB_RETEST     |       13 | D5_CORE_PLUS_EXP_BREAKOUT_ACCEPT_LIVE4H |
| FVG_RETEST    |      197 | D6_CORE_PLUS_EXP_NO_G1_LIVE4H           |
| BOS_RETEST    |      110 | D6_CORE_PLUS_EXP_NO_G1_LIVE4H           |
| SWEEP_RECLAIM |      101 | D6_CORE_PLUS_EXP_NO_G1_LIVE4H           |
| OB_RETEST     |       17 | D6_CORE_PLUS_EXP_NO_G1_LIVE4H           |

## Boundary
Discovery on reused XAU history only. Any selected winner requires frozen temporal/fresh-OOS replication before EA use.