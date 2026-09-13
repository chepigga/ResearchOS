# UNIVERSAL_CONTEXT_MARKET_CONDITIONAL_ADAPTIVE_CALIBRATION_LAB_006
**Verdict: MARKET_CONDITIONAL_ADAPTIVE_CALIBRATION_NOT_SUPPORTED**

## Primary gates
- H1 adaptive EXPANSION: **FAIL** — pooled +0.7588 ATR, CI [+0.7588, +0.7588], N=3.
- H2 adaptive RETRACEMENT: **FAIL** — pooled -0.0639 ATR, CI [-0.3210, +0.1705], N=317.
- H3 adaptive COMPRESSION: **FAIL** — accuracy 48.45%, CI [40.00%, 56.69%], N=322.
- H4 confidence calibration: **FAIL** — Brier 0.2707, ECE 0.1511, N=728.
- H5 coverage / abstention sanity: **FAIL** — markets in-band {'EXPANSION': 0, 'RETRACEMENT': 4, 'COMPRESSION': 5}.
- H6 adaptive > rank-only baseline: **PASS** — positive states 2/3, CI-positive states 1/3.

## Market data

| market   |   h4_rows |   ready_bars | first               | last                |
|:---------|----------:|-------------:|:--------------------|:--------------------|
| XAUUSD   |      6417 |         6216 | 2022-06-01 00:00:00 | 2026-07-23 20:00:00 |
| BTCUSDT  |     12228 |        12027 | 2021-01-01 00:00:00 | 2026-07-31 20:00:00 |
| EURUSD   |      5514 |         5313 | 2023-01-02 00:00:00 | 2026-07-17 20:00:00 |
| USDJPY   |      3105 |         2904 | 2024-09-15 20:00:00 | 2026-08-31 20:00:00 |
| GBPUSD   |      3108 |         2902 | 2024-09-15 20:00:00 | 2026-08-31 20:00:00 |
| AUDUSD   |      3117 |         2899 | 2024-09-15 20:00:00 | 2026-08-31 20:00:00 |
| USDCAD   |      3117 |         2906 | 2024-09-15 20:00:00 | 2026-08-31 20:00:00 |

## EXPANSION by market

| market   | state     |   adaptive_n |   adaptive_mean |   baseline_n |   baseline_mean |   state_bars |   adaptive_cov |   conflict_rate |
|:---------|:----------|-------------:|----------------:|-------------:|----------------:|-------------:|---------------:|----------------:|
| AUDUSD   | EXPANSION |            0 |        nan      |           58 |          0.0314 |          139 |         0.0000 |          0.0000 |
| BTCUSDT  | EXPANSION |            0 |        nan      |           97 |          0.0355 |          169 |         0.0000 |          0.0000 |
| EURUSD   | EXPANSION |            0 |        nan      |           61 |          0.1100 |          129 |         0.0000 |          0.0000 |
| GBPUSD   | EXPANSION |            0 |        nan      |           71 |         -0.1046 |          173 |         0.0000 |          0.0000 |
| USDCAD   | EXPANSION |            0 |        nan      |           69 |         -0.1253 |          170 |         0.0000 |          0.0000 |
| USDJPY   | EXPANSION |            0 |        nan      |           54 |          0.2196 |          124 |         0.0000 |          0.0000 |
| XAUUSD   | EXPANSION |            3 |          0.7588 |           80 |          0.1443 |          162 |         0.0185 |          0.0000 |

Adaptive minus rank-only: {'observed': 0.7194175146849042, 'ci_lo': 0.6221050897993705, 'ci_hi': 0.8093817576700658, 'n_a': 3, 'n_b': 490, 'clusters': 223}

## RETRACEMENT by market

| market   | state       |   adaptive_n |   adaptive_mean |   baseline_n |   baseline_mean |   state_bars |   adaptive_cov |   conflict_rate |
|:---------|:------------|-------------:|----------------:|-------------:|----------------:|-------------:|---------------:|----------------:|
| AUDUSD   | RETRACEMENT |           30 |          0.7656 |          358 |          0.0250 |          782 |         0.0550 |          0.0000 |
| BTCUSDT  | RETRACEMENT |           45 |          0.1862 |          551 |         -0.0664 |         1047 |         0.0430 |          0.0000 |
| EURUSD   | RETRACEMENT |           32 |          0.0941 |          301 |         -0.2136 |          682 |         0.0572 |          0.0000 |
| GBPUSD   | RETRACEMENT |           17 |         -1.5234 |          313 |         -0.2948 |          760 |         0.0289 |          0.0000 |
| USDCAD   | RETRACEMENT |          104 |         -0.2135 |          315 |          0.1621 |          725 |         0.1834 |          0.0000 |
| USDJPY   | RETRACEMENT |            7 |         -0.7177 |          297 |         -0.1813 |          736 |         0.0136 |          0.0000 |
| XAUUSD   | RETRACEMENT |           82 |         -0.0184 |          270 |          0.0609 |          645 |         0.1721 |          0.0000 |

