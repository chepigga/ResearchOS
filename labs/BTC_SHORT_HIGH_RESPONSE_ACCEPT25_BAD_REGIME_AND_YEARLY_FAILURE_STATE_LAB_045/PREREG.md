# BTC_SHORT_HIGH_RESPONSE_ACCEPT25_BAD_REGIME_AND_YEARLY_FAILURE_STATE_LAB_045

## Purpose
Explain the weak historical windows of the already-passed LAB044 bounded SHORT execution policy without changing the signal, entry, stop, target, horizon, or costs.

## Frozen execution policy
- Source: `BTC_FLOW_LEVEL_SHORT_HIGH_RESPONSE_ENTRY_CLOCK_AND_WIDE_SURVIVAL_EXECUTION_LAB_044/output/execution_stream.csv`.
- Exact formal policy: `clock=ACCEPT`, `stop_atr=2.5`, `traded=True`, `signal_time < 2026-08-01`.
- Expected N = 327 trades from LAB044.
- Frozen payoff = `net_r_5bps` from LAB044; no re-simulation in this LAB.
- Frozen weak periods, identified only from LAB044 primary execution transfer and used descriptively here: `2022`, `2023`, `2025_H1`.
- Frozen strong periods: `2021`, `2024`, `2025_H2`, `2026_JAN_JUL`.
- This is reused-data failure-state research, not fresh OOS.

## Causal regime clock
All regime features must be known strictly before the ACCEPT entry bar.
- `entry_time` is frozen LAB044 ACCEPT class-time close.
- `regime_time = entry_time - 15 minutes`.
- Price/ATR/metrics features use only data at or before `regime_time`.
- No feature may use the ACCEPT bar, post-entry path, SL/TP result, or future yearly label.

## Data
- Binance USD-M BTCUSDT 15m klines, same lineage as LAB035/LAB044.
- Binance USD-M BTCUSDT daily metrics resampled to M15, same lineage as LAB034: `count_long_short_ratio`, `sum_open_interest`.
- No funding/basis is added because it is not present in the frozen LAB034 metrics archive used by this lineage.

## Frozen feature family (10)
Primary hypotheses are marked PRIMARY.

1. `downside_extension_72h_atr` — distance from prior 72h high to regime close, normalized by causal ATR14. **PRIMARY H1:** BAD > GOOD (late/overextended short hypothesis).
2. `bear_trend_eff_24h` — `(close[t-24h] - close[t]) / sum(abs(M15 close changes over prior 24h))`; positive means efficient bearish travel. **PRIMARY H2:** BAD < GOOD.
3. `flow_persist_12h` — fraction of prior 48 M15 metric observations with `delta_ls_12 > 0` (retail crowd becoming more long, hence contrarian SHORT vulnerability). **PRIMARY H3:** BAD < GOOD.
4. `bear_trend_24h_atr` — `(close[t-24h]-close[t])/ATR14`.
5. `bear_trend_72h_atr` — `(close[t-72h]-close[t])/ATR14`.
6. `downside_extension_24h_atr` — distance from prior 24h high to regime close / ATR14.
7. `atr_rank_90d` — percentile rank of current causal ATR14 versus strictly prior 90d M15 ATR14 distribution.
8. `flow_persist_3h` — fraction of prior 12 M15 observations with `delta_ls_12 > 0`.
9. `oi_logchg_3h` — log OI change over prior 3h.
10. `oi_logchg_12h` — log OI change over prior 12h.

No threshold search, no quintile promotion, no router construction in this LAB.

## Tests
### A. BAD vs GOOD failure-state discrimination
For each frozen feature:
- Mann–Whitney U, BAD vs GOOD;
- rank-biserial correlation (RBC, BAD relative to GOOD);
- BH-FDR across all 10 features.
Expected primary directions:
- H1 `downside_extension_72h_atr`: RBC > 0.
- H2 `bear_trend_eff_24h`: RBC < 0.
- H3 `flow_persist_12h`: RBC < 0.

### B. Trade-level economic alignment
Across all 327 frozen trades, Spearman feature vs `net_r_5bps`, BH-FDR across 10 features.
Expected signs:
- H1 extension: rho < 0.
- H2 bearish efficiency: rho > 0.
- H3 flow persistence: rho > 0.

### C. 7-day cluster robustness for primaries
For H1/H2/H3, bootstrap the BAD-GOOD mean feature difference using 7-day signal-time clusters, 5000 draws, seed 20260908. This tests whether the period distinction is not explained by a handful of weeks. Expected CI direction follows H1/H2/H3.

### D. Fixed period map
Report feature means and frozen LAB044 ACCEPT2.5 economics for:
`2021`, `2022`, `2023`, `2024`, `2025_H1`, `2025_H2`, `2026_JAN_JUL`.
Also report period-level Spearman of feature mean vs frozen EV/original across these 7 periods as descriptive only because N_period=7.

## Gates
1. exact frozen ACCEPT2.5 pre-Aug trades = 327;
2. frozen execution payoff/timestamp coverage = 100%;
3. futures regime-feature coverage >=99%;
4. metrics regime-feature coverage >=95%;
5. H1 BAD>GOOD;
6. H1 |RBC| >=0.15;
7. H1 BH q <=0.10;
8. H1 trade-level rho <0;
9. H2 BAD<GOOD;
10. H2 |RBC| >=0.15;
11. H2 BH q <=0.10;
12. H2 trade-level rho >0;
13. H3 BAD<GOOD;
14. H3 |RBC| >=0.15;
15. H3 BH q <=0.10;
16. H3 trade-level rho >0;
17. at least 2 of 3 primary discrimination q <=0.10;
18. at least 1 primary 7d bootstrap CI excludes zero in preregistered direction;
19. at least 1 frozen feature has discrimination BH q <=0.10;
20. at least 1 frozen feature has trade-payoff BH q <=0.10;
21. 2025H2 and 2026 are not used to tune any threshold/weight;
22. August 2026 is not used for selection.

## Verdict
- `PASS_CAUSAL_BAD_REGIME_STATE_FOUND_REUSED` only if >=17/22 and gates 5,9,13 include at least two expected-direction primary passes plus gate 17 and gate 18.
- `WATCH_FAILURE_STATE_PARTIAL_REUSED` if >=11/22 or at least one primary is statistically/economically aligned.
- otherwise `FAIL_NO_CAUSAL_YEARLY_FAILURE_STATE`.

## Guardrail
Even a PASS here would identify a reused-data regime dimension only. It would not authorize a new live veto. Any regime cutoff/router must be preregistered and independently replicated in a later LAB. Live allocation remains 0.
