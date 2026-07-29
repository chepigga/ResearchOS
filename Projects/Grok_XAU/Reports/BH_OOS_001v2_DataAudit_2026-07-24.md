# BH_OOS_001v2 Data Audit

**Date:** 2026-07-24  
**Laboratory:** BH_OOS_001 v2  
**Status:** DATA_COVERAGE_FAIL / OOS NOT OPENED

## Uploaded file

- Filename: `XAUUSD_M15_202601020100_202607172345.csv`
- SHA256: `cf73c81110f2fc6451accee4b602750e4ab852ae2df656fde76dec4fa1915495`
- Data rows: `12,818`
- First bar: `2026-01-02 01:00:00`
- Last bar: `2026-07-17 23:45:00`
- Ordering: monotonic increasing
- Duplicate timestamps: `0`
- Invalid OHLC rows: `0`

## Spread diagnostics

- Minimum: `0` points
- Median: `42` points
- Mean: `42.996` points
- 95th percentile: `60` points
- Maximum: `140` points

The observed median exceeds the earlier working assumption of approximately 30-35 points. This does not alter the preregistered `-0.05R/trade` correction for BH_OOS_001v2; it is recorded for later execution-sensitivity work only.

## Coverage gate

Required frozen coverage:

- warmup/control source: `2024-12-01` onward;
- OOS endpoint: `2026-07-23`.

Actual coverage misses:

- all bars from `2024-12-01` through `2026-01-02 00:45`;
- all bars after `2026-07-17 23:45` through the registered endpoint `2026-07-23`.

Therefore the original `N=88 (B52/S36), EV=+0.276R` control cannot be reproduced from this file, and Step 1 must not be opened under the preregistered protocol.

## Decision

- Step 0: **NOT RUN — insufficient control coverage**
- Step 1: **NOT RUN — control gate not passed and OOS tail incomplete**
- Formal verdict: **none**
- `InpBH_Enable`: remains `false`

No partial OOS expectancy or PASS/FAIL result is reported, to avoid contaminating the preregistered validation before the control gate is satisfied.

## Required replacement export

Same broker feed, XAUUSD M15, exact requested range:

`2024-12-01 00:00:00` through at least `2026-07-23 23:45:00`.

Before rerunning the exporter, load/download older M15 history in the same MT5 terminal until December 2024 is available.