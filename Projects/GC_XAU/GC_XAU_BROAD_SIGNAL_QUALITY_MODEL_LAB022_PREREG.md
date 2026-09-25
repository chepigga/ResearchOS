# GC_XAU LAB022 — BROAD_SIGNAL_QUALITY_MODEL — PREREG

Date frozen: 2026-09-25
Scope: GC futures / COMEX Broad causal labels -> XAUUSD response.
Parent: LAB018 exact causal Broad registry + LAB019 causal HTF convention.

## Question
Which pre-entry information makes a Broad signal high-quality, and can a simple causal score separate TRADE / WATCH / REJECT without retuning the underlying Broad signal engine?

## Universe
Primary legs:
BASE1 / DOM2 / DOM_CONT / MIX2 / MIXED / REV1 / REV2.
REV3P excluded.

Chronological split unchanged:
- TRAIN = W1-W5
- VALID = W6-W7
- POST = W8-W9

## XAU mapping
Use Massive C:XAUUSD M1 quote aggregates as in LAB018/019.
UTC only.
Entry proxy = next exact M1 minute.
ATR14 = prior completed M1 bars only.

## Frozen pre-entry features
No future information:
1. LEG categorical.
2. SIDE: BUY / SELL.
3. H1 trend state using completed H1 bars only:
   close vs EMA20 + EMA20 3-bar slope.
4. H4 trend state with same definition.
5. H1 aligned to signal side: binary.
6. H4 aligned to signal side: binary.
7. BOTH H1&H4 aligned: binary.
8. Signed pre-signal price impulse normalized by XAU M1 ATR14:
   - IMP3 = side * (last completed M1 close - close 3 completed bars earlier) / ATR14
   - IMP5
   - IMP15
   - IMP30
9. For each impulse horizon, binary aligned = impulse > 0.

No post-signal price feature may enter the quality score.

## Primary outcome
Y = signed XAU +5m response / causal M1 ATR14.

Secondary outcomes:
- direction hit Y > 0
- TP1.5 reach before SL1 within 30m
- TP2 reach before SL1 within 30m
- MFE30 / MAE30 in R with SL distance = 1 ATR for diagnostic comparability.

## Model
Interpretable additive TRAIN-only ridge model.

Continuous target:
Y5_ATR.

Design matrix:
- intercept
- LEG one-hot, BASE1 as reference
- SIDE BUY binary
- H1 aligned
- H4 aligned
- BOTH aligned
- IMP3 / IMP5 / IMP15 / IMP30 continuous, winsorized only with TRAIN 1st/99th percentiles then standardized using TRAIN mean/std.

Ridge lambda is FIXED before outcomes at 10.0.
No lambda search.

A second TRAIN-only logistic ridge uses the same features for P(Y>0), same fixed lambda=10.

Quality score for an event:
- zEV = ridge predicted Y5_ATR
- pUP = logistic predicted probability Y>0.

TRAIN thresholds are frozen from predicted quality distribution, not outcome optimization:
- TRADE = zEV >= TRAIN 70th percentile AND pUP >= 0.55
- REJECT = zEV <= TRAIN 30th percentile OR pUP <= 0.45
- WATCH = otherwise.

No percentile or probability threshold search after VALID/POST is visible.

## Required reporting
Overall and separately by LEG and SIDE:
- N
- raw Y5 EV
- PF-like positive/negative magnitude ratio
- directional hit-rate
- TP1.5 reach
- TP2 reach
- mean MFE30
- mean MAE30
- score bucket TRADE / WATCH / REJECT.

Feature importance:
- standardized ridge coefficient
- logistic coefficient
- univariate TRAIN uplift for aligned vs counter state.

Robustness:
- TRAIN / VALID / POST
- each W1-W9 separately
- monthly/quality-window sign consistency where possible.

## Pass criteria
Signal-quality model is useful only if:
1. TRADE bucket Y5 EV > WATCH > REJECT in TRAIN, VALID and POST;
2. TRADE EV > 0 in VALID and POST;
3. TRADE PF-like ratio > 1 in VALID and POST;
4. TRADE direction hit > 52% in VALID and POST;
5. no single LEG supplies >70% of TRADE events;
6. positive result is not carried by only one quality window.

Passing does NOT authorize live/production changes.
If pass: proceed to leg-specific execution labs.
If fail: keep Broad as logger and study separate leg-specific confirmation models rather than one universal score.
