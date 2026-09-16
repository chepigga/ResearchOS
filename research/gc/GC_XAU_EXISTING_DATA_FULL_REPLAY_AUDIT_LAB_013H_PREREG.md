# GC_XAU_EXISTING_DATA_FULL_REPLAY_AUDIT_LAB_013H — PREREG

## Purpose

Verify the entire current `BUYER_BREAKOUT_LONG_001 -> FTMO XAU D1 limit` historical chain using only the already-collected frozen data. No new market data are required for this audit.

This LAB exists because LAB013 forward parity and historical implementation/data replay answer different questions. LAB013 remains frozen as a forward protocol; LAB013H does not rewrite it.

## Frozen data

### AMP/CQG GC

- Asset: `AMP_GC_HISTORY_EXPORTER_001_GCEZ26_20260806_182355__20260915_182355_TICKS.csv.zip`
- SHA256: `81d675597368a9f6c78eee726ed547737366ffd8d8e54aa976bce50111db752b`
- Symbol: `GCEZ26`
- Frozen loader semantics: `volume_real` if >0 else `volume`; BUY only when `is_buy=1 AND is_sell=0`; SELL only when `is_sell=1 AND is_buy=0`; all other directional states excluded.

### FTMO-Demo XAUUSD

Use the same 32 daily raw-tick files already frozen by LAB006–011, 2026-08-03 through 2026-09-15. The workflow reuses the exact frozen Drive IDs from LAB006. Required metadata spot checks: `FTMO-Demo`, `COPY_TICKS_ALL`.

Execution uses actual XAU Bid/Ask raw ticks. No synthetic spread is substituted.

## Frozen sensor

`BUYER_BREAKOUT_LONG_001`, completed GC M1 bars only:

- `a_buy = delta_frac >= prior240 Q90(delta_frac) AND buy_vol >= prior240 Q75(buy_vol)`
- `high >= prior20_high`
- `close > open`
- `close_pos >= 0.75`
- positive `body_atr`
- event enters only if the next reconstructed GC M1 bar is exactly clock-contiguous.

No threshold, session, regime, depth, exit, or side is changed.

## Audit A — independent GC implementation parity

Build the complete AMP GC M1 timeline twice:

1. canonical path from `gc_m1_orderflow_edge_discovery_003.py`;
2. independent replay written for LAB013H directly from the raw AMP CSV.

Compare on every common reconstructed M1 bar:

- OHLC
- buy/sell volume
- delta fraction
- ATR14
- body_atr
- close_pos
- causal Q90 delta
- causal Q75 buy volume
- prior20 high
- `a_buy`
- `BUYER_BREAKOUT_LONG_001`

Also compare eligible event timestamps and 5m/15m event returns against the frozen LAB004 AMP event ledger.

## Audit B — XAU raw/execution replay

From the existing 32 FTMO XAU raw-tick files:

- verify file count, quote-valid rows, timestamp order, positive/non-crossed Bid/Ask;
- rebuild XAU M1 mid-price ATR14;
- recalibrate the broker-clock offset on the frozen grid `[-240,+240]` minutes in 30-minute steps;
- require the historical best offset to reproduce the frozen clock alignment;
- rebuild executable AMP signal references from raw XAU ticks;
- independently simulate frozen D1.00 limit execution.

### Operational D1 E3 incumbent

- depth = `1.00 * XAU ATR14(M1)` below contemporaneous market Ask;
- expiry = 3 minutes;
- fill when Ask first touches/crosses the limit; fill price is the limit price, matching LAB008/009 historical implementation;
- SL = 1.50 ATR;
- TP = 3R = 4.50 ATR;
- hard timeout = original signal clock +30 minutes;
- path for SL/TP/timeout = Bid;
- one active setup at a time;
- `+0.05R` adverse cost per filled trade.

Compare D1 E3 independent replay against the frozen LAB009 `AMP_ALL / ONE_ACTIVE_SETUP / 0.050R` metrics.

### Historical E1 diagnostic

Replay the exact same geometry with expiry = 1 minute. This is descriptive only. It does not promote E1 because the 1m expiry was discovered post hoc in LAB011.

## PASS conditions

`HISTORICAL_REPLAY_PASS` requires:

- AMP source SHA exact;
- independent GC reconstruction has identical bar timestamps to canonical reconstruction;
- exact `a_buy` and final signal parity;
- all numeric feature differences within stated floating tolerances;
- eligible AMP event timestamp set identical to LAB004;
- LAB004 5m/15m event returns reproduced within tolerance;
- 32 non-empty XAU trading-day files present;
- XAU quote-valid data monotonic and non-crossed;
- clock calibration reproduces the frozen offset;
- D1 E3 independent replay reproduces LAB009 fills and core R metrics within tolerance.

A PASS means the historical implementation/data chain is internally reproducible. It is **not independent OOS evidence** and does not convert the historical candidate into production-certified edge.
