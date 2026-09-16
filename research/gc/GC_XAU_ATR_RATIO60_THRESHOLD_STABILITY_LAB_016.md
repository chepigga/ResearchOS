# GC_XAU_ATR_RATIO60_THRESHOLD_STABILITY_LAB_016

**Status: THRESHOLD_NEIGHBORHOOD_STABLE_PASS_NOT_OOS**

Frozen grid only; no threshold optimization.

| Thr | Fills | Retain | SumR | EV/fill | PF | MaxDD R | VALID fills | VALID SumR | VALID EV/fill | VALID PF | LOO-week min EV/signal |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1.10000 | 66 | 64.1% | +30.734 | +0.466 | 1.851 | 4.200 | 21 | +12.398 | +0.590 | 2.073 | +0.0911 |
| 1.13000 | 72 | 69.9% | +42.656 | +0.592 | 2.117 | 5.250 | 23 | +14.298 | +0.622 | 2.135 | +0.1371 |
| 1.16577 | 76 | 73.8% | +42.456 | +0.559 | 2.027 | 5.250 | 24 | +13.248 | +0.552 | 1.971 | +0.1403 |
| 1.20000 | 78 | 75.7% | +40.356 | +0.517 | 1.929 | 5.250 | 24 | +13.248 | +0.552 | 1.971 | +0.1324 |
| 1.23000 | 81 | 78.6% | +37.206 | +0.459 | 1.798 | 5.250 | 26 | +11.148 | +0.429 | 1.708 | +0.1205 |

## Gates

- PASS — `incumbent_exact_reproduction`
- PASS — `four_of_five_full_pf_above_baseline`
- PASS — `four_of_five_full_evfill_above_baseline`
- PASS — `four_of_five_valid_pf_above_baseline`
- PASS — `four_of_five_valid_evfill_above_baseline`
- PASS — `four_of_five_retain_ge65pct_fills`
- PASS — `incumbent_loo_week_min_ev_positive`
- PASS — `no_new_optimum_selected`

## Governance

LAB016 does not select a new best threshold. If the neighborhood passes, the LAB015 threshold 1.1657688284518744 remains frozen for subsequent research because it was selected before this stability audit.
