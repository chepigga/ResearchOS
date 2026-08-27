# BTC_M15_CONTEXT_M5_MULTI_EVENT_EXPANSION_LAB_031 — RESULT

Date: 2026-08-27

Preregistration: `9040a3898ab1732ff94d88f074909154bfe68fcd`
Operationalization: `4a2aa06d7e1a51263ceff554b7c82443d729ce49`

Formal verdict: `ALL_M5_EVENT_FAMILIES_REJECTED`

## 2025 M5 family results
- MICRO_BREAK_RETEST: N44, EV +0.149464R, PF 1.3239, DD 10.2236R, 1.5x-cost EV +0.119464R, overlap with BASE3 79.55%. Fails independence gate.
- COMPRESSION_RELEASE: N39, EV +0.016923R, PF 1.0304, DD 9.54R, 1.5x-cost EV -0.013077R. Rejected.
- FAILED_RESPONSE_RECLAIM: N38, EV -0.110R, PF 0.7895, DD 5.36R. Rejected.

No family passed all frozen gates, therefore none was admitted into the portfolio expansion router.

## Existing BASE3 reference
2024–2025:
- N107
- 53.5 trades/year
- EV +0.223178R
- PF 1.5241
- MaxDD 5.30R
- 75% profitable months
- Recovery 4.506
- worst rolling 3M -1.06R
- 1.5x-cost EV +0.193178R

2026 shadow:
- EV +0.34R
- PF 1.97
- DD 2.24R

## Interpretation
The strongest M5 family, MICRO_BREAK_RETEST, preserves positive economics but mostly fires in the same temporal neighborhoods as the existing M15 router. Therefore M5 execution events inside the same M15 contexts do not solve the 150–300 trades/year objective. To increase frequency without destroying smoothness, the next search should target additional independent M15 context/regime families rather than denser M5 triggering inside existing contexts.
