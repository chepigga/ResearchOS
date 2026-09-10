# LAB008 runtime addendum — frozen before outcome computation

This addendum records parser/censoring details discovered by the schema-only probe. It does not alter selectors, thresholds, directions, RR, or costs.

## Observed archive schema
The sealed release archive contains daily CSV members with header:
`time_msc,time_server,bid,ask,spread_price,spread_points,last,volume,volume_real,flags`.
Primary LAB008 uses server timestamps and aggregates raw ticks to causal M1 bid OHLC plus ask OHLC/tick count. Weekend header-only members are allowed.

Although the archive contains 2026-08-26 and 2026-08-27, primary fresh outcomes are capped at **2026-08-25 23:59:59.999** exactly as preregistered. No later ticks may resolve earlier entries.

## Right-censoring
For a signal whose SL or TP is hit before the cap, the observed hit is valid even if 120h has not elapsed.
If neither SL nor TP is hit and `entry_time + 120h` is later than the primary data cap, label the event `CENSORED` and exclude it from EV/PF/DD/WR/CumR. Report censored counts separately.
A normal `TIME` exit is allowed only when a complete 120h horizon exists before the cap.

## Historical candidate parity
Before accepting fresh outcomes, reconstruct frozen H1 mechanic candidates on historical data and compare `(H1 bar open time, direction)` against the stored LAB001 XAU pool on a recent fully-warmed interval. Exact parity is required on `2025-01-01` through `2026-07-23`; otherwise LAB008 is technical-fail and outcomes are not interpreted.

## Fresh independent legs
BUY and SELL are routed independently through the one-position rule. A BUY position cannot suppress a SELL candidate and vice versa. This matches the per-leg question requested for LAB008.
