# BTC_REVERSAL_LIMIT_RETEST_YEARLY_STABILITY_AND_FRESH_AUG2026_REPLICATION_LAB_007

## Question
Does the frozen LAB006 BTC reversal limit-retest geometry remain positive year-by-year, and does it replicate on genuinely fresh August 2026 Binance Spot BTCUSDT 15m data that was not present in LAB001–006 monthly archives?

## Frozen setup — no optimization
- Parent impulse: exact LAB003/LAB005 rule: completed BTC 60m absolute log-return >= prior 30d 97.5th percentile; 4h cooldown.
- Selector: exact DEV-trained BTC-only CORE logistic CONT/REV router from LAB003/LAB005, DEV q80 top bucket; only routed REV events execute.
- Entry: exact LAB005 primary `LIMIT_R0.50_T60`: event close + impulse_dir × 0.50 × event M15 range; TTL 4 completed M15 bars; no market fallback.
- Stop: 1.00 × parent event M15 range from filled limit.
- Primary TP: 1.5R.
- Same-bar SL+TP ambiguity: SL-first.
- Primary all-in cost stress: 5 bps round trip converted to R by stop fraction.
- RR2.0 is audit only and cannot rescue primary failure.
- No thresholds, model coefficients, limit distance, TTL, stop, RR, costs, or gates may be changed after fresh data are loaded.

## Data clock
Historical fit/audit data:
- Binance Spot BTCUSDT completed 15m monthly archives from 2021-01-01 through 2026-07-31 only.

Fresh sealed replication:
- Binance Spot BTCUSDT daily 15m archives for event dates 2026-08-01 through 2026-08-31.
- 2026-09-01 daily bars may be downloaded only as forward outcome support so an August 31 event can complete its frozen +24h path; September events are never candidates.
- No forward filling.
- Features use only information available at the completed impulse bar.

## Buckets
Primary yearly table:
- 2021
- 2022
- 2023
- 2024
- 2025
- 2026_JAN_JUL
- FRESH_AUG2026

For each bucket report:
- selected REV signals
- filled limits / fill rate
- TP / SL / TIME rates
- net EV R at RR1.5 / 5bps
- Profit Factor
- cumulative net R
- max DD R
- max consecutive losses
- 0.25% and 0.50% equity return / closed-equity max DD
- max overlap / initial risk load

## Frozen gates
Historical stability gates:
1. `dev_positive_years_ge_3_of_4`: at least 3 of 2021–2024 have net EV > 0 at RR1.5 / 5bps.
2. `year_2025_positive`: 2025 net EV > 0.
3. `y2026_jan_jul_positive`: 2026 Jan–Jul net EV > 0.
4. `recent_pf_gt_1`: PF > 1 in both 2025 and 2026 Jan–Jul.
5. `recent_closed_dd_050_lt_5pct`: 0.5% risk closed-equity max DD < 5% in both 2025 and 2026 Jan–Jul.

Fresh replication gates:
6. `fresh_selected_rev_ge_3`: at least 3 frozen selected REV signals in August.
7. `fresh_filled_ge_3`: at least 3 filled primary limits in August.
8. `fresh_net_ev_positive`: fresh filled trades net EV > 0 at RR1.5 / 5bps.
9. `fresh_pf_gt_1`: fresh PF > 1.
10. `fresh_closed_dd_050_lt_5pct`: fresh 0.5% closed-equity max DD < 5%.

## Verdict rule
- `PASS_FRESH_AUG_REPLICATION_AND_YEARLY_STABILITY`: historical gates 1–5 all PASS and fresh gates 6–10 all PASS.
- `WATCH_FRESH_SAMPLE_TOO_SMALL`: historical gates 1–5 all PASS, but fresh selected or filled N < 3; fresh sign is descriptive only and cannot promote.
- `WATCH_MIXED_YEARLY_STABILITY`: fresh gates pass but at least one historical stability gate fails.
- `FAIL_FRESH_REPLICATION`: fresh N >= 3 and fresh EV <= 0 or PF <= 1.
- Otherwise `FAIL_YEARLY_STABILITY`.

## Scientific constraint
August 2026 is consumed exactly once by this preregistered frozen test. Any hypothesis created after viewing August results must treat August as reused audit data, not a fresh holdout.
