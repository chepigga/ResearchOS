# BTC_REVERSAL_H4_PIVOT_M15_TWO_BAR_CONFIRM_FORMAL_REPLICATION_AND_CANONICAL_UNION_LAB_018

## Role
Formal replication/promotion test of the audit-only `TWO_BAR_CONFIRM_12H` child rule discovered in LAB017, plus frozen union economics with canonical `P975_T25 + VF1`.

This LAB does **not** search thresholds, child rules, parent families, stops, targets, TTLs, or costs.

## Frozen lineage
- Exact frozen orthogonal H4 parent artifact from valid LAB016 v2: `H4_7D_PIVOT_SWEEP_RECLAIM_nonoverlap_selected.csv`.
- Hard parity: 610 raw H4 pivot parents -> 294 frozen T25 REV pre-orthogonality -> 81 removed within ±24h of canonical -> 213 orthogonal parents.
- Recent parity: exactly 22 parents in 2025 H2 and 21 parents in 2026 Jan-Jul.
- Exact canonical artifact from LAB015: `part_a_p975_t25_signal_stream.csv`.
- Loader: LAB007 `L7.load_panel()` so the right edge and Aug support bars match the validated lineage.

## Frozen primary H4->M15 bridge
Parent: `H4_7D_PIVOT_SWEEP_RECLAIM`, already strict-nonoverlap with canonical.

Child search window: 12 hours after completed H4 parent.

Primary child: `TWO_BAR_CONFIRM_12H` exactly as implemented in LAB017:
- H4 parent supplies direction/context only.
- Two completed M15 child bars must satisfy the frozen two-bar reversal confirmation.
- The second confirming M15 bar supplies local execution geometry.
- Entry = frozen reversal-side passive limit at 0.50 x child M15 range.
- Limit TTL = 4 M15 bars = 60 minutes.
- Stop = 1.00 x child M15 range from entry.
- TP = 1.50R.
- Same-bar SL+TP ambiguity = SL-first.
- Cost stress = 5 bps round trip notional.
- No market fallback.

## Frozen maturity
`VF1`: a real trade is admitted only if, before the current child signal, at least one prior virtual child limit in the same 7-day H4-child episode has actually filled.
- Prior virtual outcome is not needed.
- Unfilled shadow orders and pre-maturity child opportunities contribute 0 real R.

## Windows
- 2025_H2: 2025-07-01 to 2026-01-01 UTC.
- 2026_JAN_JUL: 2026-01-01 to 2026-08-01 UTC.
- POOLED_RECENT: 2025-07-01 to 2026-08-01 UTC.
- AUG2026_REUSED_AUDIT: descriptive only; already consumed.
- Historical 2021-2025H1: descriptive only.

All 2025H2/2026 windows are reused research windows, not fresh holdouts.

## Metrics
### H4 module
- parent N / child-found N / virtual fills / VF1-mature opportunities / real fills;
- fills per month;
- mean R/fill, cumulative R, PF, max closed-equity DD R;
- leave-one-7d-episode-out worst remaining R;
- month-by-month R;
- direction split: reversal BUY vs reversal SELL;
- max concurrent real trades.

### Canonical + H4 union
- total fills and fills/month;
- canonical vs incremental H4 fills;
- CumR / EV / PF / max DD R;
- max concurrent real trades;
- initial-risk load at 0.25% and 0.50% risk/trade;
- compounded equity return and max closed-equity DD at 0.25% / 0.50%;
- monthly R and module contribution.

## Primary gates
1. `lineage_exact`: 610/294/81/213 and recent 22/21 exact parity.
2. `h2_real_fills_ge_8`.
3. `y2026_real_fills_ge_5`.
4. `mean_R_positive_both`.
5. `pf_gt_1_30_both`.
6. `cumR_positive_both`.
7. `pooled_ev_ge_0_25R`.
8. `pooled_pf_ge_1_50`.
9. `pooled_loeo_positive`.
10. `pooled_maxdd_le_3R`.
11. `union_freq_ge_3_per_month`.
12. `union_incremental_cumR_ge_2R`: union CumR exceeds frozen canonical CumR by at least +2R.
13. `union_pf_ge_1_75`.
14. `union_maxdd_le_4R`.
15. `union_max_concurrent_risk_050_lt_4pct`.
16. `union_positive_both_recent_windows`.

### Verdict
- `PASS_FORMAL_TWO_BAR_REPLICATION_REUSED`: >=14/16 AND gates 1,4,5,6,7,8,9,11,12,16 all PASS.
- `WATCH_TWO_BAR_REPLICATION`: >=11/16, both recent H4 windows cumulative R >0, and union CumR > frozen canonical CumR.
- otherwise `FAIL_TWO_BAR_REPLICATION`.

Even PASS is **research promotion only**, not fresh validation and not live authorization.

## No post-hoc rescue
- No alternate child rule may rescue a failed primary.
- No threshold, TTL, limit distance, SL, TP, cost, episode gap, or router cutoff may be changed after results are seen.
- Monthly/directional analyses are descriptive diagnostics only.

## Live status
Live allocation remains **0** regardless of LAB018 verdict. Fresh replication, M1/raw execution parity, exact current prop costs/slippage, and prop-rule implementation remain required before EA/live use.
