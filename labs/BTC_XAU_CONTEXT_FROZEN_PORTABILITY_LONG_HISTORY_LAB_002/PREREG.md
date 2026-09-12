# BTC_XAU_CONTEXT_FROZEN_PORTABILITY_LONG_HISTORY_LAB_002 — preregistration

## Why LAB002 exists
LAB001 used the frozen ResearchOS `btc_15m.zip`, which was discovered after preregistration to contain only 2025-10-01 through 2025-10-31. That one-month sample produced zero H4-ready bars because the frozen Context router requires long warm-up. LAB002 fixes the **data horizon only**; no strategy rule, threshold, component, weight, or hypothesis is changed in response to outcomes.

## Market / fixed history
- Market: Binance USD-M Futures BTCUSDT.
- Native resolution: 15m monthly public archive from `data.binance.vision`.
- Fixed months: **2021-01 through 2026-07 inclusive**.
- H4 is aggregated causally from native M15, epoch-aligned.
- Missing archive months, if any, are reported. If >2 months are missing or a gap intersects the evaluation population, the result is flagged DATA_INCOMPLETE rather than silently patched.

## Frozen logic — unchanged from XAU LAB007-LAB018
1. Exact H4 Context router score definitions, readiness mask, 3-bar smoothing, hysteresis/min-hold/gap.
2. Temporal role semantics from LAB009.
3. G1 compression = `range24_ratio < 0.85 AND atr_ratio < 0.95`.
4. D1 HTF Bias and D2 Trend Pressure; D14 = exact D1/D2 concordance, no retuning.
5. Frozen population = `PULLBACK + G1 + D14 != 0`.
6. Exact M15 confirmation components from LAB016:
   - OB_CONFIRM
   - IMBALANCE_CONFIRM
   - LIQUIDITY_CONFIRM
   - PRICE_ACTION_CONFIRM
   Equal 25% weights; score ∈ {0,25,50,75,100}.
7. First-passage target = first ±1 H4 ATR from the H4 close/availability time within 8h. With native M15 data, if both sides are touched in one M15 candle, mark AMBIGUOUS and exclude from resolved accuracy.

## Primary hypotheses — identical thresholds to LAB001
H1 — HIGH75 overall transfers:
- N resolved >= 60
- accuracy > 55%
- weekly-cluster bootstrap 95% CI lower bound > 50%.

H2 — BULL HIGH75 transfers:
- N resolved >= 30
- accuracy > 60%
- CI lower bound > 50%.

H3 — BEAR HIGH75 transfers:
- N resolved >= 25
- accuracy > 55%
- CI lower bound > 50%.

H4 — XAU directional asymmetry transfers:
- BULL accuracy - BEAR accuracy > 0
- both sides N >= 25
- weekly-cluster bootstrap 95% CI lower bound > 0.

## Mandatory diagnostics
- H4 ready bar count and episode count.
- Gate counts: PULLBACK, G1, D14, pairwise intersections, final population.
- Score buckets 0/25/50/75/100.
- BULL/BEAR HIGH75 metrics.
- Component value by side.
- Exact 3-of-4 and 4-of-4 composition counts/accuracy.
- Calendar-year HIGH75 metrics 2021–2026 where eligible.
- 24h signed follow-through in ATR units.

## Verdict mapping
- `BTC_PORTABILITY_CONFIRMED`: H1 passes and at least one of H2/H3 passes, with no side N>=25 below 45% accuracy.
- `BTC_PARTIAL_PORTABILITY`: H1 fails but at least one directional H2/H3 passes, or H1 passes while directional structure differs materially from XAU.
- `BTC_PORTABILITY_NOT_SUPPORTED`: H1 fails and neither H2 nor H3 passes, with adequate population.
- `BTC_PORTABILITY_UNDERPOWERED`: final resolved population is insufficient for H1 and both directional tests.
- `DATA_INCOMPLETE`: fixed history could not be assembled causally enough to evaluate.

## Anti-overfit constraints
- No threshold changes after outcomes.
- No component or score redefinition.
- No BTC-specific weights in this LAB.
- No selecting favorable years or sessions.
- Any attractive BTC-specific rule discovered is diagnostic only and requires a new preregistered LAB.

## Interpretation boundary
This tests **direction/confirmation portability**, not trade profitability, RR, fees, slippage, funding, or FTMO BTCUSD execution parity. It cannot be used as `P(profitable trade)`.