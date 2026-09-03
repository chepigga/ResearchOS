# BTC_REVERSAL_LIMIT_RETEST_YEARLY_STABILITY_AND_FRESH_AUG2026_REPLICATION_LAB_007

**Verdict:** **FAIL_YEARLY_STABILITY**

Role: frozen LAB006 yearly stability + one-shot fresh August 2026 replication; not a live strategy.

## Frozen setup
- Exact LAB006 selector + `LIMIT_R0.50_T60` + SL 1.0× event M15 range + TP 1.5R.
- Same-bar ambiguity = SL-first; no market fallback.
- Primary cost stress = 5 bps round trip.
- Frozen router q80: **0.324358**.

## Data integrity
- Historical monthly files through 2026-07: **67**.
- Fresh daily files loaded: **32** (2026-08-01…2026-09-01; Sep 1 is outcome support only).
- Combined completed-bar coverage: **2021-01-01 00:00:00+00:00 → 2026-09-01 23:45:00+00:00**.
- August 2026 is consumed once here as the fresh holdout.

## Primary RR1.5 / 5bps by year

| Bucket | Selected REV | Filled | Fill | TP | SL | TIME | Net EV R | PF | Cum R | Max DD R | Max consec L | 0.5% eq return | 0.5% max DD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2021 | 47 | 27 | 57.4% | 55.6% | 44.4% | 0.0% | +0.337 | 1.728 | +9.09 | 3.19 | 3 | +4.59% | 1.59% |
| 2022 | 33 | 20 | 60.6% | 35.0% | 60.0% | 5.0% | -0.139 | 0.781 | -2.79 | 5.87 | 3 | -1.42% | 2.92% |
| 2023 | 9 | 6 | 66.7% | 33.3% | 33.3% | 33.3% | +0.262 | 1.698 | +1.57 | 2.25 | 2 | +0.78% | 1.12% |
| 2024 | 33 | 24 | 72.7% | 33.3% | 66.7% | 0.0% | -0.236 | 0.671 | -5.66 | 9.48 | 5 | -2.83% | 4.66% |
| 2025 | 27 | 18 | 66.7% | 55.6% | 44.4% | 0.0% | +0.276 | 1.556 | +4.96 | 4.06 | 3 | +2.47% | 2.02% |
| 2026_JAN_JUL | 22 | 15 | 68.2% | 60.0% | 40.0% | 0.0% | +0.412 | 1.929 | +6.17 | 2.28 | 2 | +3.10% | 1.14% |
| FRESH_AUG2026 | 0 | 0 | 0.0% | — | — | — | — | — | — | — | — | — | — |

## RR2.0 audit / 5bps

| Bucket | Filled | Net EV R | PF | Cum R |
|---|---:|---:|---:|---:|
| 2021 | 27 | +0.170 | 1.276 | +4.59 |
| 2022 | 20 | +0.036 | 1.056 | +0.71 |
| 2023 | 6 | +0.428 | 2.143 | +2.57 |
| 2024 | 24 | -0.194 | 0.745 | -4.66 |
| 2025 | 18 | +0.423 | 1.816 | +7.61 |
| 2026_JAN_JUL | 15 | +0.512 | 1.988 | +7.67 |
| FRESH_AUG2026 | 0 | — | — | — |

## Gates
- FAIL — `dev_positive_years_ge_3_of_4`
- PASS — `year_2025_positive`
- PASS — `y2026_jan_jul_positive`
- PASS — `recent_pf_gt_1`
- PASS — `recent_closed_dd_050_lt_5pct`
- FAIL — `fresh_selected_rev_ge_3`
- FAIL — `fresh_filled_ge_3`
- FAIL — `fresh_net_ev_positive`
- FAIL — `fresh_pf_gt_1`
- FAIL — `fresh_closed_dd_050_lt_5pct`

**Score 4/10 → FAIL_YEARLY_STABILITY**

## Interpretation rules
- If fresh selected or filled N < 3, August sign is descriptive only and cannot promote.
- RR2.0 remains audit-only regardless of its result.
- August 2026 is no longer fresh for any later hypothesis generated after this report.
