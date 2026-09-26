# LAB071 — CF191G LAB070 FIXED-RULE ROBUSTNESS — PREREGISTRATION

## Purpose

Stress-test the already frozen LAB070 candidate without changing any trading threshold or management fraction.

Frozen rule:
`entry vol percentile >= 0.80 + FAILED_EARLY at t+15m + still active -> close 50%, keep 50% frozen runner`.

No retuning of P80, 15m, FAILED_EARLY, or 50%.

## Source

Use exact LAB070 paired control/modified trade outcomes and exact chronological signal order.

## A. Execution-cost stress

LAB070 assumes linear baseline cost. Add EXTRA cost only to the 50% reduced leg at t+15m:
- +0.5 bps
- +1.0 bps
- +2.0 bps

Extra R charge on acted trade:
`0.5 * extra_bps/10000 * entry_price / (1.5 * entry_ATR)`.

Report N/EV/PF/SumR/MaxDD/R-DD for each period and scenario.

Primary cost robustness criterion:
At +1.0 bps extra, BOTH 2021–2025 and 2026 must still have:
- R/DD >= frozen control;
- SumR >= 98% frozen control.

+2.0 bps is severe stress and descriptive only.

## B. Paired block bootstrap

Fixed seed = 69071.
5000 replicates.
Block length = 50 chronological trades.
Resample paired CONTROL and LAB070 trade blocks using the same sampled block indices, preserving within-block local clustering.

For each replicate calculate:
- SumR delta = modified - control;
- MaxDD delta;
- R/DD delta.

Report median, 10th/90th percentiles, and probability(delta R/DD > 0).

Primary bootstrap robustness criterion:
- median delta R/DD > 0 in BOTH periods;
- P(delta R/DD > 0) >= 0.60 in BOTH periods.

## C. Stability map

Descriptive only:
- yearly 2021–2025 control vs LAB070;
- monthly Mar–Aug 2026 control vs LAB070;
- action count and net delta by period.

No selection of 'good' years/months and no regime-specific retuning.

## Promotion

LAB070 becomes a DEMO-CANDIDATE only if both the +1bps cost criterion and bootstrap criterion pass in both periods.
Otherwise remain shadow/research only.