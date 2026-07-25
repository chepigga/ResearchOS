# ADR-FT-DEEP-001 — Tester evidence classifies FT core as REGIME

**Date:** 2026-07-25  
**Status:** ACCEPTED FOR TESTER EVIDENCE / FORMAL RAW-BAR ORACLE PENDING

## Context

`TZ-FT-DEEP-001` asks whether NYBUY + LONBUY is a persistent edge or a regime-dependent trend bet. Step 0 required parity against tester v1.56 before any long-run interpretation.

## Evidence

Step 0 passed:

- NYBUY: oracle N=18 versus tester-executed N=17; 15 matches within one M5 bar; overlap 83.33% versus oracle and 88.24% versus tester.
- LONBUY: oracle N=7 versus tester-executed N=7; 7/7 matches.

Direct tester evidence for 2023-01-01..2026-07-23:

- N=135;
- EV execution-net `+1.123733R`;
- sum `+151.704R`;
- PF `2.761`;
- early chronological half EV `-0.007685R`;
- late chronological half EV `+1.878012R`;
- 2023 negative, 2024–2026 positive.

## Decision

Under the frozen verdict rule, the direct tester result is **REGIME**, because one chronological half is non-positive while the other carries essentially all profit.

Consequences:

1. Do not scale FT as an always-on stationary edge.
2. Do not tune entry parameters on the inspected data.
3. Preserve the frozen engine for the final raw-bar oracle.
4. If the final oracle confirms REGIME, the next research line is a preregistered regime classifier, not unconditional risk increase.

## Limitation

This is tester evidence with live/portfolio gates included. The formal raw-bar oracle remains pending because the supplied M5 file begins in 2025. Final GO/REGIME/NO-GO registration requires the Strategy Tester stream export covering 2022-06..2026-07.
