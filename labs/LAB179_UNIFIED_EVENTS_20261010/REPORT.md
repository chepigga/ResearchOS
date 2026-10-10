# LAB179 — UNIFIED PRICE EVENTS × LIQUIDITY IDENTITY × IMPULSE
BTC M5, 2021–2026-08-10; exploratory, not executable strategy.

Input: frozen LAB171 11620 nonoverlap routes + LAB175 7311 sequential routes, plus fresh M5 direct impulse scan 1329 valid RR>=1.5. Union raw 20260 events. Last completed H1 14TR ATR. Direct impulse closed candle breakout of previous 24 M5 high/low by 0.15 ATR, body>=0.18 ATR, last 3 bar displacement >=0.45 ATR; first qualifying per side within 12 bars. TP nearest already-known previous 6h/12h/48h extrema or prior day H/L; structural stop at previous 12 M5 extrema +/-0.1 ATR. No oracle future endpoints used for signal construction.

Level identity: prior-day extrema keyed by source previous UTC day, rolling extrema keyed by last completed M5 bar whose high/low forms level; first candidate within 24h per (direction, level ID) retained. 13412 resulting episodes:
- LAB171 price pullback 8265 BUY4025 SELL4240 (805 posthoc wave-aligned routes, 750 unique waves).
- LAB175 CONTINUATION 4227 BUY2124 SELL2103 (488 aligned routes, 416 waves).
- LAB175 REVERSAL 73 BUY36 SELL37 (14 aligned routes, 14 waves).
- New DIRECT_IMPULSE 847 BUY418 SELL429 (351 aligned routes, 341 waves).
Posthoc union 1298 distinct LAB169 same-direction waves of 2754 (47.1%) vs LAB176 420 (15.3%). Improvement cannot be attributed to impulse alone; LAB171's broader candidates reintroduced. This IS NOT full unified detector architecture: it is a shared event bus merging disparate detectors.

Limitations: 24h grouping arbitrary; rolling extreme last-occurrence not true persistent liquidity object; target overlapping and opposite-side portfolio conflict unaddressed; conditional R:R only, NOT fills/profits. 2025–2026 cannot be called untouched OOS. LAB169 2754 waves mismatches canonical LAB161 2680. No Crowd/OI/Profile. No production EA. Run script local lab179_run.py; output local LAB179_ALL_EVENTS.csv LAB179_LIQUIDITY_EPISODES.csv LAB179_MONTHLY.csv LAB179_SUMMARY.csv LAB179_REPORT.md.

Next: canonical wave parity; compare matched waves for detector ablations; implement actual persistent level lifecycle, structural zone merge and same-origin candidate clustering, 3-engine classification from ONE shared scanner, no change in any prop bot until broker spec validation.
