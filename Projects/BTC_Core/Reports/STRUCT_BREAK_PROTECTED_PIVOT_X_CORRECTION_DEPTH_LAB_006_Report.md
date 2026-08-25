# STRUCT_BREAK_PROTECTED_PIVOT_X_CORRECTION_DEPTH_LAB_006

**Date:** 2026-08-25  
**Status:** REJECTED_AS_MISSING_SELECTOR  
**Preregistered spec:** ResearchOS commit `021cdfe79b147981e2a5a32518fe6d9252b0a5a5`

## Question
Can causal `protected pivot significance × correction depth/maturity` explain why the frozen `riskATR > 3.72` tail exists and provide the missing entry-quality selector that makes STRUCT_BREAK profitable?

## Data / causality
- BTCUSDT M15 exact release dataset used in LAB004/005.
- Verdict period: 2019-09-08 through 2025-12-31.
- STRUCT_BREAK trades: 1,465.
- DEV: 767 trades, 2019-09..2022-12.
- VAL: 698 trades, 2023-01..2025-12.
- Frozen tail: `riskATR > 3.72`, 132 trades = 65 DEV + 67 VAL.
- 2026 excluded.
- Existing R already includes 0.06R round-turn cost.
- Stop pivot reconstructed exactly as frozen v002: last stop-side M15 5-5 pivot satisfying `pivot+5 <= fill-1`.
- All 1,465 trades have complete protected-pivot and correction features.
- No feature uses post-entry information.

## Frozen LAB006 structural features
Protected pivot: PIVOT_AGE_BARS, PIVOT_SHARPNESS_ATR, PIVOT_CONFIRM_REJECTION_ATR.
Correction: CORR_DEPTH_ATR, CORR_DURATION_BARS, CORR_EFFICIENCY, PRIOR_IMPULSE_ATR, CORR_RETRACE_RATIO, CORR_DURATION_RATIO.

Correction is measured from the prior opposite confirmed 5-5 pivot to the stop-side 5-5 pivot, not from stop to entry. Therefore CORR_DEPTH_ATR is not a relabeling of riskATR.

## Result A — structural features explain the riskATR tail
A fixed 9-feature structural logistic model trained on DEV to classify tail membership:
- DEV AUC: 0.939
- VAL AUC: 0.894
- VAL AP: 0.574 at 9.6% tail prevalence.

Top transferable single features:
- PIVOT_AGE_BARS: DEV AUC 0.889, VAL 0.818.
- PIVOT_SHARPNESS_ATR: DEV 0.674, VAL 0.732.
- PIVOT_CONFIRM_REJECTION_ATR: DEV 0.679, VAL 0.725.
- CORR_DEPTH_ATR: DEV 0.692, VAL 0.690.

Stable medians:
- PIVOT_AGE_BARS: DEV tail 23 vs non-tail 12; VAL tail 22 vs 13.
- PIVOT_SHARPNESS_ATR: DEV 2.30 vs 1.81; VAL 2.66 vs 1.85.
- CORR_DEPTH_ATR: DEV 4.32 vs 2.74; VAL 4.30 vs 2.90.

Interpretation: `riskATR > 3.72` is largely the geometric signature of an older, sharper stop pivot formed after a deeper correction.

## Result B — the same features do not predict trade success
Target: `REACHED_1R = be==1 OR R>1`.

No single structural feature transfers as an entry-quality discriminator. Best VAL separability was PIVOT_SHARPNESS_ATR at only ~0.533 AUC-equivalent, p=0.128.

Fixed multivariate results:
- PROTECTED: DEV AUC 0.525, VAL 0.526; selected DEV EV +0.127R, VAL +0.020R, VAL N=245, 95% CI [-0.136,+0.179].
- CORRECTION: DEV AUC 0.544, VAL 0.486; selected DEV EV +0.150R, VAL +0.006R, VAL N=263, 95% CI [-0.152,+0.165].
- COMBINED: DEV AUC 0.574, VAL 0.514; selected DEV EV +0.231R, VAL +0.021R, VAL N=270, 95% CI [-0.127,+0.176].
- BASELINE: DEV AUC 0.534, VAL 0.461; selected VAL EV -0.150R.
- BASELINE+STRUCT: DEV AUC 0.578, VAL 0.498; selected VAL EV +0.007R.

COMBINED VAL yearly selected EV:
- 2023: -0.066R
- 2024: +0.186R
- 2025: -0.059R
Only 1/3 VAL years positive.

## Gates
WATCH required all:
1. Causality/data integrity — PASS.
2. COMBINED VAL AUC >0.55 — FAIL (0.514).
3. top-third EV >0 in DEV and VAL — PASS, but VAL only +0.021R.
4. VAL selected N >=100 — PASS (270).
5. BASELINE+STRUCT relative uplift — PASS relative to poor baseline, but absolute VAL EV only +0.007R.

WATCH therefore FAILS.
STRONG CANDIDATE also fails: VAL EV <+0.10R, CI crosses zero, only 1/3 VAL years positive.

## Post-hoc robustness — not part of verdict
All 18 protected-feature × correction-feature cross-products were added in one fixed L2 model with no term selection:
- DEV AUC 0.605
- VAL AUC 0.501
- VAL selected EV +0.032R
- 95% CI [-0.128,+0.204]
It also fails to transfer.

Within frozen tail, no feature has stable DEV→VAL outcome discrimination. PIVOT_CONFIRM_REJECTION_ATR looked strongest in VAL (~0.626 AUC) but had DEV ~0.483 and VAL p~0.083, so it is not admissible as a selector.

Applying the preregistered COMBINED score on top of the frozen tail gives 33 VAL trades with EV -0.127R; diagnostic only.

## Formal verdict
`TAIL_GEOMETRY_EXPLAINED__OUTCOME_SELECTOR_REJECTED`

LAB006 strongly explains what `riskATR > 3.72` is: an older, sharper protected stop pivot associated with a deeper correction. But those properties do not explain why the trade wins.

Therefore protected pivot / correction depth in this formalization is rejected as the missing profitability selector. The missing information must occur elsewhere in the sequence, most plausibly between correction extreme → break → retest/fill, rather than in static pre-break geometry alone.

## Next clean falsification
A causal event-sequence test:
`CORRECTION EXTREME → LIQUIDITY SWEEP / FAILED ACCEPTANCE → BREAK DISPLACEMENT QUALITY → FIRST RETEST RESPONSE`, with no threshold mining and the same DEV/VAL discipline.
