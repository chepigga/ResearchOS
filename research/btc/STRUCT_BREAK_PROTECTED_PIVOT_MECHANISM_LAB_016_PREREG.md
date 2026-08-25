# STRUCT_BREAK_PROTECTED_PIVOT_MECHANISM_LAB_016 — PREREG

Date: 2026-08-25

## Question
Does the simple protected-pivot mechanism — pivot age + causal unviolated status + pre-entry displacement + frozen riskATR tail — provide stable outcome separation beyond merely explaining tail membership?

## Population
Frozen STRUCT_BREAK v002 trades, 2019-09 through 2025-12, 2026 excluded. Existing R includes 0.06R round-turn cost.

## Features (causal, pre-entry only)
1. `PIVOT_AGE_BARS`: frozen LAB006 stop-side 5-5 pivot age at fill.
2. `PIVOT_UNVIOLATED`: after pivot confirmation (`p_idx+5`) through entry-1, BUY stop-pivot low is never traded below; SELL stop-pivot high is never traded above.
3. `PIVOT_DISPLACEMENT_ATR`: maximum favorable excursion away from the stop pivot from pivot confirmation through entry-1, normalized by ATR14 at entry. BUY: `(max(high)-pivot_low)/ATR`; SELL: `(pivot_high-min(low))/ATR`.
4. `riskATR`: frozen STRUCT_BREAK stop distance in ATR. Tail threshold remains frozen at `riskATR > 3.72`.

## No threshold mining
- `riskATR > 3.72` is frozen from prior work.
- High age and high displacement buckets are set from DEV (2019-2022) quantiles only before viewing VAL outcomes. Primary high bucket = q67; secondary diagnostic = q91 to match the prior ~top-9% observation.
- No PnL-driven threshold search.

## Primary tests
A. Continuous 4-feature logistic outcome model trained on DEV only for `REACHED_1R`, evaluated on VAL.
B. Nested fixed rules on VAL:
   - riskATR tail only;
   - tail + unviolated;
   - tail + age>=DEV q67;
   - tail + displacement>=DEV q67;
   - tail + unviolated + age>=q67 + displacement>=q67.
C. Year-by-year 2023/2024/2025 EV and counts.
D. Rolling/expanding yearly walk-forward using the same four raw features, to check direction stability rather than one split.
E. Correlations among age, displacement and riskATR to determine redundancy.

## Promotion criteria
No production promotion unless all hold:
- VAL continuous model AUC >= 0.55;
- selected VAL EV >= +0.10R;
- bootstrap 95% CI lower bound > 0 for the primary all-four rule OR expanding walk-forward aggregate;
- at least 2/3 VAL years positive;
- selected VAL N >= 40.

This is a mechanism test, not a strategy optimization. If gates fail, the result may still establish structural interpretation but not an entry selector.