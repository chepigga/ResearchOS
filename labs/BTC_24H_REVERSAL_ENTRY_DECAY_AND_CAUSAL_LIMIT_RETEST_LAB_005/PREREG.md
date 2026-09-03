# BTC_24H_REVERSAL_ENTRY_DECAY_AND_CAUSAL_LIMIT_RETEST_LAB_005 — PREREG

Frozen before outputs.

- Universe: Binance Spot BTCUSDT completed M15 bars, 2021-01 through latest available 2026-08 monthly archive.
- Parent event: exact LAB003/LAB004 impulse definition: completed BTC 60m absolute log-return >= prior 30d 97.5th percentile; 4h cooldown.
- Frozen selector: exact LAB003 BTC-only CORE logistic CONT/REV router trained on DEV 2021-2024; top bucket threshold = DEV q80 of max(CONT,REV); LAB005 executes only top-bucket events routed REV.
- Common exit for execution comparison: parent impulse bar +96 M15 closes, preserving LAB003 24h clock and isolating entry timing.
- Market entries: immediate next M15 open, +15m, +30m, +60m.
- Primary causal limit: event_close + impulse_dir * 0.50 * event M15 range; reversal-side limit order, TTL 4 M15 bars (60m), no market fallback.
- Secondary audit limits only: 0.25x and 1.00x event range, same TTL. They cannot rescue a primary failure.
- DEV: 2021-2024; bridge: 2025; OOS: 2026. No 2026 tuning.
- Primary questions: (1) is there monotone entry decay from MKT_0 to MKT_30/MKT_60 in both bridge and OOS? (2) does primary limit achieve >=30% fill rate in both bridge and OOS? (3) on the exact same filled events, does primary limit improve reversal return versus immediate market entry in both bridge and OOS?
- A PASS authorizes a later SL/TP economics LAB only. It does not authorize live trading. Any later monetization must preserve R:R >=1:1.5 and prop-safe risk.
