# CONTEXT_REVERSAL_SEMANTIC_DEFINITION_AND_COMPETING_MODE_BOUNDARY_AUDIT_LAB_015

## Goal
Audit the *semantic definition* of frozen LAB010 Reversal without changing any Context score weights, hysteresis, smoothing, or state-machine constants.

## Frozen parent
- Parent Context: LAB010 exact implementation.
- Expected state counts: PULLBACK=7641, EXPANSION=4568, RANGE=2184, REVERSAL=29.
- Frozen actual Reversal transitions: expected 9.
- Data: Binance BTCUSDT H1 2020-01 through 2026-07, H4 Context.

## Question
Does frozen Reversal behave like an event-driven reversal state, or is it better understood as a *boundary / directional-control-change* state relative to the competing modes?

## No tuning
No score weights, thresholds, smoothing, hysteresis, min-hold, gap, or timeouts may be changed after outcomes are known.

## Audits
For every transition destination (REVERSAL, PULLBACK, EXPANSION, RANGE), characterize bars t-2, t-1, t0 using frozen features and frozen smoothed scores.

### Feature families
1. Event reversal features: swing_sweep, rejection_wick, RSI turn, RSI rhythm turn, EMA20 cross, ADX decay.
2. Direction-control features: EMA stack state, D1 bias, BOS direction vs D1 bias, close vs EMA20/50, EMA20/50 ordering, EMA50 slope sign.
3. Competition features: smoothed score margins REV-PULLBACK, REV-EXPANSION, REV-RANGE; rank of REVERSAL; incumbent previous regime.
4. Volatility/structure: ATR ratio, ADX14, range24 ratio, EMA spread/ATR, relative volume.

## Matched boundary controls
For each actual REVERSAL transition at t0:
- identify same-year, same volatility-state non-REVERSAL transitions;
- additionally identify nearest-score-boundary bars where Reversal rank <=2 but Current Context != REVERSAL.
No outcome/PnL is used.

## Primary semantic tests
A. `EVENT_ENRICHMENT`: median number of active event-reversal features at t0 for REVERSAL transitions exceeds matched non-REVERSAL transitions by >=1.
B. `CONTROL_CHANGE_ENRICHMENT`: share of REVERSAL transitions showing either D1-bias conflict, EMA stack break/change, or BOS against prior directional control exceeds matched controls by >=20 percentage points.
C. `BOUNDARY_MARGIN`: absolute winning margin of REVERSAL over best competitor at t0 is smaller than median winning margin of PULLBACK/EXPANSION/RANGE transitions, consistent with a boundary state.
D. `INCUMBENT_PATTERN`: at least 70% of REVERSAL transitions originate from directional modes (PULLBACK or EXPANSION), not RANGE.
E. `NEAR_MISS_SIMILARITY`: Reversal rank<=2 non-Reversal near-miss bars share the semantic pattern with actual Reversal transitions; report standardized feature-distance, no tuning.

## Classification
- `EVENT_REVERSAL_SEMANTICS_SUPPORTED` if A passes and B fails.
- `CONTROL_CHANGE_BOUNDARY_SEMANTICS_SUPPORTED` if B+C+D pass and A is not uniquely dominant.
- `MIXED_REVERSAL_SEMANTICS` if both A and B pass but C/D do not jointly resolve the definition.
- `REVERSAL_SEMANTICS_UNRESOLVED` otherwise.

## Technical gates
- Parent state parity exact.
- Reversal score reconstruction exact.
- Causality perturbation PASS on all audited frozen features before cutoff.
- No PnL/edge metrics are permitted in this LAB.
