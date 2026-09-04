# BTC_REVERSAL_EPISODE_CAUSAL_VIRTUAL_FILL_MATURITY_AND_LATE_REENTRY_TRANSFER_LAB_013

**Verdict:** **PASS_CAUSAL_VIRTUAL_FILL_MATURITY_TRANSFER**

Role: causal virtual-fill maturity / late-reentry transfer audit over the exact frozen reversal branch; no new selector, entry geometry, stop, target, or regime gate.

## Primary and audit policy economics

| Window | Policy | Admit | Fills | Cum R | EV/op | PF | Max DD | Worst ep | Top ep share | LOEO worst | Boot CI low | Max ep fills |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2025_H2 | BASE_ALL | 16 | 12 | +6.64 | +0.415 | 2.458 | 2.38 | -1.20 | 62.8% | -0.39 | -1.167 | 5 |
| 2025_H2 | VF1_MATURE | 10 | 7 | +7.40 | +0.463 | 7.841 | 1.08 | +0.00 | 66.5% | +1.76 | +0.000 | 4 |
| 2025_H2 | VF2_MATURE | 7 | 5 | +4.58 | +0.286 | 5.228 | 1.08 | +0.00 | 74.8% | +0.34 | +0.000 | 3 |
| 2025_H2 | OPP2_MATURE | 9 | 6 | +5.99 | +0.374 | 6.532 | 1.08 | +0.00 | 79.8% | +0.34 | +0.000 | 4 |
| 2025_H2 | VF1_KNOWN_OUTCOME | 9 | 7 | +7.40 | +0.463 | 7.841 | 1.08 | +0.00 | 66.5% | +1.76 | +0.000 | 4 |
| 2025_H2 | KNOWN_POSITIVE | 9 | 7 | +7.40 | +0.463 | 7.841 | 1.08 | +0.00 | 66.5% | +1.76 | +0.000 | 4 |
| 2026_JAN_JUL | BASE_ALL | 22 | 15 | +6.17 | +0.281 | 1.929 | 2.28 | -1.70 | 55.9% | +0.11 | -0.252 | 6 |
| 2026_JAN_JUL | VF1_MATURE | 10 | 8 | +6.50 | +0.296 | 4.096 | 1.07 | -0.66 | 83.2% | -0.66 | -0.068 | 5 |
| 2026_JAN_JUL | VF2_MATURE | 6 | 6 | +6.10 | +0.277 | 6.725 | 1.07 | +0.00 | 79.8% | +0.38 | +0.000 | 4 |
| 2026_JAN_JUL | OPP2_MATURE | 12 | 9 | +5.46 | +0.248 | 2.736 | 2.08 | -1.70 | 83.2% | -1.70 | -0.176 | 5 |
| 2026_JAN_JUL | VF1_KNOWN_OUTCOME | 5 | 5 | +7.16 | +0.325 | inf | 0.00 | +0.00 | 100.0% | +0.00 | +0.000 | 5 |
| 2026_JAN_JUL | KNOWN_POSITIVE | 3 | 3 | +4.26 | +0.194 | inf | 0.00 | +0.00 | 100.0% | +0.00 | +0.000 | 3 |
| POOLED_RECENT | BASE_ALL | 38 | 27 | +12.81 | +0.337 | 2.144 | 2.38 | -1.70 | 29.8% | +5.78 | -0.203 | 6 |
| POOLED_RECENT | VF1_MATURE | 20 | 15 | +13.91 | +0.366 | 5.369 | 1.08 | -0.66 | 41.9% | +6.75 | -0.019 | 5 |
| POOLED_RECENT | VF2_MATURE | 13 | 11 | +10.68 | +0.281 | 5.971 | 1.08 | +0.00 | 44.6% | +4.96 | +0.019 | 4 |
| POOLED_RECENT | OPP2_MATURE | 21 | 15 | +11.45 | +0.301 | 3.708 | 2.08 | -1.70 | 45.7% | +4.29 | -0.095 | 5 |
| POOLED_RECENT | VF1_KNOWN_OUTCOME | 14 | 12 | +14.56 | +0.383 | 14.458 | 1.08 | +0.00 | 45.8% | +7.40 | +0.000 | 5 |
| POOLED_RECENT | KNOWN_POSITIVE | 12 | 10 | +11.66 | +0.307 | 11.780 | 1.08 | +0.00 | 44.3% | +6.02 | +0.000 | 4 |

## Virtual-fill maturity buckets

