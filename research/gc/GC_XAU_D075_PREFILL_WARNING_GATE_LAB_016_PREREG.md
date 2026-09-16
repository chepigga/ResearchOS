# GC_XAU_D075_PREFILL_WARNING_GATE_LAB_016 — PREREG

## Purpose

Test whether the LAB015 fill-time warning can be moved to a **causal, executable checkpoint before the resting D1 XAU limit is touched**.

Frozen baseline remains:
`BUYER_BREAKOUT_LONG_001 -> XAU D1.00 -> E3 -> SL1.5 ATR -> TP3R -> hard timeout signal+30m -> +0.05R/fill -> corrected one-active`.

Existing AMP GC + FTMO XAU raw ticks only. No new market data, no retune of the baseline.

## Causal warning checkpoint

For each corrected accepted E3 fill:

- `order_start_ask` is the frozen executable Ask at order start.
- `D1_limit = order_start_ask - 1.00 * XAU_ATR14_M1`.
- `D075_warning = order_start_ask - 0.75 * XAU_ATR14_M1`.
- Warning time is the **first XAU quote tick after order start** with `Ask <= D075_warning` while still `Ask > D1_limit`.
- The warning is executable only if it occurs at least **250 ms before the frozen D1 fill timestamp**.
- If price gaps directly from above D075 through/touching D1, the trade is `NO_CAUSAL_WARNING` and cannot be vetoed by LAB016.

No tick at or after the D1 fill may enter any primary feature.

## Population

Primary model population is corrected AMP accepted D1/E3 fills that have an executable D075 warning.

Primary label:
- `SL=1` for frozen SL.
- `SL=0` for TP or TIMEOUT.

Trades without a causal warning remain unchanged in overlay economics.

## Frozen features at D075 warning

### GC signal/order-start features
1. `gc_delta_excess`
2. `gc_buy_strength`
3. `gc_body_atr`
4. `gc_range_atr`
5. `gc_close_pos`
6. `gc_breakout_atr`
7. `gc_buy_loc_excess`
8. `xau_spread_start_atr`

### Warning-time features, all strictly pre-fill
9. `warning_delay_sec`
10. `warning_lead_to_fill_sec` — diagnostic geometry known historically but **NOT used by classifier** because live fill time is unknown.
11. `xau_spread_warning_atr`
12. `xau_prefill_range_warning_atr`
13. `xau_mom_10s_warning_atr`
14. `xau_mom_30s_warning_atr`
15. `xau_approach_velocity_atr_per_sec`
16. `xau_remaining_to_d1_atr`
17. `gc_post_delta_to_warning`

Classifier features exclude item 10.

## Model

Frozen before results:
- Logistic regression, `C=1.0`, `class_weight=balanced`.
- Median imputation + standardization learned on train only.
- Initial train: first 45 warning-eligible fills.
- Test blocks: 12 fills, expanding walk-forward.
- No hyperparameter search, feature subset search, or alternate model.

## Veto rule

For each fold:
- fit on expanding training data;
- threshold = 75th percentile of **training** predicted SL probability;
- cancel the D1 limit at D075 warning when test `p_sl >= threshold`.

No threshold optimization.

## Conservative overlay

Within the OOF chronological period:
- vetoed baseline fill -> `0R`;
- non-vetoed fills unchanged;
- no-warning fills unchanged;
- no-fills unchanged;
- signals newly freed by cancellation are **not reclaimed** in LAB016.

A later state-transition resimulation is required before EA promotion.

## Gates

Candidate passes only if all are true:
1. at least 70% of corrected accepted fills have an executable D075 warning;
2. at least 40 warning-eligible OOF fills and both classes present;
3. OOF SL AUC >= 0.60;
4. OOF veto share 10–40%;
5. vetoed SL rate >= 1.25x OOF warning-eligible baseline SL rate;
6. conservative overlay total R > baseline total R over same original-signal OOF period;
7. overlay EV/original signal > baseline EV/original signal;
8. overlay MaxDD <= baseline MaxDD;
9. chronological second-half overlay EV/original signal > 0.

PASS status: `HISTORICAL_CAUSAL_PREFILL_GATE_CANDIDATE_PASS_NOT_OOS`.
Otherwise: `HISTORICAL_CAUSAL_PREFILL_GATE_FAIL_NOT_OOS`.

## Governance

LAB016 is historical bounded discovery, not independent OOS. A PASS does not change the production EA. It requires a separate full corrected one-active re-simulation with cancellations and reclaimed signals, followed by dependency/Monte-Carlo stress.
