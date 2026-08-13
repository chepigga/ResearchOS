# SELL_CORE_005 — CANONICAL VERDICT

Canonical run: **SELL_CORE_005B acceptance-safe correction**. The first 005A run is invalid for inference because resistance objects were not retired after acceptance above them.

## Frozen mechanism

- H4 bear = canonical H4 Supertrend ATR10 x3 DOWN, BAR_OPEN lag1.
- Local bull correction = completed H1 close > EMA20, EMA20 rising vs 4 H1 bars ago, close > close 4 bars ago.
- H1_HORIZONTAL = causal H1 swing high, pivot strength 2.
- H4_HORIZONTAL = causal H4 swing high, pivot strength 2.
- H4_DESC_TRENDLINE = last two causal H4 swing highs descending; line projected forward.
- Resistance lifecycle: first unresolved interaction only. M15 close above => ACCEPTED/INVALIDATED forever; M15 high above + close below => FAILED_BREAKOUT event and retire level.
- SELL entry next M1 open; SL 1.5 x completed H1 ATR14; no TP; 48h primary / 72h sensitivity; $27.5/BTC cost proxy.

## Primary result

| Module | N | EV48 | PF48 | EV72 | PF72 | price EV48 |
|---|---:|---:|---:|---:|---:|---:|
| H1 horizontal | 333 | -0.286R | 0.66 | -0.244R | 0.72 | -0.293% |
| H4 horizontal | 75 | -0.445R | 0.49 | -0.353R | 0.61 | -0.373% |
| H4 descending trendline | 47 | -0.371R | 0.55 | -0.461R | 0.49 | -0.314% |
| Combined OR | 331 | -0.263R | 0.68 | -0.221R | 0.75 | -0.259% |

Cluster bootstrap, Combined OR 48h: CI [-0.486R, -0.028R], P(EV>0)=1.42%.

## Transfer by year — Combined OR 48h

- 2024: -0.179R, PF 0.78
- 2025: -0.217R, PF 0.74
- 2026: -0.486R, PF 0.44

So the failure is 3/3 years, not a one-year regime artifact.

## Location incremental value

Matched against generic non-location M15 failed breakouts with same year + exact H4 ST age + nearest H1 ATR%:

- 48h: location event -0.229R vs control -0.142R; delta -0.087R; P(delta>0)=27.2%.
- 72h: location event -0.216R vs control +0.024R; delta -0.240R; P(delta>0)=7.3%.

Thus these causal H1/H4 resistance definitions do not improve generic failed-breakout execution.

## Occurrence test

Next H4 after location failure:
- EV48 -0.164R, PF 0.80
- EV72 -0.134R, PF 0.84

So location occurrence is not an episode selector either.

## Surviving diagnostic clue: B2

The only positive market-clock cell is B2, repeating the clue already seen in SELL_CORE_004:

- H1 horizontal B2: +0.234R / PF 1.32 at 48h; +0.496R / PF 1.63 at 72h.
- Combined OR B2: +0.190R / PF 1.25 at 48h; +0.473R / PF 1.60 at 72h.

But B2 is not stable 3/3. Combined OR B2:
- 2024: -0.253R (48h), -0.542R (72h)
- 2025: +0.865R, +1.006R
- 2026: +0.045R, +1.394R

This remains a recent-regime clue, not a frozen SELL rule.

## Verdict

**REJECT** `H4 bear + H1 bull correction + failed breakout of causal H1/H4 swing resistance or H4 descending trendline` as the current SELL core.

This rejects these specific mechanical proxies for the visual setup; it does not prove that every form of visually significant global resistance is useless. The screenshots appear to use slower, more selective structural geometry than a generic H1/H4 pivot stream, so any future continuation must test a truly higher-timeframe/major-structure definition rather than adding more low-timeframe filters.
