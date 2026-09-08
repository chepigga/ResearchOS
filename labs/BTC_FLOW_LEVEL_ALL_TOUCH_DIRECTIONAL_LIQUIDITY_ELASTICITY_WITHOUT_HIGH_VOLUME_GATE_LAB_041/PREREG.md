# BTC_FLOW_LEVEL_ALL_TOUCH_DIRECTIONAL_LIQUIDITY_ELASTICITY_WITHOUT_HIGH_VOLUME_GATE_LAB_041

## Purpose
Test whether directional liquidity elasticity / thin-book continuation exists on the full frozen FLOW→LEVEL TOUCH universe once the historical HIGH_VOLUME gate is removed.

## Frozen lineage
- Source: `BTC_FLOW_LEVEL_PRETOUCH_NET_TAKER_DELTA_PRICE_RESPONSE_AND_CVD_ABSORPTION_LAB_038/output/cvd_absorption_stream.csv`.
- Preserve exact FLOW direction, level/touch timestamp, ACCEPT/REJECT classification, ATR and post-classification residual from LAB035–038.
- Selection/inference uses only `signal_time < 2026-08-01`; August 2026 is audit-only.
- No HIGH_VOLUME restriction.

## Causal state variables
At each touch, all features are already frozen from bars strictly before the touch bar:
- pressure magnitude = `abs(fut_netdelta_norm_60)`;
- directional response = `fut_disp_atr_60`;
- futures elasticity = `fut_disp_atr_60 / max(abs(fut_netdelta_norm_60), 0.25)`;
- spot elasticity = `spot_disp_atr_60 / max(abs(spot_netdelta_norm_60), 0.25)`;
- futures-minus-spot elasticity;
- futures elasticity acceleration = elasticity60 - elasticity15.

For every resolved event, compute thresholds from **all prior resolved touches in the strictly previous 90 calendar days**, current event excluded, minimum 40 prior touches. No global fallback.

Rolling state map:
- THIN_BOOK = pressure magnitude <= prior90 median AND directional response > prior90 median;
- DRIVEN_MOVE = pressure magnitude > prior90 median AND directional response > prior90 median;
- ABSORPTION = pressure magnitude > prior90 median AND directional response <= prior90 median;
- WEAK = pressure magnitude <= prior90 median AND directional response <= prior90 median;
- UNRESOLVED otherwise.

## Primary hypothesis
Within the same LOW_PRESSURE half, THIN_BOOK must beat WEAK on frozen post-classification residual ATR. This isolates low resistance / high price response from CVD magnitude.

Primary tests:
1. THIN_BOOK residual > WEAK residual.
2. 7-day cluster bootstrap of THIN_BOOK − WEAK residual, 5000 draws, seed 20260908.
3. ACCEPT-rate comparison is diagnostic; the mechanism is allowed to affect continuation quality rather than probability of break.

## Secondary causal elasticity diagnostics
Use strictly-prior rolling90 medians on the full universe to classify HIGH_ELASTICITY vs LOW_ELASTICITY from futures elasticity60. Compare residual and 7d cluster bootstrap.
Report threshold-free Spearman elasticity→residual on the resolved LOW_PRESSURE cohort, with BH-FDR across the frozen family:
- fut_elasticity_15/30/60
- spot_elasticity_15/30/60
- fut_minus_spot_elasticity_60
- fut_elasticity_accel_15_60

## Transfer
Report THIN_BOOK by 2021, 2022, 2023, 2024, 2025H1, 2025H2, 2026 Jan-Jul, pooled recent, LONG, SHORT, fixed 2022 SHORT, August audit.
Report frequency/month.

## Gates
1 all classified pre-Aug >=1900;
2 feature coverage >=95%;
3 rolling resolved >=85%;
4 THIN N>=250;
5 WEAK N>=250;
6 THIN residual positive;
7 THIN residual > WEAK;
8 THIN-WEAK gap >=0.30 ATR;
9 residual bootstrap CI lower >0;
10 THIN ACCEPT >= WEAK ACCEPT (diagnostic);
11 THIN frequency >=3/month;
12 rolling HIGH_ELASTICITY residual > LOW_ELASTICITY;
13 rolling elasticity gap >=0.20 ATR;
14 rolling elasticity bootstrap CI lower >0;
15 primary elasticity rho positive;
16 |primary rho|>=0.05;
17 primary rho BH q<=0.10;
18 any elasticity feature BH q<=0.10;
19 LONG THIN positive N>=100;
20 SHORT THIN positive N>=100;
21 2022 SHORT positive N>=20;
22 pooled recent positive N>=80;
23 2025H2 positive;
24 2026 positive;
25 August not used.

PASS only if >=19/25 and gates 6,7,9,12,14,22,23,24 pass. WATCH if >=13/25 or THIN has a meaningful positive gap but proof/transfer incomplete. Otherwise FAIL.

## Guardrail
Mechanism test only. No entry, stop, take-profit or sizing optimization. Any rolling state remains research-only until independent execution replication. Live allocation = 0.
