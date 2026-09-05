# BTC_REVERSAL_P975_T25_CONFIRMATION_AND_SECOND_PARENT_FAMILY_DISCOVERY_LAB_015

## Part A — P975_T25 confirmation

**Verdict:** **PASS_CONFIRM_P975_T25**  
Frozen canonical T25 cutoff: **0.313090**

| Window | Selected REV | Mature | Fills | Fills/mo | Mean R/fill | Cum R | PF | DD R | LOEO worst |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2025_H2 | 27 | 16 | 11 | 1.83 | +0.713 | +7.85 | 3.425 | 1.10 | +3.30 |
| 2026_JAN_JUL | 28 | 15 | 12 | 1.71 | +0.589 | +7.06 | 2.619 | 2.08 | -1.54 |
| POOLED_RECENT | 55 | 31 | 23 | 1.77 | +0.648 | +14.91 | 2.962 | 2.08 | +6.31 |
| AUG2026_REUSED_AUDIT | 0 | 0 | 0 | 0.00 | — | +0.00 | — | 0.00 | — |

### Part A gates
- PASS — `h2_fills_ge_10`
- PASS — `y2026_fills_ge_10`
- PASS — `h2_mean_R_ge_040`
- PASS — `y2026_mean_R_ge_040`
- PASS — `pf_ge_2_both`
- PASS — `cumR_positive_both`
- PASS — `maxdd_le_25_both`
- PASS — `pooled_cumR_ge_12`
- PASS — `pooled_freq_ge_15pm`
- PASS — `pooled_all_loeo_positive`

**Score 10/10 → PASS_CONFIRM_P975_T25**

### Historical descriptive audit

| Window | Fills | Cum R | Mean R/fill | PF | DD R |
|---|---:|---:|---:|---:|---:|
| 2021 | 22 | +7.08 | +0.322 | 1.685 | 3.70 |
| 2022 | 15 | +0.42 | +0.028 | 1.050 | 5.19 |
| 2023 | 4 | -0.35 | -0.087 | 0.845 | 2.25 |
| 2024 | 17 | -0.61 | -0.036 | 0.943 | 4.48 |
| 2025_H1 | 3 | -0.96 | -0.318 | 0.563 | 2.19 |

## Part B — second parent-family discovery

Discovery is non-promotional; a positive family needs its own replication LAB.

| Family | Window | Selected REV | Mature | Fills | Fills/mo | Mean R/fill | Cum R | PF | DD R | LOEO worst |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| RANGE60_EXTREME | 2025_H2 | 22 | 5 | 3 | 0.50 | -0.652 | -1.96 | 0.066 | 2.10 | -1.96 |
| RANGE60_EXTREME | 2026_JAN_JUL | 19 | 12 | 5 | 0.71 | -0.055 | -0.28 | 0.914 | 2.13 | -1.76 |
| RANGE60_EXTREME | POOLED_RECENT | 41 | 17 | 8 | 0.62 | -0.279 | -2.23 | 0.579 | 2.61 | -3.71 |
| RANGE60_EXTREME | AUG2026_REUSED_AUDIT | 2 | 0 | 0 | 0.00 | — | +0.00 | — | 0.00 | — |
| VOLUME60_SHOCK | 2025_H2 | 18 | 8 | 6 | 1.00 | -0.538 | -3.23 | 0.312 | 3.65 | -3.65 |
| VOLUME60_SHOCK | 2026_JAN_JUL | 19 | 13 | 10 | 1.43 | +0.184 | +1.84 | 1.339 | 2.16 | -0.31 |
| VOLUME60_SHOCK | POOLED_RECENT | 37 | 21 | 16 | 1.23 | -0.087 | -1.39 | 0.862 | 5.00 | -3.54 |
| VOLUME60_SHOCK | AUG2026_REUSED_AUDIT | 2 | 1 | 1 | 1.00 | +1.319 | +1.32 | inf | 0.00 | +0.00 |
| PERSISTENT60_MOVE | 2025_H2 | 57 | 46 | 32 | 5.33 | -0.374 | -11.97 | 0.521 | 15.01 | -14.20 |
| PERSISTENT60_MOVE | 2026_JAN_JUL | 47 | 33 | 20 | 2.86 | +0.143 | +2.85 | 1.263 | 4.30 | +0.10 |
| PERSISTENT60_MOVE | POOLED_RECENT | 104 | 79 | 52 | 4.00 | -0.175 | -9.12 | 0.746 | 15.01 | -11.87 |
| PERSISTENT60_MOVE | AUG2026_REUSED_AUDIT | 4 | 1 | 0 | 0.00 | — | +0.00 | — | 0.00 | — |

