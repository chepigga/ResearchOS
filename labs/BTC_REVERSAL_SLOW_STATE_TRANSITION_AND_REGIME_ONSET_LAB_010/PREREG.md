# BTC_REVERSAL_SLOW_STATE_TRANSITION_AND_REGIME_ONSET_LAB_010 — preregistration

## Question
Can a causal transition/onset layer detect when the frozen BTC reversal branch is entering a favorable regime, especially the 2025 onset, using only changes in slow state that are known before the current parent impulse?

## Frozen base strategy
Inherited exactly from LAB006–LAB009:
- parent impulse = completed BTC 60m |return| >= prior 30d 97.5th percentile, 4h cooldown;
- frozen LAB003 BTC-only CONT/REV router and DEV q80 threshold;
- only frozen `selected_rev` opportunities are eligible;
- entry = `LIMIT_R0.50_T60`, no market fallback;
- SL = 1.0 × parent event M15 range;
- TP = 1.5R primary;
- same-bar SL+TP = SL-first;
- cost stress = 5 bps round trip.

No base parameter may change after outputs are observed.

## Causal boundary
Every transition feature is calculated from slow-state series whose latest price input ends four M15 bars before the event row, i.e. before the current 60m impulse window. Lags/deltas then look further backward from that already-shifted state. No post-impulse, fill, path, year-label, future return, acceptance-history, router-score, current impulse-shape, MFE or MAE feature is allowed in the transition layer.

## Frozen transition features
All are event-direction oriented where direction matters.

### TREND_TRANSITION
- 7d and 30d change in aligned 30d return;
- 7d and 30d change in aligned 60d return;
- 7d and 30d change in aligned 90d return;
- current aligned return curvature: 30d−60d and 60d−90d.

### EFFICIENCY_TRANSITION
- 7d and 30d change in 30d efficiency;
- 7d and 30d change in 60d efficiency;
- 7d and 30d change in 90d efficiency.

### VOL_TRANSITION
- 7d and 30d change in 30d realized volatility;
- 7d and 30d change in 60d realized volatility;
- 7d and 30d change in 90d realized volatility;
- 7d and 30d change in the 30d/90d realized-volatility ratio.

### POSITION_TRANSITION
- 7d and 30d change in event-direction-oriented position within the prior 30d range;
- 7d and 30d change in event-direction-oriented position within the prior 90d range.

Primary family: `TRANSITION_COMBINED` = all four families above.

Audit-only families: `TREND_TRANSITION`, `EFFICIENCY_TRANSITION`, `VOL_TRANSITION`, `POSITION_TRANSITION`. Audit families cannot rescue a failed primary.

## Model and threshold
- Fixed Ridge regression, alpha = 10.0.
- Median imputation + standardization.
- Target per eligible frozen `selected_rev`: frozen RR1.5 net R after 5 bps if filled; 0R if the frozen limit did not fill.
- ON threshold = median fitted score on the training sample for that walk-forward fit.
- No test-year threshold tuning.

## Expanding yearly walk-forward
- test 2022: train 2021;
- test 2023: train 2021–2022;
- test 2024: train 2021–2023;
- test 2025: train 2021–2024;
- test 2026 Jan–Jul: train 2021–2025;
- August 2026: reused audit only; LAB007 consumed it and the frozen REV selector had zero August opportunities.

The 2025 test is the key onset check: its transition model and threshold are frozen from 2021–2024 only.

## Primary comparison
For each year compare:
- BASE = every frozen `selected_rev` opportunity;
- GATED = trade only when `TRANSITION_COMBINED` score >= frozen training median; abstained opportunities contribute 0R.

Report signals, ON count, coverage, fills, cumulative R, delta R, EV/opportunity, EV/traded, PF, max DD R and max consecutive losses.

Also report 2025 H1 and H2 separately using the same frozen 2025 model/threshold. This is descriptive onset localization only and does not alter promotion gates.

## Promotion gates
Primary combined gate only:
1. pooled 2022–2026 gated cumulative R > BASE;
2. pooled gated max DD R < BASE;
3. 2022 cumulative-R delta > 0;
4. 2024 cumulative-R delta > 0;
5. gated 2025 cumulative R > 0;
6. gated 2026 Jan–Jul cumulative R > 0;
7. gated positive years >= 4 of 5;
8. pooled gate coverage between 25% and 75%;
9. pooled 2025+2026 gated cumulative R >= 70% of BASE 2025+2026 cumulative R;
10. pooled 2025+2026 gated max DD <= BASE max DD.

`PASS_SLOW_STATE_TRANSITION_ONSET` requires >=8/10 and gates 1,3,4,5,6,9 all PASS.
`WATCH_PARTIAL_TRANSITION_ONSET` requires >=6/10, positive 2025 and 2026 gated results, and >=50% recent-profit retention.
Otherwise FAIL.

## Scientific status
2022/2024 motivated the hypothesis and are mechanism-discovery years; the inherited selector was originally fit on full DEV 2021–2024. 2025/2026 have also been observed in earlier LABs. Therefore a PASS is a causal walk-forward research pass, not production authorization. Live allocation remains zero.