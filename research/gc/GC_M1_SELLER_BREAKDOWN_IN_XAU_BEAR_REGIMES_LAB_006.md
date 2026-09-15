# GC_M1_SELLER_BREAKDOWN_IN_XAU_BEAR_REGIMES_LAB_006

XAU coverage UTC after frozen -2h clock correction: `2026-08-02 23:05:00+00:00` → `2026-09-08 18:03:00+00:00`. Bear days: **14/33**.

**EXPOST_BEAR_DAY is deliberately non-causal and used only to falsify bullish-drift explanations. CAUSAL_TRAILING_4H_DOWN is the deployable-style diagnostic.**

## EXPOST_BEAR_DAY

| Feed / setup | N | XAU 5m | XAU 15m | XAU 30m | XAU 60m | GC 15m |
|---|---:|---:|---:|---:|---:|---:|
| RITHMIC SELL_OF | 105 | +0.122 | +0.351 | +0.837 | +5.300 | -0.008 |
| RITHMIC SELL_PRICE_NO_OF | 661 | -0.029 | -0.017 | -0.060 | +4.051 | +0.156 |
| RITHMIC BUY_OF_IN_BEAR_CONTROL | 101 | -0.386 | -0.632 | -0.450 | +2.819 | -0.330 |
| AMP SELL_OF | 95 | +0.090 | +0.458 | +1.163 | +5.493 | +0.262 |
| AMP SELL_PRICE_NO_OF | 552 | +0.036 | +0.105 | +0.222 | +4.516 | +0.106 |
| AMP BUY_OF_IN_BEAR_CONTROL | 89 | -0.295 | -0.748 | -0.846 | +2.337 | -0.314 |

## CAUSAL_TRAILING_4H_DOWN

| Feed / setup | N | XAU 5m | XAU 15m | XAU 30m | XAU 60m | GC 15m |
|---|---:|---:|---:|---:|---:|---:|
| RITHMIC SELL_OF | 87 | -0.046 | -0.201 | -0.339 | +3.497 | -0.506 |
| RITHMIC SELL_PRICE_NO_OF | 539 | -0.042 | -0.302 | -0.534 | +3.494 | -0.137 |
| RITHMIC BUY_OF_IN_BEAR_CONTROL | 117 | -0.349 | -0.310 | -0.194 | +3.092 | +0.261 |
| AMP SELL_OF | 80 | -0.173 | -0.219 | -0.388 | +3.185 | -0.282 |
| AMP SELL_PRICE_NO_OF | 466 | -0.006 | -0.296 | -0.351 | +3.766 | -0.120 |
| AMP BUY_OF_IN_BEAR_CONTROL | 109 | -0.253 | -0.321 | -0.179 | +3.050 | +0.294 |

## Interpretation gate

Evidence against simple bullish drift is stronger if SELL_OF is positive on XAU inside bearish regimes and outperforms SELL_PRICE_NO_OF, with similar sign on Rithmic and AMP. BUY_OF_IN_BEAR_CONTROL is reported as a sanity check. No thresholds are changed from the frozen mirrored breakout candidate.
