# GC_XAU_D075_PREFILL_WARNING_GATE_LAB_016

**Status: HISTORICAL_CAUSAL_PREFILL_GATE_FAIL_NOT_OOS**

Causal historical discovery at D0.75, strictly before frozen D1 touch.

## Population

- Corrected accepted fills: **103**
- Executable D0.75 warnings: **94 (91.3%)**
- Median warning lead to D1 fill: **5.325s**
- P10 warning lead: **0.647s**

## Walk-forward

- OOF warning-eligible fills: **49**
- SL AUC: **0.489**
- Veto: **17/49 (34.7%)**
- Veto SL rate: **64.7%**, enrichment **1.06x**

## Conservative overlay

- Baseline -> overlay SumR: **+6.24R -> +7.58R**
- EV/original signal: **+0.05160R -> +0.06267R**
- MaxDD: **8.40R -> 6.50R**
- Late-half overlay EV/signal: **+0.11148R**

## Gates

- PASS — `warning_coverage_ge70pct`
- PASS — `oof_ge40_and_both_classes`
- FAIL — `oof_sl_auc_ge0_60`
- PASS — `veto_share_10_to_40pct`
- FAIL — `veto_sl_enrichment_ge1_25x`
- PASS — `overlay_sum_gt_baseline`
- PASS — `overlay_ev_signal_gt_baseline`
- PASS — `overlay_maxdd_le_baseline`
- PASS — `late_half_overlay_ev_pos`

## Strongest descriptive features

| Feature | AUC* | Failure side |
|---|---:|---|
| gc_breakout_atr | 0.624 | LOW |
| gc_body_atr | 0.604 | LOW |
| xau_mom_30s_warning_atr | 0.601 | LOW |
| gc_range_atr | 0.581 | LOW |
| warning_delay_sec | 0.560 | HIGH |
| xau_approach_velocity_atr_per_sec | 0.557 | LOW |
| gc_buy_loc_excess | 0.553 | LOW |
| xau_mom_10s_warning_atr | 0.537 | LOW |

`AUC*` is full-history descriptive only, not OOF evidence.

A PASS is still not production promotion; reclaimed-signal state transitions are not simulated in LAB016.