| Window | Prior virtual fills | Opps | Fills | Fill mean R | Fill positive | Cum R | Median h from ep start | Median h from first VF |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 2025_H2 | 0 | 6 | 5 | -0.152 | 40.0% | -0.76 | 0.0 | — |
| 2025_H2 | 1 | 3 | 2 | +1.414 | 100.0% | +2.83 | 78.5 | 74.5 |
| 2025_H2 | 2 | 2 | 2 | +0.159 | 50.0% | +0.32 | 121.2 | 119.0 |
| 2025_H2 | 3+ | 5 | 3 | +1.419 | 100.0% | +4.26 | 164.0 | 163.8 |
| 2026_JAN_JUL | 0 | 12 | 7 | -0.047 | 42.9% | -0.33 | 0.0 | — |
| 2026_JAN_JUL | 1 | 4 | 2 | +0.201 | 50.0% | +0.40 | 22.6 | 13.2 |
| 2026_JAN_JUL | 2 | 2 | 2 | +1.453 | 100.0% | +2.91 | 107.5 | 28.5 |
| 2026_JAN_JUL | 3+ | 4 | 4 | +0.799 | 75.0% | +3.20 | 101.4 | 85.2 |
| POOLED_RECENT | 0 | 18 | 12 | -0.091 | 41.7% | -1.09 | 0.0 | — |
| POOLED_RECENT | 1 | 7 | 4 | +0.807 | 75.0% | +3.23 | 25.8 | 19.2 |
| POOLED_RECENT | 2 | 4 | 4 | +0.806 | 75.0% | +3.22 | 121.2 | 69.6 |
| POOLED_RECENT | 3+ | 9 | 7 | +1.065 | 85.7% | +7.45 | 159.5 | 147.2 |

## Primary VF1 interpretation
- Pooled BASE: **+12.81R** → VF1: **+13.91R**; retention **108.5%**.
- Pooled PF: **2.144 → 5.369**; max DD **2.38R → 1.08R**.
- Max real fills in one episode under VF1: **5** = up to **1.25%** initial episode budget at 0.25%/trade or **2.50%** at 0.50%/trade.
- Early virtual-fill bucket: N=12, mean **-0.091R/fill**. Mature bucket >=1 prior VF: N=15, mean **+0.927R/fill**.

## Historical descriptive audit

| Window | Policy | Admit | Fills | Cum R | PF | DD |
|---|---|---:|---:|---:|---:|---:|
| 2021 | BASE_ALL | 47 | 27 | +9.09 | 1.728 | 3.19 |
| 2021 | VF1_MATURE | 29 | 18 | +3.72 | 1.399 | 3.12 |
| 2022 | BASE_ALL | 33 | 20 | -2.79 | 0.781 | 5.87 |
| 2022 | VF1_MATURE | 21 | 12 | -3.93 | 0.527 | 7.28 |
| 2023 | BASE_ALL | 9 | 6 | +1.57 | 1.698 | 2.25 |
| 2023 | VF1_MATURE | 4 | 3 | +0.76 | 1.662 | 1.14 |
| 2024 | BASE_ALL | 33 | 24 | -5.66 | 0.671 | 9.48 |
| 2024 | VF1_MATURE | 18 | 13 | -1.42 | 0.836 | 2.39 |
| 2025_H1 | BASE_ALL | 11 | 6 | -1.68 | 0.616 | 2.16 |
| 2025_H1 | VF1_MATURE | 3 | 2 | +0.10 | 1.089 | 1.13 |

## Gates
- PASS — `h2_2025_cum_positive`
- PASS — `y2026_cum_positive`
- PASS — `pooled_cum_positive`
- PASS — `pooled_retains_ge_70pct_base`
- PASS — `h2_2025_retains_ge_70pct_base`
- PASS — `y2026_retains_ge_70pct_base`
- PASS — `pooled_pf_ge_base`
- PASS — `pooled_maxdd_le_base`
- PASS — `vf0_fill_mean_nonpositive`
- PASS — `vf1plus_fill_mean_positive`
- PASS — `pooled_all_loeo_positive`
- FAIL — `pooled_cluster_bootstrap_ci_low_gt_0`

**Score 11/12 → PASS_CAUSAL_VIRTUAL_FILL_MATURITY_TRANSFER**

## Status
- `VF1_MATURE` is the only primary maturity rule; audit policies cannot rescue it.
- Virtual fill knowledge requires actual frozen fill_time strictly before the current event; no future path is used to activate VF1.
- Outcome-aware audits delay prior outcomes by +24h15m.
- 2025 H2 and 2026 Jan-Jul are reused research windows, not fresh holdouts.
- August 2026 remains consumed and has zero frozen REV opportunities.
- No live allocation is authorized by LAB013 alone.
