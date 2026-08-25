# STRUCT_BREAK_PROTECTED_PIVOT_MECHANISM_LAB_016 — RESULT

Date: 2026-08-25
Preregistration: e18a7d8fa285845b5abec6d3a2ec30db218c341a

Formal verdict: `ALL_FOUR_SELECTOR_REJECTED__OLD_PIVOT_AGE_CONDITIONAL_WATCH`

## Primary result
Frozen `riskATR > 3.72` tail:
- DEV N=65, EV +0.460R
- VAL N=67, EV +0.121R

All-four q67 rule (`riskATR>3.72 AND age>=15 AND displacement>=4.56ATR AND unviolated`):
- DEV N=54, EV +0.409R
- VAL N=54, EV +0.068R

Thus adding all four does not improve the frozen tail.

## Redundancy
Spearman 2019-2025:
- pivot age vs riskATR: rho 0.396
- displacement vs riskATR: rho 0.646
- pivot age vs displacement: rho 0.552

Inside the riskATR tail, `PIVOT_UNVIOLATED` is 100% in both DEV and VAL, so it adds no selection information.

DEV-trained continuous 4-feature REACHED_1R model:
- DEV AUC 0.524
- VAL AUC 0.492
- selected VAL EV -0.046R

Expanding yearly walk-forward selected aggregate:
- N=401
- EV -0.050R
- 95% CI [-0.171,+0.074]

## Surviving WATCH seed
DEV-frozen q91 age threshold = 22 bars.

`riskATR > 3.72 AND pivot_age >= 22`:
- DEV N=37, EV +0.494R, CI about [+0.021,+0.975]
- VAL N=34, EV +0.293R, CI about [-0.134,+0.749]

VAL yearly:
- 2023 N=10 EV +0.330R
- 2024 N=7 EV +0.169R
- 2025 N=17 EV +0.322R

Across 2019-2025: N=71, EV about +0.398R; pooled bootstrap lower CI positive (~+0.08R).

This does not pass promotion because VAL N<40 and VAL CI crosses zero, but it is the simplest coherent positive structural lineage that survives this test.

Interpretation: displacement is largely a restatement of wide riskATR, and unviolated is intrinsic to the tail. The relatively independent dimension is the age of the protected pivot.
