# BTC_REVERSAL_EPISODE_CAUSAL_VIRTUAL_FILL_MATURITY_AND_LATE_REENTRY_TRANSFER_LAB_013

## Question
Does the frozen BTC reversal branch become materially stronger if early episode probes are observed only as **virtual limits**, and real risk is activated only after the episode has causally demonstrated at least one prior virtual fill?

## Frozen parent
No selector, entry, stop, target, cost, or episode definition changes are permitted.

- Exact frozen REV selector from the LAB003 lineage.
- Exact `LIMIT_R0.50_T60` entry: reversal-side limit at 0.50× parent M15 range, TTL 60m, no market fallback.
- SL = 1.00× parent M15 range from fill.
- TP = 1.5R.
- 5 bps round-trip notional cost stress.
- Conservative M15 first-hit resolution inherited unchanged.
- Primary episode definition = globally assigned 7-day signal-gap episodes from LAB011/012.
- `NO_FILL = 0R`.

## Causal virtual-state clock
For every current frozen REV opportunity at event time `t`, scan only earlier opportunities in the same 7d episode.

A prior virtual limit counts as a **known virtual fill** only when its frozen `fill_time < t`.

No TP/SL/24h outcome of a prior virtual trade is needed by the primary rule. Outcome-aware audits may use a prior result only after the inherited conservative knowledge time `prior_event_time + 24h15m <= t`.

The state is calculated globally before slicing evaluation windows, so an episode crossing a calendar/window boundary carries its already-known virtual state forward.

## Primary policy — `VF1_MATURE`
Real trading is permitted on the current frozen opportunity **iff at least one earlier virtual limit in the same 7d episode has already filled before the current event time**.

This means the first actual fill in an episode can be skipped as a zero-risk virtual probe; later opportunities may become real once that virtual fill is known.

There is no post-hoc real-trade count cap in the primary policy. LAB013 tests maturity transfer, not a new cap. Episode risk load is reported for later engineering.

## Audit-only policies
These cannot replace the primary verdict:

- `VF2_MATURE`: require >=2 prior known virtual fills.
- `OPP2_MATURE`: require >=2 prior frozen opportunities, regardless of fill.
- `VF1_KNOWN_OUTCOME`: require VF1 plus >=1 prior filled opportunity whose conservative +24h15m outcome is already known.
- `KNOWN_POSITIVE`: require >=1 prior filled opportunity with a causally known positive net-R outcome.

## Maturity diagnostics
Before outcomes are inspected, report opportunity/fill economics by prior-known-virtual-fill bucket:

- 0 prior virtual fills
- 1 prior virtual fill
- 2 prior virtual fills
- 3+ prior virtual fills

Also report opportunity ordinal, hours since first episode opportunity, hours since first known virtual fill, and counts of causally known prior outcomes.

## Evaluation windows
Primary transfer windows:

- `2025_H2`: 2025-07-01 through 2025-12-31 UTC.
- `2026_JAN_JUL`: 2026-01-01 through 2026-07-31 UTC.
- `POOLED_RECENT`: union of the two windows.

Historical descriptive audit:

- 2021, 2022, 2023, 2024, 2025_H1.

August 2026 remains a consumed holdout and has zero frozen REV opportunities; it is not treated as fresh evidence.

## Metrics
For BASE and each policy:

- admitted opportunities / fills
- CumR, EV per opportunity, EV per admitted opportunity, PF
- max closed-equity DD in R, max consecutive losses
- episode count, positive/negative episodes
- worst episode R
- top episode share of gross positive R
- worst leave-one-episode-out remaining R
- 5,000-draw 7d episode-cluster bootstrap 95% CI
- max real fills in one episode
- implied max cumulative initial episode budget at 0.25% and 0.50% risk/trade

## Primary promotion gates for `VF1_MATURE`
1. 2025 H2 CumR > 0.
2. 2026 Jan-Jul CumR > 0.
3. Pooled recent CumR > 0.
4. Pooled recent retains >=70% of BASE CumR.
5. 2025 H2 retains >=70% of BASE CumR.
6. 2026 Jan-Jul retains >=70% of BASE CumR.
7. Pooled PF >= BASE PF.
8. Pooled max DD <= BASE max DD.
9. The `0 prior virtual fills` bucket has fill-level mean R <= 0.
10. The pooled `>=1 prior virtual fill` bucket has fill-level mean R > 0.
11. Pooled worst leave-one-episode-out remaining R > 0.
12. Pooled episode-bootstrap CI lower bound > 0.

Verdicts:

- `PASS_CAUSAL_VIRTUAL_FILL_MATURITY_TRANSFER`: >=10/12 gates, with gates 1–8 all passing.
- `WATCH_CAUSAL_MATURITY_PARTIAL`: both recent windows and pooled remain positive, pooled retention >=50%, and >=7/12 gates pass.
- Otherwise `FAIL_VIRTUAL_FILL_MATURITY_DOES_NOT_TRANSFER`.

## Scientific restrictions
- No threshold search after seeing outputs.
- No feature selection or ML in LAB013.
- Audit policies cannot rescue a failed primary `VF1_MATURE` result.
- 2025 H2 and 2026 are reused research windows, not fresh holdouts.
- LAB013 alone does not authorize live allocation or EA deployment.
