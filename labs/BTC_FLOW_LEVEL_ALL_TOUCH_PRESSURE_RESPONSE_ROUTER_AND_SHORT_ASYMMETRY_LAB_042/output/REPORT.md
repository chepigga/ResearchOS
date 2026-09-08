# BTC_FLOW_LEVEL_ALL_TOUCH_PRESSURE_RESPONSE_ROUTER_AND_SHORT_ASYMMETRY_LAB_042

**Verdict: WATCH_ROUTER_POSITIVE_SHORT_ASYMMETRY_PROOF_INCOMPLETE — 21/24**

## Frozen router
- resolved pre-Aug: **1926**; DRIVEN frequency **10.61/month**

| State | N | ACCEPT | Residual | Hit | L/S |
|---|---:|---:|---:|---:|---:|
| ABSORPTION | 272 | 0.632 | -0.092 | 0.430 | 119/153 |
| DRIVEN_MOVE | 700 | 0.689 | +0.567 | 0.517 | 333/367 |
| THIN_BOOK | 264 | 0.720 | +0.382 | 0.458 | 156/108 |
| WEAK | 690 | 0.716 | +0.154 | 0.475 | 355/335 |

## Primary router separation
- ALL DRIVEN−ABSORPTION: **+0.659 ATR**, 95% CI **[-0.182, +1.486]**
- SHORT DRIVEN−ABSORPTION: **+0.952 ATR**, 95% CI **[-0.165, +2.078]**

## By side

| State | Side | N | ACCEPT | Residual | Hit |
|---|---:|---:|---:|---:|---:|
| ABSORPTION | SHORT | 153 | 0.595 | -0.302 | 0.425 |
| ABSORPTION | LONG | 119 | 0.681 | +0.178 | 0.437 |
| DRIVEN_MOVE | SHORT | 367 | 0.687 | +0.650 | 0.523 |
| DRIVEN_MOVE | LONG | 333 | 0.691 | +0.475 | 0.511 |
| THIN_BOOK | SHORT | 108 | 0.731 | +1.303 | 0.528 |
| THIN_BOOK | LONG | 156 | 0.712 | -0.256 | 0.410 |
| WEAK | SHORT | 335 | 0.693 | -0.147 | 0.469 |
| WEAK | LONG | 355 | 0.738 | +0.437 | 0.482 |

## SHORT−LONG bootstrap by state

| State | Gap | 95% CI |
|---|---:|---:|
| DRIVEN_MOVE | +0.175 | [-0.694, +0.976] |
| ABSORPTION | -0.480 | [-1.953, +0.884] |
| THIN_BOOK | +1.560 | [+0.138, +3.011] |
| WEAK | -0.584 | [-1.403, +0.188] |

## DRIVEN / ABSORPTION transfer

| State | Slice | N | ACCEPT | Residual | Hit | L/S |
|---|---|---:|---:|---:|---:|---:|
| DRIVEN_MOVE | 2021 | 120 | 0.742 | +0.842 | 0.550 | 52/68 |
| DRIVEN_MOVE | 2022 | 126 | 0.690 | +0.348 | 0.492 | 64/62 |
| DRIVEN_MOVE | 2023 | 127 | 0.606 | +0.855 | 0.496 | 65/62 |
| DRIVEN_MOVE | 2024 | 146 | 0.678 | +0.374 | 0.527 | 70/76 |
| DRIVEN_MOVE | 2025_H1 | 56 | 0.732 | +0.477 | 0.536 | 21/35 |
| DRIVEN_MOVE | 2025_H2 | 55 | 0.727 | +0.428 | 0.491 | 27/28 |
| DRIVEN_MOVE | 2026_JAN_JUL | 70 | 0.700 | +0.550 | 0.529 | 34/36 |
| DRIVEN_MOVE | POOLED_RECENT | 125 | 0.712 | +0.496 | 0.512 | 61/64 |
| DRIVEN_MOVE | AUG_REUSED | 1 | 0.000 | -3.173 | 0.000 | 0/1 |
| DRIVEN_MOVE | LONG | 333 | 0.691 | +0.475 | 0.511 | 333/0 |
| DRIVEN_MOVE | SHORT | 367 | 0.687 | +0.650 | 0.523 | 0/367 |
| DRIVEN_MOVE | 2022_SHORT | 62 | 0.677 | +0.428 | 0.484 | 0/62 |
| ABSORPTION | 2021 | 39 | 0.590 | -0.619 | 0.410 | 14/25 |
| ABSORPTION | 2022 | 41 | 0.683 | +0.477 | 0.463 | 18/23 |
| ABSORPTION | 2023 | 43 | 0.535 | -0.607 | 0.326 | 23/20 |
| ABSORPTION | 2024 | 48 | 0.667 | +1.451 | 0.479 | 19/29 |
| ABSORPTION | 2025_H1 | 29 | 0.690 | -0.315 | 0.379 | 14/15 |
| ABSORPTION | 2025_H2 | 32 | 0.531 | -1.152 | 0.469 | 14/18 |
| ABSORPTION | 2026_JAN_JUL | 40 | 0.725 | -0.449 | 0.475 | 17/23 |
| ABSORPTION | POOLED_RECENT | 72 | 0.639 | -0.762 | 0.472 | 31/41 |
| ABSORPTION | AUG_REUSED | 0 | — | — | — | 0/0 |
| ABSORPTION | LONG | 119 | 0.681 | +0.178 | 0.437 | 119/0 |
| ABSORPTION | SHORT | 153 | 0.595 | -0.302 | 0.425 | 0/153 |
| ABSORPTION | 2022_SHORT | 23 | 0.609 | -0.037 | 0.391 | 0/23 |

## Gates
- PASS — `resolved_preaug_ge_1900`
- PASS — `driven_n_ge_650`
- PASS — `absorption_n_ge_250`
- PASS — `driven_residual_positive`
- PASS — `absorption_residual_le_zero`
- PASS — `all_gap_ge_0_40`
- FAIL — `all_boot_ci_lower_gt_zero`
- PASS — `driven_accept_ge_absorption`
- PASS — `driven_frequency_ge_8_month`
- PASS — `short_driven_n_ge_250`
- PASS — `short_absorption_n_ge_100`
- PASS — `short_driven_positive`
- PASS — `short_absorption_le_zero`
- PASS — `short_gap_ge_0_50`
- FAIL — `short_boot_ci_lower_gt_zero`
- PASS — `short_thin_gt_long_thin`
- PASS — `short_thin_n100_positive`
- PASS — `long_thin_n100`
- PASS — `long_driven_positive`
- PASS — `short_driven_positive_dup`
- FAIL — `pooled_recent_driven_positive_n150`
- PASS — `both_2025h2_2026_driven_positive`
- PASS — `2022_short_driven_positive_n30`
- PASS — `august_not_used`

## Guardrail
Frozen LAB041 causal router states; no new thresholds/features/execution optimization. Reused historical lineage, not fresh OOS. August audit-only. Live allocation = **0**.
