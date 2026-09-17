# GC→XAU SHORT CHRIS POST10 TRANSFER LAB007

**Status:** `HISTORICAL_GC_XAU_SHORT_CHRIS_TRANSFER_PASS_NOT_OOS`

Frozen LAB006 gate transferred to executable FTMO-Demo XAUUSD. Historical only; not independent OOS.

Clock: **UTC + 180m**, M1 return correlation **0.986917**.

## XAU directional transfer

| Feed | Group | H | N | EV bps | EV ATR | WR |
|---|---|---:|---:|---:|---:|---:|
| RITHMIC_RAW | all_oof | 5m | 14 | +1.442 | +0.355 | 42.9% |
| RITHMIC_RAW | all_oof | 10m | 14 | +3.242 | +0.652 | 50.0% |
| RITHMIC_RAW | all_oof | 20m | 14 | +2.783 | +0.750 | 57.1% |
| RITHMIC_RAW | all_oof | 30m | 14 | +5.177 | +1.107 | 57.1% |
| RITHMIC_RAW | selected | 5m | 7 | +3.580 | +0.800 | 42.9% |
| RITHMIC_RAW | selected | 10m | 7 | +10.021 | +2.052 | 71.4% |
| RITHMIC_RAW | selected | 20m | 7 | +12.497 | +2.707 | 85.7% |
| RITHMIC_RAW | selected | 30m | 7 | +18.916 | +3.728 | 85.7% |
| RITHMIC_RAW | rejected | 5m | 7 | -0.696 | -0.090 | 42.9% |
| RITHMIC_RAW | rejected | 10m | 7 | -3.536 | -0.748 | 28.6% |
| RITHMIC_RAW | rejected | 20m | 7 | -6.931 | -1.207 | 28.6% |
| RITHMIC_RAW | rejected | 30m | 7 | -8.562 | -1.515 | 28.6% |
| AMP_CQG_RAW_EXCLUSIVE | all_oof | 5m | 15 | +0.529 | +0.075 | 33.3% |
| AMP_CQG_RAW_EXCLUSIVE | all_oof | 10m | 15 | +4.642 | +0.908 | 66.7% |
| AMP_CQG_RAW_EXCLUSIVE | all_oof | 20m | 15 | +4.329 | +0.786 | 60.0% |
| AMP_CQG_RAW_EXCLUSIVE | all_oof | 30m | 15 | +7.195 | +1.153 | 60.0% |
| AMP_CQG_RAW_EXCLUSIVE | selected | 5m | 8 | +3.207 | +0.664 | 37.5% |
| AMP_CQG_RAW_EXCLUSIVE | selected | 10m | 8 | +11.449 | +2.205 | 87.5% |
| AMP_CQG_RAW_EXCLUSIVE | selected | 20m | 8 | +12.359 | +2.314 | 75.0% |
| AMP_CQG_RAW_EXCLUSIVE | selected | 30m | 8 | +20.115 | +3.628 | 75.0% |
| AMP_CQG_RAW_EXCLUSIVE | rejected | 5m | 7 | -2.531 | -0.597 | 28.6% |
| AMP_CQG_RAW_EXCLUSIVE | rejected | 10m | 7 | -3.137 | -0.574 | 42.9% |
| AMP_CQG_RAW_EXCLUSIVE | rejected | 20m | 7 | -4.848 | -0.960 | 42.9% |
| AMP_CQG_RAW_EXCLUSIVE | rejected | 30m | 7 | -7.570 | -1.675 | 42.9% |

## Exact-common selected subset

Common selected seed-times: **6**; XAU 10m EV **+11.740 bps**; WR **83.3%**.

## Frozen gates

- PASS — `clock_offset_eq_180`
- PASS — `clock_corr_ge_098`
- PASS — `rith_selected_n_ge6`
- PASS — `amp_selected_n_ge6`
- PASS — `rith_selected_10m_ev_pos`
- PASS — `amp_selected_10m_ev_pos`
- PASS — `rith_selected_gt_baseline_10m`
- PASS — `amp_selected_gt_baseline_10m`
- PASS — `rith_selected_gt_rejected_10m`
- PASS — `amp_selected_gt_rejected_10m`
- PASS — `rith_selected_wr_ge50`
- PASS — `amp_selected_wr_ge50`
- PASS — `rith_selected_20m_nonneg`
- PASS — `amp_selected_20m_nonneg`
- PASS — `common_selected_10m_ev_pos`

## Decision

The frozen GC Chris POST10 gate transfers positively to executable XAU historically. Advance only to a separately preregistered XAU execution-geometry study; do not tune LAB007 post hoc.
