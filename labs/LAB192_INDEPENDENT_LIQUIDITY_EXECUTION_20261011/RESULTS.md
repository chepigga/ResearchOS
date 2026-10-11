# LAB192 independent execution with swing liquidity

Input: LAB191 5087 debounced breakouts. Chronologically earliest candidate per breakout, filtered by inherited LAB191 48h-high/low geometric eligibility; 3044 eligible, 3009 with confirmed prior H1/H4 2L2R swing target at least 1.5R away.

Known swing availability: after two right candles close; 14-day lookback. M5 next-open fills, same-bar ambiguity SL-first, 24h timeout, structural stop frozen LAB191.

Total round-trip all-in modeled costs 0/5/10/15 basis points are scenarios, not broker data.

All 3009: 0bps +0.008R, 5bps -0.112R, 10bps -0.232R, 15bps -0.351R, TP-first 31.47%.

L/S against trade and OI build 256: 0bps +0.317R, 5bps +0.198R, 10bps +0.080R, 15bps -0.039R, TP-first 40.63%.

Filtered 10bps split TRAIN 2021-23 n167 +0.127R; 2024 n42 -0.060R; CHECK 2025-Aug26 n47 +0.035R.

CRITICAL LIMITATION: inherited LAB191 48h-target geometry gate preselected candidates before new H1/H4 pivot target replay. Need fresh full 5087-event eligibility scan before making a production claim.

Other limitations: level proxy not actual resting liquidity, +5min publication delay assumed, previously researched holdout, multiple overlapping signals, no broker execution or prop DD simulation.

Local files LAB192_REPORT.md, LAB192_EXECUTION_SUMMARY.csv, LAB192_H1_H4_INDEPENDENT_TRADES.csv, LAB192_H1_INDEPENDENT_TRADES.csv, lab192_replay.py.