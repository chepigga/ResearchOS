# XAU_CONTEXT_CONFIRMATION_COMPONENT_REDUNDANCY_AND_75PCT_REPLICATION_LAB_017

**Verdict: 75PCT_COMPOSITION_FRAGILE**

- Population: **397**; exact resolved: **220**
- HIGH75: **N=72**, accuracy **0.681**, 95% CI **[0.583, 0.781]** — H1 **PASS**
- Critical redundancy pairs: **0**
- H2 composition robustness: **FAIL** (2/2 eligible combinations >50%)
- H3 collapsed-domain robustness: **N/A**
- H4 BULL/BEAR symmetry: **FAIL**

## Pairwise redundancy

| component_a       | component_b          |   n11 |   n10 |   n01 |   n00 |    phi |   jaccard_positive |   agreement | critically_redundant   |
|:------------------|:---------------------|------:|------:|------:|------:|-------:|-------------------:|------------:|:-----------------------|
| OB_CONFIRM        | IMBALANCE_CONFIRM    |    65 |    53 |   158 |   121 | -0.014 |              0.236 |       0.469 | False                  |
| OB_CONFIRM        | LIQUIDITY_CONFIRM    |    23 |    95 |   103 |   176 | -0.171 |              0.104 |       0.501 | False                  |
| OB_CONFIRM        | PRICE_ACTION_CONFIRM |   102 |    16 |   257 |    22 | -0.088 |              0.272 |       0.312 | False                  |
| IMBALANCE_CONFIRM | LIQUIDITY_CONFIRM    |    49 |   174 |    77 |    97 | -0.238 |              0.163 |       0.368 | False                  |
| IMBALANCE_CONFIRM | PRICE_ACTION_CONFIRM |   214 |     9 |   145 |    29 |  0.213 |              0.582 |       0.612 | False                  |
| LIQUIDITY_CONFIRM | PRICE_ACTION_CONFIRM |   113 |    13 |   246 |    25 | -0.017 |              0.304 |       0.348 | False                  |

## Exact 75% combinations

| combination     | missing_component    |   n_resolved |   accuracy | eligible   | positive   | fragile_low   |
|:----------------|:---------------------|-------------:|-----------:|:-----------|:-----------|:--------------|
| NO_OB           | OB_CONFIRM           |           26 |      0.538 | True       | True       | False         |
| NO_IMBALANCE    | IMBALANCE_CONFIRM    |            7 |      0.714 | False      | False      | False         |
| NO_LIQUIDITY    | LIQUIDITY_CONFIRM    |           31 |      0.742 | True       | True       | False         |
| NO_PRICE_ACTION | PRICE_ACTION_CONFIRM |            0 |    nan     | False      | False      | False         |

## 100% bucket

- N_resolved: **8**; accuracy: **0.875**

## Conditional incremental value

| component            |   eligible_strata |   weighted_conditional_accuracy_premium |   total_weight |
|:---------------------|------------------:|----------------------------------------:|---------------:|
| OB_CONFIRM           |                 4 |                                   0.110 |             62 |
| IMBALANCE_CONFIRM    |                 4 |                                   0.032 |             79 |
| LIQUIDITY_CONFIRM    |                 4 |                                   0.103 |             68 |
| PRICE_ACTION_CONFIRM |                 1 |                                  -0.062 |              8 |

## HIGH75 side symmetry

| side   |   n_resolved |   accuracy |
|:-------|-------------:|-----------:|
| BULL   |           42 |      0.762 |
| BEAR   |           30 |      0.567 |

## Constraints

- Frozen LAB016 confirmation definitions and equal 25% weights.
- Reused-history robustness audit, not fresh OOS validation.
- Confirmation % is evidence coverage, NOT probability of profit and NOT automatic-entry permission.