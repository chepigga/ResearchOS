# GC SHORT CHRIS/AEIF POST10 DISTANCE GATE WALKFORWARD LAB006

**Status:** `HISTORICAL_POST10_DISTANCE_GATE_WALKFORWARD_PASS_NOT_OOS`

Feature: `cp10_dist_seed_high`; gate: expanding prior-event Q50 after 8 historical events.

## OOF results

| Feed | Target | N | Selected | Share | Baseline EV | Selected EV | Rejected EV | Uplift | Selected WR |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| AMP_CQG_RAW_EXCLUSIVE | resid_10_20_atr | 15 | 8 | 53.3% | +1.1234 | +2.2459 | -0.1595 | +1.1225 | 87.5% |
| AMP_CQG_RAW_EXCLUSIVE | resid_10_30_atr | 15 | 8 | 53.3% | +1.1248 | +2.3992 | -0.3316 | +1.2744 | 75.0% |
| RITHMIC_RAW | resid_10_20_atr | 14 | 7 | 50.0% | +0.8038 | +2.0300 | -0.4224 | +1.2262 | 85.7% |
| RITHMIC_RAW | resid_10_30_atr | 14 | 7 | 50.0% | +0.9612 | +2.7023 | -0.7798 | +1.7411 | 85.7% |

## Frozen gates

- PASS — `rith_oof_n_ge12`
- PASS — `amp_oof_n_ge12`
- PASS — `rith_selection_25_75`
- PASS — `amp_selection_25_75`
- PASS — `rith_selected_ev_pos`
- PASS — `amp_selected_ev_pos`
- PASS — `rith_selected_gt_baseline`
- PASS — `amp_selected_gt_baseline`
- PASS — `rith_uplift_ge010`
- PASS — `amp_uplift_ge010`
- PASS — `rith_selected_wr_ge55`
- PASS — `amp_selected_wr_ge55`
- PASS — `rith_secondary_nonneg`
- PASS — `amp_secondary_nonneg`

## Decision

This exact historical GC walk-forward gate passes. It may advance to a separate GC->XAU transfer/execution study, but it is not OOS and not demo/live ready.
