# BTC_BASE3_X_FAILED_RANGE_EXPANSION_DRAWDOWN_ROUTER_LAB_036

Date: 2026-08-27

## Objective
Diagnose and reduce drawdown of BASE3 + FAILED_RANGE_EXPANSION with PRIOR_BALANCE_DISTANCE_ATR > 1.0 without changing the underlying entry definitions.

## Frozen parent streams
- BASE3 = OLD_PROTECTED_BREAK + COMPRESSION_SELL + LOW_RV_BREAK
- FAILED_RANGE_EXPANSION candidate = PRIOR_BALANCE_DISTANCE_ATR > 1.0

## No entry retuning
No changes to event definitions, thresholds, direction filters, TP/SL/BE rules, or side selection.

## Frozen router variants
R0 Baseline: current one-position priority router.
R1 Loss-streak cooldown: after 2 consecutive realized losses in portfolio, skip new FAILED_RANGE_EXPANSION entries for next 48 M15 bars; BASE3 unchanged.
R2 Drawdown risk cut: when realized portfolio drawdown reaches >=4R, FAILED_RANGE_EXPANSION risk multiplier = 0.5 until equity recovers to within 1R of previous peak; BASE3 risk unchanged.
R3 Stream risk scale: FAILED_RANGE_EXPANSION fixed 0.75R weight; BASE3 fixed 1.0R weight.
R4 Combined risk control: R2 + fixed 0.75 risk multiplier on FAILED_RANGE_EXPANSION.

All router state must depend only on previously closed trades.

## Primary evaluation window
2023-2025 research/validation lineage; 2026 shadow only.

## Primary gates
- Portfolio EV >= +0.15R-equivalent per accepted trade
- PF >= 1.35
- MaxDD <= 10R
- profitable months >= 60%
- Recovery Factor >= 2
- worst rolling 3M >= -3R
- trade frequency >= 115/year; target remains 150-300/year but this LAB must not manufacture frequency
- 1.5x cost EV > 0

## Selection rule
A router can be promoted only if it improves MaxDD versus baseline and passes all primary quality gates. Prefer the least complex passing router. No post-hoc parameter changes.
