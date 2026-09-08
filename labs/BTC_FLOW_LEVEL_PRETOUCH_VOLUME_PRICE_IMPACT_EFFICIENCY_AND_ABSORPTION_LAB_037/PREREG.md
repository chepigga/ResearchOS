# BTC_FLOW_LEVEL_PRETOUCH_VOLUME_PRICE_IMPACT_EFFICIENCY_AND_ABSORPTION_LAB_037

## Purpose
Test whether pre-touch price-impact efficiency separates high-volume level acceptance (ignition) from high-volume rejection (absorption), while preserving the frozen FLOW / level / touch / acceptance lineage from LAB035–036.

## Frozen lineage
- Source activation state: `BTC_FLOW_LEVEL_PREBREAK_VOLUME_IGNITION_VS_ABSORPTION_AND_OI_CONTINUATION_LAB_036/output/volume_activation_stream.csv`.
- Use only LAB036 rows with `signal_time < 2026-08-01` for selection/inference. August 2026 remains audit-only.
- FLOW direction, 12h level, touch time, ACCEPT/REJECT classification, ATR, LAB035 residual, and LAB036 HIGH_VOLUME flag are frozen and must not be recomputed or retuned.
- Primary comparison is restricted to frozen `HIGH_VOLUME` touches: `IGNITION` = HIGH_VOLUME+ACCEPT vs `ABSORPTION` = HIGH_VOLUME+REJECT.

## Data
Binance BTCUSDT spot and USD-M futures 15m klines via the same downloader used by LAB034/036. Required fields: close, quote volume, taker-buy quote volume. Touch bar is excluded from every pre-touch feature.

## Causal feature construction
For each touch at M15 open timestamp `t`, use only fully closed bars strictly before `t`.
For windows 15m / 30m / 60m:
1. directional displacement in ATR = `side * (last_pre_touch_close - close_before_window) / frozen_atr14`;
2. aligned aggressive taker notional = taker-buy quote for LONG flow; `(quote - taker_buy_quote)` for SHORT flow, summed over the window;
3. normalize aggressive notional by its strictly-prior trailing-90d median for the same venue/window (minimum 30d history);
4. impact efficiency = directional displacement ATR / normalized aligned aggressive notional.

Positive high impact = relatively large price progress for the amount of aligned aggressive capital. Low/negative impact under high volume = absorption-like behavior.

Frozen feature family (7):
- `fut_impact_eff_15`
- `fut_impact_eff_30`
- `fut_impact_eff_60` (PRIMARY)
- `spot_impact_eff_15`
- `spot_impact_eff_30`
- `spot_impact_eff_60`
- `fut_minus_spot_impact_60`

No threshold search, no level search, no entry/SL/TP optimization.

## Primary hypotheses / tests
A. **Ignition vs absorption discrimination**
- On frozen HIGH_VOLUME pre-Aug rows, compare each impact feature between IGNITION and ABSORPTION with Mann–Whitney U / rank-biserial effect.
- Direction expected: IGNITION > ABSORPTION for `fut_impact_eff_60`.
- BH-FDR across the 7 frozen impact features.

B. **Residual quality after classification**
- On ACCEPT rows pre-Aug, Spearman correlation between each frozen impact feature and frozen LAB035 post-classification residual ATR.
- BH-FDR across the 7 features.
- Primary expected sign for `fut_impact_eff_60`: positive.

C. **Cluster robustness**
- For HIGH_VOLUME rows, compute a 7-day cluster bootstrap of mean LAB035 residual for the top vs bottom half of `fut_impact_eff_60`, split by the unconditional pre-Aug median only. This is a reporting contrast, not a promoted trading threshold.
- 5000 draws, fixed seed 20260908.

## Transfer slices
Report frozen primary feature and residual by:
- 2021, 2022, 2023, 2024, 2025H1, 2025H2, 2026 Jan-Jul;
- LONG / SHORT;
- fixed stress slice 2022 SHORT;
- pooled recent 2025H2+2026;
- August 2026 audit only.

## PASS / WATCH / FAIL gates
1. frozen LAB036 high-volume lineage >= 500 rows;
2. futures impact coverage >=95%;
3. spot impact coverage >=95%;
4. IGNITION >=150 and ABSORPTION >=100;
5. primary `fut_impact_eff_60` IGNITION > ABSORPTION;
6. primary rank-biserial magnitude >=0.10;
7. primary state-discrimination BH q <=0.10;
8. at least one frozen impact feature state-discrimination BH q <=0.10;
9. primary ACCEPT residual Spearman rho >0;
10. primary ACCEPT residual |rho| >=0.05;
11. primary residual BH q <=0.10;
12. high-impact-half minus low-impact-half HIGH_VOLUME residual >= +0.15 ATR;
13. cluster bootstrap CI lower bound >0;
14. 2022 SHORT high-impact residual positive with N>=20;
15. pooled recent high-impact residual positive with N>=40;
16. both 2025H2 and 2026 high-impact residual positive;
17. August not used for selection.

Verdict labels:
- PASS only if >=14/17 and gates 5,7,9,13,16 pass.
- WATCH if >=9/17 or mechanism is directionally useful but transfer/statistical proof incomplete.
- otherwise FAIL.

## Guardrails
This LAB tests mechanism only. Any median-half or transfer slice is diagnostic and cannot be promoted to an EA rule without an independent replication LAB. Live allocation = 0.
