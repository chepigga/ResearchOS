# STRUCT_BREAK_PROTECTED_PIVOT_X_CORRECTION_DEPTH_LAB_006 — TZ v001

Status: PREREGISTERED
Date: 2026-08-25
Universe: BTCUSDT M15 exact release data, 2019-09-08..2025-12-31 for verdict. 2026 excluded.
Baseline: frozen STRUCT_BREAK v002. `riskATR > 3.72` remains exploratory frozen tail; threshold must not move.

## Purpose
Test whether the apparent `riskATR` tail is explained by a causal structural state: significance of the stop-side confirmed M15 5-5 pivot and maturity/depth of the immediately preceding countertrend correction.

## Causality
All features must be fully knowable no later than the bar before the limit fill. The stop pivot is exactly the last confirmed 5-5 pivot satisfying `pivot_index + 5 <= fill_index - 1`, matching run_v002.

## Frozen feature definitions
For each trade at fill index t and side:

### Protected-pivot block
- `PIVOT_AGE_BARS = t - p`, where p is the exact stop-side 5-5 pivot index.
- `PIVOT_SHARPNESS_ATR`: on the fixed 5-5 confirmation wings only. BUY low: min(max(high[p-5:p])-low[p], max(high[p+1:p+6])-low[p]) / ATR14[t-1]. SELL high: min(high[p]-min(low[p-5:p]), high[p]-min(low[p+1:p+6])) / ATR14[t-1].
- `PIVOT_CONFIRM_REJECTION_ATR`: BUY `(close[p+5]-low[p])/ATR14[t-1]`; SELL `(high[p]-close[p+5])/ATR14[t-1]`.

### Correction block
Let q be the latest opposite-type confirmed 5-5 pivot before p. Let r be the latest same-type 5-5 pivot before q.
- `CORR_DEPTH_ATR = abs(extreme[p]-extreme[q]) / ATR14[t-1]`.
- `CORR_DURATION_BARS = p - q`.
- `CORR_EFFICIENCY = abs(close[p]-close[q]) / sum(abs(diff(close[q:p+1])))`.
- `PRIOR_IMPULSE_ATR = abs(extreme[q]-extreme[r]) / ATR14[t-1]`.
- `CORR_RETRACE_RATIO = correction_price_depth / prior_impulse_price_depth`.
- `CORR_DURATION_RATIO = (p-q)/(q-r)`.

No feature may use post-entry bars or the distance from stop pivot to entry/broken level except the already frozen `riskATR` baseline.

## Splits
- DEV: 2019-09..2022-12.
- VAL: 2023-01..2025-12.
- 2026: excluded from verdict.

## Tests
1. Tail-explanation: tail vs non-tail distribution and single-feature AUC on DEV and VAL.
2. Entry-quality: target `REACHED_1R = (be==1) OR (R>1.0)`. Report single-feature AUC DEV/VAL.
3. Fixed multivariate models, no hyperparameter search: LogisticRegression C=1, L2, standardized features.
   - PROTECTED = 3 protected-pivot features.
   - CORRECTION = 6 correction features.
   - COMBINED = all 9 features.
   - BASELINE = riskATR + causal LAB004 regime variables DIR72_ATR, ER72, VOL24_14D, LOC30D.
   - BASELINE_PLUS_STRUCT = BASELINE + all 9 LAB006 features.
4. Models train on DEV only. Threshold for selected subset = DEV 67th percentile of each model score. Apply unchanged to VAL.
5. Report VAL N, EV after existing 0.06R cost, bootstrap 95% CI, reached-1R rate, and yearly EV.
6. Primary question: does BASELINE_PLUS_STRUCT improve VAL outcome ranking/EV over BASELINE, and does a structural-only selector retain positive DEV and VAL EV without moving thresholds?

## Gates
WATCH requires all:
- no data/causality failure;
- combined structural model VAL AUC for REACHED_1R > 0.55;
- DEV-selected top-third has EV > 0 in both DEV and VAL;
- VAL selected N >= 100;
- BASELINE_PLUS_STRUCT VAL AUC exceeds BASELINE by >= 0.02 OR selected VAL EV improves by >= +0.05R.

STRONG CANDIDATE additionally requires:
- selected VAL EV >= +0.10R;
- bootstrap 95% CI lower bound > 0;
- positive EV in at least 2 of 3 VAL calendar years.

If these gates fail, protected-pivot/correction-depth is rejected as the missing selector in this formalization. No post-hoc threshold rescue inside LAB006.
