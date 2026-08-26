# BTC_LOW_ACTIVITY_FLOW_ALIGNMENT_FLIP_LAB_008 — VERDICT

## Frozen hypothesis

- Target: CLEAN MFE >= 2.5R within 32 M15 bars before structural SL.
- LOW ACTIVITY: at least 2 of 3 frozen LAB007 features below their 2023-2025 Q20 thresholds:
  - counter_volume_z_3 <= -0.6860859555
  - total_volume_z_6 <= -0.6452099475
  - trades_z_12 <= -0.6733550471
- FLOW ALIGNMENT: flow_delta_12 > 0 in future BOS direction.
- FLOW FLIP: flow_flip_3v3 > 0.
- PRIMARY: LOW_ACTIVITY_SCORE >= 2 AND (ALIGNMENT OR FLIP).

2026 is exposed from LAB007 and is diagnostic only. Independent replication is untouched 2019-2022.

## Results

Native Binance full sample: 5984 signals, 3276 executable events, 479 LARGE (14.62%).

### Discovery 2023-2025
- Baseline 15.32%.
- LOW2_ONLY: 56/268 = 20.90%, +5.57pp.
- PRIMARY: 41/213 = 19.25%, +3.93pp.
- Alignment/flip reduced LOW2 by -1.65pp.

### Exposed 2026
- Baseline 16.24%.
- LOW2_ONLY: 10/41 = 24.39%, +8.15pp.
- PRIMARY: 10/37 = 27.03%, +10.79pp.
- LOW2_X_ALIGN: 7/22 = 31.82%, +15.58pp.
- Diagnostic only; not fresh OOS.

### Independent 2019-2022
- Baseline 13.75%, N=1615.
- LOW2_ONLY: 41/277 = 14.80%, +1.06pp.
- PRIMARY: 32/218 = 14.68%, +0.93pp.
- LOW2_X_ALIGN: 22/137 = 16.06%, +2.31pp.
- LOW2_X_ALIGN_AND_FLIP: 15/88 = 17.05%, +3.30pp.
- Frozen state-score AUC = 0.5165; AP = 0.1439.
- None of the fixed independent rules reached conventional statistical significance versus complement.

### Primary yearly transfer
- 2020: +9.41pp
- 2021: -7.25pp
- 2022: +3.61pp
- 2023: +3.90pp
- 2024: +10.77pp
- 2025: -3.11pp
- 2026: +10.79pp (exposed)

## Verdict

The broad LOW ACTIVITY + ALIGNMENT/FLIP hypothesis does **not** pass strict regime-independent replication. The 2026 result is strong but already exposed. On untouched 2019-2022, the primary rule adds only +0.93pp and the frozen score is nearly random (AUC 0.5165).

There is a weaker residual signal in **LOW ACTIVITY + FLOW ALIGNMENT** (+2.31pp independent) and **LOW ACTIVITY + ALIGNMENT AND FLIP** (+3.30pp, smaller n), but 2021 breaks both badly. Treat this as a **regime-dependent candidate**, not an EA selector.

Next research should test whether the effect is conditionally stable by volatility/trend/liquidity regime using only pre-registered regime variables. Do not optimize new flow thresholds on the same years.
