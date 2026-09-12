# UNIVERSAL_CONTEXT_STATE_GEOMETRY_AND_DIRECTION_DECOUPLING_LAB_002
**Verdict: GEOMETRY_DIRECTION_DECOUPLING_NOT_SUPPORTED**

## Primary gates
- H1 EXPANSION geometry: **FAIL** — pooled range effect +0.079 ATR, CI [+0.007, +0.158].
- H2 COMPRESSION geometry: **FAIL** — pooled range effect -0.011 ATR, CI [-0.046, +0.026].
- H3 Directional Pressure cross-market: **FAIL** — pooled signed8 +0.024 ATR, CI [+0.003, +0.045].
- H4 HIGH vs MODERATE pressure: **FAIL** — pooled delta +0.024 ATR, CI [-0.018, +0.063].
- H5 Direction across geometry states: **FAIL**.
- H6 Geometry breadth: **PASS**.

## Market data / ready bars

| market   |   h4_rows |   ready_bars | first               | last                |
|:---------|----------:|-------------:|:--------------------|:--------------------|
| XAUUSD   |      6417 |         6216 | 2022-06-01 00:00:00 | 2026-07-23 20:00:00 |
| BTCUSDT  |     12228 |        12027 | 2021-01-01 00:00:00 | 2026-07-31 20:00:00 |
| EURUSD   |      5514 |         5313 | 2023-01-02 00:00:00 | 2026-07-17 20:00:00 |

## Geometry occupancy

| market   |   COMPRESSION |   EXPANSION |   RETRACEMENT |   TRANSITION |
|:---------|--------------:|------------:|--------------:|-------------:|
| BTCUSDT  |         0.201 |       0.071 |         0.452 |        0.277 |
| EURUSD   |         0.243 |       0.080 |         0.413 |        0.265 |
| XAUUSD   |         0.222 |       0.092 |         0.418 |        0.268 |

## Geometry semantic effects

| market   | state       | metric        |   n_state |   n_other |   mean_state |   mean_other |   effect |
|:---------|:------------|:--------------|----------:|----------:|-------------:|-------------:|---------:|
| BTCUSDT  | EXPANSION   | range8_atr    |       848 |     11177 |       1.6678 |       1.4584 |   0.2094 |
| BTCUSDT  | COMPRESSION | range8_atr    |      2412 |      9613 |       1.4696 |       1.4740 |  -0.0044 |
| BTCUSDT  | RETRACEMENT | range8_atr    |      5431 |      6594 |       1.4296 |       1.5090 |  -0.0793 |
| BTCUSDT  | RETRACEMENT | absclose8_atr |      5431 |      6594 |       0.6468 |       0.6876 |  -0.0408 |
| EURUSD   | EXPANSION   | range8_atr    |       390 |      4557 |       1.4286 |       1.5100 |  -0.0814 |
| EURUSD   | COMPRESSION | range8_atr    |      1208 |      3739 |       1.5630 |       1.4844 |   0.0785 |
| EURUSD   | RETRACEMENT | range8_atr    |      2051 |      2896 |       1.4773 |       1.5223 |  -0.0450 |
| EURUSD   | RETRACEMENT | absclose8_atr |      2051 |      2896 |       0.7243 |       0.7651 |  -0.0408 |
| XAUUSD   | EXPANSION   | range8_atr    |       523 |      5265 |       1.4773 |       1.4955 |  -0.0182 |
| XAUUSD   | COMPRESSION | range8_atr    |      1276 |      4512 |       1.4066 |       1.5185 |  -0.1119 |
| XAUUSD   | RETRACEMENT | range8_atr    |      2425 |      3363 |       1.5329 |       1.4657 |   0.0672 |
| XAUUSD   | RETRACEMENT | absclose8_atr |      2425 |      3363 |       0.7575 |       0.7326 |   0.0248 |

## Direction by market

| market   |    n |   mean_signed8 |   bull_n |   bull_mean |   bear_n |   bear_mean |
|:---------|-----:|---------------:|---------:|------------:|---------:|------------:|
| BTCUSDT  | 9386 |         0.0183 |     4835 |      0.0349 |     4551 |      0.0006 |
| EURUSD   | 3795 |        -0.0110 |     1929 |     -0.0141 |     1866 |     -0.0078 |
| XAUUSD   | 4375 |         0.0673 |     2896 |      0.1083 |     1479 |     -0.0129 |

## Pressure magnitude by market

| market   |   high_n |   moderate_n |   high_mean |   moderate_mean |   effect |
|:---------|---------:|-------------:|------------:|----------------:|---------:|
| BTCUSDT  |     5607 |         3779 |      0.0340 |         -0.0050 |   0.0390 |
| EURUSD   |     2208 |         1587 |     -0.0193 |          0.0005 |  -0.0198 |
| XAUUSD   |     2740 |         1635 |      0.0762 |          0.0525 |   0.0237 |

## H5 — direction by geometry state

