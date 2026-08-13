# U02C3 — v283 Market Clock, NO TP / Stop-or-Time

Same episode-first v283 historical shadow and canonical H4 Supertrend clock as U02C2.

Exit policy: SL = 1.5 × completed H1 ATR14; **no TP**; otherwise time exit at 24/48/72h. Cost proxy $27.5/BTC. Results reported in both R and price-percent.

## Core matrix

| Side | State | N | EV24 R | EV24 % | PF24 | EV48 R | EV48 % | PF48 | EV72 R | EV72 % | PF72 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| BUY | TIER_A | 26 | +0.937 | +0.877% | 3.13 | +0.737 | +0.703% | 2.62 | +0.651 | +0.716% | 2.31 |
| BUY | OTHER_B3 | 177 | +0.203 | +0.236% | 1.35 | +0.337 | +0.255% | 1.47 | +0.210 | +0.217% | 1.28 |
| BUY | OTHER_B1 | 109 | +0.147 | +0.107% | 1.23 | +0.334 | +0.325% | 1.45 | +0.520 | +0.503% | 1.67 |
| BUY | OTHER_B2 | 153 | -0.082 | -0.088% | 0.89 | -0.321 | -0.274% | 0.63 | -0.184 | -0.155% | 0.79 |
| BUY | TIER_B | 47 | -0.368 | -0.086% | 0.54 | -0.255 | +0.093% | 0.70 | -0.237 | +0.124% | 0.72 |
| SELL | SELL_B3 | 121 | -0.232 | -0.212% | 0.67 | -0.004 | +0.045% | 1.00 | -0.081 | -0.069% | 0.90 |

## Year stability

### BUY Tier A
- 2024: N4, EV24 +2.148R / +2.281%
- 2025: N18, EV24 +0.768R / +0.666%
- 2026: N4, EV24 +0.485R / +0.421%

Positive 3/3 years, but N=26 total.

### BUY B3
- 2024: N47, EV24 +0.180R / +0.337%
- 2025: N91, EV24 +0.096R / +0.072%
- 2026: N39, EV24 +0.480R / +0.497%

Positive 3/3 years at 24h. At 48/72h R stays positive all years, but 2025 price-percent is around flat/slightly negative; 24h is the cleanest common horizon.

### BUY Tier B
Risk-normalized R is negative in all three years and all horizons. Price-percent becomes slightly positive at 48/72h aggregate because stop widths/exposure differ, so the veto is strongest under fixed-risk sizing, not fixed-lot sizing.

### BUY B1
Aggregate improves without TP, especially at 48/72h, but it is not stable:
- 2024 strongly positive
- 2025 negative
- 2026 roughly flat/slightly positive

Therefore B1 remains NO-TRADE for a simple stable router, but the reason is regime instability rather than globally negative EV.

### SELL B3
- 2024 and 2025 negative at 24h
- 2026 strongly positive
- full 2024–26 EV24 = -0.232R / -0.212%
- 48h approximately flat overall

So generic SELL B3 + v283 timing is still rejected; 2026 is a regime-specific migration candidate.

## Bootstrap diagnostics

Event bootstrap, 20k resamples:
- Tier A BUY 24h: EV +0.937R, 95% CI about [+0.199, +1.751], P(EV>0) ≈ 99.4%.
- Tier A BUY 48h: EV +0.737R, P(EV>0) ≈ 97.4%.
- BUY B3 24h: EV +0.203R, P(EV>0) ≈ 94.5%; price-percent P(EV>0) ≈ 97.2%.
- Tier B BUY 24h: EV -0.368R, P(EV>0) ≈ 3.9%.
- SELL B3 24h: EV -0.232R, P(EV>0) ≈ 2.9%.

Tier A minus Tier B:
- 24h ΔEV ≈ +1.306R; bootstrap P(Tier A > Tier B) ≈ 99.9%.
- 48h ΔEV ≈ +0.989R; P ≈ 98.5%.

## Revised simple router

1. B4 opposite + BUY: premium BUY candidate, full risk only after same-state timing null confirms v283 adds value.
2. B3 + BUY: broad BUY candidate; 24h time exit is currently the cleanest common horizon.
3. B4 aligned + BUY: veto under fixed-risk sizing.
4. B3 + SELL: reject as generic rule; isolate 2026 regime separately.
5. B2: reject.
6. B1: reject in simple router due instability, not due negative aggregate EV.

Frequency of Tier A + BUY B3 remains about 1.49 episode-first opportunities/week.

## Critical next test

This matrix still mixes state edge and v283 timing edge. Next mandatory LAB: compare actual v283 timestamps with random / matched timestamps inside the **same market-clock state**. That determines whether v283 should remain an execution layer at all, or whether the simple state router alone is sufficient.
