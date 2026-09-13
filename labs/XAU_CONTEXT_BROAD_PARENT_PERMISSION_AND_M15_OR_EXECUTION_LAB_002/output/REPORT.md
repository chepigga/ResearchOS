# XAU_CONTEXT_BROAD_PARENT_PERMISSION_AND_M15_OR_EXECUTION_LAB_002
**Verdict: FREQUENCY_LIFT_FOUND_BUT_EDGE_NOT_PRESERVED**
**Discovery winner: NONE**
**Baseline parity: True {'trades': True, 'ev40': True, 'pf40': True, 'ddpct': True}**

## Parent summary

| parent                       |   qualifying_h4_all |   qualifying_h4_eval |   episodes_all |   permission_hours_eval |   permission_pct_eval |   trades |   mean_trades_month |   median_trades_month |   pct_months_ge10 |   gross_expectancy_r |   commission_expectancy_r |   spread20_expectancy_r |   spread40_expectancy_r |   pf_spread40 |   cum_spread40_r |   mean_spread40_r_month |   max_dd_r |   max_dd_pct_at_025 |   max_consecutive_losses |   win_rate_net40 |   median_hold_h |   p90_hold_h |   timeout_frac |   positive_blocks |   min_block_cum_r |   top_abs_trade_share | h1_frequency   | h2_edge   | h3_both   | classification   |
|:-----------------------------|--------------------:|---------------------:|---------------:|------------------------:|----------------------:|---------:|--------------------:|----------------------:|------------------:|---------------------:|--------------------------:|------------------------:|------------------------:|--------------:|-----------------:|------------------------:|-----------:|--------------------:|-------------------------:|-----------------:|----------------:|-------------:|---------------:|------------------:|------------------:|----------------------:|:---------------|:----------|:----------|:-----------------|
| P0_BASELINE_E75              |                  62 |                   53 |             42 |                964.0000 |                0.0315 |       98 |              2.3333 |                0.0000 |            0.0714 |               0.1813 |                    0.1721 |                  0.1237 |                  0.0753 |        1.1407 |           7.3792 |                  0.1757 |     7.6836 |              1.9209 |                        5 |           0.5000 |          1.3417 |       8.0000 |         0.1327 |                 3 |           -2.8042 |                0.0137 | False          | False     | False     | NOT_VIABLE       |
| P1_PULLBACK_D14              |                1310 |                 1197 |            158 |               8428.0000 |                0.2750 |      711 |             16.9286 |               17.0000 |            0.7619 |               0.0177 |                    0.0064 |                 -0.0583 |                 -0.1229 |        0.8129 |         -87.3774 |                 -2.0804 |   126.0890 |             31.5222 |                       10 |           0.4219 |          1.3000 |       5.2667 |         0.0577 |                 2 |          -69.0450 |                0.0024 | True           | False     | False     | FREQUENCY_ONLY   |
| P2_G1_D14                    |                 299 |                  271 |             74 |               2568.0000 |                0.0838 |      238 |              5.6667 |                4.5000 |            0.2381 |              -0.0100 |                   -0.0213 |                 -0.0845 |                 -0.1476 |        0.7782 |         -35.1380 |                 -0.8366 |    42.1966 |             10.5492 |                        7 |           0.3992 |          1.1000 |       5.0583 |         0.0672 |                 1 |          -27.6660 |                0.0113 | False          | False     | False     | NOT_VIABLE       |
| P3_EXPANSION_D14             |                 848 |                  804 |             98 |               5200.0000 |                0.1697 |      444 |             10.5714 |                9.5000 |            0.5000 |               0.1510 |                    0.1410 |                  0.0861 |                  0.0312 |        1.0537 |          13.8322 |                  0.3293 |    21.5527 |              5.3882 |                        8 |           0.4685 |          1.2333 |       5.1883 |         0.0608 |                 3 |          -14.1360 |                0.0054 | False          | False     | False     | NOT_VIABLE       |
| P4_PULLBACK_OR_EXPANSION_D14 |                2158 |                 2001 |            154 |              11508.0000 |                0.3755 |      897 |             21.3571 |               21.0000 |            0.7619 |               0.0571 |                    0.0458 |                 -0.0181 |                 -0.0821 |        0.8717 |         -73.6549 |                 -1.7537 |   112.8489 |             28.2122 |                       12 |           0.4326 |          1.2500 |       4.8500 |         0.0491 |                 2 |          -73.1156 |                0.0021 | True           | False     | False     | FREQUENCY_ONLY   |
| P5_NONRANGE_D14              |                2158 |                 2001 |            154 |              11508.0000 |                0.3755 |      897 |             21.3571 |               21.0000 |            0.7619 |               0.0571 |                    0.0458 |                 -0.0181 |                 -0.0821 |        0.8717 |         -73.6549 |                 -1.7537 |   112.8489 |             28.2122 |                       12 |           0.4326 |          1.2500 |       4.8500 |         0.0491 |                 2 |          -73.1156 |                0.0021 | True           | False     | False     | FREQUENCY_ONLY   |
| P6_D14_ALL                   |                2205 |                 2046 |            154 |              11736.0000 |                0.3829 |      908 |             21.6190 |               22.5000 |            0.7619 |               0.0565 |                    0.0453 |                 -0.0190 |                 -0.0832 |        0.8703 |         -75.5368 |                 -1.7985 |   116.6142 |             29.1535 |                       12 |           0.4317 |          1.2833 |       4.9717 |         0.0518 |                 2 |          -78.3539 |                0.0020 | True           | False     | False     | FREQUENCY_ONLY   |

