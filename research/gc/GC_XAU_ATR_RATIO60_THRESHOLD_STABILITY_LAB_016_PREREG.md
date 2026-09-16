# GC_XAU_ATR_RATIO60_THRESHOLD_STABILITY_LAB_016 — PREREG

## Purpose
Test whether the LAB015 causal veto `atr_ratio_60 HIGH 1.1657688284518744` represents a stable neighborhood rather than a lucky threshold.

## Frozen baseline
- Signal: `BUYER_BREAKOUT_LONG_001`.
- Execution: corrected `D1.00_E3M`, one-active clock from actionable order start.
- Limit depth 1.00 ATR, expiry 3m, SL 1.5 ATR, TP 3R, hard horizon unchanged.
- Stress cost: +0.05R/fill as in LAB013H/LAB015.
- No geometry or signal retuning.

## Existing data only
Use the exact frozen AMP GC archive and LAB013H E3 raw outcomes already used by LAB015. No new market data.

## Frozen discriminator definition
`atr_ratio_60 = ATR14(current completed GC M1) / median(ATR14 of prior 60 completed M1 bars)` using the causal shifted rolling median already implemented in LAB015.

A veto is applied when `atr_ratio_60 >= threshold` before the XAU order is allowed.

## Frozen threshold grid
No optimization and no extra threshold search:
- 1.10
- 1.13
- 1.1657688284518744 (LAB015 incumbent challenger)
- 1.20
- 1.23

## Periods
- TRAIN: signal time < 2026-09-01T00:00:00Z
- VALID: signal time >= 2026-09-01T00:00:00Z
- FULL: all frozen observations

## Required metrics per threshold
- accepted signals
- fills and retained fill fraction vs corrected baseline
- SumR
- EV/signal
- EV/fill
- PF
- MaxDD R
- TRAIN and VALID separately
- leave-one-UTC-week-out minimum EV/signal on FULL
- weekly EV/signal table

## Stability gates
The LAB015 threshold is considered neighborhood-stable only if:
1. LAB015 incumbent reproduces exactly within floating tolerance: FULL fills 76, SumR 42.455943823874804, EV/fill 0.5586308397878266, PF 2.0267636851587336, MaxDD 5.25R.
2. At least 4 of 5 frozen thresholds have FULL PF > corrected baseline PF 1.3799527829165632.
3. At least 4 of 5 have FULL EV/fill > corrected baseline EV/fill 0.23387120985174975.
4. At least 4 of 5 have VALID PF > corrected VALID PF 1.2595996954108832.
5. At least 4 of 5 have VALID EV/fill > corrected VALID EV/fill 0.17345979647909035.
6. At least 4 of 5 retain >=65% of baseline FULL fills (>=67 of 103).
7. The LAB015 incumbent has positive leave-one-week-out minimum EV/signal.
8. No threshold is selected as a new optimum in this LAB.

## Interpretation
PASS supports the existence of a broad high-volatility failure regime and keeps 1.1657688284518744 frozen as the research challenger because it was selected in LAB015. FAIL means the apparent discriminator is threshold-fragile and must not be promoted.
