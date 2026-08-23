# XAU_RETEST_BAR_EARLY_HEALTH_PROXY_AND_IFVG_ENTRY_LAB_007 — v001 REPORT

**Verdict:** `NO_EARLY_HEALTH_PROXY`  
**Holdout opened:** `false`

## Canonical / causal audit

- canonical SHA: `db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b`
- Discovery training retests: **16,642**
- Confirmation OOS retests: **14,577**
- model features stop at the completed LAB005 retest-confirmation bar
- actual trade entry remains the next contiguous M1 open after that retest close
- sealed holdout `>=2025-07-01`: untouched

## OOS future-health prediction

The model predicts the frozen LAB006 future `PRIMARY_BOTH` state surprisingly well:

- Confirmation ROC AUC: **0.7632**
- frozen Discovery top-30% cutoff: **0.563689**
- selected future-health precision: **59.16%**
- rejected future-health rate: **17.23%**
- health gap: **+41.93 pp**

But this does **not** recover directional/economic edge:

- selected directional correctness: **71.33%**
- rejected directional correctness: **71.78%**
- direction gap: **-0.45 pp**
- weekly direction-gap CI includes zero.

Thus `G1_MODEL_DISCRIMINATION` passes while `G11_EARLY_SELECTION_UPLIFT` fails.

## Primary executable economics — Confirmation / 1.5R / serial

- N: **2,498**
- trades/week: **31.68**
- EV: **-0.1859R**
- PF: **0.722**
- TP rate: **32.23%**
- total: **-464.4R**
- max DD: **475.4R**
- worst day: **-10.61R**
- BUY EV: **-0.1786R**
- SELL EV: **-0.1938R**
- BACK EV: **-0.2062R**
- THROUGH EV: **-0.1674R**
- +$0.10 stress EV: **-0.2636R**
- weekly 95% CI: **[-0.2428, -0.1456]R**

Discovery also fails: EV **-0.1995R**, PF **0.707**.  
2R Confirmation also fails: EV **-0.1614R**, PF **0.772**.

## Why a 0.763 AUC still loses money

The parent counterfactual is reproduced exactly:

- true future-health (`PRIMARY_BOTH=true`) LAB005 retest entry EV: **+0.1893R**
- future-health fail EV: **-0.3661R**
- therefore the selected subset needs approximately **65.9%** true-health precision merely to break even.

LAB007 reaches only **59.2%**.

More importantly, its false positives are extremely toxic:

- selected + true health: N **2,602**, EV **+0.192R**
- selected + false health: N **1,796**, EV **-0.751R**, directional correctness only **52.7%**

Those false positives erase the good selected trades.

## iFVG finding

The model coefficient table shows the structural problem:

- `existing_aligned_ifvg` coefficient: **+2.146**
- full OOS AUC: **0.763**
- OOS AUC without existing iFVG: **0.558**

So most health-label predictability comes from knowing that an aligned iFVG already exists.

But inside the Confirmation cohort where that iFVG is already present:

- N: **5,050**
- future-health base rate: **59.64%**
- retest-bar geometry AUC: **0.505**
- top-30% geometry health precision: **60.82%**
- top-30% EV: **-0.1834R**

That is effectively no discrimination. A single retest bar cannot tell whether the already-present iFVG will be followed by healthy re-acceleration or failure.

## Frozen gates

- G0_DATA_CAUSALITY: PASS
- G1_MODEL_DISCRIMINATION: PASS
- G2_PRIMARY_POWER: PASS
- G3_CONFIRMATION_EV: FAIL
- G4_WEEK_CLUSTER_CI: FAIL
- G5_SPLIT_TRANSFER: FAIL
- G6_2R_SURVIVAL: FAIL
- G7_DIRECTION_BREADTH: FAIL
- G8_BRANCH_BREADTH: FAIL
- G9_PROP_DD_PROXY: FAIL
- G10_COST_STRESS: FAIL
- G11_EARLY_SELECTION_UPLIFT: FAIL

## Interpretation

LAB007 closes the **single-retest-bar** early-health hypothesis.

> The retest-close contains enough information to predict the formal LAB006 health label mainly because an iFVG may already be present, but it does not contain enough information to distinguish profitable continuation from toxic false-positive iFVG setups.

The next causal dimension, if pursued, should not be more confirmation after the retest and should not be another threshold on the same bar. The rational next test is the **pre-retest micro-sequence** already known before the entry: 3–5 completed M1 bars describing how price approached, penetrated and reclaimed the role-flip zone, optionally with causal tick-volume/intensity features. Entry must remain the LAB005 next-open price.

No holdout opening or live/EA allocation is authorized.
