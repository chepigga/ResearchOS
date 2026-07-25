# FT_DEEP_001 partial result

**Status:** INCONCLUSIVE  
**Input:** `XAUUSD_M5_20220601_20260723.csv`  
**Input SHA256:** `43a00406241ccad5136c111e9f58f06494abd2883507bbbf350eaa172d8be4c4`

## Coverage

- rows: `100,000`
- first: `2025-02-19 06:30`
- last: `2026-07-23 23:45`
- calendar depth: `17.05 months`
- D1 warmup-complete start: `2025-12-03 01:05`
- warmup-complete evaluable depth: `7.62 months`

The file is truncated and cannot support the registered 42-month verdict.

## Step 0

- NYBUY: oracle `18`, tester target `17`, delta `+1` — count PASS.
- LONBUY: oracle `7`, diagnostic tester reference `7`, delta `0` — count PASS.
- required entry-time overlap: BLOCKED because tester 156-1 entry fixture is missing.

Step 0 status: `COUNT_PASS / TIME_OVERLAP_BLOCKED`.

## Warmup-complete diagnostic

- N: `27`
- EV_net: `+2.160244R`
- Sum: `+58.326586R`
- WR: `59.26%`
- PF: `6.050`
- NYBUY: N=20, EV=`+2.85R`, Sum=`+57.0R`
- LONBUY: N=7, EV=`+0.189512R`, Sum=`+1.326586R`

## Regime diagnostics

- zero-entry months: `4/8`
- top-three months: `93.31%` of total R
- zero months: March, May, June and July 2026
- HTF blocks: NYBUY `5,087`; LONBUY `5,927`

This exceeds the frozen 70% REGIME concentration trigger, but the formal verdict remains INCONCLUSIVE because depth is below 24 months and N is below 90.

## Files

- `FT_DEEP_trades.csv` — warmup-complete trade-level output.
- `FT_DEEP_monthly.csv` — monthly N/EV/sumR including zero months.
- `FT_DEEP_step0_count_parity.csv` — count gate and unresolved time-overlap gate.
- `FT_DEEP_reject_summary.csv` — aggregated reject funnel.
- [Report](../../../Reports/FT_DEEP_001_PartialRun_2026-07-25.md)
- [Optimized oracle](../../../Code/Python/FT_DEEP_Oracle_v002.py)
- [Chunked exporter](../../../Code/Exporters/XAUUSD_M5_DEEP_Exporter_v002.mq5)
