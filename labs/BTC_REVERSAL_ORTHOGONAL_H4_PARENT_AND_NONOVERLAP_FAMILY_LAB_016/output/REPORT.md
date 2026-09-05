# BTC_REVERSAL_ORTHOGONAL_H4_PARENT_AND_NONOVERLAP_FAMILY_LAB_016

Role: strict non-overlap H4 parent-family discovery outside ±24h of frozen canonical `P975_T25`; frozen `T25 + VF1 + LIMIT0.5/SL1/TP1.5/5bps`.

Frozen T25 cutoff: **0.313090**

## Orthogonality census

| Family | Raw H4 parents | T25 REV pre-filter | Removed ±24h canonical | Non-overlap selected | Removal share |
|---|---:|---:|---:|---:|---:|
| H4_DISPLACEMENT_EXTREME | 375 | 151 | 85 | 66 | 56.3% |
| H4_FAILED_EXTENSION | 19 | 8 | 6 | 2 | 75.0% |
| H4_7D_PIVOT_SWEEP_RECLAIM | 610 | 294 | 81 | 213 | 27.6% |

## Non-overlap H4 family economics

| Family | Window | Selected | Mature | Fills | Fills/mo | Mean R/fill | Cum R | PF | DD R | LOEO worst |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| H4_DISPLACEMENT_EXTREME | 2025_H2 | 8 | 0 | 0 | 0.00 | — | +0.00 | — | 0.00 | — |
| H4_DISPLACEMENT_EXTREME | 2026_JAN_JUL | 7 | 0 | 0 | 0.00 | — | +0.00 | — | 0.00 | — |
| H4_DISPLACEMENT_EXTREME | POOLED_RECENT | 15 | 0 | 0 | 0.00 | — | +0.00 | — | 0.00 | — |
| H4_DISPLACEMENT_EXTREME | AUG2026_REUSED_AUDIT | 0 | 0 | 0 | 0.00 | — | +0.00 | — | 0.00 | — |
| H4_FAILED_EXTENSION | 2025_H2 | 0 | 0 | 0 | 0.00 | — | +0.00 | — | 0.00 | — |
| H4_FAILED_EXTENSION | 2026_JAN_JUL | 0 | 0 | 0 | 0.00 | — | +0.00 | — | 0.00 | — |
| H4_FAILED_EXTENSION | POOLED_RECENT | 0 | 0 | 0 | 0.00 | — | +0.00 | — | 0.00 | — |
| H4_FAILED_EXTENSION | AUG2026_REUSED_AUDIT | 0 | 0 | 0 | 0.00 | — | +0.00 | — | 0.00 | — |
| H4_7D_PIVOT_SWEEP_RECLAIM | 2025_H2 | 22 | 2 | 0 | 0.00 | — | +0.00 | — | 0.00 | — |
| H4_7D_PIVOT_SWEEP_RECLAIM | 2026_JAN_JUL | 21 | 0 | 0 | 0.00 | — | +0.00 | — | 0.00 | — |
| H4_7D_PIVOT_SWEEP_RECLAIM | POOLED_RECENT | 43 | 2 | 0 | 0.00 | — | +0.00 | — | 0.00 | — |
| H4_7D_PIVOT_SWEEP_RECLAIM | AUG2026_REUSED_AUDIT | 6 | 3 | 0 | 0.00 | — | +0.00 | — | 0.00 | — |

## Discovery verdicts
- **H4_DISPLACEMENT_EXTREME: REJECT_ORTHOGONAL_H4_DISCOVERY (1/10)**
  - FAIL `h2_selected_ge_10`
  - FAIL `y2026_selected_ge_10`
  - FAIL `h2_real_fills_ge_5`
  - FAIL `y2026_real_fills_ge_5`
  - FAIL `mean_R_positive_both`
  - FAIL `pf_gt_12_both`
  - FAIL `cumR_positive_both`
  - FAIL `pooled_freq_ge_075`
  - FAIL `pooled_loeo_positive`
  - PASS `pooled_maxdd_le_4R`
- **H4_FAILED_EXTENSION: REJECT_ORTHOGONAL_H4_DISCOVERY (1/10)**
  - FAIL `h2_selected_ge_10`
  - FAIL `y2026_selected_ge_10`
  - FAIL `h2_real_fills_ge_5`
  - FAIL `y2026_real_fills_ge_5`
  - FAIL `mean_R_positive_both`
  - FAIL `pf_gt_12_both`
  - FAIL `cumR_positive_both`
  - FAIL `pooled_freq_ge_075`
  - FAIL `pooled_loeo_positive`
  - PASS `pooled_maxdd_le_4R`
