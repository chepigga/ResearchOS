# XAU_CONTEXT_REVERSAL_COMPETITION_AND_TRANSITION_OVERLAY_LAB_011

**Verdict: TRANSITION_OVERLAY_ARCHITECTURE_NOT_SUPPORTED**

> Persistent-state + transition-overlay diagnostic only. No trading edge or execution claim.

- Valid Context H4 bars: **6,216**
- Frozen episodes: **610**
- R3 raw-reversal events: **204**
- Suppressed R3 overlay events: **200**
- G1 compression bars inside Pullback/Expansion: **789**

## Primary gates

| Gate | Eligible | Effect | 95% CI | Transfer | Pass |
|---|---|---:|---:|---|---|
| R-H1 suppressed reversal overlay | YES | +0.0292 | [-0.0576, +0.1185] | PASS | FAIL |
| R-H2 cross-main-state robustness | YES | — | — | — | PASS |
| C_H1 breakout_1atr_8h | NO | +0.0970 | [+0.0516, +0.1431] | PASS | FAIL |
| C_H2 range_atr_24h | NO | +0.2556 | [+0.0713, +0.4546] | PASS | FAIL |

## Reversal competition

| Class | Events |
|---|---:|
| SMOOTHING_SUPPRESSED | 188 |
| HYSTERESIS_SUPPRESSED | 12 |
| ADMITTED_REVERSAL | 4 |

## Reversal overlay by main state

| State | N overlay | N control | 24h flip premium |
|---|---:|---:|---:|
| PULLBACK | 52 | 2696 | +0.0118 |
| EXPANSION | 77 | 950 | +0.0511 |
| RANGE | 15 | 480 | -0.0229 |

## Interpretation constraints

- R3 and G1 were frozen before outcomes; LAB011 does not search new thresholds.
- Primary comparisons are state-stratified: an overlay must add information beyond the persistent main state.
- Suppressed reversal events are precisely the events a parallel overlay could show while the main state remains unchanged.
- Reused history: even a pass remains discovery-only and cannot authorize automated entries or risk changes.