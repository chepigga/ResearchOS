# UNIVERSAL_CONTEXT_STATE_SPECIFIC_PREDICTIVE_HEADS_LAB_003
**Verdict: STATE_SPECIFIC_HEADS_NOT_SUPPORTED**

## Primary gates
- H1 EXPANSION HIGH continuation: **FAIL** — pooled +0.0889 ATR, CI [-0.0092, +0.1804], N=695.
- H2 EXPANSION HIGH vs non-HIGH: **FAIL** — delta +0.0422 ATR, CI [-0.0889, +0.1707].
- H3 RETRACEMENT continuation: **FAIL** — pooled +0.0619 ATR, CI [-0.0177, +0.1434], N=6570.
- H4 RETRACEMENT reversal: **FAIL** — pooled -0.0417 ATR, CI [-0.3341, +0.2615], N=149.
- H5 COMPRESSION breakout direction: **FAIL** — pooled accuracy 51.44%, CI [48.23%, 54.68%], N=2296.
- H6 coverage sanity: **PASS**.

## Market data

| market   |   h4_rows |   ready_bars | first               | last                |
|:---------|----------:|-------------:|:--------------------|:--------------------|
| XAUUSD   |      6417 |         6216 | 2022-06-01 00:00:00 | 2026-07-23 20:00:00 |
| BTCUSDT  |     12228 |        12027 | 2021-01-01 00:00:00 | 2026-07-31 20:00:00 |
| EURUSD   |      5514 |         5313 | 2023-01-02 00:00:00 | 2026-07-17 20:00:00 |

## EXPANSION HIGH

| market   |   n |   mean |
|:---------|----:|-------:|
| BTCUSDT  | 276 | 0.1065 |
| EURUSD   | 168 | 0.0672 |
| XAUUSD   | 251 | 0.0842 |

## EXPANSION HIGH vs non-HIGH

| market   |   n_a |   n_b |   mean_a |   mean_b |   effect |
|:---------|------:|------:|---------:|---------:|---------:|
| BTCUSDT  |   276 |   502 |   0.1065 |   0.0873 |   0.0192 |
| EURUSD   |   168 |   190 |   0.0672 |  -0.0398 |   0.1070 |
| XAUUSD   |   251 |   227 |   0.0842 |   0.0297 |   0.0546 |

## RETRACEMENT continuation

| market   |    n |    mean |
|:---------|-----:|--------:|
| BTCUSDT  | 3935 |  0.0485 |
| EURUSD   | 1199 | -0.0754 |
| XAUUSD   | 1436 |  0.2136 |

## RETRACEMENT reversal

| market   |   n |    mean |
|:---------|----:|--------:|
| BTCUSDT  |  77 |  0.0899 |
| EURUSD   |  32 | -0.2642 |
| XAUUSD   |  40 | -0.1170 |

## COMPRESSION first-passage

| market   |    n |   accuracy |
|:---------|-----:|-----------:|
| BTCUSDT  | 1100 |     0.5000 |
| EURUSD   |  613 |     0.5204 |
| XAUUSD   |  583 |     0.5352 |

## Coverage

| market   |   exp_eligible |   exp_high |   exp_high_cov |   ret_eligible |   ret_nonabstain |   ret_nonabstain_cov |   comp_eligible |   comp_resolved_head |   comp_resolved_cov |
|:---------|---------------:|-----------:|---------------:|---------------:|-----------------:|---------------------:|----------------:|---------------------:|--------------------:|
| BTCUSDT  |            778 |        276 |         0.3548 |           5096 |             4012 |               0.7873 |            2414 |                 1331 |              0.5514 |
| EURUSD   |            387 |        178 |         0.4599 |           2049 |             1548 |               0.7555 |            1291 |                  747 |              0.5786 |
| XAUUSD   |            519 |        273 |         0.5260 |           2393 |             1886 |               0.7881 |            1382 |                  739 |              0.5347 |

## Side asymmetry diagnostic

| market   | head        | side   |   n |    mean |
|:---------|:------------|:-------|----:|--------:|
| BTCUSDT  | EXPANSION   | BULL   | 365 |  0.1152 |
| BTCUSDT  | EXPANSION   | BEAR   | 413 |  0.0754 |
| BTCUSDT  | COMPRESSION | BULL   | 613 |  0.5122 |
| BTCUSDT  | COMPRESSION | BEAR   | 487 |  0.4846 |
| EURUSD   | EXPANSION   | BULL   | 188 |  0.0205 |
| EURUSD   | EXPANSION   | BEAR   | 170 | -0.0008 |
| EURUSD   | COMPRESSION | BULL   | 282 |  0.5957 |
| EURUSD   | COMPRESSION | BEAR   | 331 |  0.4562 |
| XAUUSD   | EXPANSION   | BULL   | 304 |  0.0935 |
| XAUUSD   | EXPANSION   | BEAR   | 174 | -0.0031 |
| XAUUSD   | COMPRESSION | BULL   | 229 |  0.5895 |
| XAUUSD   | COMPRESSION | BEAR   | 354 |  0.5000 |

Compression HIGH minus MODERATE accuracy: +0.0359, CI [-0.0636, +0.1315].

## Common-window diagnostic

| market   |   exp_high_n |   exp_high_mean |   ret_cont_n |   ret_cont_mean |   comp_n |   comp_accuracy |
|:---------|-------------:|----------------:|-------------:|----------------:|---------:|----------------:|
| BTCUSDT  |          178 |          0.1124 |         2187 |          0.0807 |      671 |          0.5216 |
| EURUSD   |          158 |          0.0725 |         1074 |         -0.1217 |      579 |          0.5216 |
| XAUUSD   |          213 |          0.0773 |         1100 |          0.3151 |      478 |          0.5377 |

## Boundary
Frozen LAB002 geometry was not changed. LAB003 tests predictive heads only; it does not establish executable entry/SL/TP, profit probability, or broker economics.