# BTC_INDEPENDENT_M15_CONTEXT_FAMILY_DISCOVERY_LAB_032 — PREREG

Date: 2026-08-27

## Objective
Find 2–4 independent M15 context families that can complement the current smooth-equity BASE3 router and increase natural trade frequency without moving execution to M5.

## Base trade population
Canonical BREAK_RETEST trades from frozen STRUCT_BREAK v002. Contexts are evaluated as selectors on the broad BREAK_RETEST population; they are not restricted to old-protected-pivot age/riskATR.

## Frozen context families

### F1 FAILED_RANGE_EXPANSION
Within the 8 completed M15 bars before canonical fill, find an expansion bar whose true range is >= 2.0x the lagged rolling median true range of the prior 20 M15 bars. The expansion closes in the adverse direction of the eventual trade and in the outer 25% of its range. Before fill, price closes back through that expansion bar midpoint in the eventual trade direction. No requirement for sweep or old pivot.

### F2 BALANCE_BREAK_FAILURE
Define a pre-break balance as the 12 completed M15 bars ending 3 bars before fill. Its range must be <= the lagged 20-day median of 12-bar ranges. During the final 3 completed bars before fill, price closes outside the balance in the adverse direction, then closes back inside the balance before fill. Eventual trade direction is the failure direction back into/through the balance.

### F3 IMPULSE_EXHAUSTION_RECLAIM
Within the 8 completed M15 bars before fill, there must be 3 consecutive adverse closes with cumulative close-to-close displacement >= 1.5 ATR14 measured at the third bar. Before fill, a completed M15 bar closes back through the midpoint of that 3-bar impulse in the eventual trade direction.

### F4 VOLATILITY_SHOCK_MEAN_REENTRY
Within the 8 completed bars before fill, ATR14 / lagged median ATR14(96) must reach >= 1.5. After that shock, before fill, a completed bar must close back inside the pre-shock 8-bar close range in the eventual trade direction. This tests a volatility-shock re-entry sequence rather than a static high/low-vol filter.

## Causality
All context information must be available before the canonical fill. No current unfinished higher-timeframe bar, future profile, future pivot, or post-fill data may enter context construction.

## Splits
- DEV: 2019-09 through 2022-12
- VAL: 2023-01 through 2025-12
- 2026: contaminated/shadow only; excluded from promotion.

The 2019–2025 history has been inspected in prior research and is therefore RESEARCH/DEV material, not pristine OOS. LAB032 is discovery/rediscovery only. Any survivor requires a later frozen replication/forward/alternate-market test.

## Family gates on VAL
A context becomes a replication seed only if all hold:
- DEV EV > 0
- VAL EV >= +0.10R
- VAL PF >= 1.25
- VAL frequency 30–70 trades/year (N 90–210 across 2023–2025)
- at least 2/3 VAL years positive
- 1.5x cost EV > 0
- overlap with current BASE3 <= 40% within +/-8 M15 bars
- no single VAL year contributes >70% of positive net R

## Portfolio diagnostic
Each surviving context is added separately to the frozen BASE3 router under one-position priority after BASE3. A useful addition should move toward the strategic target:
- 150–300 trades/year
- portfolio EV >= +0.15R
- PF >= 1.35
- MaxDD <= 10R
- >=60% profitable months
- Recovery Factor >=2

Portfolio diagnostics cannot rescue a family that fails its individual preregistered gate.

## Restrictions
- No threshold tuning after results.
- No side-only promotion in this LAB.
- No M5 execution.
- Do not revive the previously falsified sweep mechanism as an old-pivot explanation.
- Rejection/failure definitions above are frozen before PnL calculation.
