# XAU_H1_CONTEXT_ALIGNED_EXECUTABLE_RR15_COST_YEAR_TRANSFER_LAB_006

**Verdict: POSITIVE_BUT_TRANSFER_NOT_CONFIRMED**

> Reused-history execution diagnostic. Synthetic all-in bps costs on bid-only M1 are not true MT5 bid/ask replication. No production promotion is authorized.

## Frozen executable universe

- Frozen H1 HIGH ALIGNED rows: **1195**
- Unique executable event signals: **1195**
- Primary single-position trades: **488**
- Duplicate rows removed: **0**
- Overlap signals skipped: **707**

## Primary 2 bps all-in RT

- EV: **+0.05700R**
- PF: **1.098**
- Win rate: **44.06%**
- CumR: **+27.82R**
- Max closed-trade DD: **26.76R** = **6.69% @0.25% risk**
- Recovery factor: **1.04**
- Median hold: **7.0h**

## Weekly cluster bootstrap

- 95% CI EV: **[-0.07019, +0.18086]R**; P(EV>0)=0.805

## Cost stress

- 1 bps: N=488, EV **+0.07922R**, PF **1.139**, CumR +38.66R, DD 25.13R
- 2 bps: N=488, EV **+0.05700R**, PF **1.098**, CumR +27.82R, DD 26.76R
- 3 bps: N=488, EV **+0.03478R**, PF **1.058**, CumR +16.97R, DD 28.40R
- 5 bps: N=488, EV **-0.00965R**, PF **0.984**, CumR -4.71R, DD 31.66R

## Year transfer (2 bps)

- 2023: N=105, EV **-0.05800R**, PF **0.909**, CumR -6.09R, DD 26.76R
- 2024: N=145, EV **-0.01345R**, PF **0.978**, CumR -1.95R, DD 15.06R
- 2025: N=162, EV **+0.19289R**, PF **1.366**, CumR +31.25R, DD 10.44R
- 2026: N=76, EV **+0.06063R**, PF **1.105**, CumR +4.61R, DD 9.46R

## Gates

- PASS — `G1_2bps_ev_gt_zero`
- FAIL — `G2_2bps_pf_ge_1_20`
- FAIL — `G3_bootstrap_ci_lo_gt_zero`
- FAIL — `G4_all_4_years_positive_pf_gt1_n20`
- FAIL — `G5_loyo_4of4_ev_positive`
- FAIL — `G6_5bps_ev_gt_zero_pf_gt_1_05`
- FAIL — `G7_dd_at_025_le_4pct`
- FAIL — `G8_recovery_factor_ge_2`
- PASS — `G9_n_ge_100`
