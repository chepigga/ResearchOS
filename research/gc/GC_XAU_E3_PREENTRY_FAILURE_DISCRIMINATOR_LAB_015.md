# GC_XAU_E3_PREENTRY_FAILURE_DISCRIMINATOR_LAB_015

**Status: CAUSAL_PREENTRY_VETO_CHALLENGER_PASS_NOT_OOS**

Existing frozen AMP GC + LAB013H E3 outcomes only. Baseline geometry unchanged; every veto is replayed through corrected one-active state.

## Corrected E3 baseline

| Period | Fills | Sum R | EV/fill | PF | MaxDD R |
|---|---:|---:|---:|---:|---:|
| TRAIN | 70 | +18.365 | +0.262 | 1.444 | 5.250 |
| VALID | 33 | +5.724 | +0.173 | 1.260 | 8.400 |
| FULL | 103 | +24.089 | +0.234 | 1.380 | 8.400 |

## Pre-entry feature separation

| Feature | TRAIN fail/good median | TRAIN AUC* | VALID fail/good median | VALID AUC* |
|---|---:|---:|---:|---:|
| delta_excess | +0.0794 / +0.0949 | 0.536 | +0.0808 / +0.0595 | 0.619 |
| buy_q75_ratio | +1.8013 / +1.7604 | 0.535 | +1.7629 / +1.7056 | 0.516 |
| close_pos | +0.8750 / +0.8913 | 0.551 | +0.9310 / +0.9010 | 0.645 |
| body_atr | +1.0846 / +1.5110 | 0.632 | +1.1570 / +1.1826 | 0.524 |
| breakout_atr | +0.6055 / +0.8225 | 0.597 | +0.4912 / +0.9566 | 0.702 |
| range_atr | +1.3631 / +1.7667 | 0.612 | +1.4206 / +1.5193 | 0.571 |
| atr_ratio_60 | +1.0699 / +1.0019 | 0.557 | +1.0665 / +0.9797 | 0.690 |

`AUC* = max(AUC, 1-AUC)`: 0.5 means no separation.

## TRAIN-selected top single

Frozen from TRAIN: **atr_ratio_60 HIGH 1.16577**.

| Period | Fills | Sum R | EV/fill | PF | MaxDD R |
|---|---:|---:|---:|---:|---:|
| TRAIN | 52 | +29.208 | +0.562 | 2.054 | 4.200 |
| VALID | 24 | +13.248 | +0.552 | 1.971 | 5.250 |
| FULL | 76 | +42.456 | +0.559 | 2.027 | 5.250 |

### Top-single promotion gates

- PASS — `train_retained_fills_ge30`
- PASS — `valid_retained_fills_ge15`
- PASS — `train_ev_fill_improves`
- PASS — `train_pf_improves`
- PASS — `valid_ev_fill_improves`
- PASS — `valid_pf_improves`
- PASS — `valid_sum_r_ge80pct_baseline`
- PASS — `full_dd_improve10pct_or_pf_plus015`
- PASS — `full_retained_fills_ge65pct`
- PASS — `causal_features_only`

## TRAIN-selected composite diagnostic

Composite: **OR** — atr_ratio_60 HIGH 1.16577; buy_q75_ratio LOW 1.24444.

| Period | Fills | Sum R | EV/fill | PF | MaxDD R |
|---|---:|---:|---:|---:|---:|
| TRAIN | 39 | +39.218 | +1.006 | 3.597 | 2.100 |
| VALID | 19 | +9.447 | +0.497 | 1.900 | 4.200 |
| FULL | 58 | +48.665 | +0.839 | 2.901 | 4.200 |

Composite promotion: **FAIL**.

## Research selection

Historical challenger selected for further robustness work: **TOP_SINGLE** — atr_ratio_60 HIGH 1.16577.

## Governance

This is still historical/post-discovery evidence, not independent OOS certification. No production logic is changed by LAB015 alone.
