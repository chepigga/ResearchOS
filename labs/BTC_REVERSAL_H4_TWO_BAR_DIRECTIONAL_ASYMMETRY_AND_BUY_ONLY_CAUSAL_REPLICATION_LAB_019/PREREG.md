# BTC_REVERSAL_H4_TWO_BAR_DIRECTIONAL_ASYMMETRY_AND_BUY_ONLY_CAUSAL_REPLICATION_LAB_019

## Role
Formal directional-asymmetry replication on the already frozen H4-pivot -> M15 TWO_BAR_CONFIRM_12H -> VF1 stream from LAB018.

This LAB is **not fresh OOS**. 2025H2, 2026 Jan-Jul and August 2026 are reused/consumed research windows. The purpose is to determine whether the strong recent BUY-vs-SELL asymmetry is broad enough to justify a frozen BUY-only candidate for future fresh replication.

## Frozen lineage
No signal, execution, cost, parent, router, maturity or episode parameter may change.

- Exact LAB016 orthogonal H4 parent lineage: 610 raw -> 294 T25 -> 81 removed within ±24h canonical -> 213 orthogonal parents.
- Exact LAB017/018 child rule: `TWO_BAR_CONFIRM_12H`.
- H4 parent supplies context only; M15 child supplies entry/SL geometry.
- Virtual execution: `LIMIT 0.50 * child_range`, TTL 60m, SL `1.0 * child_range`, TP `1.5R`, same-bar SL-first, TIME_EXIT at frozen parent 24h boundary, 5 bps stress.
- Exact LAB018 VF1 maturity stream is reused. All H4 child signals remain shadow/virtual regardless of direction.
- **Primary real-order candidate is BUY-only:** `impulse_dir < 0` (bearish parent displacement -> reversal BUY).
- SELL (`impulse_dir > 0`) remains virtual/shadow and receives **zero real PnL** under the BUY-only candidate, but its virtual fills may still update the already-frozen VF1 episode state because this information is causal and risk-free.
- Frozen canonical module remains exact LAB015 `P975_T25 + VF1` and is not retrained or filtered.

## Primary questions
1. Does H4 two-bar BUY remain profitable in both reused recent windows after formal promotion?
2. Is H4 two-bar SELL consistently inferior/negative in both reused recent windows?
3. Does BUY dominance also exist in older 2021-2025H1 windows, or is it a recent-only asymmetry?
4. Does canonical + H4 BUY-only improve economics/risk relative to canonical alone and relative to the LAB018 all-direction H4 union?

## Windows
Directional module windows are assigned by frozen `parent_time`.

- 2021
- 2022
- 2023
- 2024
- 2025_H1
- 2025_H2
- 2026_JAN_JUL
- `POOLED_RECENT = 2025-07-01 .. 2026-08-01`
- `HIST_PRE_RECENT = 2021-01-01 .. 2025-07-01`
- `ALL_PRE_AUG = 2021-01-01 .. 2026-08-01`
- `AUG2026_REUSED_AUDIT` descriptive only

## Metrics
For BUY and SELL separately:
- real fills
- fills/month
- cumulative R
- mean R/fill
- Profit Factor
- max DD R
- max consecutive losses
- episode count / positive episodes / negative episodes
- leave-one-episode-out worst remaining R

Additional BUY robustness:
- recent monthly table and positive-month count
- leave-one-month-out worst remaining R over pooled recent
- deterministic 5,000-draw 7d-episode cluster bootstrap of mean R/fill, seed `20260905`; report 2.5/50/97.5 percentiles
- historical window table 2021, 2022, 2023, 2024, 2025H1
- number of positive historical windows
- leave-one-historical-window-out worst remaining R

Directional asymmetry:
- BUY minus SELL mean R/fill in each recent window
- BUY minus SELL cumulative R in each recent window

## BUY-only union
Combine:
- exact frozen LAB015 canonical real fills
- H4 TWO_BAR real fills only where `impulse_dir < 0`

For 2025H2, 2026 Jan-Jul and pooled recent report:
- fills and fills/month
- canonical fills / H4 BUY fills
- cumulative R
- mean R/fill
- PF
- max DD R
- conservative maximum concurrency using canonical `event_time + 24h` when actual canonical exit is unavailable
- risk load at 0.25% and 0.50% per trade
- compounded equity return/DD at 0.25% and 0.50% risk/trade

Also compare pooled BUY-only union against:
- canonical-only frozen pooled result
- LAB018 all-direction union pooled result: 41 fills, 3.15/month, +21.67R, PF 2.402, DD 3.75R.

## Frozen gates
### Recent BUY confirmation
1. `lineage_exact`
2. `buy_h2_fills_ge_6`
3. `buy_2026_fills_ge_5`
4. `buy_cumR_positive_both_recent`
5. `buy_meanR_ge_0_30_both_recent`
6. `buy_pf_gt_1_50_both_recent`
7. `buy_sell_mean_delta_positive_both_recent`
8. `sell_cumR_negative_both_recent`
9. `buy_recent_loeo_positive`
10. `buy_recent_cluster_bootstrap_low_gt_0`

### Historical structural support
11. `hist_buy_cumR_positive`
12. `hist_buy_pf_gt_1_20`
13. `hist_buy_positive_windows_ge_3_of_5`
14. `hist_buy_leave_one_window_out_positive`

### BUY-only union
15. `union_freq_ge_2_75_per_month`
16. `union_cumR_gt_all_direction_union_21_67R`
17. `union_pf_ge_2_50`
18. `union_maxdd_le_3_75R`
19. `union_riskload_050_lt_4pct`

## Verdict logic
- `PASS_STRUCTURAL_BUY_DOMINANCE_REUSED`: >=16/19, all critical recent gates 1,4,5,6,7,8,9 pass, all historical gates 11-14 pass, and union gates 15-19 pass.
- `PASS_RECENT_BUY_DOMINANCE_REUSED`: >=14/19, all critical recent gates 1,4,5,6,7,8,9 pass, union gates 15-19 pass, but one or more historical gates 11-14 fail.
- `WATCH_RECENT_BUY_ASYMMETRY`: both recent BUY windows profitable and BUY beats SELL in both, but critical robustness/union gates prevent PASS.
- Else `FAIL_BUY_ONLY_DIRECTIONAL_REPLICATION`.

## Interpretation restrictions
- A PASS is a **research promotion on reused windows**, not live authorization.
- BUY-only cannot be declared prospectively validated until future fresh data or another genuinely untouched sample confirms it.
- No SELL rescue, alternate child rule, threshold change, outcome gate, time filter, RR change or cost change may be introduced after this preregistration.
- Live allocation remains 0.
