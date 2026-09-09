# CROSS_MARKET_CAUSAL_CONTEXT_CONTINUOUS_SCORE_INTERACTION_LAB_002 — preregistration

Status: **REUSED-HISTORY DISCOVERY / INTERACTION ABLATION ONLY**. No production gate, EA rule, or risk sizing change may be promoted from this lab alone.

## Frozen lineage

- BTC: use the exact 327 `PERSISTENT_EXIT` frozen SHORT-v1 trades already attached to causal H4 Context in `CROSS_MARKET_CAUSAL_CONTEXT_ROUTER_LAB_001`.
- XAU: use the canonical native XAU M1 asset `XAUUSD_M1_20220601_20260723_TICK_NATIVE.csv`, SHA256 `db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b`, and the frozen `pool_excess.parquet` event pool. Event clock remains `signal bar open + TF duration`; Context is only from the last fully closed H4 bar.
- Router point definitions, smoothing, inertia, and all alpha thresholds are frozen from LAB001. No score threshold is optimized.

## Primary continuous score

For each event/trade, with the four frozen pre-smoothed router component scores in `[0,100]`:

`C = (score_expansion + score_pullback - score_reversal - score_range) / 200`

Thus `C in [-1,+1]`. This equal-weight contrast is declared before outcomes are inspected in LAB002. No bias weight is embedded in C.

## Direction compatibility interaction

- BTC is SHORT: `BEAR=+1`, `NEUTRAL=0`, `BULL=-1`.
- XAU event direction: BUY is aligned with `BULL`, SELL with `BEAR`; opposite bias is `-1`, neutral is `0`.
- Compatibility is analyzed as a separate stratum / interaction matrix; it does not alter C.

## Primary outcomes

- BTC: `net_r_5bps` from frozen SHORT-v1 execution stream.
- XAU: drift-adjusted `excess` is primary; raw `R` is secondary only.

## Predeclared tests

For each market:

1. Quintile and decile tables of outcome vs C (quantile edges use C only, never outcomes).
2. Ordered-bin monotonicity: adjacent non-decreasing fraction and correlation of bin number with mean outcome.
3. Continuous slope of outcome on raw C (descriptive, no fitted threshold).
4. Weekly cluster bootstrap (3000 draws) for:
   - top-quintile minus bottom-quintile mean outcome lift;
   - continuous slope.
5. Time transfer using global score bins:
   - BTC: 2021, 2022, 2023, 2024, 2025-H1, 2025-H2, 2026-Jan-Jul;
   - XAU: 2022, 2023, 2024, 2025, 2026.
6. Direction-compatibility matrix crossed with C quintile.

## Frozen gates

A market is `CONTINUOUS_CONTEXT_SUPPORTED` only if all are true:

- top quintile mean outcome > bottom quintile mean outcome;
- weekly-cluster bootstrap 95% CI lower bound for top-bottom lift > 0;
- continuous slope > 0;
- weekly-cluster bootstrap 95% CI lower bound for slope > 0;
- quintile adjacent monotonic fraction >= 0.75;
- time transfer is positive in at least 5/7 BTC periods (with >=5 observations in both extreme quintiles) or 4/5 XAU years (with >=100 observations in both extreme quintiles).

Cross-market promotion requires both markets to pass. Anything weaker is discovery evidence only.

## Interpretation rule

A positive result means Context contains graded information about conditional alpha quality. It does **not** authorize risk modulation yet. A negative/mixed result rejects continuous Context as a general cross-market overlay in this frozen form.