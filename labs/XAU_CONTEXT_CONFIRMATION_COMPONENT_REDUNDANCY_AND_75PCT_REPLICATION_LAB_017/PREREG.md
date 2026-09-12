# XAU_CONTEXT_CONFIRMATION_COMPONENT_REDUNDANCY_AND_75PCT_REPLICATION_LAB_017 — PREREG

## Status
Preregistered before LAB017 runner/outcomes. This is a **reused-history structural audit / robustness replication**, not fresh OOS validation and not a trading-edge test.

## Frozen lineage
- Base: LAB016 output commit `e851c023ab51b00c29286ba8f143e2b461ec5c7a`.
- Canonical XAU: release `ak47`, `XAUUSD_M1_20220601_20260723_TICK_NATIVE.csv`, SHA256 `db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b`.
- Frozen Context/router, G1 compression, D14 concordance, M15 aggregation and exact ±1 ATR / 8h first-passage target are unchanged.
- Frozen confirmation definitions are imported unchanged from LAB016:
  1. `OB_CONFIRM`
  2. `IMBALANCE_CONFIRM`
  3. `LIQUIDITY_CONFIRM`
  4. `PRICE_ACTION_CONFIRM`
- Equal weights remain frozen at 25% each. No threshold/definition/weight tuning is allowed in LAB017.

## Population
Exactly the LAB016 population:
`PULLBACK & G1_VOL_COMPRESSION & D14_CONCORDANCE != 0`.
Primary direction outcome uses only exact `BULL_FIRST` / `BEAR_FIRST` ±1 ATR resolutions in the next 8h.

## Purpose
LAB016 found `SETUP_CONFIRMATION >=75%` with 68.1% first-passage accuracy (N=72), while OB and Liquidity had suspiciously similar prevalence/accuracy. LAB017 tests whether the 75% layer is robust to component composition or is an artefact of duplicated evidence.

## Frozen redundancy diagnostics
For each pair among the four binary components compute on the full LAB016 population:
- 2x2 counts,
- Pearson/phi correlation for binary variables,
- Jaccard similarity among positive observations,
- exact agreement rate.

### Critical redundancy rule
A pair is `CRITICALLY_REDUNDANT` only if **both**:
- `abs(phi) >= 0.80`, and
- `Jaccard >= 0.80`.

This threshold is fixed before outcomes. Agreement alone cannot declare redundancy because two rare negatives can inflate agreement.

OB↔Liquidity is the preregistered focal pair; all six pairs are reported.

## Conditional incremental diagnostic
For each component C, stratify resolved observations by the exact 3-bit pattern of the other three components. Keep strata where both C=1 and C=0 have >=5 resolved observations. Within each eligible stratum compute accuracy(C=1)-accuracy(C=0). Aggregate using weight `min(n_present,n_absent)`.

This metric is diagnostic only. It answers whether a component adds information after holding the other three confirmation states fixed; it does not change the score in LAB017.

## 75% replication / composition robustness
`HIGH75 = confirmation >=75%` is frozen exactly as LAB016.

### H1 — absolute 75% replication
On exact resolved observations with HIGH75:
- N >= 60,
- accuracy >55%,
- weekly-cluster bootstrap 95% CI lower bound >50%.
Pass only if all three hold.

### H2 — 3-of-4 composition robustness
For the four exact 75% combinations (exactly three confirmations present):
- `NO_OB` = IMBALANCE + LIQUIDITY + PRICE_ACTION
- `NO_IMBALANCE` = OB + LIQUIDITY + PRICE_ACTION
- `NO_LIQUIDITY` = OB + IMBALANCE + PRICE_ACTION
- `NO_PRICE_ACTION` = OB + IMBALANCE + LIQUIDITY

A combination is eligible at N_resolved >=15.
H2 passes if:
- at least 3 combinations are eligible,
- at least 3 eligible combinations have accuracy >50%, and
- no eligible combination has accuracy <45%.

The 100% (4/4) bucket is reported separately and remains descriptive unless N_resolved >=30.

### H3 — non-duplicate-domain robustness
If any pair is CRITICALLY_REDUNDANT, collapse that pair into one evidence domain for this diagnostic only. The collapsed score has three domains and `STRONG_COLLAPSED` means all three domains are present. H3 passes if N_resolved >=40 and accuracy >55% with weekly-cluster CI lower >50%.
If no pair is critically redundant, H3 is `NOT_APPLICABLE` and does not penalize the verdict.

### H4 — side symmetry at HIGH75
For BULL and BEAR D14 predictions separately at HIGH75:
- each side N_resolved >=20,
- both accuracies >50%,
- absolute difference <=15 percentage points.

## Bootstrap
- 5,000 weekly-cluster bootstrap draws.
- Seed `2026091217`.
- Cluster key: calendar week ending Sunday from `available_time`.

## Verdict
- `75PCT_ROBUST_NO_CRITICAL_REDUNDANCY`: H1+H2+H4 pass and no critical redundant pair.
- `75PCT_ROBUST_WITH_REDUNDANCY`: H1+H2+H4 pass, critical redundancy exists, and H3 passes.
- `75PCT_COMPOSITION_FRAGILE`: H1 passes but H2 or H4 fails, or critical redundancy exists and H3 fails.
- `75PCT_NOT_REPLICATED`: H1 fails.

## Interpretation constraints
- A positive verdict supports a human-facing **setup evidence score**, not probability of profit.
- Reused history means even a positive verdict remains discovery/robustness evidence only.
- No automated-entry permission, risk increase, or weight optimization is authorized by this LAB.
