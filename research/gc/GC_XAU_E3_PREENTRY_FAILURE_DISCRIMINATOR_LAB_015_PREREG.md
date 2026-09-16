# GC_XAU_E3_PREENTRY_FAILURE_DISCRIMINATOR_LAB_015 — PREREG

## Purpose
Test whether already-known **causal information available at the GC signal close / before the XAU limit order starts** can distinguish future failed corrected-E3 fills from successful/positive fills.

This LAB uses only the already-collected frozen AMP GC archive and the frozen/corrected E3 execution outcomes produced by LAB013H. No new market data are collected.

## Frozen baseline
- Sensor: `BUYER_BREAKOUT_LONG_001` unchanged.
- Execution: XAU `D1.00_E3M`, SL 1.5 ATR, TP 3R, hard timeout signal+30m, +0.05R/fill stress.
- One-active semantics: corrected clock from LAB013H: unfilled setup remains busy until `order_start + 3m`, where `order_start = next M1 after the completed GC signal bar`; filled setup remains busy until its exit.
- Cohort: AMP_ALL only for primary discriminator work.

## Labels
Among **corrected-one-active accepted and filled E3 trades only**:
- `FAIL` = stress R < 0.
- `GOOD` = stress R > 0.
- exact zero, if any, excluded from classification diagnostics.

The R outcome is never used to construct a feature.

## Causal feature set — frozen before outcome analysis
Computed from the completed GC signal bar and prior bars only:
1. `delta_excess = delta_frac - q90_delta`
2. `buy_q75_ratio = buy_vol / q75_buy`
3. `close_pos`
4. `body_atr`
5. `breakout_atr = (high - prior20_high) / atr14`
6. `range_atr = (high - low) / atr14`
7. `atr_ratio_60 = atr14 / median(prior 60 completed bars atr14)`; prior-only denominator
8. `utc_hour_sin`, `utc_hour_cos` as two cyclic clock coordinates; these are diagnostic only and may not form a standalone veto unless train evidence is stable.

No post-signal XAU path, fill delay, MFE/MAE, future GC bars, future volatility, status, exit time, or future order-flow value may enter a feature.

## Temporal split
- TRAIN/DISCOVERY: signal time < `2026-09-01T00:00:00Z`.
- VALIDATION: signal time >= `2026-09-01T00:00:00Z`.

All feature direction and thresholds are selected on TRAIN only.

## Bounded discriminator search
For each scalar feature 1–7:
- evaluate whether high values or low values are associated with FAIL on TRAIN;
- candidate veto thresholds are TRAIN empirical quantiles Q20, Q25, Q33, Q67, Q75, Q80 only;
- require veto to remove at least 10% and at most 40% of TRAIN fills;
- rank candidate vetoes by TRAIN `retained_sum_R - baseline_sum_R` subject to retained TRAIN EV/fill > baseline TRAIN EV/fill and retained TRAIN PF > baseline TRAIN PF.

A feature is called **single-feature promising** only if its selected TRAIN veto also improves VALIDATION EV/fill and PF without making VALIDATION SumR lower by more than 20% solely because of excessive trade removal.

## Composite screen
At most the top **two distinct** TRAIN-selected single-feature veto flags may be combined. Only these predeclared forms are tested:
- OR veto: reject if either flag fires.
- 2-of-2 veto: reject only if both flags fire.

Selection is made on TRAIN only. VALIDATION is untouched until the composite is frozen.

## Promotion gate
A pre-entry veto is a **research challenger**, not a production change, only if all are true:
- TRAIN retained fills >= 30;
- VALIDATION retained fills >= 15;
- TRAIN EV/fill > baseline and PF > baseline;
- VALIDATION EV/fill > baseline and PF > baseline;
- VALIDATION SumR >= 0.80 × baseline validation SumR;
- full-sample MaxDD improves by >= 10% OR full-sample PF improves by >= 0.15;
- full-sample retained fill count >= 65% of baseline;
- no use of post-entry information.

If gates fail: `NO_CAUSAL_PREENTRY_VETO_PROMOTED`.

## Diagnostics
Report for every feature:
- TRAIN and VALIDATION FAIL/GOOD medians;
- rank AUC for FAIL classification (direction-free `max(AUC,1-AUC)`);
- selected TRAIN-only veto, if any;
- retained/rejected fills, EV/fill, PF, SumR, MaxDD;
- validation degradation/improvement.

Also report rejected-trade composition: number of SL, negative TIMEOUT, positive TIMEOUT, TP. This composition is diagnostic only and cannot affect threshold selection.

## Governance
This is bounded historical discriminator research on a post-discovery candidate. It does not create independent OOS evidence and cannot modify `BUYER_BREAKOUT_LONG_001`, D1 depth, E3 expiry, SL/TP, or the corrected one-active baseline.