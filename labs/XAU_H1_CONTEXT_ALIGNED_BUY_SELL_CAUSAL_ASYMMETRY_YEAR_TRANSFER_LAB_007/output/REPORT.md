# XAU_H1_CONTEXT_ALIGNED_BUY_SELL_CAUSAL_ASYMMETRY_YEAR_TRANSFER_LAB_007

**Verdict: BUY_SELL_ASYMMETRY_MIXED**

> Reused-history diagnostic. BUY-only was motivated by LAB006; no production promotion is authorized.

## Frozen parity
- Context eligible: **263405**
- H1 HIGH ALIGNED rows: **1195**
- Combined LAB006 primary: **488**
- BUY-only primary: **385** (from 954 events; skipped 569)
- SELL-only primary: **103** (from 241 events; skipped 138)

## Attribution asymmetry — exact LAB006 combined ledger
- BUY: N=385, EV **+0.11184R**, PF **1.199**
- SELL: N=103, EV **-0.14797R**, PF **0.779**
- EV BUY-SELL: **+0.25980R**
- Weekly bootstrap 95% CI: **[-0.02250, +0.55849]R**, P>0=0.966

## Counterfactual separate ledgers
- BUY-only: N=385, EV **+0.11184R**, PF **1.199**, CumR +43.06R, DD 13.05R = 3.26% @0.25%, Recovery 3.30
- SELL-only: N=103, EV **-0.14797R**, PF **0.779**, CumR -15.24R
- EV BUY_ONLY-SELL_ONLY: **+0.25980R**
- Difference bootstrap 95% CI: **[-0.02250, +0.55849]R**, P>0=0.966
- BUY-only EV bootstrap 95% CI: **[-0.03418, +0.24758]R**, P>0=0.932

## BUY-only year transfer (2 bps)
- 2023: N=68, EV **+0.01395R**, PF **1.023**, CumR +0.95R, DD 12.15R
- 2024: N=128, EV **+0.04639R**, PF **1.079**, CumR +5.94R, DD 12.95R
- 2025: N=159, EV **+0.20061R**, PF **1.383**, CumR +31.90R, DD 9.94R
- 2026: N=30, EV **+0.14241R**, PF **1.261**, CumR +4.27R, DD 9.13R

## BUY-only cost stress
- 1 bps: N=385, EV **+0.13384R**, PF **1.244**, CumR +51.53R, DD 12.53R
- 2 bps: N=385, EV **+0.11184R**, PF **1.199**, CumR +43.06R, DD 13.05R
- 3 bps: N=385, EV **+0.08983R**, PF **1.157**, CumR +34.59R, DD 13.92R
- 5 bps: N=385, EV **+0.04582R**, PF **1.077**, CumR +17.64R, DD 15.86R

## BUY-only concentration diagnostics
- Best positive year share: 0.741
- Best positive month share: 0.185
- Top-10 positive weeks share: 0.559

## Gates
- PASS — `A1_attribution_ev_diff_gt_zero`
- FAIL — `A2_attribution_boot_ci_lo_gt_zero`
- PASS — `A3_counterfactual_ev_diff_gt_zero`
- FAIL — `A4_counterfactual_boot_ci_lo_gt_zero`
- PASS — `B1_buy_2bps_ev_gt_zero`
- FAIL — `B2_buy_2bps_pf_ge_1_20`
- FAIL — `B3_buy_boot_ci_lo_gt_zero`
- PASS — `B4_buy_all4_years_positive`
- PASS — `B5_buy_loyo_4of4_positive`
- PASS — `B6_buy_5bps_ev_gt_zero_pf_gt_1_05`
- PASS — `B7_buy_dd_at_025_le_4pct`
- PASS — `B8_buy_recovery_ge_2`
- PASS — `B9_buy_n_ge_100`
