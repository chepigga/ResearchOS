# ADR-FT-REJECTED-001 — CONFIRMS-REGIME

**Date:** 2026-07-25  
**Status:** ACCEPTED  
**Scope:** Research decision only; no EA patch

## Decision

`FT_REJECTED_001` returns **CONFIRMS-REGIME** under the frozen rules.

The rejected 2023 population has `N=268` and `EV=-0.031983R`. The ACCEPT 2023 population has `N=22` and `EV=-0.439417R`. The broad rejected population is negative in the EARLY half and positive in the LATE half.

Therefore the weak early period is not explained primarily by the quality gates or by the small executed sample.

## Consequences

1. Keep all current FT gates unchanged.
2. Do not scale FT as an always-on stationary edge.
3. Record gate-loosening candidates for separate preregistered OOS work only.
4. Preserve `SL_TOO_TIGHT_USD`; its full-period EV is `-0.150530R` on `N=508`.
5. No threshold optimization is permitted on the inspected 2023–2026 data.

## Registered candidates

- `ALL/FAR_FROM_SWING_HIGH`: N=245, EV `+0.164429R`.
- `ALL/SCORE_BLOCK`: N=318, EV `+0.208001R`.
- `LONBUY/FAR_FROM_SWING_HIGH`: N=91, EV `+0.307528R`.
- `NYBUY/SCORE_BLOCK`: N=297, EV `+0.202525R`.

No candidate is approved for implementation.