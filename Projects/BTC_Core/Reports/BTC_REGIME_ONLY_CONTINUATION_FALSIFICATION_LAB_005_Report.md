# BTC REGIME-ONLY CONTINUATION FALSIFICATION — LAB005

**Date:** 2026-08-25  
**Status:** COMPLETED / REGIME-ONLY REPRODUCTION FAIL  
**Universe:** BTCUSDT M15 exact release data  
**Primary question:** Can the causal market regime, with STRUCT_BREAK removed, reproduce the `riskATR > 3.72` tail's outcome edge?

## 1. Frozen inputs
- Exact M15 clock: 242,700 bars, 2019-09-08 17:45 → 2026-08-10 20:30.
- DEV: 2019-09 → 2022-12.
- VAL: 2023-01 → 2025-12.
- 2026 excluded from model fitting, thresholds, and verdict.
- Frozen tail: `riskATR > 3.72`; no retuning.
- Regime features: `DIR72_ATR`, `ER72`, `VOL24_14D`, `LOC30D`.
- Every regime feature uses only the previous fully closed M15 bar.
- Full-clock regime direction = sign of `DIR72_ATR`.
- High-regime cut = top 9% of DEV market time by the frozen Step-2 tail-likeness score; no outcome optimization.

## 2. Regime-only forward path

At **regime onset** on VAL 2023–2025:

| Regime score | N | signed 24h return | signed 72h return |
|---|---:|---:|---:|
| RAW4 | 373 | **+1.55 ATR** | **+4.08 ATR** |
| MAG4 | 511 | +0.68 ATR | +0.57 ATR |

RAW4 forward path is clearly directional. Therefore causal regime is real information about subsequent price path.

However path direction is not equivalent to monetizable R-expectancy under the frozen payoff geometry.

## 3. Regime-only synthetic strategy

STRUCT_BREAK is removed completely.

Synthetic execution:
- entry = next/current M15 open when high-regime state begins;
- side = sign(`DIR72_ATR`);
- SL distance is frozen from DEV `riskATR` tail distribution, not optimized:
  - Q25 = 3.970 ATR
  - Q50 = 4.652 ATR
  - Q75 = 5.402 ATR
- TP = 2.3R;
- BE after +1R;
- cost = 0.06R;
- one position at a time.

VAL results:

| Score | Stop scale | N | EV | bootstrap 95% CI | Positive years |
|---|---|---:|---:|---|---:|
| RAW4 | Q25 | 152 | +0.074R | [-0.135, +0.297] | 2/3 |
| RAW4 | Q50 | 136 | -0.019R | [-0.245, +0.209] | 2/3 |
| RAW4 | Q75 | 120 | +0.046R | [-0.188, +0.283] | 1/3 |
| MAG4 | Q25 | 233 | +0.066R | [-0.104, +0.239] | 2/3 |
| MAG4 | Q50 | 200 | +0.025R | [-0.157, +0.214] | 2/3 |
| MAG4 | Q75 | 166 | -0.016R | [-0.221, +0.191] | 2/3 |

**No regime-only configuration reaches the preregistered +0.10R economic gate. No confidence interval excludes zero.**

The conclusion is unchanged under opposite intrabar ordering assumptions.

## 4. Nearest-regime surrogate control — strongest test

For each of the 67 VAL `riskATR > 3.72` STRUCT_BREAK trades:
1. freeze its side and its exact `riskATR`;
2. find 20 nearest **non-STRUCT_BREAK** M15 moments in the same calendar year using standardized causal `DIR/ER/VOL/LOCATION`;
3. exclude ±3h around every STRUCT_BREAK entry and ±7 days around the source trade;
4. enter mechanically at the control M15 open;
5. use the source trade's own `riskATR`, TP=2.3R, BE=+1R and 0.06R costs.

Results:

- actual STRUCT_BREAK tail: **+0.121R**
- matched regime-only controls (K=20): **-0.071R**
- structural-minus-control: **+0.191R**
- paired source bootstrap 95% CI: **[-0.180, +0.565]R**
- P(diff <= 0): **0.159**

Sensitivity:
- K=5 control EV = **-0.141R**, structural-minus-control = **+0.261R**
- K=10 control EV = **-0.086R**, structural-minus-control = **+0.207R**
- K=20 control EV = **-0.071R**, structural-minus-control = **+0.191R**

Entering matched controls at bar close instead of open gives **-0.085R**, so the sign is not an open-entry artifact.

Yearly K=20:
- 2023: tail **+0.177R** vs control **-0.198R**
- 2024: tail **+0.015R** vs control **+0.025R**
- 2025: tail **+0.182R** vs control **-0.066R**

## 5. Interpretation

LAB004 showed that conditioning on regime removes roughly 63% of the raw tail-vs-nontail difference **inside the STRUCT_BREAK population**.

LAB005 asks the stronger question: does regime alone monetize when the structural event itself is removed?

Answer: **no**.

The causal regime can identify directional persistence in price, especially RAW4, but it cannot reproduce the tail's +0.121R payoff under the frozen 2.3R / BE geometry. Closely matched non-STRUCT_BREAK market moments are neutral-to-negative even when they inherit the exact side and riskATR of each tail trade.

This means:
- `riskATR tail = simply regime` is **not supported**.
- regime is probably a **context / amplifier**, not the whole cause.
- a residual contribution from structural timing, entry geometry, or another structural state remains plausible.
- that residual is **not yet statistically validated**, because N=67 and the paired CI still crosses zero.

## 6. Formal verdict

**REGIME_ONLY_REPRODUCTION_FAIL**  
**STRUCTURAL_RESIDUAL_WATCH**

Do not promote `riskATR > 3.72` as a rule.

But do not discard the structural hypotheses. The correct next experiment is now narrowly scoped:

> Within matched regime, explain why STRUCT_BREAK tail timestamps outperform nearby non-STRUCT_BREAK timestamps.

Primary candidates to test next, one at a time:
1. protected-pivot prominence / correction depth;
2. sweep-before-break;
3. break/entry geometry (limit location relative to impulse and retest).

No new `riskATR` threshold search is allowed.
