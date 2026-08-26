# BTC_NATIVE_FLOW_REGIME_ROUTER_TO_POSITIVE_CONTINUATION_LAB_015

## Verdict

`NATIVE_FLOW_ADDS_RANK_INFORMATION_BUT_ROUTER_IS_NOT_STABLE`

## Frozen design

- Target: clean MFE >= 2.5R within 32 M15 bars before structural SL.
- Primary universe: ALL BUY BOS.
- Secondary universe: LOW_ACTIVITY BUY BOS.
- All predictors end at i-1; BOS candle and post-BOS data are excluded.
- Independent LOYO years: 2020, 2022, 2023, 2024, 2025.
- 2021 is diagnostic only and excluded from independent training.
- 2026 is pseudo-forward.
- Fixed model: L2 logistic regression, C=0.35, balanced classes.
- Router: ALLOW = top train-score tercile, REDUCE = middle tercile, SKIP = bottom tercile.
- No threshold, feature, or hyperparameter rescue after results.
- Frozen Binance M15 data SHA256: `19acf95a3bb7a868fa1e6c8da8dbc73d4a2f7004b771e394bbee8e6c5b6e58b9`.

## Primary pooled independent LOYO result — ALL BUY BOS

N = 1,194 events; baseline LARGE rate = 13.90%; baseline FAIL rate = 44.89%.

### PRICE_REGIME_ONLY

- AUC: 0.5374
- AP: 0.1578
- ALLOW LARGE: 15.29%
- SKIP LARGE: 12.31%
- ALLOW - SKIP LARGE: +2.98 pp
- ALLOW uplift vs baseline: +1.39 pp

### PRICE_REGIME_PLUS_NATIVE_FLOW

- AUC: 0.5841
- AP: 0.1729
- Incremental AUC vs price-regime-only: **+0.0466**
- ALLOW N = 390 (32.66%)
- ALLOW LARGE: **18.21%**
- REDUCE LARGE: 13.49%
- SKIP N = 426 (35.68%)
- SKIP LARGE: **10.33%**
- ALLOW - SKIP LARGE: **+7.88 pp**
- ALLOW uplift vs baseline: **+4.30 pp**
- ALLOW FAIL: 45.90%
- SKIP FAIL: 46.01%
- SKIP - ALLOW FAIL: only **+0.11 pp**

The native-flow model therefore materially improves ranking of LARGE continuation, but the same scalar router does not cleanly rank FAIL risk in the opposite direction.

## Yearly transfer

For PRICE_REGIME_PLUS_NATIVE_FLOW on ALL BUY BOS:

- valid years: 5/5
- ALLOW LARGE > SKIP LARGE: **5/5 years**
- ALLOW LARGE > yearly baseline: **5/5 years**
- SKIP FAIL > ALLOW FAIL: only **2/5 years**

Selected yearly LARGE rates (ALLOW vs SKIP):

- 2020: 17.39% vs 13.49%
- 2022: 19.67% vs 9.20%
- 2023: 17.65% vs 2.22%
- 2024: 22.02% vs 11.54%
- 2025: 12.12% vs 10.00%

Thus the positive-continuation ranking is directionally stable across every independent year, while FAIL ordering is not.

## 2021 diagnostic

2021 remains a different regime:

- ALLOW LARGE: 12.77%
- REDUCE LARGE: 16.90%
- SKIP LARGE: 10.56%
- baseline LARGE: 12.69%

The router is not monotonic in this excluded diagnostic year; the middle tier performs best.

## 2026 pseudo-forward

- baseline LARGE: 13.93%
- ALLOW N = 55, LARGE = 16.36%
- REDUCE N = 40, LARGE = **20.00%**
- SKIP N = 27, LARGE = **0.00%**

The forward directional veto works strongly: the frozen SKIP tier retained zero LARGE continuations in this sample. However, REDUCE outperformed ALLOW, so the fixed tercile router is not fully calibrated/monotonic.

## Mechanism diagnostic

Across the five independent folds, several coefficients had the same sign in all 5/5 folds. The strongest stable interactions/features included:

- `rv_7d_vs_prev23d × flow_churn_12`: positive in 5/5
- `range_7d_vs_prev23d × flow_churn_12`: negative in 5/5
- `trades_7d_vs_prev23d`: negative in 5/5
- `price_response_per_flow_12`: negative in 5/5
- `trend_eff_7d × flow_persistence_12`: positive in 5/5
- `aligned_flow_no_result_share_12`: negative in 5/5
- `flow_align_12`: positive in 5/5

This supports an interaction interpretation: native flow quality is conditional on volatility/range/trend regime rather than being a universal one-dimensional buy-pressure signal.

## Interpretation

LAB015 confirms an incremental causal pre-BOS native-flow signal for future positive continuation. It does **not** validate a production ALLOW/REDUCE/SKIP router yet.

The key failure is structural: `is_large` and `is_fail` are not simple complements. A model optimized to rank LARGE can separate future large continuations consistently while failing to rank FAIL in the opposite order. A single scalar score is therefore too restrictive.

## Next justified test

`BTC_NATIVE_FLOW_DUAL_HEAD_CONTINUATION_X_FAILURE_ROUTER_LAB_016`

Freeze two causal heads rather than one scalar router:

1. P(LARGE continuation)
2. P(FAIL / adverse path)

Then map the joint state into ALLOW / REDUCE / SKIP without assuming `P(FAIL) = 1 - P(LARGE)`. Keep the same LOYO years, 2021 diagnostic, 2026 pseudo-forward, frozen features/data, and no threshold rescue.

## Research status

This is a research routing result only. No execution-cost, broker, prop-risk, or EA admission claim is made.
