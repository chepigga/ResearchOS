# BTC_FLOW_LEVEL_DIRECTIONAL_LIQUIDITY_ELASTICITY_AND_THIN_BOOK_CONTINUATION_LAB_040

## Purpose
Test whether the positive `THIN_LIQUIDITY` cell observed in causal rolling LAB039 reflects a real directional liquidity-elasticity mechanism: relatively large price displacement in FLOW direction despite relatively small net taker pressure, followed by positive continuation.

## Frozen lineage
- Input: `BTC_FLOW_LEVEL_CVD_PRESSURE_X_PRICE_RESPONSE_CAUSAL_ROLLING_INTERACTION_REPLICATION_LAB_039/output/rolling_interaction_stream.csv`.
- FLOW direction, level, touch, HIGH_VOLUME flag, rolling 90d pressure/response medians, rolling cells, ACCEPT/REJECT state, ATR and post-classification `residual_atr` are frozen.
- Selection/inference: `signal_time < 2026-08-01`; August 2026 audit only.
- No level, flow, volume, entry, SL, TP or horizon changes.

## Primary causal comparison
Restrict to frozen LOW_PRESSURE resolved rows from LAB039:
- `THIN_LIQUIDITY` = pressure below/equal prior-90d pressure median AND response above prior-90d response median.
- `WEAK` = pressure below/equal prior-90d pressure median AND response below/equal prior-90d response median.

Primary hypothesis: THIN_LIQUIDITY has larger post-classification `residual_atr` than WEAK. This isolates price responsiveness while holding the pressure regime low.

## Frozen elasticity feature family
Using already-causal pre-touch LAB038 fields:
- `fut_elasticity_15 = fut_disp_atr_15 / max(abs(fut_netdelta_norm_15), 0.25)`
- `fut_elasticity_30`
- `fut_elasticity_60` (PRIMARY continuous feature)
- `spot_elasticity_15`
- `spot_elasticity_30`
- `spot_elasticity_60`
- `fut_minus_spot_elasticity_60`
- `fut_elasticity_accel_15_60 = fut_elasticity_60 - fut_elasticity_15`

No threshold search over elasticity values.

## Tests
1. THIN_LIQUIDITY vs WEAK residual mean and ACCEPT-rate.
2. 7-day cluster bootstrap, 5000 draws, seed 20260908, for THIN-WEAK residual and ACCEPT-rate gaps.
3. Within LOW_PRESSURE resolved rows, Spearman each frozen elasticity feature vs `residual_atr`; BH-FDR across 8 features.
4. Mann-Whitney THIN vs WEAK for each elasticity feature; BH-FDR across 8 features. This verifies that the cell corresponds to higher measured elasticity rather than only a naming artifact.
5. Causal rolling elasticity state: for each HIGH_VOLUME event, compute the median `fut_elasticity_60` from strictly prior 90 calendar days HIGH_VOLUME events, minimum 20 observations, no global fallback. Report HIGH_ELASTICITY vs LOW_ELASTICITY residual only as replication diagnostic.
6. Transfer for frozen THIN_LIQUIDITY: 2021, 2022, 2023, 2024, 2025H1, 2025H2, 2026 Jan-Jul, pooled recent, LONG, SHORT, fixed 2022 SHORT; August audit only.
7. Frequency per month.

## Gates
1. frozen HIGH_VOLUME pre-Aug >=500;
2. resolved LAB039 rolling cells >=400;
3. THIN_LIQUIDITY N>=50;
4. WEAK N>=120;
5. THIN residual positive;
6. THIN residual > WEAK residual;
7. THIN-WEAK residual gap >= +0.50 ATR;
8. residual cluster-bootstrap lower CI >0;
9. THIN ACCEPT-rate >= WEAK ACCEPT-rate;
10. ACCEPT-rate bootstrap lower CI >0;
11. primary fut_elasticity_60 median THIN > WEAK;
12. primary elasticity state BH q <=0.10;
13. at least one elasticity state feature BH q <=0.10;
14. primary elasticity residual rho >0;
15. primary residual |rho|>=0.05;
16. primary residual BH q<=0.10;
17. rolling HIGH_ELASTICITY residual > LOW_ELASTICITY residual;
18. rolling elasticity bootstrap lower CI >0;
19. 2022 SHORT THIN positive with N>=8;
20. pooled recent THIN positive with N>=15;
21. both 2025H2 and 2026 THIN positive;
22. LONG THIN positive;
23. SHORT THIN positive;
24. THIN frequency >=0.5/month;
25. August not used for selection.

Verdict:
- PASS only if >=19/25 and gates 5,6,8,11,14,18,20,21 pass.
- WATCH if >=13/25 or the primary THIN-vs-WEAK residual direction is positive but proof/transfer is incomplete.
- otherwise FAIL.

## Guardrail
This is a mechanism LAB, not a tradable rule. Any rolling elasticity split is diagnostic-only until independently replicated. Live allocation = 0.
