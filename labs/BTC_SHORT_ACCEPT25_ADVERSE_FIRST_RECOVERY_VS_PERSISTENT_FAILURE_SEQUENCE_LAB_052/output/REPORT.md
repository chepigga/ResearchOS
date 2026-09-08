# BTC_SHORT_ACCEPT25_ADVERSE_FIRST_RECOVERY_VS_PERSISTENT_FAILURE_SEQUENCE_LAB_052

**Verdict: PASS_ADVERSE_RECOVERY_VS_PERSISTENT_FAILURE_SEQUENCE — 14/15**

## Frozen parity
- LAB051 ADVERSE_FIRST cohort: **145**; M15 path coverage: **100.0%**

## Primary adverse-first sequence

| State | N | Share | Residual EV | Frozen parent EV | Median min after adverse | Severe +1R share |
|---|---:|---:|---:|---:|---:|---:|
| RECOVERED_FIRST | 31 | 21.4% | +0.372 | +0.597 | 15 | 0.0% |
| PERSISTENT_FAILURE_FIRST | 59 | 40.7% | -0.084 | -0.638 | 30 | 0.0% |
| UNRESOLVED | 55 | 37.9% | — | -0.910 | — | 61.8% |

RECOVERED−PERSISTENT residual gap: **+0.456R**, 7d bootstrap 95% CI **[+0.063, +0.833]**, clusters=79
RECOVERED residual **+0.372R**; PERSISTENT residual **-0.084R**

## Frozen transfer

| Slice | N | Resolved | Recovered N | Persistent N | Rec residual | Persist residual | Gap | Boot 95% CI |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| 2021 | 22 | 14 | 7 | 7 | +0.683 | -0.313 | +0.996 | [+0.114, +1.636] |
| 2022 | 24 | 16 | 4 | 12 | +0.006 | -0.259 | +0.266 | [-0.746, +1.365] |
| 2023 | 21 | 12 | 4 | 8 | +0.365 | +0.112 | +0.252 | [-1.057, +1.489] |
| 2024 | 33 | 21 | 5 | 16 | -0.208 | -0.003 | -0.205 | [-1.010, +0.452] |
| 2025_H1 | 15 | 7 | 3 | 4 | -0.032 | -0.483 | +0.451 | [-0.844, +1.335] |
| 2025_H2 | 11 | 6 | 2 | 4 | +1.335 | -0.694 | +2.029 | [+1.861, +2.205] |
| 2026_JAN_JUL | 19 | 14 | 6 | 8 | +0.623 | +0.525 | +0.098 | [-0.732, +1.008] |
| BAD_POOLED | 39 | 23 | 7 | 16 | -0.010 | -0.315 | +0.305 | [-0.451, +1.041] |
| RECENT_POOLED | 30 | 20 | 8 | 12 | +0.801 | +0.119 | +0.682 | [-0.090, +1.449] |

## Severe-adverse diagnostic
- +1.0R adverse after ADVERSE_FIRST before sequence/end: ALL **23.4%**, RECOVERED **0.0%**, PERSISTENT **0.0%**

## Gates
- PASS — `exact_lab051_adverse_first_n145`
- PASS — `path_coverage_ge99pct`
- PASS — `sequence_resolved_n_ge60`
- PASS — `recovered_first_n_ge20`
- PASS — `persistent_failure_first_n_ge20`
- PASS — `recovered_residual_positive`
- PASS — `persistent_residual_negative`
- PASS — `residual_gap_ge0_30r`
- PASS — `residual_gap_boot_lower_gt0`
- PASS — `persistent_parent_ev_lt_recovered_parent_ev`
- PASS — `bad_pooled_persistent_residual_negative`
- PASS — `bad_pooled_residual_gap_positive`
- PASS — `recent_pooled_recovered_residual_positive`
- FAIL — `recent_pooled_persistent_residual_nonpositive`
- PASS — `august_not_used_for_selection`

## Guardrail
Sequence mechanism audit only. No early exit, breakeven, stop tightening, trailing, re-entry, allocation, or new threshold is promoted. Reused historical lineage; not fresh OOS. Live allocation = **0**.
