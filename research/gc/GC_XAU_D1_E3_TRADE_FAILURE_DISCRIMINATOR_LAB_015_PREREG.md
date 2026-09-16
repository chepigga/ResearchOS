# GC_XAU_D1_E3_TRADE_FAILURE_DISCRIMINATOR_LAB_015 — PREREG

## Purpose

Test whether the already-frozen corrected GC `BUYER_BREAKOUT_LONG_001 -> XAU D1.00 E3M` lineage contains a **causal, pre-entry/fill-time discriminator of future trade failure**.

This is a bounded historical discovery lab on the already-collected AMP GC + FTMO XAU data. It is **not independent OOS** and it must not promote a production filter by itself.

## Frozen population

Primary cohort: `AMP_ALL`, corrected one-active semantics from LAB014H.

A scored observation is an **accepted corrected E3 fill**. Expected historical population is 103 fills.

Primary failure label:
- `SL = 1` when frozen outcome status is `SL`.
- `SL = 0` for `TP` or `TIMEOUT`.

Secondary label is diagnostic only:
- `NEGATIVE_NET = 1` when stress-adjusted realized `R < 0`.

No post-fill information may enter any feature.

## Frozen causal features

All features must be known no later than the actual fill timestamp.

### GC signal-bar features
1. `gc_delta_excess = delta_frac - q90_delta`
2. `gc_buy_strength = buy_vol / q75_buy`
3. `gc_body_atr = body_atr`
4. `gc_range_atr = range_atr`
5. `gc_close_pos = close_pos`
6. `gc_breakout_atr = (high - prior20_high) / atr14`
7. `gc_buy_loc_excess = buy_loc - q75_buyloc`

### XAU order-start / pre-fill features
8. `fill_delay_sec`
9. `xau_spread_start_atr = (ask_start - bid_start) / xau_atr14_m1`
10. `xau_spread_fill_atr = (ask_fill - bid_fill) / xau_atr14_m1`
11. `xau_prefill_range_atr = (max(mid) - min(mid)) / xau_atr14_m1` from order start through fill
12. `xau_fill_overshoot_atr = (limit_price - ask_fill) / xau_atr14_m1`
13. `xau_mom_10s_atr = (mid_fill - mid_at_or_before_fill_minus_10s) / xau_atr14_m1`
14. `xau_mom_30s_atr = (mid_fill - mid_at_or_before_fill_minus_30s) / xau_atr14_m1`

### GC post-signal flow available by fill
15. `gc_post_delta_frac` over exclusive-direction AMP trades from GC order-start UTC through XAU fill UTC.

Additional diagnostic columns may be exported but may not be used by the primary classifier unless separately preregistered in a later LAB.

## Model — frozen before result

- Logistic regression.
- `C = 1.0`.
- `class_weight = balanced`.
- Median imputation learned on training data only.
- Standardization learned on training data only.
- No feature selection.
- No hyperparameter search.

## Walk-forward validation

Sort accepted fills by signal timestamp.

- Initial training set: first **45** fills.
- Test block size: **12** fills.
- Expanding training window; retrain before each next block.
- All observations after the first 45 are out-of-fold walk-forward predictions.

If a test block contains only one class, block AUC is `NA`; aggregate OOF AUC is still computed if both classes occur across the full OOF set.

## Frozen veto rule

For each fold:
1. Fit classifier on the expanding training window only.
2. Compute predicted SL probability on that training window.
3. Set threshold to the **75th percentile** of training predicted SL probability.
4. Veto a test fill when its predicted SL probability is `>= threshold`.

This is a fixed top-risk-quartile rule, not an optimized threshold.

The overlay is deliberately conservative: vetoed baseline fills are set to `0R`, but this LAB **does not reclaim later signals that might become available because a vetoed trade was never opened**. Recovered one-active opportunities require a separate re-simulation LAB.

## Primary outputs

- Full 103-trade feature/label table.
- Descriptive univariate feature separation table.
- Walk-forward predictions and fold diagnostics.
- Baseline vs veto overlay R metrics on the OOF period.
- Feature coefficient stability across folds.

## Discovery gates

A historical discriminator candidate passes only if all are true:

1. `OOF SL AUC >= 0.60`.
2. OOF veto share is between `10%` and `40%`.
3. SL rate inside vetoed trades is at least `1.25x` the OOF baseline SL rate.
4. Conservative veto overlay total R on the OOF period is greater than baseline total R.
5. Conservative veto overlay EV per original signal on the OOF period is greater than baseline.
6. Overlay EV per original signal in the chronological second half of OOF is `> 0`.
7. At least 3 walk-forward blocks are evaluable or, if fewer due class sparsity, aggregate OOF contains both classes and at least 40 OOF fills.

Status if all gates pass: `HISTORICAL_FAILURE_DISCRIMINATOR_CANDIDATE_PASS_NOT_OOS`.
Otherwise: `HISTORICAL_FAILURE_DISCRIMINATOR_FAIL_NOT_OOS`.

## Prohibited

- No changing D1.00, E3, SL1.5, TP3, 30m hard horizon, cost stress, or corrected one-active semantics.
- No threshold sweep.
- No alternate classifiers in LAB015.
- No session/news/regime filters added post hoc.
- No deleting losing trades or data gaps.
- No feature subset search.
- No using post-fill MFE/MAE, exit path, final status timing, or realized R as an input feature.

## Governance

A PASS identifies a **research candidate only**. Before changing the EA, the candidate must be frozen and re-simulated trade-by-trade with corrected one-active state transitions, including any newly recoverable signals, then subjected to dependency/Monte-Carlo stress and eventually untouched forward/OOS validation.
