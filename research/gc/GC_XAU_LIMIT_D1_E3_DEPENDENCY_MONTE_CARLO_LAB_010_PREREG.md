# GC_XAU_LIMIT_D1_E3_DEPENDENCY_MONTE_CARLO_LAB_010 — PREREG

Status: PREREGISTERED BEFORE LAB010 OUTCOME

## Frozen candidate

No parameter search in this LAB.

Candidate frozen from LAB009:
- GC BUYER_BREAKOUT_LONG_001 signal unchanged
- XAU Buy Limit = market-reference Ask - 1.00 * XAU ATR14(M1)
- limit expiry = 3 minutes
- SL = 1.5 ATR
- TP = 3R
- hard timeout = 30 minutes from original signal
- ONE_ACTIVE_SETUP
- extra adverse cost stress = 0.05R per filled trade, on top of quoted FTMO spread already embedded

Primary cohort: COMMON_CLOCK.
Secondary cohort: AMP_ALL.

## Diagnostics

Using the frozen LAB009 sequences only:

1. Day contribution table and concentration of total PnL.
2. Leave-one-signal-day-out jackknife EV.
3. Leave-one-week-out jackknife EV.
4. 10,000 day-block bootstrap paths preserving all signals inside sampled days.
5. Bootstrap distribution of EV R/original signal and maximum sequence DD R.
6. Translate DD distribution to 0.25% and 0.50% risk per filled trade approximation.
7. Positive-week fraction and worst observed closed UTC day remain descriptive references from LAB009.

## Descriptive robustness gates

At the frozen +0.05R cost:

- bootstrap P(EV > 0) >= 80% on COMMON_CLOCK;
- bootstrap P(EV > 0) >= 80% on AMP_ALL;
- minimum leave-one-week-out EV > 0 on COMMON_CLOCK;
- minimum leave-one-week-out EV > 0 on AMP_ALL;
- no single signal day contributes more than 50% of positive total PnL on COMMON_CLOCK;
- bootstrap 95th percentile max DD at 0.50% risk < 5% on COMMON_CLOCK.

These are historical robustness diagnostics, not independent OOS certification.
