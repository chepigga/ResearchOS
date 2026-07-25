# FT_DEEP_001 Input Index

**Status:** incomplete / blocked

| Artifact | Required | Current state |
|---|---|---|
| Frozen TZ | `TZ-FT-DEEP-001` | received; SHA256 `8438dd2b8affeedb882cfd18e1ae9a0e17077337dbacd90c8de9df24afa5bd8c` |
| Engine source | `AK47_FT_EA_156.mq5` | received; SHA256 `838b3e180a139008c69792c0f122f3da66a590ef5e6ee98056056f0938311b65` |
| Full same-feed XAUUSD M5 | 2022-06-01 warmup through 2026-07-23 | missing |
| Available XAUUSD M5 | 2025-01-01 23:00 through 2026-04-21 23:45 | received; 95,466 rows; SHA256 `cd2e3285c0e4660786a019999fb3e746257c2cbd4d400fe48092cdbbc7760a80` |
| Tester 156-1 entry fixture | NYBUY/LONBUY entry times for 2026-01-01..2026-07-23 | missing |
| Historical candidate diagnostic | `AK47_v154b_oracle_outcomes.csv` | accessible in File Library; not a substitute for v1.56 parity |

## Required next input

Run `Code/Exporters/XAUUSD_M5_DEEP_Exporter_v001.mq5` in the same broker
terminal and upload `XAUUSD_M5_20220601_20260723.csv`.

Also upload the tester 156-1 deals/signals export so Step 0 can calculate the
registered >=80% entry-time overlap.
