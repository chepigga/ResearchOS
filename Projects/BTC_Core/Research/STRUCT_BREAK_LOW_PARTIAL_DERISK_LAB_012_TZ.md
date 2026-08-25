# STRUCT_BREAK_LOW_PARTIAL_DERISK_LAB_012 — preregistration

Date: 2026-08-25
Branch: lab/btc-struct-break-regime-004

## Question
Can the already validated LAB008 LOW30 state be monetized by reducing existing exposure rather than fully exiting and later re-entering?

## Frozen upstream state
- Canonical STRUCT_BREAK v002.
- DEV: 2019-09 through 2022-12.
- VAL: 2023-01 through 2025-12.
- 2026 excluded.
- LOW30 is exactly the LAB008 frozen bottom-tertile 30-minute response score trained on DEV only.
- LOW is evaluated only on trades alive at 30m and still below +1R, exactly as LAB008.
- No pre-entry selector and no re-entry.

## Policies
At the 30m LOW decision close a fixed fraction of the current position at the observed market state; the residual position follows the original canonical stop / BE / TP without any changes.

Primary fixed branches:
1. LOW -> reduce 25%; keep 75% canonical.
2. LOW -> reduce 50%; keep 50% canonical.
3. LOW -> reduce 75%; keep 25% canonical.

Control:
- canonical HOLD 100%.

No percentage may be selected on VAL. All three are reported symmetrically.

## Cost model
Canonical cost remains 0.06R round-turn. Partial de-risk does not add turnover: the same original position volume is closed in two pieces. Cost is allocated linearly by closed fraction; no re-entry commission is introduced.

For a LOW trade with canonical FINAL_R and 30m EXIT_NOW_R, total policy result is:

`policy_R = f * EXIT_NOW_R + (1-f) * FINAL_R`

where f is 0.25 / 0.50 / 0.75.

## Primary metrics
Report separately for DEV and VAL:
- LOW-only EV
- whole-portfolio EV
- cumulative closed-trade Max DD
- Recovery Factor / sumR
- yearly transfer
- paired bootstrap CI of policy-minus-canonical per trade
- left-tail loss distribution and number of full-SL-equivalent outcomes

## Prop-risk diagnostic
Because partial de-risk changes exposure after 30m, also estimate mark-to-market risk after LOW using exact M5 paths where available:
- maximum remaining adverse loss after LOW
- reduction in post-LOW adverse excursion versus full HOLD
- effect on worst LOW trade and portfolio drawdown proxy.

## Promotion gate
A branch is promotable only if on VAL:
1. portfolio EV is not lower than canonical by more than 0.005R/trade;
2. Max DD improves by at least 10%;
3. at least 2/3 VAL years do not worsen materially;
4. paired bootstrap does not show statistically meaningful economic damage;
5. no hidden extra turnover/re-entry is used.

If all fixed partial branches materially worsen EV without a compensating DD improvement, verdict = reject partial de-risk at LOW30.

## Interpretation constraint
This LAB does not claim LOW predicts future before entry. It tests only adaptive exposure management after LOW is causally observed.
