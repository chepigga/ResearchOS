# GC_AMP_LIVE_BUYER_BREAKOUT_PARITY_LAB_013 — PREREG

## Purpose

Audit whether the **realtime AMP/CQG MT5 implementation** of the frozen `BUYER_BREAKOUT_LONG_001` sensor reproduces the canonical offline reconstruction exactly enough to trust LAB012 forward-shadow observations.

This is a **data / implementation parity audit**. It is not strategy discovery, not threshold optimization, and not an outcome/PnL study.

## Frozen lineage

- Sensor: `BUYER_BREAKOUT_LONG_001`.
- Instrument/feed: AMP Futures MT5/CQG GC contract used by the current branch (`GCEZ26` in the historical archive; live symbol must be explicitly logged).
- Bar clock: UTC M1 from raw `time_msc`.
- Raw event source: MT5 `CopyTicksRange(..., COPY_TICKS_ALL, ...)` / equivalent exporter, filtered to valid Last trades with positive volume and **exclusive** BUY/SELL aggressor flags.
- Volume semantics: `volume_real` when `>0`, otherwise integer `volume`.
- Simultaneous BUY+SELL or neither side: excluded from directional aggregation.

Canonical offline feature engineering remains the implementation in `research/gc/gc_m1_orderflow_edge_discovery_003.py`.

## Frozen signal definition

For each completed GC M1 bar:

1. Aggregate exclusive directional raw trades into OHLC, `buy_vol`, `sell_vol`, `volume`, `delta`, `delta_frac`.
2. ATR14 = simple rolling mean of True Range over 14 completed reconstructed M1 bars.
3. Causal references use **prior bars only**:
   - `q90_delta` = Q90 of prior 240 completed M1 `delta_frac` values;
   - `q75_buy` = Q75 of prior 240 completed M1 `buy_vol` values;
   - `prior20_high` = maximum high of prior 20 completed M1 bars.
4. `a_buy = delta_frac >= q90_delta AND buy_vol >= q75_buy`.
5. `close_pos = (close-low)/(high-low)`, with `0.5` for a zero-range bar.
6. `body_atr = (close-open)/ATR14`.
7. Frozen signal:

`signal_bool = a_buy AND close>open AND close_pos>=0.75 AND high>=prior20_high AND body_atr>0`

No extra session, trend, spread, news, volatility, DOM, regime, or outcome filter may be inserted in LAB013.

## Independent paths being compared

### Path A — realtime snapshot

A non-trading MT5 observer records one row for every warmup-valid completed M1 bar, including the raw inputs, causal thresholds, derived features, and final `signal_bool` **at decision time**. It must not rewrite old rows.

### Path B — offline rebuild

Afterward, the same clock interval is reconstructed independently from exported AMP/CQG raw ticks using the canonical Python logic. The offline rebuild must not read live feature values when computing its own features.

## Required parity fields

Exact boolean/integer parity:

- `bar_time_utc_ms`
- `a_buy`
- `signal_bool`

Numerical parity within frozen tolerances:

- OHLC: absolute error <= `1e-8`
- `buy_vol`, `sell_vol`: absolute error <= `1e-8`
- `delta_frac`, `q90_delta`, `close_pos`, `body_atr`: absolute error <= `1e-10`
- `q75_buy`, `prior20_high`, `atr14`: absolute error <= `1e-8`

The evaluator must also report signal timestamp set equality, duplicate bars, missing-live bars, missing-rebuild bars, and excluded/dual-flag raw tick counts where available.

## PASS gate

`LAB013_PASS` requires all of the following on untouched post-freeze observations:

- >= 500 paired warmup-valid completed M1 bars;
- >= 5 rebuilt `BUYER_BREAKOUT_LONG_001` signals;
- zero duplicate `(symbol, bar_time_utc_ms)` snapshot rows after append-only version resolution;
- zero missing bars in either path within the scored common-clock set;
- 100% `a_buy` parity;
- 100% `signal_bool` parity;
- exact equality of live vs rebuild signal timestamp sets;
- every required numeric field within its frozen tolerance;
- no evidence that a live snapshot used future/current-bar data inside a causal reference.

Before these conditions are satisfied, status is `INSUFFICIENT_FRESH_PARITY_SAMPLE` or `PARITY_FAIL`; never silently PASS a small sample.

## Governance

- LAB013 may expose implementation/data defects and fix the logger/export plumbing.
- It may **not** change BUYER_BREAKOUT_LONG_001 thresholds or redefine the signal.
- Any strategy-rule change creates a new candidate/version and cannot inherit LAB012/LAB013 evidence.
- LAB012 shadow collection may continue in parallel, but its results are not trusted for production promotion until LAB013 passes.
