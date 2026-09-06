# BTC_REVERSAL_H4_BUY_EDGE_REGIME_ONSET_AND_2025H2_STRUCTURAL_TRANSITION_LAB_020

## Question
Did the H4 two-bar BUY branch undergo a real causal regime transition near 2025 H2, and if so which pre-entry state variables changed at the same time?

## Frozen lineage
- Exact persisted LAB018 `TWO_BAR_CONFIRM_12H + VF1` stream.
- Exact H4 7d pivot-sweep/reclaim parents from LAB016.
- BUY means reversal BUY (`impulse_dir < 0`).
- No change to selector, T25 router, parent definition, child rule, VF1 state, limit geometry, TTL, SL, TP or costs.
- LAB019 recent BUY/Sell economics are reference only; no post-hoc trading filter may be promoted in this LAB.

## Windows
- Historical: 2021, 2022, 2023, 2024, 2025 H1.
- Onset window: 2025 H2.
- Transfer window: 2026 Jan-Jul.
- August 2026: consumed/reused stress audit only.

## Part A — outcome change-point audit
Use only real-filled H4 BUY trades, ordered by fill time. Scan candidate split points with at least 6 BUY fills on each side. Report the split maximizing absolute mean-R difference, its timestamp, pre/post mean R, PF and DD. This is descriptive evidence only; it cannot define a trading rule.

Bootstrap the BUY trade sequence by 7d episode clusters (5000 draws) and report how often the best split falls within 2025-04-01..2025-10-01. A broad onset band counts as supportive; exact-date precision is not claimed.

## Part B — fixed causal state fingerprint
Features are computed using information available no later than the M15 child signal time. No TP/SL/outcome or future bars enter features.

Fixed feature set:
1. `ret_24h` — close/close 24h ago - 1.
2. `ret_72h` — close/close 72h ago - 1.
3. `ret_7d` — close/close 7d ago - 1.
4. `range_pos_7d` — signal close position in trailing 7d high-low.
5. `range_pos_30d` — signal close position in trailing 30d high-low.
6. `rv_ratio_24h_7d` — std(M15 log returns, 24h) / std(M15 log returns, 7d).
7. `range_ratio_24h_7d` — trailing 24h high-low / trailing 7d high-low.
8. `parent_range_pct` — frozen H4 parent range / parent close.
9. `parent_body_frac` — abs(parent close-parent open) / parent range.
10. `parent_reclaim_frac` — for BUY low-sweep: (parent close-parent low)/parent range.
11. `router_conf` — frozen router confidence.
12. `child_latency_h` — parent_time to child signal_time.
13. `child_parent_range_ratio` — M15 child range / H4 parent range.
14. `prior_virtual_fills` — causal VF count known at signal.
15. `episode_age_h` — current signal time minus first signal time of current frozen 7d episode.

Primary comparisons:
- 2025 H1 vs 2025 H2 BUY child opportunities.
- HIST_PRE_RECENT (2021-2025H1) vs POOLED_RECENT (2025H2-2026 Jul) BUY child opportunities.

For each feature report medians, standardized mean difference, and Cliff's delta. A `stable_shift` requires the same sign in both comparisons and |Cliff's delta| >= 0.33 in both.

## Part C — H2-regime similarity transfer audit
This is diagnostic, not promotion.
- Train a fixed L2 logistic classifier (`C=1.0`, StandardScaler + median imputation) to distinguish BUY child opportunities in 2025 H2 (`1`) from BUY child opportunities in 2021-2025H1 (`0`) using exactly the fixed features above.
- Threshold is frozen as the median model score among 2025 H2 training observations.
- Apply unchanged to 2026 Jan-Jul and August 2026.
- Report coverage and economics of real BUY fills above/below threshold.

Supportive transfer requires in 2026: regime-like real fills have positive CumR and mean R, and their mean R exceeds non-regime-like fills. August is report-only and cannot rescue/fail the scientific verdict by itself.

## Verdict
`PASS_CAUSAL_REGIME_ONSET_SUPPORTED` requires:
1. best BUY change point in 2025-04-01..2025-10-01;
2. post-split mean R > pre-split mean R;
3. at least 3 stable-shift causal features;
4. at least one stable-shift feature is structural/price-state (`ret_*`, range position, vol/range ratio, parent geometry), not only router/latency/VF state;
5. 2026 H2-similarity transfer is supportive.

`WATCH_REGIME_ONSET_PARTIAL` if the change point is near H2 2025 and at least 2 stable causal shifts exist but transfer is weak/mixed.
Otherwise `FAIL_NO_CAUSAL_REGIME_ONSET_SUPPORT`.

## Guardrails
- No feature threshold optimization for PnL.
- No feature deletion/addition after results.
- No calendar rule may be promoted.
- No live allocation from this LAB.
- Any candidate regime filter requires a separately preregistered replication LAB.
