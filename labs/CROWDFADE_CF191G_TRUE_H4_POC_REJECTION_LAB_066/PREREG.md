# LAB066 — CF191G TRUE H4 VOLUME-PROFILE / POC REJECTION — PREREGISTRATION

## Purpose

Test the podcast/video mechanism with actual Binance USD-M aggregate trades, not OHLC-only proxies.

LAB066 reconstructs H4 volume-at-price and POC for the exact LAB065 H4 composite-event universe.
Diagnostic only. No entry/exit/risk action.

## Frozen event universe

Use the exact LAB065 H4 composite definition:
- H4 quote volume >= causal 80th percentile of prior 180 completed H4 candles
- sweep of prior 6 completed H4 candles
- close in opposite third of the event range
- H4 OI change < 0

Event direction:
- +1 for swept-low / upper-third close
- -1 for swept-high / lower-third close

Expected full composite H4 counts from LAB065:
- 2021–2025: 221
- 2026 Mar–Aug: 21

## True volume profile from aggTrades

For every composite H4 candle, use all official Binance USD-M BTCUSDT aggregate trades with timestamps inside [H4 open, H4 close).

For each aggTrade:
- price = aggregate trade price
- base_qty = aggregate quantity
- quote_notional = price * base_qty

Aggregate quote_notional by exact traded price.

Define:
- POC = exact price level with maximum quote_notional
- POC_location = (POC - H4_low) / (H4_high - H4_low)
- lower_third_share = quote_notional traded at prices <= low + range/3 divided by total H4 quote_notional
- upper_third_share = quote_notional traded at prices >= low + 2*range/3 divided by total H4 quote_notional

Also compute notional-weighted price quantiles q15 and q85; [q15,q85] is reported as central 70% price mass and is NOT called standard Value Area.

## Profile alignment classes

For LONG-rejection H4 event:
- POC_ALIGNED if POC_location <= 1/3
- POC_MIDDLE if 1/3 < POC_location < 2/3
- POC_OPPOSITE if POC_location >= 2/3

For SHORT-rejection H4 event mirror the classification:
- POC_ALIGNED if POC_location >= 2/3
- POC_MIDDLE if 1/3 < POC_location < 2/3
- POC_OPPOSITE if POC_location <= 1/3

No threshold search.

## Event-level outcomes

Starting from the H4 event close, in the event direction report causal forward:
- signed return at 1h / 4h / 8h / 12h
- MFE / MAE over 4h / 8h / 12h

Primary event horizon = 4h.

Primary mechanism hypothesis in BOTH 2021–2025 and 2026:
- POC_ALIGNED mean/median signed 4h return > POC_OPPOSITE
- POC_ALIGNED 4h MFE > POC_OPPOSITE 4h MFE
- POC_ALIGNED 4h MAE < POC_OPPOSITE 4h MAE

Report sample sizes; no action is promoted from event-level results.

## CF191g overlap map

Separately map canonical CF191g fills occurring after the H4 event close and before the next H4 close (event_close <= fill < event_close+4h).

Classify each overlap:
- SUPPORTIVE_ALIGNED: CF191g side == H4 event direction AND POC_ALIGNED
- SUPPORTIVE_MIDDLE
- SUPPORTIVE_OPPOSITE
- ADVERSE_ALIGNED: CF191g side == -H4 event direction AND POC_ALIGNED
- other / none

Report frozen CF191g EV / PF / MFE / MAE, but treat any class with N < 20 historical or N < 5 in 2026 as shadow-only.

## Guardrails

No use of delta_ratio.
No OHLC-only POC proxy.
No optimization of thirds, volume percentile, OI threshold, or event age.
No production rule from LAB066.