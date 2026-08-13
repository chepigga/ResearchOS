# SELL_CORE_004 — HTF_BEAR_TREND × LOCAL_BULL_CORRECTION × FAILED_BREAKOUT

## Verdict

**FAIL for the cheap generic M15-swing implementation; visual hypothesis itself is NOT rejected.**

Frozen implementation:
- HTF bear = canonical H4 Supertrend ATR10×3 DOWN, BAR_OPEN lag1;
- local bullish correction = completed H1 close > EMA20, EMA20 rising vs 4 H1 bars ago, close > close 4 H1 bars ago;
- failed breakout = M15 high sweeps last causally confirmed M15 swing high (pivot strength 2) and same M15 bar closes back below;
- next M1 entry; SELL;
- SL 1.5×completed H1 ATR14; no TP; 48h primary / 72h sensitivity; $27.5/BTC cost proxy.

## Layering

- Failed breakout any: N 4614, EV48 +0.001R, PF 1.00.
- + HTF bear: N 2232, EV48 +0.043R, PF 1.06.
- + local bull correction: N 759, EV48 **-0.084R**, PF **0.90**; EV72 -0.019R, PF 0.98.
- + frozen SELL_B3 age 27–50: N 215, EV48 **-0.126R**, PF 0.84; EV72 -0.064R.

Primary cluster bootstrap:
- 48h EV -0.084R, CI [-0.321,+0.158], P(EV>0)=23.8%.
- 72h EV -0.019R, CI [-0.321,+0.301], P(EV>0)=43.8%.

Yearly primary:
- 2024: -0.103R (48h), -0.218R (72h)
- 2025: +0.074R, +0.227R
- 2026: -0.271R, -0.067R

Same-state timing null:
- 48h event -0.084R vs matched controls -0.125R, delta +0.041R, CI [-0.039,+0.120], P(delta>0)=84.3%.
- 72h delta +0.031R, CI [-0.062,+0.119], P(delta>0)=74.4%.
Thus exact failed-breakout timing is slightly better than matched generic correction timestamps but does not create a profitable trade population.

Next fixed H4 after occurrence is also negative:
- 48h -0.126R, PF 0.845
- 72h -0.106R, PF 0.874
So this generic occurrence is not an episode selector either.

## Market-clock clue (exploratory, not promoted)

B2 is the only positive bucket:
- B1: EV48 -0.321R, EV72 -0.403R
- **B2: EV48 +0.292R PF1.38; EV72 +0.571R PF1.71**
- B3: ~0
- B4: strongly negative

But B2 is not stable 3/3:
- 2024: EV48 -0.349R; EV72 -0.400R
- 2025: +1.295R; +1.640R
- 2026: +0.032R; +0.744R
Therefore B2 is only a clue, not a frozen selector.

## Why this does not refute the user's visual setup

The screenshots show more than a generic M15 swing failure. They show rejection at a **meaningful HTF location**: a horizontal structural resistance and/or a global descending trendline. SELL_CORE_004 deliberately used the cheapest location-free proxy (last confirmed M15 swing high). It generated 4,617 failed-breakout events, far broader than the visual setup.

The missing variable is therefore likely **HTF resistance significance/location**, not another momentum indicator. A proper next test should preserve the same global-bear/local-correction/failure sequence but require the failed breakout to occur at a causal HTF structural resistance (e.g. confirmed H1/H4 swing-high / descending HTF trendline), with no post-hoc threshold grid.
