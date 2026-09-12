# UNIVERSAL_CONTEXT_NORMALIZED_CROSS_MARKET_STATE_ENGINE_LAB_001
**Verdict: UNIVERSAL_STATE_ENGINE_NOT_SUPPORTED**

## Primary gates
- H1 EXPANSION future range: **FAIL** — pooled effect +0.170 ATR, CI [+0.106, +0.236].
- H2 RANGE compression: **FAIL** — pooled effect -0.034 ATR, CI [-0.068, +0.002].
- H3 PULLBACK 24h trend follow-through: **FAIL** — pooled mean +0.038 ATR, CI [-0.048, +0.121].
- H4 EXPANSION 8h trend continuation: **PASS** — pooled mean +0.097 ATR, CI [+0.026, +0.164].
- H5 state breadth: **PASS**.

## Market data / ready bars

| market   |   h4_rows |   ready_bars | first               | last                |
|:---------|----------:|-------------:|:--------------------|:--------------------|
| XAUUSD   |      6417 |         6216 | 2022-06-01 00:00:00 | 2026-07-23 20:00:00 |
| BTCUSDT  |     12228 |        12027 | 2021-01-01 00:00:00 | 2026-07-31 20:00:00 |
| EURUSD   |      5514 |         5313 | 2023-01-02 00:00:00 | 2026-07-17 20:00:00 |

## State occupancy

| market   |   EXPANSION |   PULLBACK |   RANGE |   REVERSAL |   TRANSITION |
|:---------|------------:|-----------:|--------:|-----------:|-------------:|
| BTCUSDT  |       0.091 |      0.321 |   0.276 |      0.000 |        0.312 |
| EURUSD   |       0.109 |      0.288 |   0.303 |      0.000 |        0.301 |
| XAUUSD   |       0.123 |      0.276 |   0.281 |      0.000 |        0.320 |

## Per-market semantic effects

| market   | state     | metric        |   n_state |    n_other |   mean_state |   mean_other |   effect |         n |     mean |
|:---------|:----------|:--------------|----------:|-----------:|-------------:|-------------:|---------:|----------:|---------:|
| BTCUSDT  | EXPANSION | range8_atr    | 1094.0000 | 10931.0000 |       1.7629 |       1.4441 |   0.3187 |  nan      | nan      |
| BTCUSDT  | RANGE     | range8_atr    | 3316.0000 |  8709.0000 |       1.4521 |       1.4812 |  -0.0291 |  nan      | nan      |
| BTCUSDT  | PULLBACK  | signed24_atr  |  nan      |   nan      |     nan      |     nan      | nan      | 3823.0000 |  -0.0099 |
| BTCUSDT  | EXPANSION | signed8_atr   |  nan      |   nan      |     nan      |     nan      | nan      |  903.0000 |   0.1533 |
| BTCUSDT  | REVERSAL  | reverse12_atr |  nan      |   nan      |     nan      |     nan      | nan      |    0.0000 | nan      |
| EURUSD   | EXPANSION | range8_atr    |  539.0000 |  4408.0000 |       1.4366 |       1.5118 |  -0.0753 |  nan      | nan      |
| EURUSD   | RANGE     | range8_atr    | 1511.0000 |  3436.0000 |       1.5381 |       1.4885 |   0.0497 |  nan      | nan      |
| EURUSD   | PULLBACK  | signed24_atr  |  nan      |   nan      |     nan      |     nan      | nan      | 1193.0000 |  -0.0772 |
| EURUSD   | EXPANSION | signed8_atr   |  nan      |   nan      |     nan      |     nan      | nan      |  424.0000 |   0.0323 |
| EURUSD   | REVERSAL  | reverse12_atr |  nan      |   nan      |     nan      |     nan      | nan      |    0.0000 | nan      |
| XAUUSD   | EXPANSION | range8_atr    |  700.0000 |  5088.0000 |       1.5955 |       1.4799 |   0.1157 |  nan      | nan      |
| XAUUSD   | RANGE     | range8_atr    | 1621.0000 |  4167.0000 |       1.4065 |       1.5278 |  -0.1214 |  nan      | nan      |
| XAUUSD   | PULLBACK  | signed24_atr  |  nan      |   nan      |     nan      |     nan      | nan      | 1321.0000 |   0.2805 |
| XAUUSD   | EXPANSION | signed8_atr   |  nan      |   nan      |     nan      |     nan      | nan      |  584.0000 |   0.0558 |
| XAUUSD   | REVERSAL  | reverse12_atr |  nan      |   nan      |     nan      |     nan      | nan      |    0.0000 | nan      |

## H5 detail

- BTCUSDT: PASS; core>=3%: 3/4; max core=32.1%; transition=31.2%.
- EURUSD: PASS; core>=3%: 3/4; max core=30.3%; transition=30.1%.
- XAUUSD: PASS; core>=3%: 3/4; max core=28.1%; transition=32.0%.

## Secondary REVERSAL pooled diagnostic
- reverse12 mean: +nan ATR, CI [+nan, +nan], N=0.

## Common-window robustness (diagnostic only)

| market   | state     | metric       |   n_state |   n_other |   mean_state |   mean_other |   effect |         n |     mean |
|:---------|:----------|:-------------|----------:|----------:|-------------:|-------------:|---------:|----------:|---------:|
| BTCUSDT  | EXPANSION | range8_atr   |  656.0000 | 6202.0000 |       1.7982 |       1.4450 |   0.3532 |  nan      | nan      |
| BTCUSDT  | RANGE     | range8_atr   | 1995.0000 | 4863.0000 |       1.4261 |       1.5005 |  -0.0744 |  nan      | nan      |
| BTCUSDT  | PULLBACK  | signed24_atr |  nan      |  nan      |     nan      |     nan      | nan      | 2113.0000 |   0.0112 |
| BTCUSDT  | EXPANSION | signed8_atr  |  nan      |  nan      |     nan      |     nan      | nan      |  565.0000 |   0.2109 |
| EURUSD   | EXPANSION | range8_atr   |  493.0000 | 4038.0000 |       1.4398 |       1.5098 |  -0.0700 |  nan      | nan      |
| EURUSD   | RANGE     | range8_atr   | 1437.0000 | 3094.0000 |       1.5386 |       1.4852 |   0.0534 |  nan      | nan      |
| EURUSD   | PULLBACK  | signed24_atr |  nan      |  nan      |     nan      |     nan      | nan      | 1061.0000 |  -0.1378 |
| EURUSD   | EXPANSION | signed8_atr  |  nan      |  nan      |     nan      |     nan      | nan      |  391.0000 |   0.0543 |
| XAUUSD   | EXPANSION | range8_atr   |  573.0000 | 3937.0000 |       1.6306 |       1.4693 |   0.1613 |  nan      | nan      |
| XAUUSD   | RANGE     | range8_atr   | 1344.0000 | 3166.0000 |       1.3805 |       1.5362 |  -0.1557 |  nan      | nan      |
| XAUUSD   | PULLBACK  | signed24_atr |  nan      |  nan      |     nan      |     nan      | nan      |  950.0000 |   0.3187 |
| XAUUSD   | EXPANSION | signed8_atr  |  nan      |  nan      |     nan      |     nan      | nan      |  495.0000 |   0.0867 |

## Boundary
No asset-specific threshold or outcome-driven retuning was used. This LAB validates state semantics only; it does not establish setup confirmation, entry timing, profit probability, or prop-firm execution economics.