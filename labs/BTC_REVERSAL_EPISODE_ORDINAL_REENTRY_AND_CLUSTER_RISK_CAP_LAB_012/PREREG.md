# BTC_REVERSAL_EPISODE_ORDINAL_REENTRY_AND_CLUSTER_RISK_CAP_LAB_012 — preregistration

## Question
Is the recent frozen BTC reversal edge best understood as a harvestable sequence of re-entries inside 7-day market episodes, and can a prop-safe causal cap preserve most of the edge while limiting cluster risk?

## Frozen base
Inherited exactly from LAB011 / LAB006:
- frozen REV selector;
- entry `LIMIT_R0.50_T60`, no market fallback;
- SL = 1.0 × parent event M15 range;
- TP = 1.5R;
- same-bar ambiguity = SL-first;
- 5 bps round-trip cost;
- NO_FILL = 0R;
- global 7-day episode IDs assigned before slicing windows.

Primary windows:
- 2025_H2 = 2025-07-01 through 2025-12-31;
- 2026_JAN_JUL = 2026-01-01 through 2026-07-31.
These windows are already seen and are not fresh holdouts.

## Ordinal diagnostics
Within each global 7-day episode report:
- selected-REV opportunity ordinal;
- actual fill ordinal;
- net R by fill ordinal 1, 2, 3, 4+;
- cumulative contribution of first fill, second fill, third fill and later fills;
- positive/negative episode counts by ordinal availability.

No ordinal threshold is optimized from the outputs.

## Causal slot simulation
A cap controls admitted limit orders, not retrospectively selected winners.
For a candidate signal at time t:
- an earlier accepted order that has already filled counts as a permanently consumed slot for that episode;
- an earlier accepted order still within its 60-minute TTL reserves a slot;
- a no-fill order whose TTL expired releases its slot;
- a future fill may not be used to reject an order at an earlier timestamp.
This prevents future-fill leakage.

## Policies
BASE_ALL = all frozen opportunities.

Primary policy, fixed before outputs:
- `MAX2_FILL_SLOTS`: at most two filled/committed entry slots per 7-day episode using the causal reservation rule above.

Audit-only policies:
- `MAX1_FILL_SLOTS`;
- `MAX3_FILL_SLOTS`;
- `LOSSSTOP_1R`: stop admitting new episode signals once conservatively known realized episode P/L <= -1.0R;
- `MAX2_PLUS_LOSSSTOP_1R`.

For LOSSSTOP causality, a prior trade outcome is treated as known only at `event_time + 24h15m` even if TP/SL likely occurred earlier. This intentionally delays the stop and cannot create look-ahead advantage.

## Risk mapping
Each admitted filled trade carries 1R initial risk.
- at 0.25% risk/trade: MAX1/2/3 corresponds to 0.25% / 0.50% / 0.75% cumulative initial risk budget per episode;
- at 0.50% risk/trade: MAX1/2/3 corresponds to 0.50% / 1.00% / 1.50% per episode.
This is a cumulative episode budget, not a claim about simultaneous floating DD.

## Metrics
For each window and policy:
- admitted signals, fills, fill rate;
- cumulative R, EV/opportunity, EV/admitted signal, PF;
- max DD R, max consecutive losses;
- episode count, positive/negative episodes;
- worst episode R;
- top episode share of gross positive R;
- leave-one-episode-out worst remaining R;
- episode-cluster bootstrap 95% CI of EV/opportunity.

Ordinal table reports N, mean/median R, positive rate, cumulative R for fill ordinal 1,2,3,4+.

## Primary promotion gates for MAX2_FILL_SLOTS
1. 2025_H2 capped cumulative R > 0;
2. 2026_JAN_JUL capped cumulative R > 0;
3. pooled capped cumulative R > 0;
4. pooled capped R retains >=70% of BASE pooled R;
5. 2025_H2 capped R retains >=60% of BASE 2025_H2 R;
6. 2026 capped R retains >=60% of BASE 2026 R;
7. pooled max DD R <= BASE pooled max DD R;
8. worst capped episode R >= -2.25R;
9. pooled top episode positive share <=60%;
10. pooled worst leave-one-episode-out remaining R > 0;
11. pooled cluster-bootstrap CI lower bound > 0;
12. ordinal 2 fills have positive mean net R pooled.

`PASS_PROP_SAFE_EPISODE_HARVEST` requires >=10/12 with gates 1,2,3,4,7,8 passing.
`WATCH_EPISODE_HARVEST_PARTIAL` requires both windows positive and pooled positive but misses PASS.
Otherwise `FAIL_REENTRY_CAP_DOES_NOT_PRESERVE_EDGE`.

## Scientific status
This LAB diagnoses execution/risk architecture only. It cannot authorize live allocation, change selector parameters, promote RR2.0, or claim fresh replication.