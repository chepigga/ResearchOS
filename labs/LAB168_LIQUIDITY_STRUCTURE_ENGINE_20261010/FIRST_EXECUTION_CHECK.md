# LAB168 FIRST EXECUTION CHECK — BTCUSDT M5
Date: 2026-10-10
Status: EXPLORATORY / FAIL, NOT PRODUCTION OR VALIDATED WAVE-MATCHED ENGINE.
Source: user-provided btc_5m(1).zip, 589793 M5 bars through 2026-08-10; 12053 structural setups, 25967 eligible (RR>=1.5) entries across modes, 4054 MARKET portfolio2 entries.

## Assumptions
Closed H1 SMA14 TR ATR, H1/H4 EMA50 plus 4-bar slope, prior 2h/6h/12h/48h highs/lows, previous-day levels, 6h range width1-4 ATR and path efficiency<=.35. Continuation requires aligned H1/H4 and 2h sweep/reclaim. Range prior 6h sweep/reclaim; reversal other sweep with immediate 2h midpoint confirmation. Structural stop extreme +/- 0.1ATR. Continuation target nearest forward 6h/12h/48h/day extreme, range target opposing 6h edge, reversal 6h mid. Market next open vs extra M5 confirmation vs 60m retest. 24h timeout. Intrabar stop-first except limit fill bar skipped, which creates potential optimism and requires fixing. Roundtrip cost approximation 7.5bps (not verified broker). No crowd/OI/profile. No parameter optimization. No profile nodes nor wave-ID matching, 2025-26 not pristine OOS.

|mode|entry|n|TP-first %|gross EV R|net EV R @7.5bps|median geometry RR|
|---|---|---:|---:|---:|---:|---:|
|Continuation|market|2821|21.092|-0.007|-0.377|3.696|
|Continuation|confirm|1262|24.406|-0.021|-0.307|2.928|
|Continuation|limit|2288|13.243|-0.041|-0.724|7.523|
|Range|market|8527|16.125|0.004|-0.312|5.244|
|Range|confirm|4297|20.991|-0.008|-0.234|3.529|
|Range|limit|6744|10.098|-0.110|-0.642|9.646|
|Reversal|market|4|25.0|-0.358|-0.491|1.610|
|Reversal|limit|24|37.5|+0.526|-0.030|3.419|

Simplified portfolio2 market: continuation 1436 trades net EV -0.431R; range 2614 net EV -0.329R; reversal only 4 net EV -0.491R. Portfolio implementation max2 and one per mode/side/day, not full broker execution.
The reversal gate is overly strict / under-sampled and not a reliable test of reversal concept. Time-gap audit and limit fill-bar bid/ask/tick simulation incomplete.
Counts are NOT 2680-wave coverage and cannot be reported as fraction of ~40 big moves/month.
Interpretation: simple price-structure routes with +0.1ATR stops do not show exploitable net edge under this cost proxy. Gross EV near zero. No production promotion.

Next lab priorities: wave-ID mapping and missing-wave taxonomy first; revise stop geometry and entry timing independently, HOLD OUT untouched period; benchmark against no-signal alternatives. Real broker spread, commissions, symbols, swaps, stop/freeze levels and strategy rules are required before proposing EA.
