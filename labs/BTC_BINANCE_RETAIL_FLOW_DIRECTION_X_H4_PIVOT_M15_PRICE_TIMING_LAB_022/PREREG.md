# BTC_BINANCE_RETAIL_FLOW_DIRECTION_X_H4_PIVOT_M15_PRICE_TIMING_LAB_022

## Question
Can Binance retail account positioning provide the directional layer while the frozen H4 pivot -> M15 two-bar architecture provides timing, with a 12h time exit and no fixed TP?

## Frozen price-timing lineage
- Exact persisted LAB018 `TWO_BAR_CONFIRM_12H` stream.
- H4 parent: strict orthogonal `H4_7D_PIVOT_SWEEP_RECLAIM` from LAB016.
- M15 child: exact two consecutive reversal closes within 12h.
- Existing local-extreme limit geometry is used only in the execution section; no retuning.
- Primary direction test is at the completed M15 child close and has no stop/TP.

## Retail flow data
- Binance USD-M BTCUSDT public futures metrics archive.
- Field: `count_long_short_ratio`.
- Resample causally to M15 using the last observation at/before each M15 close.
- Flow feature: `delta_ls_12 = ratio_t - ratio_{t-12 M15}`.

The exact absolute magnitude thresholds from the earlier standalone retail-flow experiment are not persisted in ResearchOS. They MUST NOT be reconstructed from outcomes. Therefore this bridge LAB uses a preregistered causal rank definition:
- At time t compute q20/q80 from delta_ls_12 observations strictly before t over the trailing 90 calendar days.
- Require at least 30 days / 1000 historical M15 observations.
- `delta_ls_12 >= q80` => retail longs expanded strongly => FLOW SHORT.
- `delta_ls_12 <= q20` => retail longs contracted strongly => FLOW LONG.
- middle 60% => ABSTAIN.
This rank rule is fixed before the run and cannot be changed after results.

## Part A — clean common-clock directional test
Universe: all frozen H4->M15 TWO_BAR child signals with valid price/flow history.
At M15 child close:
- PRICE direction = reversal direction implied by H4 parent.
- FLOW direction = contrarian extreme-rank rule above.
- Future outcome = signed BTC close move exactly 12h later / ATR14(M15) known at signal close.
No stop, no target, no execution simulation.
Report PRICE-only, FLOW-extreme, FLOW∩PRICE agreement, and FLOW-vs-PRICE conflict; yearly 2021..2026 and pooled.

## Part B — executable bridge
Universe: frozen local-extreme limit opportunities from LAB018 where that limit actually filled; no VF1 requirement in the primary bridge because the hypothesis under test is exactly `flow=direction, price=timing`.
Admission: FLOW extreme exists at child signal close AND FLOW side agrees with H4 reversal side.
Entry: exact persisted LAB018 limit entry/fill time.
Primary exit: emergency SL = 1.5 × ATR14(M15) from entry, no TP, otherwise close exactly 12h after fill.
Conservative stop resolution: if the fill bar also reaches SL, SL wins.
Cost: fixed 5 bps round-turn in price terms.
Audit: same admitted trades with no stop and pure 12h time exit.
Audit: same admitted trades requiring frozen VF1 maturity.

## Flow-only reference
For context only, select non-overlapping (>=12h apart) M15 flow-extreme observations and measure 12h signed ATR return. It is not allowed to rescue Part B.

## Windows
- 2021
- 2022 bearish stress test
- 2023
- 2024
- 2025 H1
- 2025 H2
- 2026 Jan-Jul
- Aug 2026 reused audit only
- pooled pre-Aug and pooled recent where applicable.

## Primary gates
1. Binance metrics cover >=90% of 2022 M15 timestamps after the first valid warmup.
2. Part-A FLOW-extreme sample N>=30 pre-Aug.
3. Part-A FLOW signed mean > 0 pre-Aug.
4. Part-A FLOW∩PRICE agreement mean > PRICE-only mean on the same valid child-signal universe.
5. Part-B admitted bounded trades N>=12 pre-Aug.
6. Part-B bounded mean net ATR > 0.
7. Part-B bounded profit factor > 1.25.
8. 2022 admitted SHORT branch has N>=3 and cumulative net ATR > 0.
9. Recent 2025H2 + 2026 Jan-Jul combined admitted bounded cumulative net ATR > 0.
10. Part-B no-stop time-exit audit mean net ATR > 0.

PASS requires >=8/10 and critical gates 1,3,5,6,9. WATCH if directional Part A is positive but executable sample is sparse or unstable. Otherwise FAIL.

## Guardrails
- No absolute retail-flow cutoff search.
- No TP search, stop search, horizon search, or side-specific rescue.
- No calendar regime filter.
- August 2026 is consumed/reused audit only.
- This is still reused research lineage, not fresh prospective OOS.
- Live allocation remains 0.