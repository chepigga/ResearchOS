# GC SHORT CHRIS/AEIF DELAYED RESOLUTION PATH LAB004

**Status:** `HISTORICAL_DELAYED_RESOLUTION_PATH_SIGNAL_NOT_OOS`

Frozen LAB003 event set; no signal retuning and no trading overlay.

## Evidence-gate candidates

| Feature | Target | Rith VALID AUC | AMP VALID AUC | Orientation | Rith FULL AUC | AMP FULL AUC |
|---|---|---:|---:|---:|---:|---:|
| cp10_bear_frac | winner15 | 1.000 | 1.000 | +1 | 0.817 | 0.985 |
| cp10_bear_frac | winner30 | 1.000 | 1.000 | +1 | 0.871 | 0.923 |
| cp10_closepos | winner15 | 1.000 | 1.000 | -1 | 0.783 | 0.902 |
| cp10_closepos | winner30 | 1.000 | 1.000 | -1 | 0.833 | 0.915 |
| cp10_cum_body | winner15 | 1.000 | 1.000 | +1 | 0.825 | 1.000 |
| cp10_cum_body | winner30 | 1.000 | 1.000 | +1 | 0.892 | 0.923 |
| cp10_dist_seed_close | winner15 | 1.000 | 1.000 | +1 | 0.850 | 0.985 |
| cp10_dist_seed_close | winner30 | 1.000 | 1.000 | +1 | 0.875 | 0.908 |
| cp10_dist_seed_high | winner15 | 1.000 | 1.000 | +1 | 0.850 | 1.000 |
| cp10_dist_seed_high | winner30 | 1.000 | 1.000 | +1 | 0.892 | 0.923 |
| cp10_mae | winner15 | 0.840 | 0.840 | -1 | 0.717 | 0.902 |
| cp10_mae | winner30 | 0.840 | 0.840 | -1 | 0.833 | 0.838 |
| cp10_mfe | winner15 | 0.880 | 0.880 | +1 | 0.742 | 0.932 |
| cp10_mfe | winner30 | 0.880 | 0.880 | +1 | 0.817 | 0.854 |
| cp10_ret | winner15 | 1.000 | 1.000 | +1 | 0.850 | 1.000 |
| cp10_ret | winner30 | 1.000 | 1.000 | +1 | 0.883 | 0.923 |
| cp1_bear_frac | winner30 | 0.700 | 0.700 | +1 | 0.600 | 0.531 |
| cp1_closepos | winner30 | 0.760 | 0.760 | -1 | 0.583 | 0.546 |
| cp3_bear_frac | winner30 | 0.680 | 0.680 | +1 | 0.558 | 0.615 |
| cp3_dist_seed_close | winner30 | 0.680 | 0.680 | -1 | 0.667 | 0.538 |
| cp3_dist_seed_high | winner30 | 0.800 | 0.800 | -1 | 0.733 | 0.585 |
| cp5_cum_body | winner15 | 0.680 | 0.680 | +1 | 0.500 | 0.773 |
| cp5_cum_body | winner30 | 0.680 | 0.680 | +1 | 0.617 | 0.692 |
| cp5_mfe | winner30 | 0.680 | 0.680 | +1 | 0.583 | 0.569 |

## Decision

A causal delayed-resolution path signal exists descriptively. Do NOT trade it yet; preregister a walk-forward decision-gate LAB005 using only the identified feature/checkpoint family.