### Discovery verdicts
- **RANGE60_EXTREME: REJECT_DISCOVERY (0/7)**
  - FAIL `h2_fills_ge_6`
  - FAIL `y2026_fills_ge_7`
  - FAIL `mean_positive_both`
  - FAIL `pf_gt_12_both`
  - FAIL `cum_positive_both`
  - FAIL `pooled_freq_ge_075`
  - FAIL `pooled_loeo_positive`
- **VOLUME60_SHOCK: REJECT_DISCOVERY (3/7)**
  - PASS `h2_fills_ge_6`
  - PASS `y2026_fills_ge_7`
  - FAIL `mean_positive_both`
  - FAIL `pf_gt_12_both`
  - FAIL `cum_positive_both`
  - PASS `pooled_freq_ge_075`
  - FAIL `pooled_loeo_positive`
- **PERSISTENT60_MOVE: REJECT_DISCOVERY (3/7)**
  - PASS `h2_fills_ge_6`
  - PASS `y2026_fills_ge_7`
  - FAIL `mean_positive_both`
  - FAIL `pf_gt_12_both`
  - FAIL `cum_positive_both`
  - PASS `pooled_freq_ge_075`
  - FAIL `pooled_loeo_positive`

### Overlap with canonical P975_T25 selected events

| Family | Selected | Exact overlap | Within ±24h | Share |
|---|---:|---:|---:|---:|
| RANGE60_EXTREME | 199 | 0 | 199 | 100.0% |
| VOLUME60_SHOCK | 168 | 0 | 168 | 100.0% |
| PERSISTENT60_MOVE | 430 | 0 | 430 | 100.0% |

### Descriptive canonical + discovery union

| Family added | Window | Real fills | Fills/mo | Cum R | Mean R/fill | PF | DD R |
|---|---|---:|---:|---:|---:|---:|---:|
| RANGE60_EXTREME | 2025_H2 | 14 | 2.33 | +5.89 | +0.421 | 2.105 | 3.18 |
| RANGE60_EXTREME | 2026_JAN_JUL | 17 | 2.43 | +6.79 | +0.399 | 1.897 | 2.30 |
| RANGE60_EXTREME | POOLED_RECENT | 31 | 2.38 | +12.68 | +0.409 | 1.983 | 3.18 |
| VOLUME60_SHOCK | 2025_H2 | 17 | 2.83 | +4.62 | +0.272 | 1.582 | 2.25 |
| VOLUME60_SHOCK | 2026_JAN_JUL | 22 | 3.14 | +8.90 | +0.405 | 1.911 | 3.18 |
| VOLUME60_SHOCK | POOLED_RECENT | 39 | 3.00 | +13.52 | +0.347 | 1.764 | 3.52 |
| PERSISTENT60_MOVE | 2025_H2 | 43 | 7.17 | -4.13 | -0.096 | 0.854 | 10.63 |
| PERSISTENT60_MOVE | 2026_JAN_JUL | 32 | 4.57 | +9.92 | +0.310 | 1.652 | 5.58 |
| PERSISTENT60_MOVE | POOLED_RECENT | 75 | 5.77 | +5.79 | +0.077 | 1.133 | 10.63 |

## Status
- Part A uses reused research windows; it is a formal re-freeze, not fresh prospective confirmation.
- Part B is discovery-only and cannot become canonical from this LAB.
- August 2026 remains consumed/reused audit only.
- No live allocation is authorized by LAB015 alone.
