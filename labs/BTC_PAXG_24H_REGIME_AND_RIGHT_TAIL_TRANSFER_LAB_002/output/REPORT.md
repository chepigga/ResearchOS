# BTC_PAXG_24H_REGIME_AND_RIGHT_TAIL_TRANSFER_LAB_002

**Verdict:** **FAIL_NO_ROBUST_RIGHT_TAIL_TRANSFER**

Coverage: 2021-01-01 00:00:00+00:00 -> 2026-07-31 23:45:00+00:00 | bars 195,578
DEV tail thresholds: CONT +2.068%, REV +1.980%, ABS +3.758%

- BRIDGE_2025: 301 events
- DEV_2021_2024: 1,155 events
- OOS_2026: 174 events

## AUC

|Split|Side|BTC|BTC+PAXG|Delta|
|---|---|---:|---:|---:|
|DEV_2021_2024|CONT|0.5940|0.6196|+0.0256|
|DEV_2021_2024|REV|0.5887|0.6255|+0.0368|
|BRIDGE_2025|CONT|0.4888|0.4888|+0.0000|
|BRIDGE_2025|REV|0.5225|0.4965|-0.0260|
|OOS_2026|CONT|0.3490|0.4336|+0.0846|
|OOS_2026|REV|0.6454|0.6347|-0.0106|

## Router top-20

|Split|Model|N|Tail hit|Mean chosen return|95% CI|
|---|---|---:|---:|---:|---:|
|DEV_2021_2024|BTC_ONLY|231|37.7%|+0.693%|[+0.120%, +1.294%]|
|DEV_2021_2024|BTC_PLUS_PAXG|231|45.9%|+1.263%|[+0.670%, +1.828%]|
|BRIDGE_2025|BTC_ONLY|55|20.0%|-0.098%|[-0.755%, +0.577%]|
|BRIDGE_2025|BTC_PLUS_PAXG|37|16.2%|+0.499%|[-0.243%, +1.208%]|
|OOS_2026|BTC_ONLY|24|37.5%|+0.966%|[-0.681%, +2.697%]|
|OOS_2026|BTC_PLUS_PAXG|35|22.9%|+0.162%|[-0.989%, +1.349%]|

Bridge return delta: +0.596%
OOS return delta: -0.805%
OOS tail-hit delta: -14.6 pp
Bridge avg AUC delta: -0.0130
OOS avg AUC delta: +0.0370
OOS Brier improvement: -0.00383

## OOS regimes

|Regime|N|Cont tail|Rev tail|Mean abs24|
|---|---:|---:|---:|---:|
|GOLD_NEUTRAL__POS_CORR|59|18.6%|23.7%|+2.203%|
|GOLD_DOWN__POS_CORR|51|23.5%|21.6%|+2.490%|
|GOLD_UP__POS_CORR|41|22.0%|9.8%|+1.790%|
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