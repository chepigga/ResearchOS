# UNIVERSAL_CONTEXT_DIRECTIONAL_ASYMMETRY_AND_SEPARATE_BULL_BEAR_HEADS_LAB_004
**Verdict: SEPARATE_BULL_BEAR_HEADS_NOT_SUPPORTED**

## Primary gates
- H1 EXPANSION_BULL: **FAIL** — pooled +0.1148 ATR, CI [-0.0109, +0.2259], N=488.
- H2 EXPANSION_BEAR: **FAIL** — pooled +0.1186 ATR, CI [-0.0673, +0.2814], N=164.
- H3 EXPANSION asymmetry BULL-BEAR: **FAIL** — -0.0038 ATR, CI [-0.2069, +0.2206].
- H4 RETRACEMENT_BULL: **FAIL** — pooled +0.1402 ATR, CI [+0.0329, +0.2458], N=4467.
- H5 RETRACEMENT_BEAR: **FAIL** — pooled -0.0615 ATR, CI [-0.1707, +0.0468], N=2771.
- H6 COMPRESSION_BULL: **FAIL** — pooled accuracy 52.56%, CI [44.97%, 60.00%], N=293.
- H7 COMPRESSION_BEAR: **FAIL** — pooled accuracy 64.10%, CI [50.00%, 77.38%], N=78.
- H8 coverage/conflict sanity: **FAIL**.

## Market data

| market   |   h4_rows |   ready_bars | first               | last                |
|:---------|----------:|-------------:|:--------------------|:--------------------|
| XAUUSD   |      6417 |         6216 | 2022-06-01 00:00:00 | 2026-07-23 20:00:00 |
| BTCUSDT  |     12228 |        12027 | 2021-01-01 00:00:00 | 2026-07-31 20:00:00 |
| EURUSD   |      5514 |         5313 | 2023-01-02 00:00:00 | 2026-07-17 20:00:00 |

## Expansion BULL

| market   |   n |   mean |
|:---------|----:|-------:|
| BTCUSDT  | 166 | 0.1776 |
| EURUSD   | 117 | 0.1026 |
| XAUUSD   | 205 | 0.0709 |

## Expansion BEAR

| market   |   n |    mean |
|:---------|----:|--------:|
| BTCUSDT  |  83 |  0.2191 |
| EURUSD   |  33 | -0.1710 |
| XAUUSD   |  48 |  0.1439 |

## Expansion asymmetry by market

| market   |   bull_n |   bull_mean |   bear_n |   bear_mean |   bull_minus_bear |
|:---------|---------:|------------:|---------:|------------:|------------------:|
| BTCUSDT  |      166 |      0.1776 |       83 |      0.2191 |           -0.0415 |
| EURUSD   |      117 |      0.1026 |       33 |     -0.1710 |            0.2736 |
| XAUUSD   |      205 |      0.0709 |       48 |      0.1439 |           -0.0730 |

## Retracement BULL

| market   |    n |    mean |
|:---------|-----:|--------:|
| BTCUSDT  | 2446 |  0.1158 |
| EURUSD   |  784 | -0.1053 |
| XAUUSD   | 1237 |  0.3439 |

## Retracement BEAR

| market   |    n |    mean |
|:---------|-----:|--------:|
| BTCUSDT  | 1779 | -0.0819 |
| EURUSD   |  588 | -0.0028 |
| XAUUSD   |  404 | -0.0568 |

## Compression BULL

| market   |   n |   accuracy |
|:---------|----:|-----------:|
| BTCUSDT  | 141 |     0.5035 |
| EURUSD   |  84 |     0.5357 |
| XAUUSD   |  68 |     0.5588 |

## Compression BEAR

| market   |   n |   accuracy |
|:---------|----:|-----------:|
| BTCUSDT  |  32 |     0.7500 |
| EURUSD   |  32 |     0.5625 |
| XAUUSD   |  14 |     0.5714 |

## Coverage / conflicts

| market   |   exp_n |   exp_bull_cov |   exp_bear_cov |   ret_n |   ret_bull_cov |   ret_bear_cov |   ret_conflict |   comp_n |   comp_bull_cov |   comp_bear_cov |   comp_conflict |
|:---------|--------:|---------------:|---------------:|--------:|---------------:|---------------:|---------------:|---------:|----------------:|----------------:|----------------:|
| BTCUSDT  |     848 |         0.1958 |         0.0979 |    5431 |         0.4504 |         0.3276 |         0.0000 |     2414 |          0.0708 |          0.0157 |          0.0000 |
| EURUSD   |     423 |         0.2837 |         0.0851 |    2192 |         0.4466 |         0.3403 |         0.0000 |     1291 |          0.0751 |          0.0279 |          0.0000 |
| XAUUSD   |     570 |         0.3947 |         0.0860 |    2597 |         0.6015 |         0.2099 |         0.0000 |     1382 |          0.0601 |          0.0145 |          0.0000 |

## Common-window diagnostic

| market   |   exp_bull_n |   exp_bull_mean |   exp_bear_n |   exp_bear_mean |   ret_bull_n |   ret_bull_mean |   ret_bear_n |   ret_bear_mean |   comp_bull_n |   comp_bull_acc |   comp_bear_n |   comp_bear_acc |
|:---------|-------------:|----------------:|-------------:|----------------:|-------------:|----------------:|-------------:|----------------:|--------------:|----------------:|--------------:|----------------:|
| BTCUSDT  |          110 |          0.1799 |           49 |          0.1879 |         1469 |          0.1504 |          904 |         -0.0532 |            81 |          0.5802 |            16 |          0.6250 |
| EURUSD   |          109 |          0.1134 |           31 |         -0.1810 |          717 |         -0.1517 |          509 |         -0.0510 |            69 |          0.5652 |            32 |          0.5625 |
| XAUUSD   |          178 |          0.0799 |           38 |          0.2019 |          989 |          0.3771 |          271 |          0.0682 |            57 |          0.5439 |            10 |          0.5000 |

## Boundary
LAB002 geometry is unchanged. LAB004 is discovery/confirmation on reused XAU/BTC/EUR markets. Any accepted side-specific head requires unseen-market replication before production confidence or profit-probability claims.