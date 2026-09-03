# BTC_REVERSAL_SLOW_REGIME_AND_IMPULSE_ACCEPTANCE_PERSISTENCE_LAB_009 — preregistration

## Question
Can a genuinely slow, causal BTC market-phase layer — built from 30d/60d/90d pre-impulse state plus the realized behavior of prior impulses whose outcomes are already known — identify when the frozen reversal branch should trade versus abstain?

## Frozen base strategy
Inherited unchanged from LAB006/LAB007:
- parent impulse = completed BTC 60m |return| >= prior 30d 97.5th percentile, 4h cooldown;
- frozen LAB003 BTC-only CONT/REV router and DEV q80 threshold;
- only frozen `selected_rev` signals are eligible;
- entry = `LIMIT_R0.50_T60`, no market fallback;
- SL = 1.0 × parent event M15 range;
- TP = 1.5R primary;
- same-bar SL+TP = SL-first;
- cost stress = 5 bps round trip.

No base parameter may change after results are observed.

## Causal clocks
### Slow-state clock
All slow price/volatility features are sampled at the bar immediately preceding the 60m impulse window. If the parent impulse ends at index `i` and its 60m return is `close[i]/close[i-4]`, slow features end at `i-4`. The current impulse itself therefore cannot contaminate the slow state.

### Prior-impulse acceptance clock
For a previous parent impulse with event timestamp `t`, its 24h outcome is treated as known only after `t + 24h + 15m`. A current signal may use that previous impulse only if this known-time is strictly earlier than the current event time.

No current/future fill, MFE/MAE, 24h outcome, year label, or post-impulse bar may enter the regime gate.

## Slow-state features
All fixed before the run:
- impulse-direction-aligned 30d, 60d and 90d log return ending before the impulse;
- 30d, 60d and 90d trend efficiency = |net log return| / sum(|15m log returns|);
- 30d, 60d and 90d realized volatility of 15m log returns;
- realized-volatility ratio `rv30d / rv90d`;
- impulse-direction-oriented position inside prior 30d and prior 90d high/low range.

## Prior-impulse acceptance / persistence features
Calculated only from earlier parent impulses whose 24h outcome is already known:
- `accept_rate_10`: fraction of last 10 known impulses with 24h continuation return > 0;
- `accept_rate_20`: fraction of last 20 known impulses with 24h continuation return > 0;
- `mean_cont_10`: mean signed continuation return of last 10 known impulses;
- `mean_cont_20`: mean signed continuation return of last 20 known impulses;
- `same_dir_accept_rate_10`: continuation-positive fraction among the most recent 10 known impulses matching the current impulse direction;
- `same_dir_mean_cont_10`: mean continuation return among those same-direction impulses;
- `accept_ewm20`: recency-weighted acceptance sign over last 20 known impulses, weights `0.8^age`, +1 for continuation-positive and -1 otherwise;
- `accept_streak_signed`: consecutive latest acceptance/rejection streak, capped at 5; positive = continuation acceptance streak, negative = rejection/reversal streak;
- `known_impulses_30d`: count of already-known prior impulse outcomes with event time inside the preceding 30 days.

## Model families
Primary model = `SLOW_PLUS_ACCEPTANCE`.
Audit-only families:
- `SLOW_ONLY`
- `ACCEPTANCE_ONLY`

All use the same fixed pipeline:
- median imputation with empty-feature retention;
- standardization;
- Ridge regression, `alpha=10.0`.

Target per eligible frozen `selected_rev` signal:
- no limit fill within TTL -> `signal_net_R = 0`;
- filled -> frozen RR1.5 first-hit net R after 5 bps.

This prevents the gate from receiving artificial credit merely from unfilled passive orders.

## Walk-forward protocol
Expanding yearly walk-forward, threshold fixed from training scores only:
- 2022: train on 2021;
- 2023: train on 2021–2022;
- 2024: train on 2021–2023;
- 2025: train on 2021–2024;
- 2026 Jan–Jul: train on 2021–2025;
- August 2026: reused audit only and expected to have zero frozen REV signals from LAB007.

ON threshold = median fitted score on that training sample. Test signals with score >= threshold are traded; others abstain. No test-year threshold tuning.

## Primary comparison
For each test year:
- BASE = every frozen selected REV opportunity;
- GATED = only primary slow+acceptance ON opportunities; abstained opportunities contribute 0R.

Report coverage, filled count, cumulative R, EV/opportunity, EV/traded signal, PF, max DD R, max consecutive losses, and year-by-year delta.

## Promotion gates
Primary combined gate only:
1. pooled 2022–2026 gated cumulative R > BASE cumulative R;
2. pooled gated max DD R < BASE max DD R;
3. 2022 cumulative-R delta > 0;
4. 2024 cumulative-R delta > 0;
5. gated 2025 cumulative R > 0;
6. gated 2026 Jan–Jul cumulative R > 0;
7. gated positive years >= 4 of 5;
8. pooled gate coverage between 25% and 75%;
9. recent 2025+2026 gated cumulative R >= 70% of recent BASE cumulative R;
10. recent 2025+2026 gated max DD <= BASE max DD.

`PASS_SLOW_REGIME_ACCEPTANCE_ROUTER` requires >=8/10 with gates 1, 3, 4, 5, 6, and 9 all passing.
`WATCH_PARTIAL_SLOW_REGIME` requires >=6/10, positive 2025 and 2026 gated results, and recent retained return >=50% of BASE.
Otherwise FAIL.

## Scientific status
- 2022/2024 motivated this LAB and are mechanism-discovery data, not pristine holdout.
- The inherited LAB003 selector itself was fit on full DEV 2021–2024, so 2022–2024 are not end-to-end deployment-causal even though the new regime gate is walk-forward causal.
- 2025/2026 were seen in prior LABs; August 2026 was consumed in LAB007 and is no longer fresh.
- This LAB can validate or reject a slow-regime mechanism but cannot authorize production/live risk by itself.
