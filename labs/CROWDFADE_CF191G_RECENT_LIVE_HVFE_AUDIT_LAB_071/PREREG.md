# LAB071 — RECENT LIVE CF191g HVFE AUDIT

Purpose: audit the frozen LAB068 HVFE state on the most recent actual BTC CF191g demo trades.

No threshold changes. No optimization.

Frozen state:
- entry volatility = ATR14 on completed M15 / BTCUSDT close, causal percentile vs prior 2016 completed M5 points
- HIGH = percentile >= 0.80
- first 15 completed 1m bars after the M5 decision timestamp
- expansion15_atr = side*(close15-entry_ref)/entry_ATR
- eff15 = side*(close15-entry_ref)/sum(abs(1m close changes from entry_ref))
- FAILED_EARLY = expansion15_atr <= 0 OR eff15 <= 0
- HVFE = HIGH AND FAILED_EARLY

Universe:
- exact CF191g BTC trades found in the latest IC Trader and GetLeveraged reports
- do not include older CF191 (without g), CF200, SOL, or ETH

Questions:
1. Which actual trades were HVFE?
2. What was actual broker outcome in initial-risk R?
3. Did HVFE concentrate in actual losers?
4. What approximate EXIT15 and -0.75R cap outcomes would have been, using Binance move translated from the decision reference to broker entry.
5. Treat N=4 as a forward case study, not statistical proof.