## Calendar blocks

| block   |   n |   expectancy_net40 |   cum_net40_r | parent                       |
|:--------|----:|-------------------:|--------------:|:-----------------------------|
| 2023    |  22 |             0.2483 |        5.4630 | P0_BASELINE_E75              |
| 2024    |  22 |             0.1112 |        2.4468 | P0_BASELINE_E75              |
| 2025    |  38 |             0.0598 |        2.2737 | P0_BASELINE_E75              |
| 2026H1  |  16 |            -0.1753 |       -2.8042 | P0_BASELINE_E75              |
| 2023    | 182 |            -0.3794 |      -69.0450 | P1_PULLBACK_D14              |
| 2024    | 196 |            -0.1988 |      -38.9675 | P1_PULLBACK_D14              |
| 2025    | 279 |             0.0387 |       10.8017 | P1_PULLBACK_D14              |
| 2026H1  |  54 |             0.1821 |        9.8334 | P1_PULLBACK_D14              |
| 2023    |  61 |            -0.4535 |      -27.6660 | P2_G1_D14                    |
| 2024    |  57 |            -0.0617 |       -3.5187 | P2_G1_D14                    |
| 2025    |  89 |            -0.0689 |       -6.1353 | P2_G1_D14                    |
| 2026H1  |  31 |             0.0704 |        2.1821 | P2_G1_D14                    |
| 2023    |  80 |            -0.1767 |      -14.1360 | P3_EXPANSION_D14             |
| 2024    | 139 |             0.0531 |        7.3868 | P3_EXPANSION_D14             |
| 2025    | 195 |             0.0941 |       18.3575 | P3_EXPANSION_D14             |
| 2026H1  |  30 |             0.0741 |        2.2239 | P3_EXPANSION_D14             |
| 2023    | 213 |            -0.3433 |      -73.1156 | P4_PULLBACK_OR_EXPANSION_D14 |
| 2024    | 263 |            -0.0939 |      -24.6975 | P4_PULLBACK_OR_EXPANSION_D14 |
| 2025    | 348 |             0.0452 |       15.7174 | P4_PULLBACK_OR_EXPANSION_D14 |
| 2026H1  |  73 |             0.1156 |        8.4409 | P4_PULLBACK_OR_EXPANSION_D14 |
| 2023    | 213 |            -0.3433 |      -73.1156 | P5_NONRANGE_D14              |
| 2024    | 263 |            -0.0939 |      -24.6975 | P5_NONRANGE_D14              |
| 2025    | 348 |             0.0452 |       15.7174 | P5_NONRANGE_D14              |
| 2026H1  |  73 |             0.1156 |        8.4409 | P5_NONRANGE_D14              |
| 2023    | 214 |            -0.3661 |      -78.3539 | P6_D14_ALL                   |
| 2024    | 266 |            -0.0881 |      -23.4469 | P6_D14_ALL                   |
| 2025    | 355 |             0.0521 |       18.5008 | P6_D14_ALL                   |
| 2026H1  |  73 |             0.1063 |        7.7631 | P6_D14_ALL                   |

## Trigger / fill diagnostics

