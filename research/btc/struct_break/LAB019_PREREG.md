# OLD_PROTECTED_PIVOT_ASYMMETRIC_EVENT_REPLICATION_LAB_019

Date: 2026-08-25
Branch: lab/btc-struct-break-regime-004

## Frozen seeds from LAB018

A. COMPRESSION_RELEASE SELL only
B. FAILED_RESPONSE_RELEASE BUY only

No side switching, threshold optimization, ML, or feature additions.

## Common protected-pivot context
- M15 pivot 5-5 stop anchor
- pivot age >= 22 M15 bars
- pivot unviolated after confirmation through entry
- riskATR > 3.72
- TP = 2.3R
- BE after +1R
- cost = 0.06R base
- one active position per family
- 2026 excluded from primary verdict

## Frozen event definitions
Use LAB018 operational definitions exactly, commit e125b52a43a13bdf53929a7f162d1e21a19c9867.

### COMPRESSION_RELEASE SELL
- six completed M15 bars before release define compression range
- compression range <= 0.70 of rolling 43-bar median six-bar range
- release bar bearish close below compression low
- release candle body fraction >= 0.50
- retest of broken compression low within next 8 M15 bars
- entry at broken level on first retest

### FAILED_RESPONSE_RELEASE BUY
- bearish failed-response origin from confirmed pivot-3 high
- at least 2 of next 3 bars bearish and close at bar k+3 below origin close
- response must not violate prior confirmed pivot-3 low
- first close above origin high in bars k+4..k+12 is release
- retest within next 8 M15 bars
- entry at origin high on first retest

## Replication tests
1. Frozen full-sample 2019-2025 metrics, reported only as lineage consistency (not independent proof).
2. Leave-one-calendar-year-out / yearly sign stability across 2019-2025, with particular focus on 2023-2025 transfer.
3. Cost stress 1.0x, 1.25x, 1.5x.
4. Exact M1 execution replay where M1 data are available (2024-2025), preserving M15 signals and levels, for fill/SL/TP/BE ordering.
5. Side-specific trade overlap and one-global-position portfolio with the frozen BREAK_RETEST control core.
6. Block-bootstrap / paired portfolio uncertainty.
7. 2026 shadow only; not used for promotion.

## Promotion gates per seed
- DEV sign > 0 and VAL sign > 0
- VAL EV >= +0.08R
- VAL PF >= 1.15
- at least 2/3 positive VAL years
- 1.5x-cost VAL EV > 0
- M1 replay must not reverse the sign on 2024-2025
- no material dependence on one single VAL year (>70% of VAL sumR from one year = concentration warning)

## Portfolio admission gate
For BREAK_RETEST control + both frozen seeds, one active position globally:
- VAL portfolio EV > 0
- PF >= 1.20
- MaxDD not worse than control-only by more than 25%
- at least 2/3 positive VAL years
- 1.25x cost EV > 0

Venue replication is attempted only if an independent BTC M15 venue dataset already exists in ResearchOS/local assets. If no such dataset is available, this limitation must be stated explicitly and no venue claim may be made.