Adaptive minus rank-only: {'observed': 0.006981649896709838, 'ci_lo': -0.2338158748449329, 'ci_hi': 0.23832949770258263, 'n_a': 317, 'n_b': 2405, 'clusters': 357}

## COMPRESSION by market

| market   | state       |   adaptive_n |   adaptive_mean |   baseline_n |   baseline_mean |   state_bars |   adaptive_cov |   conflict_rate |
|:---------|:------------|-------------:|----------------:|-------------:|----------------:|-------------:|---------------:|----------------:|
| AUDUSD   | COMPRESSION |           16 |          0.4375 |          149 |          0.5906 |          381 |         0.0472 |          0.0000 |
| BTCUSDT  | COMPRESSION |           79 |          0.3797 |          249 |          0.5020 |          596 |         0.1527 |          0.0000 |
| EURUSD   | COMPRESSION |           90 |          0.4667 |          210 |          0.5143 |          484 |         0.2149 |          0.0000 |
| GBPUSD   | COMPRESSION |            0 |        nan      |          180 |          0.4778 |          388 |         0.0000 |          0.0000 |
| USDCAD   | COMPRESSION |           12 |          0.4167 |          176 |          0.5511 |          390 |         0.0436 |          0.0000 |
| USDJPY   | COMPRESSION |           27 |          0.4444 |          178 |          0.5337 |          440 |         0.0705 |          0.0000 |
| XAUUSD   | COMPRESSION |           98 |          0.6122 |          164 |          0.5488 |          461 |         0.3406 |          0.0000 |

Adaptive minus rank-only: {'observed': -0.043093034537205255, 'ci_lo': -0.11717441167025777, 'ci_hi': 0.02762506792360169, 'n_a': 322, 'n_b': 1306, 'clusters': 252}

## Calibration bins

| bucket   |   n |   mean_p |   observed |   abs_gap | ece_used   |
|:---------|----:|---------:|-----------:|----------:|:-----------|
| 55-60    | 514 |   0.5716 |     0.4533 |    0.1183 | True       |
| 60-70    | 214 |   0.6272 |     0.3972 |    0.2300 | True       |
| 70-100   |   0 | nan      |   nan      |  nan      | False      |

## Side mix

| market   | state       |   bars |   bull_n |   bear_n |   wait_n |
|:---------|:------------|-------:|---------:|---------:|---------:|
| AUDUSD   | COMPRESSION |    381 |       18 |        0 |      363 |
| AUDUSD   | EXPANSION   |    139 |        0 |        0 |      139 |
| AUDUSD   | RETRACEMENT |    782 |       14 |       29 |      739 |
| BTCUSDT  | COMPRESSION |    596 |       37 |       54 |      505 |
| BTCUSDT  | EXPANSION   |    169 |        0 |        0 |      169 |
| BTCUSDT  | RETRACEMENT |   1047 |       45 |        0 |     1002 |
| EURUSD   | COMPRESSION |    484 |      103 |        1 |      380 |
| EURUSD   | EXPANSION   |    129 |        0 |        0 |      129 |
| EURUSD   | RETRACEMENT |    682 |        0 |       39 |      643 |
| GBPUSD   | COMPRESSION |    388 |        0 |        0 |      388 |
| GBPUSD   | EXPANSION   |    173 |        0 |        0 |      173 |
| GBPUSD   | RETRACEMENT |    760 |       18 |        4 |      738 |
| USDCAD   | COMPRESSION |    390 |        0 |       17 |      373 |
| USDCAD   | EXPANSION   |    170 |        0 |        0 |      170 |
| USDCAD   | RETRACEMENT |    725 |      105 |       28 |      592 |
| USDJPY   | COMPRESSION |    440 |       13 |       18 |      409 |
| USDJPY   | EXPANSION   |    124 |        0 |        0 |      124 |
| USDJPY   | RETRACEMENT |    736 |       10 |        0 |      726 |
| XAUUSD   | COMPRESSION |    461 |      128 |       29 |      304 |
| XAUUSD   | EXPANSION   |    162 |        3 |        0 |      159 |
| XAUUSD   | RETRACEMENT |    645 |       68 |       43 |      534 |

## Boundary
LAB006 is a causal adaptive-calibration design test on reused markets. It does not establish fresh unseen replication, executable entry/SL/TP profitability, or broker economics.