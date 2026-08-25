# STRUCT_BREAK_LOW_RESET_X_SECOND_BREAK_LAB_013

**Date:** 2026-08-25  
**Status:** COMPLETED  
**Preregistration commit:** `5ac4bb01da40b44b23097738eb58ced966756d9f`  
**Formal verdict:** `SECOND_BREAK_NEAR_BREAKEVEN__INDEPENDENT_EDGE_NOT_VALIDATED`

## Hypothesis
Test `BREAK1 -> ENTRY1 -> LOW30 -> RECOVERY/SCRATCH -> RESET -> NEW STRUCTURE -> BREAK2 -> RETEST -> ENTRY2`, where BREAK2 is built only from post-RESET pivots that did not exist before RESET.

## Frozen M5 geometry
- causal pivot 3-3;
- BUY: new pivot high -> subsequent new pivot low -> close above the high by >=0.10 ATR14(M5); SELL symmetric;
- first valid BREAK2 only;
- retest within 12 M5 bars;
- limit entry on broken level;
- stop at new post-reset pullback pivot;
- stop 0.30–6.0 ATR;
- TP 1.5R primary, 2.0R secondary;
- cost 0.06R, 24h hold, adverse same-bar ordering;
- DEV 2019–2022, VAL 2023–2025, 2026 excluded.

## Funnel
Eligible reset events: DEV 151, VAL 151.
VAL: 82 entry2, 43 no_break2, 24 no_retest, 2 riskATR outside.
Median VAL RESET->BREAK2 115 min; BREAK2->retest 5 min; stop 2.23 ATR.

## Primary 1.5R
| Split | N | EV | 95% CI | TP rate | PF |
|---|---:|---:|---:|---:|---:|
| DEV | 93 | +0.042R | [-0.200,+0.284] | 44.1% | 1.07 |
| VAL | 82 | **+0.007R** | [-0.267,+0.281] | **42.7%** | 1.01 |

Cost-adjusted fair hazard is ~42.4%; VAL actual is 42.68%, only +0.28pp over fair.

VAL years: 2023 -0.167R; 2024 +0.107R; 2025 +0.086R. 2/3 years positive, but effect-size and CI gates fail.

## Same-event comparator
On the same 82 VAL setups that generate BREAK2:
- SECOND_BREAK EV +0.007R
- corresponding FIRST_ENTRY, evaluated as simple 1.5R/-1R, EV +0.087R
- paired difference -0.080R, CI [-0.383,+0.225]

Unconditional VAL first breaks at 1.5R are -0.060R, so comparing BREAK2 to all first breaks is misleading: the BREAK2-capable subset was already better than average at the first entry.

## Key diagnostic
VAL BREAK2 outcomes conditioned on the future canonical fate of BREAK1:
- original TP +2.3R: N20, BREAK2 TP 80%, EV +0.940R
- original SL: N36, BREAK2 TP 22.2%, EV -0.504R
- BE/other: N26, EV ~0

So BREAK2 often re-discovers the same underlying directional path rather than independently repairing a bad BREAK1.

Explicit recovered-only VAL path (`LOW -> RECOVERY -> RESET -> BREAK2`): N77, EV -0.021R, TP 41.6%.

## M15 replication
VAL N69, EV -0.136R, TP 34.8%, PF 0.79. No cross-timeframe robustness.

## M1 execution check
2024 N30 EV +0.107R and 2025 N24 EV +0.086R with 100% M5/M1 outcome agreement.

## Full policy
`canonical entry -> LOW -> scratch -> BREAK2 fresh trade`

VAL:
- canonical: EV -0.0315R, DD 38.78R
- scratch-only: EV -0.0395R, DD 49.09R
- scratch + BREAK2: EV -0.0386R, DD 43.62R

Adaptive minus canonical: -0.0071R/trade, bootstrap CI [-0.0537,+0.0392].

## Interpretation
A genuinely new structural break is far better than blind re-entry after renewed impulse:
- LAB010 ~-0.096R
- LAB011 ~-0.161R
- LAB013 +0.007R

Rebuilding structure almost removes the negative re-entry bias, but does not establish a robust independent edge.

# Verdict
`SECOND_BREAK_NEAR_BREAKEVEN__INDEPENDENT_EDGE_NOT_VALIDATED`

Supported: after LOW/recovery, do not blindly re-enter; require genuinely new structure before even considering another trade.

Not supported: take every valid BREAK2 after reset as a fresh 1.5R trade.