| state       | eligible   | pass_ci   |   observed |   ci_lo |   ci_hi |    n |   clusters |
|:------------|:-----------|:----------|-----------:|--------:|--------:|-----:|-----------:|
| EXPANSION   | True       | True      |     0.0649 |  0.0049 |  0.1259 | 1614 |        332 |
| RETRACEMENT | True       | False     |     0.0142 | -0.0126 |  0.0398 | 9293 |        579 |
| COMPRESSION | True       | False     |     0.0020 | -0.0621 |  0.0663 | 1865 |        346 |

## REVERSAL overlay diagnostic
- pooled reverse12: -0.027 ATR, CI [-0.092, +0.040], N=1580.

| market   |   count |    mean |
|:---------|--------:|--------:|
| BTCUSDT  |     853 | -0.0384 |
| EURUSD   |     327 | -0.0201 |
| XAUUSD   |     400 | -0.0094 |

## Pressure deciles diagnostic

|   ('pressure_decile', '') |   ('direction_signed8_atr', 'count') |   ('direction_signed8_atr', 'mean') |   ('direction_signed24_atr', 'count') |   ('direction_signed24_atr', 'mean') |
|--------------------------:|-------------------------------------:|------------------------------------:|--------------------------------------:|-------------------------------------:|
|                    1.0000 |                            1759.0000 |                             -0.0025 |                             1646.0000 |                              -0.0691 |
|                    2.0000 |                            1761.0000 |                             -0.0166 |                             1644.0000 |                               0.0179 |
|                    3.0000 |                            1740.0000 |                              0.0056 |                             1629.0000 |                               0.1297 |
|                    4.0000 |                            1763.0000 |                              0.0513 |                             1644.0000 |                               0.1277 |
|                    5.0000 |                            1758.0000 |                              0.0598 |                             1640.0000 |                               0.1108 |
|                    6.0000 |                            1750.0000 |                              0.0077 |                             1627.0000 |                               0.1609 |
|                    7.0000 |                            1769.0000 |                              0.0041 |                             1647.0000 |                              -0.0183 |
|                    8.0000 |                            1736.0000 |                              0.0048 |                             1607.0000 |                               0.0364 |
|                    9.0000 |                            1768.0000 |                              0.0304 |                             1632.0000 |                               0.1720 |
|                   10.0000 |                            1752.0000 |                              0.0969 |                             1626.0000 |                               0.1370 |

## Common-window diagnostic

| market   | state       | metric     |   n_state |   n_other |   mean_state |   mean_other |   effect |         n |   mean_signed8 |    bull_n |   bull_mean |    bear_n |   bear_mean |
|:---------|:------------|:-----------|----------:|----------:|-------------:|-------------:|---------:|----------:|---------------:|----------:|------------:|----------:|------------:|
| BTCUSDT  | EXPANSION   | range8_atr |  465.0000 | 6393.0000 |       1.6718 |       1.4648 |   0.2070 |  nan      |       nan      |  nan      |    nan      |  nan      |    nan      |
| BTCUSDT  | COMPRESSION | range8_atr | 1487.0000 | 5371.0000 |       1.4461 |       1.4879 |  -0.0417 |  nan      |       nan      |  nan      |    nan      |  nan      |    nan      |
| BTCUSDT  | DIRECTION   | signed8    |  nan      |  nan      |     nan      |     nan      | nan      | 5259.0000 |         0.0318 | 2901.0000 |      0.0613 | 2358.0000 |     -0.0045 |
| EURUSD   | EXPANSION   | range8_atr |  359.0000 | 4172.0000 |       1.4307 |       1.5083 |  -0.0777 |  nan      |       nan      |  nan      |    nan      |  nan      |    nan      |
| EURUSD   | COMPRESSION | range8_atr | 1163.0000 | 3368.0000 |       1.5646 |       1.4806 |   0.0841 |  nan      |       nan      |  nan      |    nan      |  nan      |    nan      |
| EURUSD   | DIRECTION   | signed8    |  nan      |  nan      |     nan      |     nan      | nan      | 3429.0000 |        -0.0110 | 1732.0000 |     -0.0096 | 1697.0000 |     -0.0126 |
| XAUUSD   | EXPANSION   | range8_atr |  413.0000 | 4097.0000 |       1.4991 |       1.4889 |   0.0102 |  nan      |       nan      |  nan      |    nan      |  nan      |    nan      |
| XAUUSD   | COMPRESSION | range8_atr | 1089.0000 | 3421.0000 |       1.3923 |       1.5209 |  -0.1286 |  nan      |       nan      |  nan      |    nan      |  nan      |    nan      |
| XAUUSD   | DIRECTION   | signed8    |  nan      |  nan      |     nan      |     nan      | nan      | 3345.0000 |         0.0705 | 2310.0000 |      0.1086 | 1035.0000 |     -0.0146 |

## Boundary
State geometry and direction use the frozen prereg formulas. No asset-specific thresholds or outcome-driven retuning are permitted in LAB002. This LAB does not establish entry, SL/TP, profit probability, or execution economics.