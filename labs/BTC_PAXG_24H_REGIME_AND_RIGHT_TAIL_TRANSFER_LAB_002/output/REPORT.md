# BTC_PAXG_24H_REGIME_AND_RIGHT_TAIL_TRANSFER_LAB_002

**Verdict:** **FAIL_NO_ROBUST_RIGHT_TAIL_TRANSFER**

Coverage: 2021-01-01 00:00:00+00:00 -> 2026-08-31 23:45:00+00:00 | bars 198,554
DEV tail thresholds: CONT +2.068%, REV +1.980%, ABS +3.758%

- BRIDGE_2025: 301 events
- DEV_2021_2024: 1,155 events
- OOS_2026: 203 events

## AUC

|Split|Side|BTC|BTC+PAXG|Delta|
|---|---|---:|---:|---:|
|DEV_2021_2024|CONT|0.5940|0.6196|+0.0256|
|DEV_2021_2024|REV|0.5887|0.6255|+0.0368|
|BRIDGE_2025|CONT|0.4888|0.4888|+0.0000|
|BRIDGE_2025|REV|0.5225|0.4965|-0.0260|
|OOS_2026|CONT|0.3825|0.4567|+0.0742|
|OOS_2026|REV|0.6330|0.6164|-0.0166|

## Router top-20

|Split|Model|N|Tail hit|Mean chosen return|95% CI|
|---|---|---:|---:|---:|---:|
|DEV_2021_2024|BTC_ONLY|231|37.7%|+0.693%|[+0.120%, +1.294%]|
|DEV_2021_2024|BTC_PLUS_PAXG|231|45.9%|+1.263%|[+0.670%, +1.828%]|
|BRIDGE_2025|BTC_ONLY|55|20.0%|-0.098%|[-0.755%, +0.577%]|
|BRIDGE_2025|BTC_PLUS_PAXG|37|16.2%|+0.499%|[-0.243%, +1.208%]|
|OOS_2026|BTC_ONLY|27|37.0%|+1.109%|[-0.457%, +2.887%]|
|OOS_2026|BTC_PLUS_PAXG|39|20.5%|-0.179%|[-1.349%, +0.962%]|

Bridge return delta: +0.596%
OOS return delta: -1.288%
OOS tail-hit delta: -16.5 pp
Bridge avg AUC delta: -0.0130
OOS avg AUC delta: +0.0288
OOS Brier improvement: -0.00418

## OOS regimes

|Regime|N|Cont tail|Rev tail|Mean abs24|
|---|---:|---:|---:|---:|
|GOLD_NEUTRAL__POS_CORR|65|21.5%|23.1%|+2.376%|
|GOLD_DOWN__POS_CORR|61|21.3%|18.0%|+2.234%|
|GOLD_UP__POS_CORR|54|22.2%|11.1%|+2.167%|
|GOLD_UP__LOW_CORR|11|18.2%|0.0%|+1.781%|
|GOLD_NEUTRAL__LOW_CORR|7|14.3%|0.0%|+1.345%|
|GOLD_DOWN__LOW_CORR|5|40.0%|20.0%|+3.146%|

## Gates
- PASS — oos_events_ge_100
- FAIL — bridge_avg_auc_delta_positive
- PASS — oos_avg_auc_delta_ge_0.02
- FAIL — oos_avg_brier_improves
- PASS — bridge_top20_return_delta_positive
- FAIL — oos_top20_return_delta_positive
- FAIL — oos_top20_tail_hit_delta_ge_0.05
- FAIL — transfer_same_sign

Score 3/8 -> FAIL_NO_ROBUST_RIGHT_TAIL_TRANSFER

No 2026 tuning is authorized after this result.