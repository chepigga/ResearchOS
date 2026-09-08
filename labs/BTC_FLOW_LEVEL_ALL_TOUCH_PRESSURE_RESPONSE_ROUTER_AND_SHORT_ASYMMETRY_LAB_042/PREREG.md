# BTC_FLOW_LEVEL_ALL_TOUCH_PRESSURE_RESPONSE_ROUTER_AND_SHORT_ASYMMETRY_LAB_042

## Purpose
Formalize and test the four-state causal pressure/response router discovered in LAB041 on the exact frozen all-touch stream, with a preregistered SHORT asymmetry branch.

## Frozen lineage
Source: `BTC_FLOW_LEVEL_ALL_TOUCH_DIRECTIONAL_LIQUIDITY_ELASTICITY_WITHOUT_HIGH_VOLUME_GATE_LAB_041/output/all_touch_elasticity_stream.csv` from persisted LAB041 head.

Frozen fields used without recomputation or retuning:
- FLOW direction (`side`)
- level/touch/acceptance lineage
- `book_state` generated causally in LAB041 from strictly-prior 90d all-touch thresholds
- `residual_atr` after the frozen classification clock

States are frozen exactly:
- `DRIVEN_MOVE` = high pressure + high directional response
- `ABSORPTION` = high pressure + low directional response
- `THIN_BOOK` = low pressure + high directional response
- `WEAK` = low pressure + low directional response

No HIGH_VOLUME gate. No new threshold, feature, entry, stop, target, or horizon search.

## Selection clock / inference
- Primary inference: `signal_time < 2026-08-01`.
- August 2026 is audit-only and may not affect verdict thresholds.
- Only resolved LAB041 states are used for router inference.

## Primary hypothesis A — router separation
`DRIVEN_MOVE` should have better post-classification residual economics than `ABSORPTION`.
Report:
- N, ACCEPT rate, residual mean, hit rate
- gap `DRIVEN_MOVE - ABSORPTION`
- 7-day cluster bootstrap, 5000 draws, seed 20260908
Expected primary residual gap >= +0.40 ATR and bootstrap lower bound > 0 for PASS-quality evidence.

## Primary hypothesis B — SHORT router branch
Within SHORT only, `DRIVEN_MOVE` should beat `ABSORPTION` and remain positive.
Report same metrics and 7-day cluster bootstrap.
Expected SHORT residual gap >= +0.50 ATR, both cohorts N>=80, lower CI >0 for PASS-quality evidence.

## Preregistered asymmetry audit
For each frozen state compare SHORT vs LONG residual means and cluster bootstrap:
- DRIVEN_MOVE: SHORT - LONG
- ABSORPTION: SHORT - LONG
- THIN_BOOK: SHORT - LONG
- WEAK: SHORT - LONG

The asymmetry hypothesis is specifically:
- SHORT `THIN_BOOK` > LONG `THIN_BOOK`, based on the repeatedly observed historical bearish branch;
- SHORT `DRIVEN_MOVE` should be positive and should not be materially worse than LONG `DRIVEN_MOVE`.
These are diagnostic/mechanism tests, not promoted execution rules.

## Transfer
Report DRIVEN_MOVE and ABSORPTION separately for:
- 2021
- 2022
- 2023
- 2024
- 2025H1
- 2025H2
- 2026 Jan-Jul
- pooled recent 2025H2+2026
- LONG / SHORT
- fixed stress slice 2022 SHORT
- August 2026 audit-only

Also report a simple frozen router policy for research only:
- `ALLOW` = DRIVEN_MOVE
- `VETO` = ABSORPTION
- THIN_BOOK / WEAK = neutral / no routing decision
No trading execution PnL is constructed; report only event residuals and event frequency.

## Bootstrap
7-day event clusters:
`cluster = floor((signal_time - 1970-01-01 UTC)/(7d))`.
Resample clusters with replacement, 5000 draws, seed 20260908.
No iid-event bootstrap.

## Gates (24)
1. resolved pre-Aug rows >=1900
2. DRIVEN_MOVE N>=650
3. ABSORPTION N>=250
4. DRIVEN residual positive
5. ABSORPTION residual <=0
6. all-router residual gap >=+0.40 ATR
7. all-router bootstrap CI lower >0
8. DRIVEN ACCEPT rate >= ABSORPTION ACCEPT rate
9. DRIVEN frequency >=8/month
10. SHORT DRIVEN N>=250
11. SHORT ABSORPTION N>=100
12. SHORT DRIVEN residual positive
13. SHORT ABSORPTION residual <=0
14. SHORT gap >=+0.50 ATR
15. SHORT bootstrap CI lower >0
16. SHORT THIN residual > LONG THIN residual
17. SHORT THIN N>=100 and positive
18. LONG THIN N>=100
19. LONG DRIVEN positive
20. SHORT DRIVEN positive
21. pooled recent DRIVEN positive N>=150
22. both 2025H2 and 2026 DRIVEN positive
23. 2022 SHORT DRIVEN positive N>=30
24. August not used for selection

Verdict:
- PASS if >=19/24 and gates 4,6,7,12,14,15,20,21,22 pass.
- WATCH if >=13/24 or both all-router and SHORT gaps are directionally positive but proof/transfer is incomplete.
- otherwise FAIL.

## Guardrail
This is a mechanism/router LAB on reused historical lineage. A positive result is not fresh OOS and does not justify live allocation. Live allocation = 0.
