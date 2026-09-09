# BTC_SHORT_V1_FROZEN_SEQUENTIAL_LIVE_TAIL_PARITY_LAB_056

## Purpose
Continue the frozen SHORT v1 validation after LAB055 without changing any alpha, threshold, entry, execution, management, cost, or sizing rule.

LAB056 has two layers:

1. **ARCHIVE_LOCKED** — the formal evidence already certified through the latest complete Binance daily archives used by LAB055.
2. **LIVE_SHADOW** — a provisional extension from Binance USD-M public REST for the current incomplete UTC day. LIVE_SHADOW may be reported only if the REST series reproduces the archived series on an overlap window. It cannot by itself promote the system to PASS.

## Frozen trading system — unchanged from LAB055
1. Binance USD-M BTCUSDT retail `count_long_short_ratio`, M15 last observation.
2. `delta_ls_12 = ratio_t - ratio_{t-12}`.
3. Strictly-prior rolling 90 calendar day q20/q80, minimum 1000 prior M15 observations.
4. Contrarian FLOW: `delta>=q80 => SHORT`; flow-only signals are 12h non-overlapping exactly as LAB022.
5. Activation level: prior 12h futures extreme, 48 closed M15 bars. SHORT level = prior12_low.
6. TOUCH if price low reaches level within signal+12h.
7. ACCEPT if one of the first 4 M15 closes from TOUCH is `close<=level`; entry at the first ACCEPT close.
8. HIGH_RESPONSE iff directional futures 60m response is above the strictly-prior 90d median response among valid all-touch events, minimum 40 prior valid events.
9. Trade only `SHORT + HIGH_RESPONSE + ACCEPT`.
10. SL = 2.5 ATR14(signal); TP = 1.5R; horizon = signal_time+12h; entry bar excluded from intrabar SL/TP; later ambiguous M15 bars are SL-first.
11. ADVERSE_FIRST = -0.5R first-passage within 120m. Do not exit there. Before recovery (`M15 close<=entry`), 2 consecutive closed M15 bars `close>level` => immediate exit at the second close (`PERSISTENT_FAILURE_EXIT`).
12. Costs = 5 bps primary / 10 bps stress. Risk reporting = 0.25% per trade.

## No-tuning law
No new filter, threshold, session, volatility gate, response cutoff, stop, target, timeout, failure rule, or cost assumption is permitted.

## ARCHIVE_LOCKED baseline
LAB055 persisted fresh September evidence through 2026-09-08:
- FLOW SHORT = 7
- HIGH_RESPONSE SHORT = 3
- trades = 2
- EV5 = +0.515657R
- PF5 = 3.705688
- CumR5 = +1.031315R
- EV10 = +0.434759R
- DD@0.25% = 0.0953%

These numbers must reproduce before any LIVE_SHADOW result is interpreted.

## LIVE_SHADOW data contract
- Retail ratio: Binance USD-M `globalLongShortAccountRatio`, 5m, resampled to M15 by the last observation exactly as LAB055 archived metrics.
- Price/flow: Binance USD-M BTCUSDT 15m futures klines.
- REST overlap begins on 2026-09-08 UTC.
- LIVE_SHADOW is enabled only if:
  - ratio overlap row parity >= 99.9%;
  - futures OHLC + quote volume + taker-buy quote overlap row parity >= 99.9%;
  - reconstructed frozen FLOW through the archived cutoff matches LAB055 persisted FLOW 100%;
  - router/state on the archived overlap matches LAB055 persisted classifications 100% where comparable.
- Every shadow signal must have its entire `signal_time + 12h` outcome horizon present. Partial-horizon signals are excluded.

## Primary questions
1. Has a new fully observable frozen FLOW SHORT appeared after the LAB055 archive cutoff?
2. Has it reached HIGH_RESPONSE + ACCEPT and become a completed frozen trade?
3. Does adding the provisional live tail change fresh September EV/PF/DD directionally?
4. Does REST-to-archive parity justify using the incomplete UTC day for monitoring only?

## Formal verdict
The formal frozen-system verdict remains governed by archive-locked data:
- `PASS_FROZEN_SHORT_V1_POSTFREEZE`: fresh archive-locked N>=5, EV5>0, PF>=1.10, EV10>0, DD@0.25%<=4%, combined EV>=0.
- `FAIL_FROZEN_SHORT_V1_POSTFREEZE`: fresh archive-locked N>=5 and EV5<=0 or PF<1.0, or DD@0.25%>4%.
- `WATCH_POSTFREEZE_INSUFFICIENT_FRESH_TRADES`: fresh archive-locked N<5.

LIVE_SHADOW receives only one of:
- `SHADOW_PARITY_PASS_NO_NEW_TRADE`
- `SHADOW_PARITY_PASS_NEW_PROVISIONAL_TRADE`
- `SHADOW_PARITY_FAIL_DO_NOT_USE`
- `SHADOW_DATA_UNAVAILABLE`

## Guardrail
No LIVE_SHADOW outcome can change the frozen rules or authorize live/prop allocation. Live allocation remains 0 pending larger archive-locked fresh N and broker/FTMO-native parity.