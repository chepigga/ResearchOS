# BTC_FLOW_LEVEL_PRETOUCH_NET_TAKER_DELTA_PRICE_RESPONSE_AND_CVD_ABSORPTION_LAB_038

## Purpose
Test whether pre-touch NET taker pressure and its price response separate frozen HIGH_VOLUME level ACCEPT (ignition) from frozen HIGH_VOLUME REJECT (absorption), improving on LAB037's aligned gross-volume impact metric.

## Frozen lineage
- Parent: `BTC_FLOW_LEVEL_PRETOUCH_VOLUME_PRICE_IMPACT_EFFICIENCY_AND_ABSORPTION_LAB_037`.
- Frozen event identity and labels come from LAB037 `impact_stream.csv` / LAB036 lineage: FLOW direction, 12h level, touch time, ACCEPT/REJECT, HIGH_VOLUME, ATR, and LAB035 post-classification residual.
- Selection/inference: `signal_time < 2026-08-01`. August 2026 audit-only.
- No recomputation or tuning of FLOW, level, touch, acceptance, high-volume threshold, entry, stop, or TP.

## Data
Binance BTCUSDT spot and USD-M futures 15m klines using the same causal downloader as LAB034–037. Touch bar is excluded from every pre-touch feature.

## Causal definitions
For each fully closed pre-touch M15 window W in {15m,30m,60m}:
- quote volume = total quote volume;
- net taker delta = `2*taker_buy_quote - quote_volume`;
- directional aligned net delta = `side * sum(net_delta)` where side is frozen FLOW direction;
- normalized aligned net delta = aligned net delta divided by the strictly-prior trailing-90d median absolute net delta for the same venue/window (minimum 30d history);
- directional price response ATR = `side * (last_pre_touch_close - close_before_window) / frozen_ATR14`;
- response efficiency = directional price response ATR / `max(abs(normalized_aligned_net_delta), 0.25)`; denominator floor 0.25 is fixed ex ante to prevent near-zero delta explosions;
- absorption gap = normalized aligned net delta - directional price response ATR. Large positive gap means strong aligned pressure with weak price progress.

CVD here is the cumulative net taker delta over the fixed 15/30/60m window, not a future-running cumulative series.

## Frozen feature family (12)
1. `fut_netdelta_norm_15`
2. `fut_netdelta_norm_30`
3. `fut_netdelta_norm_60`
4. `spot_netdelta_norm_15`
5. `spot_netdelta_norm_30`
6. `spot_netdelta_norm_60`
7. `fut_response_eff_60` (PRIMARY ignition efficiency)
8. `spot_response_eff_60`
9. `fut_absorption_gap_60` (PRIMARY absorption signature)
10. `spot_absorption_gap_60`
11. `fut_minus_spot_netdelta_60`
12. `fut_minus_spot_absorption_gap_60`

## Primary hypotheses
### A. Ignition vs absorption state discrimination on frozen HIGH_VOLUME touches
- `fut_response_eff_60`: IGNITION > ABSORPTION.
- `fut_absorption_gap_60`: ABSORPTION > IGNITION.
- Mann–Whitney U / rank-biserial for all 12 frozen features; BH-FDR across 12.

### B. ACCEPT quality after classification
On all pre-Aug ACCEPT rows, threshold-free Spearman feature vs frozen LAB035 post-classification residual ATR; BH-FDR across 12.
Expected:
- `fut_response_eff_60` rho > 0;
- `fut_absorption_gap_60` rho < 0.

### C. Fixed 2x2 mechanism map on HIGH_VOLUME touches
No optimized cutoffs. Use strictly pre-Aug unconditional medians of:
- aligned futures net delta (`fut_netdelta_norm_60`),
- directional price response ATR (`fut_disp_atr_60`).
Map four cells:
1. HIGH_PRESSURE + HIGH_RESPONSE = efficient ignition candidate;
2. HIGH_PRESSURE + LOW_RESPONSE = absorption candidate;
3. LOW_PRESSURE + HIGH_RESPONSE = thin-liquidity candidate;
4. LOW_PRESSURE + LOW_RESPONSE = weak/noise.
Report ACCEPT rate and post-classification residual by cell. The medians are diagnostic-only and cannot become an EA rule without replication.

### D. 7-day cluster bootstrap
On frozen HIGH_VOLUME rows compare cell 1 (HIGH_PRESSURE+HIGH_RESPONSE) vs cell 2 (HIGH_PRESSURE+LOW_RESPONSE) for:
- ACCEPT rate difference;
- mean frozen LAB035 residual difference among classified events.
5000 draws, seed 20260908.

## Transfer slices
Report the primary cell and primary continuous metrics for:
- 2021, 2022, 2023, 2024, 2025H1, 2025H2, 2026 Jan-Jul;
- LONG, SHORT;
- 2022 SHORT stress slice;
- pooled recent 2025H2+2026;
- August 2026 audit-only.

## Gates
1. frozen HIGH_VOLUME pre-Aug >=500;
2. futures net-delta coverage >=95%;
3. spot net-delta coverage >=95%;
4. IGNITION>=150 and ABSORPTION>=100;
5. primary response efficiency IGNITION > ABSORPTION;
6. primary response efficiency RBC >= +0.10;
7. primary response efficiency BH q <=0.10;
8. primary absorption gap ABSORPTION > IGNITION;
9. primary absorption gap state BH q <=0.10;
10. at least one state feature BH q <=0.10;
11. ACCEPT residual rho(response_eff)>0;
12. ACCEPT residual rho(absorption_gap)<0;
13. at least one residual feature BH q <=0.10;
14. efficient-ignition cell ACCEPT rate exceeds absorption cell by >=0.05;
15. efficient-ignition minus absorption cell residual >=+0.20 ATR;
16. cluster bootstrap ACCEPT-rate CI lower >0;
17. cluster bootstrap residual-difference CI lower >0;
18. 2022 SHORT efficient-ignition residual positive N>=20;
19. pooled recent efficient-ignition residual positive N>=40;
20. both 2025H2 and 2026 efficient-ignition residual positive;
21. August not used for selection.

Verdict:
- PASS if >=17/21 and critical gates 5,7,8,9,16,17,20 pass.
- WATCH if >=11/21 or mechanism is directionally useful but incomplete.
- otherwise FAIL.

## Guardrail
Mechanism discovery only. No execution policy is promoted. Live allocation = 0.