- **H4_7D_PIVOT_SWEEP_RECLAIM: REJECT_ORTHOGONAL_H4_DISCOVERY (3/10)**
  - PASS `h2_selected_ge_10`
  - PASS `y2026_selected_ge_10`
  - FAIL `h2_real_fills_ge_5`
  - FAIL `y2026_real_fills_ge_5`
  - FAIL `mean_R_positive_both`
  - FAIL `pf_gt_12_both`
  - FAIL `cumR_positive_both`
  - FAIL `pooled_freq_ge_075`
  - FAIL `pooled_loeo_positive`
  - PASS `pooled_maxdd_le_4R`

## Canonical + H4 descriptive union

| H4 family added | Window | Real fills | Fills/mo | Incremental H4 fills | H4 fill share | Cum R | Mean R/fill | PF | DD R |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| H4_DISPLACEMENT_EXTREME | 2025_H2 | 11 | 1.83 | 0 | 0.0% | +7.85 | +0.713 | 3.425 | 1.10 |
| H4_DISPLACEMENT_EXTREME | 2026_JAN_JUL | 12 | 1.71 | 0 | 0.0% | +7.06 | +0.589 | 2.619 | 2.08 |
| H4_DISPLACEMENT_EXTREME | POOLED_RECENT | 23 | 1.77 | 0 | 0.0% | +14.91 | +0.648 | 2.962 | 2.08 |
| H4_FAILED_EXTENSION | 2025_H2 | 11 | 1.83 | 0 | 0.0% | +7.85 | +0.713 | 3.425 | 1.10 |
| H4_FAILED_EXTENSION | 2026_JAN_JUL | 12 | 1.71 | 0 | 0.0% | +7.06 | +0.589 | 2.619 | 2.08 |
| H4_FAILED_EXTENSION | POOLED_RECENT | 23 | 1.77 | 0 | 0.0% | +14.91 | +0.648 | 2.962 | 2.08 |
| H4_7D_PIVOT_SWEEP_RECLAIM | 2025_H2 | 11 | 1.83 | 0 | 0.0% | +7.85 | +0.713 | 3.425 | 1.10 |
| H4_7D_PIVOT_SWEEP_RECLAIM | 2026_JAN_JUL | 12 | 1.71 | 0 | 0.0% | +7.06 | +0.589 | 2.619 | 2.08 |
| H4_7D_PIVOT_SWEEP_RECLAIM | POOLED_RECENT | 23 | 1.77 | 0 | 0.0% | +14.91 | +0.648 | 2.962 | 2.08 |

## Historical descriptive audit

| Family | Window | Fills | Cum R | Mean R/fill | PF | DD R |
|---|---|---:|---:|---:|---:|---:|
| H4_DISPLACEMENT_EXTREME | 2021 | 0 | +0.00 | — | — | 0.00 |
| H4_DISPLACEMENT_EXTREME | 2022 | 0 | +0.00 | — | — | 0.00 |
| H4_DISPLACEMENT_EXTREME | 2023 | 0 | +0.00 | — | — | 0.00 |
| H4_DISPLACEMENT_EXTREME | 2024 | 0 | +0.00 | — | — | 0.00 |
| H4_DISPLACEMENT_EXTREME | 2025_H1 | 0 | +0.00 | — | — | 0.00 |
| H4_FAILED_EXTENSION | 2021 | 0 | +0.00 | — | — | 0.00 |
| H4_FAILED_EXTENSION | 2022 | 0 | +0.00 | — | — | 0.00 |
| H4_FAILED_EXTENSION | 2023 | 0 | +0.00 | — | — | 0.00 |
| H4_FAILED_EXTENSION | 2024 | 0 | +0.00 | — | — | 0.00 |
| H4_FAILED_EXTENSION | 2025_H1 | 0 | +0.00 | — | — | 0.00 |
| H4_7D_PIVOT_SWEEP_RECLAIM | 2021 | 0 | +0.00 | — | — | 0.00 |
| H4_7D_PIVOT_SWEEP_RECLAIM | 2022 | 0 | +0.00 | — | — | 0.00 |
| H4_7D_PIVOT_SWEEP_RECLAIM | 2023 | 0 | +0.00 | — | — | 0.00 |
| H4_7D_PIVOT_SWEEP_RECLAIM | 2024 | 0 | +0.00 | — | — | 0.00 |
| H4_7D_PIVOT_SWEEP_RECLAIM | 2025_H1 | 0 | +0.00 | — | — | 0.00 |

## Status
- LAB016 is discovery-only; even a promising H4 family needs its own frozen replication LAB.
- 2025H2/2026 are reused research windows, not fresh holdouts.
- August 2026 is consumed/reused audit only.
- No live allocation is authorized.
