# LAB027 — BTC_FAILED_VALUE_MIGRATION_STRUCTURAL_REJECTION

Date: 2026-08-27
Status: preregistered before PnL calculation

## Objective
Test whether the positive LAB025/LAB026 POC_OPPOSED BREAK_RETEST subset is better explained by a causal sequence of failed value migration rather than by static POC opposition alone.

## Frozen universe
Canonical BREAK_RETEST trades only, using the same trade lineage as LAB025/026. No side selection and no change to the frozen POC migration threshold of 0.5 ATR.

## Causal profile clock
M1 volume-at-price approximation identical to LAB025:
- prior 24h M1 profile only;
- 48 bins;
- M1 volume assigned to HLC3 bin;
- 70% contiguous value area around POC;
- comparison profile ends 6h before current fill and covers the prior 24h.

## Frozen sequence definitions
For a BREAK_RETEST trade at fill time t:

1. OPPOSING_POC_MIGRATION
- BUY: current 24h POC <= lagged POC - 0.5*ATR14(M15 at t)
- SELL: current 24h POC >= lagged POC + 0.5*ATR14(M15 at t)

2. PRIOR_VALUE_ACCEPTANCE
Within the 12 completed M15 bars immediately before fill, at least 4 consecutive closes must be accepted on the side implied by the opposing migration:
- BUY trade with opposing downward POC migration: 4 consecutive closes below current VAL;
- SELL trade with opposing upward POC migration: 4 consecutive closes above current VAH.
No current/future bar is used.

3. STRUCTURAL_REJECTION
After the accepted run and before the fill, completed M15 closes must reject back through the current value area:
- BUY: at least one completed close back above VAL after the below-VAL accepted run;
- SELL: at least one completed close back below VAH after the above-VAH accepted run.
The rejection close must occur before the entry/fill bar.

4. FULL_FAILED_VALUE_MIGRATION
All three states above are true in causal order: opposing POC migration -> prior value acceptance -> structural rejection -> canonical BREAK_RETEST fill.

## Controls
A. POC_OPPOSED only — LAB026 control.
B. POC_OPPOSED + PRIOR_VALUE_ACCEPTANCE.
C. POC_OPPOSED + STRUCTURAL_REJECTION (without requiring prior acceptance).
D. FULL_FAILED_VALUE_MIGRATION — primary.

## Time splits
Retained M1 profile data begins in 2024.
- 2024 = discovery/control consistency
- 2025 = replication
- 2026 = shadow only, excluded from promotion

## Primary gates for FULL_FAILED_VALUE_MIGRATION
- 2024 EV > 0
- 2025 EV >= +0.10R
- 2025 PF >= 1.30
- 2025 N >= 15
- both 2025 half-years not negative simultaneously; weaker half >= -0.05R
- 1.5x cost 2025 EV > 0
- M1 fill rate >= 95% if replayable
- M1 EV sign not reversed
- overlap with current two-engine old-pivot core <= 20%

## Portfolio admission gates
Add D to BREAK_RETEST_CORE + OLD_PIVOT_COMPRESSION_SELL under one global active position:
- 2025 trades increase >= 10%
- EV >= +0.18R
- PF >= 1.40
- MaxDD <= 1.35x current core MaxDD
- 1.5x cost EV > 0

## Restrictions
No threshold tuning, no side split promotion, no post-hoc sequence variants in this LAB. Any alternate run length or profile clock is a future LAB.
