# GC_XAU LAB019 — BROAD_LEG_SIDE_HTF_TREND_INTERACTION — FROZEN PREREG

Frozen before interaction outcomes are calculated: 2026-09-25

## Scope
GC futures / COMEX order-flow Broad Demo -> XAUUSD. Do not mix crypto/CrowdFade or unrelated XAU strategy families.

## Parent
Exact causal Broad labels from canonical LAB018:
BASE1 / DOM2 / DOM_CONT / MIX2 / MIXED / REV1 / REV2.
REV3P is diagnostic only and is excluded from the primary family.

Canonical event registry:
GC_XAU_BROAD_LEGS_LONG_HISTORY_CAUSAL_REGISTRY.csv
SHA256: 13cfbacd8bc46d1806ccbb29cfcccdd605630fa91adbbba0417fa4d27966991d
N = 111,172 emitted Broad signals.

Chronological split is inherited unchanged:
TRAIN = W1-W5
VALID = W6-W7
POST = W8-W9

## XAU source and clock
Use the same external XAU family as LAB018: Massive C:XAUUSD 1-minute quote aggregates.
All timestamps and HTF bar boundaries are fixed UTC.
No broker-time/DST transformation is introduced in this interaction lab.

For every GC signal timestamp t0:
- XAU entry proxy = ceil(t0 to the next exact UTC minute; exact minute remains exact minute)
- ATR14 = SMA(True Range) over the 14 XAU M1 bars immediately preceding entry
- +5m endpoint = close of the M1 bar starting entry+4m
- no interpolation; missing exact clock bars are unpriced

## Frozen HTF trend definition
Only fully completed bars may be used. No forming H1 or H4 bar may enter the state.

For timeframe T in {H1,H4}:
- EMA20 is calculated on completed closes
- UP iff last completed close > EMA20 and EMA20_now > EMA20_3_completed_bars_ago
- DOWN iff last completed close < EMA20 and EMA20_now < EMA20_3_completed_bars_ago
- otherwise NEUTRAL

Signal-side alignment:
- BUY signal: aligned only with UP
- SELL signal: aligned only with DOWN

Interaction bucket:
- BOTH = H1 aligned AND H4 aligned
- H1_ONLY = H1 aligned AND H4 not aligned
- H4_ONLY = H1 not aligned AND H4 aligned
- NEITHER = neither aligned

Primary comparison = BOTH vs NOT_BOTH.
The four-bucket split is diagnostic and must all be reported.

## Outcomes
Primary information endpoint:
signed XAU +5m response / causal M1 ATR14.

Execution proxy inherited from LAB018:
- SL = 2.25 ATR
- TP = 4.50 ATR = 2R
- timeout = 300s
- same-M1 SL/TP collision = SL first
- commission proxy = 0.0007% notional per side
- fixed spread stress = 0.2 XAU

Report:
N, WR, EV5 ATR, PF5, gross execution EVR/PF, net-0.2 execution EVR/PF, SumR and sequential MaxDD.

## Anti-overfit protocol
1. Reconstruct LAB018 aggregate leg results first. If parity materially fails, stop and do not interpret interaction cells.
2. TRAIN is the only discovery layer.
3. VALID and POST remain untouched until the complete TRAIN table is frozen.
4. No outcome-derived EMA length, slope horizon, timezone, trend threshold, leg regrouping, side regrouping, or execution geometry changes.
5. No post-hoc promotion from one day/window.
6. Q65 remains unchanged and separate.

## Advancement rule
A leg × side × BOTH-aligned family is only a candidate for further exact-execution study if:
- raw +5m EV > 0 and PF > 1 in TRAIN, VALID, and POST;
- direction of BOTH-vs-NOT_BOTH uplift is consistent in all three splits;
- realistic net-0.2 execution EV is > 0 in TRAIN, VALID, and POST;
- sample size and window consistency are explicitly reported.

Passing LAB019 is research evidence only, not production authorization.
