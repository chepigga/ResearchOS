# UNIVERSAL_CONTEXT_FROZEN_HEADS_UNSEEN_MARKET_REPLICATION_LAB_005
**Verdict: UNSEEN_REPLICATION_NOT_SUPPORTED**

## Primary gates
- H1 frozen EXPANSION_BULL unseen replication: **FAIL** — pooled +0.0054 ATR, CI [-0.1238, +0.1205], N=257.
- H2 frozen COMPRESSION_BEAR unseen replication: **UNDERPOWERED** — pooled accuracy 58.62%, CI [25.90%, 83.33%], N=29.
- H3 coverage sanity: **FAIL**.

## Market data

| market   |   h4_rows |   ready_bars | first_h4            | last_h4             |
|:---------|----------:|-------------:|:--------------------|:--------------------|
| USDJPY   |      3106 |         2904 | 2024-09-15 20:00:00 | 2026-09-10 20:00:00 |
| GBPUSD   |      3109 |         2902 | 2024-09-15 20:00:00 | 2026-09-10 20:00:00 |
| AUDUSD   |      3117 |         2899 | 2024-09-15 20:00:00 | 2026-08-31 20:00:00 |
| USDCAD   |      3117 |         2906 | 2024-09-15 20:00:00 | 2026-08-31 20:00:00 |

## EXPANSION_BULL — unseen markets

| market   |   n |    mean |
|:---------|----:|--------:|
| AUDUSD   |  57 | -0.0434 |
| GBPUSD   |  72 |  0.0470 |
| USDCAD   |  72 | -0.1330 |
| USDJPY   |  56 |  0.1797 |

## COMPRESSION_BEAR — unseen markets

| market   |   n |   accuracy |
|:---------|----:|-----------:|
| AUDUSD   |   9 |     0.4444 |
| GBPUSD   |  11 |     0.5455 |
| USDCAD   |   7 |     1.0000 |
| USDJPY   |   2 |     0.0000 |

## Coverage

| market   |   exp_n |   exp_bull_n |   exp_bull_cov |   comp_n |   comp_bear_n |   comp_bear_cov |   comp_conflict |
|:---------|--------:|-------------:|---------------:|---------:|--------------:|----------------:|----------------:|
| AUDUSD   |     229 |           61 |         0.2664 |      606 |            10 |          0.0165 |          0.0000 |
| GBPUSD   |     285 |           77 |         0.2702 |      603 |            14 |          0.0232 |          0.0000 |
| USDCAD   |     254 |           76 |         0.2992 |      614 |             7 |          0.0114 |          0.0000 |
| USDJPY   |     237 |           59 |         0.2489 |      679 |             3 |          0.0044 |          0.0000 |

## Secondary frozen LAB004 heads

| head             | market   |   n | metric          |   value |
|:-----------------|:---------|----:|:----------------|--------:|
| EXPANSION_BULL   | AUDUSD   |  57 | mean_signed_atr | -0.0434 |
| EXPANSION_BULL   | GBPUSD   |  72 | mean_signed_atr |  0.0470 |
| EXPANSION_BULL   | USDCAD   |  72 | mean_signed_atr | -0.1330 |
| EXPANSION_BULL   | USDJPY   |  56 | mean_signed_atr |  0.1797 |
| EXPANSION_BEAR   | AUDUSD   |  22 | mean_signed_atr |  0.0415 |
| EXPANSION_BEAR   | GBPUSD   |  35 | mean_signed_atr | -0.2071 |
| EXPANSION_BEAR   | USDCAD   |  20 | mean_signed_atr | -0.1217 |
| EXPANSION_BEAR   | USDJPY   |  19 | mean_signed_atr | -0.2151 |
| RETRACEMENT_BULL | AUDUSD   | 499 | mean_signed_atr | -0.0871 |
| RETRACEMENT_BULL | GBPUSD   | 470 | mean_signed_atr | -0.1564 |
| RETRACEMENT_BULL | USDCAD   | 438 | mean_signed_atr |  0.0553 |
| RETRACEMENT_BULL | USDJPY   | 517 | mean_signed_atr |  0.0144 |
| RETRACEMENT_BEAR | AUDUSD   | 284 | mean_signed_atr | -0.2165 |
| RETRACEMENT_BEAR | GBPUSD   | 325 | mean_signed_atr | -0.1769 |
| RETRACEMENT_BEAR | USDCAD   | 277 | mean_signed_atr |  0.0542 |
| RETRACEMENT_BEAR | USDJPY   | 233 | mean_signed_atr | -0.3964 |
| COMPRESSION_BULL | AUDUSD   |  44 | accuracy        |  0.6364 |
| COMPRESSION_BULL | GBPUSD   |  34 | accuracy        |  0.7059 |
| COMPRESSION_BULL | USDCAD   |  29 | accuracy        |  0.2759 |
| COMPRESSION_BULL | USDJPY   |  57 | accuracy        |  0.4912 |
| COMPRESSION_BEAR | AUDUSD   |   9 | accuracy        |  0.4444 |
| COMPRESSION_BEAR | GBPUSD   |  11 | accuracy        |  0.5455 |
| COMPRESSION_BEAR | USDCAD   |   7 | accuracy        |  1.0000 |
| COMPRESSION_BEAR | USDJPY   |   2 | accuracy        |  0.0000 |

## EXPANSION_BULL yearly diagnostic

| market   |   year |   n |    mean |
|:---------|-------:|----:|--------:|
| AUDUSD   |   2025 |  28 |  0.0095 |
| AUDUSD   |   2026 |  29 | -0.0945 |
| GBPUSD   |   2025 |  49 |  0.0476 |
| GBPUSD   |   2026 |  23 |  0.0457 |
| USDCAD   |   2024 |   9 | -0.6830 |
| USDCAD   |   2025 |  40 | -0.1895 |
| USDCAD   |   2026 |  23 |  0.1805 |
| USDJPY   |   2024 |  10 |  0.2514 |
| USDJPY   |   2025 |  29 |  0.3003 |
| USDJPY   |   2026 |  17 | -0.0681 |

## Boundary
No unseen outcome was used to change a score, threshold, market, horizon, geometry definition, or verdict rule. This is market-OOS semantic replication only; it does not establish executable P/L or FTMO execution economics.