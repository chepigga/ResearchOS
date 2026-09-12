# BTC_XAU_CONTEXT_FROZEN_PORTABILITY_LAB_001 — preregistration

## Purpose
Test whether the frozen XAU Context/Confirmation semantics transfer to BTC **without retuning any thresholds, definitions, weights, or quality rules**.

## Market / data
- BTCUSDT Binance data, 15m bars, from ResearchOS release asset `btc_15m.zip` (SHA256 `19acf95a3bb7a868fa1e6c8da8dbc73d4a2f7004b771e394bbee8e6c5b6e58b9`).
- M15 is the native test resolution; H4 is aggregated causally from M15.
- Test all data available in the archive after H4 warm-up. No time-window optimization.

## Frozen logic
Reuse XAU LAB007-LAB018 definitions unchanged:
1. H4 Context router: EMA20/50/200, ATR14 ratio, RSI14, ADX14, 20-bar breakout/sweep, 24-bar range ratio, EMA spread/ATR, relative volume, rejection wick, EMA20 cross, exact point scores, 3-bar smoothing, exact hysteresis/min-hold/gap rules.
2. Temporal role semantics from LAB009.
3. G1 compression = `range24_ratio < 0.85 AND atr_ratio < 0.95`.
4. D1 HTF Bias and D2 Trend Pressure; D14 = exact concordance, unchanged.
5. Population = `PULLBACK + G1 compression + D14 != 0`.
6. M15 confirmation components unchanged from LAB016:
   - OB_CONFIRM
   - IMBALANCE_CONFIRM
   - LIQUIDITY_CONFIRM
   - PRICE_ACTION_CONFIRM
   Equal 25% weights; `SETUP_CONFIRMATION_PCT` in {0,25,50,75,100}.
7. First-passage target unchanged: first ±1 ATR move in D14 direction vs opposite, using causal future path from the signal availability time.

## Primary hypotheses
H1 — XAU high-tier transfers at all:
- Among exact-resolved BTC observations with `SETUP_CONFIRMATION_PCT >= 75`, N >= 60 and accuracy > 55% and weekly-cluster bootstrap 95% CI lower bound > 50%.

H2 — BULL high-tier transfers:
- BULL HIGH75 N >= 30, accuracy > 60%, CI lower bound > 50%.

H3 — BEAR high-tier transfers:
- BEAR HIGH75 N >= 25, accuracy > 55%, CI lower bound > 50%.

H4 — XAU directional asymmetry transfers:
- BULL HIGH75 accuracy - BEAR HIGH75 accuracy > 0 and weekly-cluster bootstrap 95% CI lower bound > 0, with both sides N >= 25.

## Secondary diagnostics
- Full score buckets 0/25/50/75/100.
- BULL/BEAR bucket metrics separately.
- Exact 3-of-4 and 4-of-4 component compositions.
- Component presence/absence accuracy by direction.
- 24h signed follow-through in ATR units.
- Year-by-year HIGH75 accuracy where sample size permits.

## Verdict mapping
- `BTC_PORTABILITY_CONFIRMED`: H1 passes and at least one of H2/H3 passes, with no evidence of catastrophic side failure (<45% accuracy with N>=25).
- `BTC_PARTIAL_PORTABILITY`: H1 fails but at least one directional H2/H3 passes, or H1 passes but directional behavior materially differs from XAU.
- `BTC_PORTABILITY_NOT_SUPPORTED`: H1 fails and neither H2 nor H3 passes.

## Anti-overfit constraints
- No threshold changes after outcomes.
- No component redefinition.
- No weight changes.
- No new side-specific quality rule in this LAB.
- Any attractive BTC-specific combination discovered here is discovery-only and requires a separate preregistered replication.

## Interpretation boundary
This LAB tests directional/confirmation semantics only. It does **not** establish FTMO BTCUSD execution parity, profitability, SL/TP win rate, or a production BTC confidence percentage.