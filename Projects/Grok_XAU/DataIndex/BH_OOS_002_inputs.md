# BH_OOS_002 Input and Lineage Index

**Status:** complete / validated  
**Date:** 2026-07-24

## Engine

- File: `AK47_FT_EA_156.mq5`
- Declared EA version: 1.56
- BH module: v1.55
- SHA256: `838b3e180a139008c69792c0f122f3da66a590ef5e6ee98056056f0938311b65`
- Role: frozen signal and execution parity contract

## Step 0 source

- File: `XAUUSD_M5.csv`
- Drive ID: `1bxX58zMh1GsYMH-9QUA2w4cK1cKgZkYJ`
- SHA256: `cd2e3285c0e4660786a019999fb3e746257c2cbd4d400fe48092cdbbc7760a80`
- Coverage: 2025-01-01 23:00 through 2026-04-21 23:45
- Use: resampled to M15 for exact historical parity

## Reference baskets

### Wide

- File: `BeltHold_trades_regen_wide-2026-07-05.csv`
- Drive ID: `1i2UF3UkGgxKsv99zxfV8NJ6q4dhwThhO`
- SHA256: `5a31437ac73c561a32a9a294c6dd1bccf29332ba21e95923fbfcf3c019279847`
- Role: canonical parent basket before EMA20 reversal selection

### Tight

- File: `BeltHold_trades_regen_tight-2026-07-05.csv`
- Drive ID: `12REUlcYz5EHgN7A9aZIayXSeFCPi2i1X`
- SHA256: `8aa002b11369e312c2571e855ed26e58110d805026950fc95e1b9ab19d1d0f21`
- Role: EMA10 sensitivity basket, N=56; not canonical N=88 parent

## OOS input

- File: `XAUUSD_M15_202412020100_202607232345.csv`
- SHA256: `7a03c7eca6d333981cc9f30c783f83c31ec15bed46d6b44ae2164a756574f1f3`
- Rows: 38,742
- First bar: 2024-12-02 01:00
- Last bar: 2026-07-23 23:45
- Duplicate timestamps: 0
- Invalid OHLC rows: 0
- Median spread field: 24 points
- 95th percentile spread field: 55 points
- Role: frozen OOS evaluation 2026-05-01..2026-07-23

## Outputs

- `Results/BH_OOS_002/v002/BH_OOS_002_oos_trades.csv`
- `Results/BH_OOS_002/v002/BH_OOS_002_monthly.csv`
- `Results/BH_OOS_002/v002/BH_OOS_002_direction.csv`
- `Results/BH_OOS_002/v002/BH_OOS_002_step0_control_diff.csv`
- `Results/BH_OOS_002/v002/BH_OOS_002_step0_summary.json`
- `Results/BH_OOS_002/v002/BH_OOS_002_oos_summary.json`
- `Results/BH_OOS_002/v002/BH_OOS_002_data_audit.json`
- `Reports/BH_OOS_002_v002_Report.md`
- `Decisions/ADR-BH-OOS-002-PASS.md`

## Verdict

Step 0 PASS. OOS PASS. Demo-only enablement permitted; live prohibited pending
one full forward month.
