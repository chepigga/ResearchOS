# STRUCT_BREAK_PERSISTENT_FLOW_VS_EXHAUSTION_LAB_007 — Preregistration

Date: 2026-08-25
Status: PREREGISTERED
Branch: lab/btc-struct-break-regime-004

## Objective
Test whether STRUCT_BREAK winners can be distinguished at entry by a latent persistent-flow state versus exhaustion, rather than by static structure geometry.

## Canonical population
- STRUCT_BREAK v002 entries from run_v002.csv.
- Primary historical universe: 2019-2025 only.
- 2026 excluded from historical fitting/verdict.
- DEV: 2019-2022.
- VAL: 2023-2025.

## Evidence layers
### Layer A — full-history causal price-sequence proxies
Available for all canonical entries using exact BTC M15 clock. Features must use only fully closed bars <= entry time:
- directional return / ATR on 1h, 4h, 12h, 24h, 72h;
- directional efficiency on the same horizons;
- velocity and acceleration of side-aligned returns;
- range expansion/compression ratios;
- side-aligned close-location / wick-pressure summaries;
- repeated attack / failed-push proxies near recent extremes;
- short-vs-long persistence deltas.

### Layer B — true Binance aggressive-flow replication
Use only the time window actually covered by available Binance flow files. Do not backfill or synthetically extend microstructure features to 2019-2025. Candidate features:
- aggressive buy/sell imbalance;
- imbalance persistence on multiple windows;
- flow acceleration/deceleration;
- signed volume concentration;
- funding if aligned and causal.
This layer is replication/forward evidence only unless its date coverage overlaps preregistered historical VAL.

## Targets
Primary historical target: original canonical outcome proxy `REACHED_1R` = (`be == 1`), because this is exactly reconstructable from run_v002 and is known causally to occur after entry.
Secondary target: `FULL_TP_2.3R` = (`R > 2.0`) under the frozen canonical TP=2.3R engine.
Do not claim TP1.5/TP2 labels unless exact entry/SL path reconstruction is available from the source detector.

## Models
1. Univariate AUC for every causal feature.
2. Fixed logistic model on price-persistence block.
3. Fixed logistic model on exhaustion/acceptance block.
4. Fixed combined logistic model.
5. No tree boosting in primary test.
6. All scaling/fitting on DEV only; apply frozen transform to VAL.

## Primary metrics
- VAL ROC AUC for REACHED_1R.
- VAL average precision.
- top-third and bottom-third EV using score cuts frozen from DEV.
- DEV→VAL sign transfer.
- yearly VAL stability.

## Gates
GO:
- combined model VAL AUC >= 0.58;
- VAL top-third EV >= +0.10R after canonical cost;
- positive EV in both DEV and VAL;
- at least 2/3 VAL years positive;
- no single feature or single year explains >50% of total gain.

WATCH:
- VAL AUC 0.55-0.58 OR VAL top-third EV 0 to +0.10R with directional stability.

FAIL:
- VAL AUC < 0.55 and no stable EV separation;
- or DEV improvement collapses/reverses in VAL.

## Falsification rule
If price-sequence and real aggressive-flow evidence both fail OOS, treat pre-entry predictability of this STRUCT_BREAK event as weak and stop adding static OHLC filters.

## Anti-leakage
All features are computed from bars/trades/funding already completed before the entry timestamp. No future extrema, future labels, full-sample normalization, or 2026 information may affect 2019-2025 feature construction/model fitting.