| parent                       | family        |   raw_triggers_eval |   valid_fills_eval |   valid_rate |
|:-----------------------------|:--------------|--------------------:|-------------------:|-------------:|
| P0_BASELINE_E75              | BOS_RETEST    |                 337 |                152 |       0.4510 |
| P0_BASELINE_E75              | FVG_RETEST    |                 382 |                212 |       0.5550 |
| P0_BASELINE_E75              | OB_RETEST     |                 121 |                 45 |       0.3719 |
| P0_BASELINE_E75              | SWEEP_RECLAIM |                 117 |                115 |       0.9829 |
| P1_PULLBACK_D14              | BOS_RETEST    |                2970 |               1397 |       0.4704 |
| P1_PULLBACK_D14              | FVG_RETEST    |                3230 |               1968 |       0.6093 |
| P1_PULLBACK_D14              | OB_RETEST     |                1035 |                456 |       0.4406 |
| P1_PULLBACK_D14              | SWEEP_RECLAIM |                1377 |               1340 |       0.9731 |
| P2_G1_D14                    | BOS_RETEST    |                 895 |                387 |       0.4324 |
| P2_G1_D14                    | FVG_RETEST    |                 979 |                561 |       0.5730 |
| P2_G1_D14                    | OB_RETEST     |                 313 |                121 |       0.3866 |
| P2_G1_D14                    | SWEEP_RECLAIM |                 428 |                416 |       0.9720 |
| P3_EXPANSION_D14             | BOS_RETEST    |                1902 |                906 |       0.4763 |
| P3_EXPANSION_D14             | FVG_RETEST    |                2030 |               1251 |       0.6163 |
| P3_EXPANSION_D14             | OB_RETEST     |                 688 |                317 |       0.4608 |
| P3_EXPANSION_D14             | SWEEP_RECLAIM |                 771 |                757 |       0.9818 |
| P4_PULLBACK_OR_EXPANSION_D14 | BOS_RETEST    |                4056 |               1932 |       0.4763 |
| P4_PULLBACK_OR_EXPANSION_D14 | FVG_RETEST    |                4401 |               2708 |       0.6153 |
| P4_PULLBACK_OR_EXPANSION_D14 | OB_RETEST     |                1431 |                648 |       0.4528 |
| P4_PULLBACK_OR_EXPANSION_D14 | SWEEP_RECLAIM |                1835 |               1789 |       0.9749 |
| P5_NONRANGE_D14              | BOS_RETEST    |                4056 |               1932 |       0.4763 |
| P5_NONRANGE_D14              | FVG_RETEST    |                4401 |               2708 |       0.6153 |
| P5_NONRANGE_D14              | OB_RETEST     |                1431 |                648 |       0.4528 |
| P5_NONRANGE_D14              | SWEEP_RECLAIM |                1835 |               1789 |       0.9749 |
| P6_D14_ALL                   | BOS_RETEST    |                4146 |               1971 |       0.4754 |
| P6_D14_ALL                   | FVG_RETEST    |                4498 |               2760 |       0.6136 |
| P6_D14_ALL                   | OB_RETEST     |                1461 |                659 |       0.4511 |
| P6_D14_ALL                   | SWEEP_RECLAIM |                1865 |               1816 |       0.9737 |

## OR-router composition

| source        |   trades | parent                       |
|:--------------|---------:|:-----------------------------|
| FVG_RETEST    |       52 | P0_BASELINE_E75              |
| BOS_RETEST    |       23 | P0_BASELINE_E75              |
| SWEEP_RECLAIM |       20 | P0_BASELINE_E75              |
| OB_RETEST     |        3 | P0_BASELINE_E75              |
| FVG_RETEST    |      296 | P1_PULLBACK_D14              |
| SWEEP_RECLAIM |      192 | P1_PULLBACK_D14              |
| BOS_RETEST    |      184 | P1_PULLBACK_D14              |
| OB_RETEST     |       39 | P1_PULLBACK_D14              |
| FVG_RETEST    |      110 | P2_G1_D14                    |
| SWEEP_RECLAIM |       71 | P2_G1_D14                    |
| BOS_RETEST    |       49 | P2_G1_D14                    |
| OB_RETEST     |        8 | P2_G1_D14                    |
| FVG_RETEST    |      202 | P3_EXPANSION_D14             |
| BOS_RETEST    |      121 | P3_EXPANSION_D14             |
| SWEEP_RECLAIM |      100 | P3_EXPANSION_D14             |
| OB_RETEST     |       21 | P3_EXPANSION_D14             |
| FVG_RETEST    |      388 | P4_PULLBACK_OR_EXPANSION_D14 |
| BOS_RETEST    |      237 | P4_PULLBACK_OR_EXPANSION_D14 |
| SWEEP_RECLAIM |      225 | P4_PULLBACK_OR_EXPANSION_D14 |
| OB_RETEST     |       47 | P4_PULLBACK_OR_EXPANSION_D14 |
| FVG_RETEST    |      388 | P5_NONRANGE_D14              |
| BOS_RETEST    |      237 | P5_NONRANGE_D14              |
| SWEEP_RECLAIM |      225 | P5_NONRANGE_D14              |
| OB_RETEST     |       47 | P5_NONRANGE_D14              |
| FVG_RETEST    |      397 | P6_D14_ALL                   |
| BOS_RETEST    |      238 | P6_D14_ALL                   |
| SWEEP_RECLAIM |      222 | P6_D14_ALL                   |
| OB_RETEST     |       51 | P6_D14_ALL                   |

## Boundary
Discovery only on reused XAU history. Any selected parent must be frozen and replicated on a separate temporal/fresh-OOS sample before EA or production use.