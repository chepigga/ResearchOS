# LAB052 — V200 2026-09-24 RETRACE RELAXATION DIAGNOSTIC

Purpose: diagnose whether the current V200 passive retrace 0.60 ATR is too strict on the actual seven IC CORE setups observed on 2026-09-24.

This is NOT a parameter-selection lab and does not change production V200.

Frozen setup population:
- exactly the seven V200 CORE pending orders present in IC Trade History on 2026-09-24;
- signal/confirmation selection is unchanged;
- each setup's signal ATR is reconstructed exactly from the broker order geometry: abs(limit - SL)/4.5;
- broker reference at confirmation is reconstructed from the frozen 0.60 ATR passive limit.

Variants:
- R060: current passive retrace 0.60 ATR, TTL 20m
- R040: passive retrace 0.40 ATR, TTL 20m
- R020: passive retrace 0.20 ATR, TTL 20m
- R000: immediate confirmation entry (market proxy), no pending TTL

All variants:
- initial SL = 4.5 signal ATR
- TP = 10 signal ATR
- trailing / BE / ExitZ OFF
- hold H24 (but this diagnostic is marked to report cutoff 2026-09-24 22:44 server; later setups may remain open)

Price path:
- Binance USD-M futures 1m for BTCUSDT / ETHUSDT / SOLUSDT on 2026-09-24.
- IC server time is converted to UTC by -3h for this date.
- To approximate IC price coordinates, a constant setup-time basis = reconstructed broker confirmation reference - Binance 1m close is added to subsequent Binance OHLC.

Metrics:
- fill count / 7
- filled setup IDs
- stop / TP / open-to-cutoff
- realized + MTM R at cutoff
- MFE / MAE in R
- delta vs current R060

Interpretation:
A one-day path diagnostic can identify obvious missed-opportunity mechanics, but cannot justify changing V200 by itself.
