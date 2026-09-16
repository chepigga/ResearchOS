# GC_XAU_D1_E3_TRADE_FAILURE_DISCRIMINATOR_LAB_015

**Status: HISTORICAL_FAILURE_DISCRIMINATOR_FAIL_NOT_OOS**

Historical bounded discovery on already-collected data only. Primary model uses only information available when the XAU limit becomes actionable.

## Population

- Corrected AMP accepted fills: **103**
- SL: **60**; non-SL: **43**; negative-net: **61**

## Walk-forward result

| Clock | OOF fills | SL AUC | Veto | Veto SL rate | Enrichment | Baseline EV/signal | Overlay EV/signal | Baseline SumR | Overlay SumR | MaxDD baseline→overlay | Late overlay EV |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ORDER_START_DEPLOYABLE | 58 | 0.411 | 27.6% | 50.0% | 0.83x | +0.092 | +0.068 | +12.99 | +9.63 | 8.40→8.80R | +0.064 |
| FILL_TIME_DIAGNOSTIC | 58 | 0.563 | 34.5% | 70.0% | 1.16x | +0.092 | +0.143 | +12.99 | +20.23 | 8.40→5.45R | +0.118 |

## Primary gates

- FAIL — `oof_sl_auc_ge_0_60`
- PASS — `oof_veto_share_10_to_40pct`
- FAIL — `veto_sl_enrichment_ge_1_25x`
- FAIL — `overlay_sum_r_gt_baseline`
- FAIL — `overlay_ev_signal_gt_baseline`
- PASS — `late_half_overlay_ev_signal_pos`
- PASS — `walkforward_evidence_sufficient`

## Strongest descriptive single features

| Feature | Clock | AUC* | SL median | non-SL median | Failure side |
|---|---|---:|---:|---:|---|
| gc_breakout_atr | ORDER_START_DEPLOYABLE | 0.640 | 0.571 | 0.8777 | LOW |
| gc_body_atr | ORDER_START_DEPLOYABLE | 0.606 | 1.108 | 1.461 | LOW |
| xau_mom_30s_atr | FILL_TIME_DIAGNOSTIC_ONLY | 0.595 | -1.012 | -0.9128 | LOW |
| gc_range_atr | ORDER_START_DEPLOYABLE | 0.584 | 1.403 | 1.66 | LOW |
| xau_spread_start_atr | ORDER_START_DEPLOYABLE | 0.559 | 0.2609 | 0.2611 | LOW |
| xau_spread_fill_atr | FILL_TIME_DIAGNOSTIC_ONLY | 0.559 | 0.2551 | 0.2629 | LOW |
| gc_buy_strength | ORDER_START_DEPLOYABLE | 0.539 | 1.757 | 1.771 | LOW |
| xau_mom_10s_atr | FILL_TIME_DIAGNOSTIC_ONLY | 0.536 | -0.5347 | -0.6221 | HIGH |

`AUC*` is directionless descriptive AUC on the full historical population and is not OOF evidence.

## Governance

The fill-time model is diagnostic only: a resting limit would already be filled at touch. A strong fill-time result can justify a later cancel/trigger redesign, not a direct filter. The LAB015 veto overlay is conservative and does not reclaim signals freed by vetoed trades; any candidate must be re-simulated with full state transitions before EA changes.
