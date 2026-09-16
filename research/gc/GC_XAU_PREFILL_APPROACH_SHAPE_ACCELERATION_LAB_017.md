# GC_XAU_PREFILL_APPROACH_SHAPE_ACCELERATION_LAB_017

**Status: HISTORICAL_CAUSAL_ACCELERATION_GATE_FAIL_NOT_OOS**

- OOF: **49** | AUC: **0.568**
- Veto: **12/49 (24.5%)**
- SL rate baseline/veto: **61.2% / 75.0%** | enrichment **1.22x**
- SumR baseline -> overlay: **+6.24R -> +10.85R**
- EV/signal: **+0.05160 -> +0.08968R**
- MaxDD: **8.40R -> 6.30R**
- Late-half overlay EV/signal: **+0.13767R**

## Gates
- FAIL — `oof_auc_ge0_60`
- PASS — `veto_share_10_to_40pct`
- FAIL — `veto_sl_enrichment_ge1_25x`
- PASS — `overlay_sum_gt_baseline`
- PASS — `overlay_ev_gt_baseline`
- PASS — `overlay_maxdd_le_baseline`
- PASS — `late_half_overlay_ev_pos`

Acceleration overlay is rejected. Bare corrected D1/E3 remains the candidate.
