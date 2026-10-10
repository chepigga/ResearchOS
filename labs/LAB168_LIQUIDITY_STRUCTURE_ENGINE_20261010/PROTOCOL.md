# LAB168 — LIQUIDITY STRUCTURE ENGINE
Status: preregistered research hypotheses; NO performance claims, NO live deployment.
Parent: LAB167 price-only first pass (negative after 7.5bps).
Date: 2026-10-10.

## Goal
Start with causal, price-only representation of liquidity proxies and structure. Trade from known level to next known level, not fixed ATR profit. Test 3 disjoint mechanisms on BTCUSDT closed M5 and higher closed bars. Distinguish hindsight 2680-wave upper bound from causal eligible opportunities.

## Common state
Known liquidity: prior-day H/L, 6h/12h/48h closed extremes, confirmed H1 fractal swings (2 right closes required). Repeated levels within 0.1 H1 ATR are merged; a target is the nearest untouched liquidity proxy in direction of trade. These are NOT actual order-book positions.
Trend: H1 completed EMA50 direction and EMA50 4-closed-H1-bar slope, confirm H4; flat/discordant = neutral. ATR: LAB161 closed H1 SMA14 true range for lineage.
Only finalized information is used for candidate evaluation. Historical prospective wave endpoints must NEVER be used to pick the candidate direction or entry.

## Engine A continuation
Previous H1/H4 trend aligned, local pullback toward previously known broken H/L or confirmed swing, price closes back with trend, then market next M5 open versus passive retest limit. Structural SL beyond pre-trigger pullback extreme plus 0.1 ATR. TP first untouched known same-direction level, RR>=1.5.
## Engine B reversal
First sweep prior known H/L, M5 close back through frozen level, then price breaks pre-sweep locally known structure by completed close. Next open versus 60m limit retest. Stop beyond sweep extreme + 0.1 ATR; TP nearest opposing previously known level; RR>=1.5.
## Engine C range
Prior known 6 completed H1 bar balance, width 1–4 H1 ATR and path efficiency<=0.35; false edge excursion and reclaim or retest; only range mode if higher trend not aligned breakout. SL outside failed excursion +0.1 ATR. TP opposite known balance boundary, or earlier known structural obstacle; RR>=1.5.

## Execution
Three independent methods per setup: signal next M5 open; one completed-bar confirmation plus next open; passive limit retest, TTL60m. Fill, partial bar ambiguity and market gap strictly conservative. TP/SL high-low M5, SL-first same bar, 24h time stop. Report no cost and hypothetic 5/7.5/10bps roundtrip. No trailing/partials. Max two portfolio positions, no simultaneous duplicates of same route. No same-bar optimistic limit TP.

## Evaluations
All signals, 1.5/2/3 RR bins, fills, TP/SL/timeout, gross/net EV, PF, worst DD, calendar-month opportunities, and distinct LAB161 wave IDs covered; split 2021-23 fit, 2024 validation, 2025-Aug2026 CHECK (reused, not pristine holdout), no tune on CHECK. Monte Carlo weekly blocks.
Before coding production obtain broker/prop name/account, symbol/spread/roundtrip commission, STOPLEVEL/FREEZELEVEL, EAs/news/hedge/order constraints, leverage/lot/swap, VPS/slippage and prop rules URL. LAB168 research protocol does not authorize live trading.

Known failure mode: LAB167 structural breakout on raw previous extrema yielded ~19% TP first and -0.359R mean net at 7.5bps; avoid interpreting level touches as directional edge.
