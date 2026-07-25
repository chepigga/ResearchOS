# FT_DEEP_001 Input Index

**Status:** partial input received / formal run blocked

| Artifact | Required | Current state |
|---|---|---|
| Frozen TZ | `TZ-FT-DEEP-001` | received; SHA256 `8438dd2b8affeedb882cfd18e1ae9a0e17077337dbacd90c8de9df24afa5bd8c` |
| Engine source | `AK47_FT_EA_156.mq5` | received; SHA256 `838b3e180a139008c69792c0f122f3da66a590ef5e6ee98056056f0938311b65` |
| Full same-feed XAUUSD M5 | 2022-06-01 warmup through 2026-07-23 | still missing |
| Uploaded deep export | filename `XAUUSD_M5_20220601_20260723.csv` | received but truncated to exactly 100,000 rows; actual coverage 2025-02-19 06:30..2026-07-23 23:45; SHA256 `43a00406241ccad5136c111e9f58f06494abd2883507bbbf350eaa172d8be4c4` |
| Chunked replacement exporter | avoid single-request truncation | `Code/Exporters/XAUUSD_M5_DEEP_Exporter_v002.mq5`; SHA256 `179a50d7026e66418e8e7083e7b4e7c804ee004fb2ab52eb7df5aa513edc6a17` |
| Frozen oracle v001 | exact v1.56 replay | committed under `Code/Python/FT_DEEP_Oracle_v001.py` |
| Optimized oracle v002 | equivalent cached/numba computation | committed under `Code/Python/FT_DEEP_Oracle_v002.py`; local SHA256 `3bd381eb0074b3986a197d1f1b23fcbbb7c0e6b0c94729465bd27252166dbe65` |
| Tester 156-1 entry fixture | NYBUY/LONBUY entry times for 2026-01-01..2026-07-23 | missing; required for >=80% time-overlap gate |
| v1.52 count diagnostic | NYBUY 16 / LONBUY 7 | accessible in historical backlog; supportive only, not a time-parity fixture |
| Historical candidate diagnostic | `AK47_v154b_oracle_outcomes.csv` | diagnostic only; not a substitute for v1.56 parity |

## Uploaded file audit

- rows: `100,000`
- first bar: `2025-02-19 06:30`
- last bar: `2026-07-23 23:45`
- duplicate timestamps: `0`
- invalid OHLC rows: `0`
- median spread: `25` points
- p95 spread: `58` points
- calendar depth: `17.05 months`
- D1 EMA50 warmup-complete start: `2025-12-03 01:05`
- warmup-complete evaluable depth: `7.62 months`

## Partial result package

Repository summary and compact CSVs:

- `Results/FT_DEEP_001/partial_2026-07-25/README.md`
- `Results/FT_DEEP_001/partial_2026-07-25/FT_DEEP_trades.csv`
- `Results/FT_DEEP_001/partial_2026-07-25/FT_DEEP_monthly.csv`
- `Results/FT_DEEP_001/partial_2026-07-25/FT_DEEP_step0_count_parity.csv`
- `Results/FT_DEEP_001/partial_2026-07-25/FT_DEEP_reject_summary.csv`

The full reject-event CSV is stored in the downloadable partial artifact package rather than committed as a large repository text file.

## Required next inputs

1. Run `Code/Exporters/XAUUSD_M5_DEEP_Exporter_v002.mq5` in the same broker terminal.
2. Upload `XAUUSD_M5_20220601_20260723_FULL.csv` and verify first/last timestamps.
3. Upload tester 156-1 `AK47_ea_dryrun_signals.csv` or equivalent entry-time export.
4. Re-run Step 0 before opening the formal 42-month verdict.
