# BTC_PAXG_24H_REGIME_AND_RIGHT_TAIL_TRANSFER_LAB_002 — preregistration

Frozen before reading LAB002 outputs.

## Hypothesis
PAXG is not treated as a direct BTC direction signal. The test asks whether completed PAXG state improves identification of 24h continuation-tail vs reversal-tail after an already-completed BTC impulse.

## Clock / causality
- Binance Spot BTCUSDT and PAXGUSDT, completed 15m bars only.
- BTC impulse inherited unchanged from LAB001: absolute completed 60m return >= prior rolling 30d 97.5th percentile, 4h cooldown.
- Decision timestamp = completed impulse bar.
- Entry reference/outcomes begin at next 15m open.
- No PAXG forward-fill.

## Splits
- DEV: 2021-2024.
- Bridge: 2025.
- Untouched OOS: 2026.

## Primary target
24h only. DEV 75th-percentile signed continuation and reversal outcomes define frozen right-tail thresholds, then transfer unchanged to bridge/OOS.

## Models
- BTC_ONLY: BTC state, impulse, volatility/range, clock features.
- BTC_PLUS_PAXG: BTC_ONLY plus PAXG 15m/60m/4h/24h state, acceleration, volume/range, BTC-PAXG divergence and rolling correlation context.
- Two logistic classifiers: continuation-tail and reversal-tail.

## Router
For each event, choose the side with larger predicted tail probability. Top-20% confidence threshold is frozen from DEV independently for each model. Compare BTC_ONLY vs BTC_PLUS_PAXG on bridge and OOS.

## Promotion gates
1. OOS >=100 events.
2. Bridge average AUC delta >0.
3. OOS average AUC delta >=+0.02.
4. OOS average Brier improves.
5. Bridge top-20 chosen-side return delta >0.
6. OOS top-20 chosen-side return delta >0.
7. OOS top-20 tail-hit delta >=+5 pp.
8. Bridge/OOS top-20 return deltas have same positive sign.

No threshold, model C, regime cutoff, impulse percentile, horizon, or top-bucket size may be tuned on 2026 after seeing results.
