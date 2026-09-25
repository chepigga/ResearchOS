# GC_XAU LAB019 — BROAD_LEG_SIDE_HTF_TREND_INTERACTION — FINAL

Date: 2026-09-25

## Status
- Registry parity: PASS (materially)
- HTF interaction discovery: PASS as information/signal effect
- Execution promotion: FAIL under inherited LAB018 cost/execution geometry
- Production / Broad Demo changes: NONE
- Q65 changes: NONE

## Inputs
- Exact Broad causal universe inherited from LAB018.
- 111,172 compact event clocks match the canonical registry exactly before XAU pricing.
- Primary labels: BASE1 / DOM2 / DOM_CONT / MIX2 / MIXED / REV1 / REV2.
- REV3P excluded from primary.
- XAU source: Massive C:XAUUSD M1 quote aggregates.
- Conservative causal HTF cutoff frozen before outcomes: latest H1/H4 bar with close strictly before the entry minute.
- H1/H4 trend: completed close vs EMA20 plus EMA20 3-bar slope.
- BOTH = H1 and H4 both aligned with signal side.

## XAU replay parity
Current-source priced primary events: 109,326.
Canonical LAB018 priced count was about 109,399.
Difference: 73 events (~0.067%), not material to the interaction conclusion.

TRAIN raw leg replay is effectively at LAB018 parity:
- BASE1 EV5 -0.03705 ATR
- DOM2 -0.07150
- DOM_CONT -0.11158
- MIX2 -0.05062
- MIXED -0.05102
- REV1 -0.00426
- REV2 -0.10012

## Primary finding
The only leg × side × BOTH family with positive raw +5m EV and PF > 1 in TRAIN, VALID and POST, while also showing positive BOTH-vs-NOT_BOTH uplift in all three splits, is:

### MIX2 × BUY × H1&H4 BOTH

| Split | N | Raw EV5 ATR | PF5 | NOT_BOTH EV5 | BOTH uplift | Gross exec EVR | Net-0.2 EVR |
|---|---:|---:|---:|---:|---:|---:|---:|
| TRAIN | 1,886 | +0.05386 | 1.0877 | -0.06329 | +0.11715 | -0.00152 | -0.15101 |
| VALID | 751 | +0.06703 | 1.1072 | -0.08303 | +0.15006 | +0.03573 | -0.02449 |
| POST | 411 | +0.03956 | 1.0658 | -0.01467 | +0.05423 | +0.00928 | -0.06485 |

Combined N = 3,048.
Weighted raw EV5 ≈ +0.05518 ATR.
Weighted gross execution EV ≈ +0.00912R.
Weighted net execution EV under inherited commission + fixed spread 0.2 ≈ -0.10822R.

Interpretation:
- H1/H4 alignment is carrying real information for MIX2 BUY.
- The raw edge is stable across chronological splits.
- The inherited 5-minute market-entry execution/cost model consumes the edge.
- Therefore this is a signal/sensor edge, not a production-ready trade rule.

## Window consistency for MIX2 BUY BOTH
Raw EV5 is positive in 8 of 9 quality windows.
The only negative window is W2.

Known/inferred window raw EV5:
- W1 +0.07230
- W2 -0.08311
- W3 +0.01627
- W4 +0.15553
- W5 +0.11366
- W6 +0.04125
- W7 +0.14104
- W8 +0.04305
- W9 +0.03749

BOTH-vs-NOT_BOTH uplift is also positive in 8/9 windows; W2 is the only sign failure.

## Other interaction notes
- DOM2 BUY BOTH improves TRAIN and VALID raw response but loses sign in POST.
- DOM_CONT BUY BOTH is negative in TRAIN, so it is not a stable family.
- REV2 cells are small and side-unstable; they must not be promoted from isolated VALID/POST spikes.
- Several H4_ONLY/H1_ONLY cells look locally attractive in one split but fail chronological sign stability.

## Decision
LAB019 does NOT authorize changing Broad Demo or production routing.

Freeze the new research fact:
MIX2 BUY + causal H1/H4 BOTH alignment is a replicated raw information edge across TRAIN/VALID/POST and 8/9 windows, but the current LAB018 execution geometry is not net-profitable.

## Next research
Next logical experiment: execution transfer on the frozen MIX2 BUY BOTH signal only.
Do not retune leg, side, EMA length, trend slope, or HTF alignment while testing execution.

Before any broker-specific execution optimization or EA change, lock the intended XAU broker/prop specification (spread, commission, stops/freeze, leverage, EA/news rules, VPS/latency/slippage).
