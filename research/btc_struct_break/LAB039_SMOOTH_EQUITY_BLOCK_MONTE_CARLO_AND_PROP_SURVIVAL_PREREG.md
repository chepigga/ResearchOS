# BTC_SMOOTH_EQUITY_BLOCK_MONTE_CARLO_AND_PROP_SURVIVAL_LAB_039

Date: 2026-08-27

## Frozen system
Use the LAB037/LAB038 current portfolio router:
- BASE3 + FAILED_RANGE_EXPANSION_DIST_GT_1
- EFFICIENCY_STATE == LOW => 0.5x risk
- otherwise 1.0x risk
- no entry changes, no selector tuning.

## Resampling
Primary Monte Carlo uses contiguous block bootstrap over the realized trade sequence to preserve serial dependence. Frozen block lengths: 5, 10, 20 trades. Primary summary uses block length 10; lengths 5 and 20 are robustness diagnostics.

For each simulation, resample until the simulated path contains the same number of trades as the historical VAL 2023-2025 sample. Use 20,000 paths per block length with fixed RNG seed 39039.

## Outputs
For each path calculate:
- MaxDD in R
- worst rolling-3-month proxy, using historical median trades per month and a 3-month rolling trade-count window
- terminal R
- max consecutive loss run

## Prop survival approximation
Risk per 1R tested: 0.25%, 0.35%, 0.50% of initial equity. For LOW efficiency trades, applied risk is half those values.

Frozen challenge approximation:
- overall loss breach: -10% from initial equity
- daily loss breach: -5% from day-start equity, calculated from simulated grouped trading days using contiguous blocks of historical day-level trade PnL
- profit targets tested: +8% and +10%
- target-before-breach probability is reported.

A second day-block bootstrap uses contiguous blocks of 5 trading days, 20,000 paths, preserving all trades and intraday PnL from sampled historical days.

## Interpretation gates
- 0.25% risk is acceptable if P(overall breach) <= 1%, P(daily breach) <= 1%, and P(target +10 before breach) >= 70% over a 3-year-equivalent path.
- 0.35% risk is acceptable if P(overall breach) <= 2.5%, P(daily breach) <= 2.5%, and target probability >= 75%.
- 0.50% risk is acceptable if P(overall breach) <= 5%, P(daily breach) <= 5%, and target probability >= 80%.

2026 remains shadow and is not used to promote risk sizing.
