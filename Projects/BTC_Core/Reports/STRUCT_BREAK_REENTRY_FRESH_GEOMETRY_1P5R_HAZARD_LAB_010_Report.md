# STRUCT_BREAK_REENTRY_FRESH_GEOMETRY_1P5R_HAZARD_LAB_010

**Date:** 2026-08-25  
**Status:** COMPLETED  
**Preregistration commit:** `487d020a161af6f83e39a4229978d95180ff4a79`  
**Formal verdict:** `FRESH_GEOMETRY_1P5R_REENTRY_REJECTED`

## Question
Treat the LAB009B re-entry as a completely new trade with fresh stop/target geometry and test whether the new impulse can deliver a transferable TP >= 1.5×SL edge.

## Frozen fresh geometries
1. ATR 1.0× ATR14(M5).
2. Last confirmed opposing M5 pivot 3-3.
3. Hybrid = farther of pivot and 1.0× ATR14(M5).

Fresh risk normalized to 1R. Cost 0.06R per re-entry. Primary TP=1.5R, secondary TP=2.0R. DEV 2019–2022, VAL 2023–2025, 2026 excluded.

## Primary TP=1.5R

| Geometry | DEV EV | VAL EV | VAL 95% CI | VAL TP rate |
|---|---:|---:|---:|---:|
| ATR 1.0× M5 | +0.071R | **-0.096R** | [-0.367,+0.175] | 38.6% |
| Local M5 pivot 3-3 | +0.095R | **-0.117R** | [-0.387,+0.158] | 37.2% |
| Hybrid | +0.157R | **-0.149R** | [-0.419,+0.120] | 35.9% |

All three are positive on DEV and negative on VAL. Every geometry is positive in only 1/3 VAL years.

For +1.5R/-1R with 0.06R cost, fair binary win probability is about 42.4%. VAL TP-before-SL rates are below fair for every branch: ATR 38.6%, local pivot 37.7%, hybrid 36.4%.

## Full portfolio effect

| Geometry | Canonical VAL EV | Adaptive VAL EV | Improvement | Max DD |
|---|---:|---:|---:|---:|
| ATR | -0.031R | -0.051R | -0.019R | 38.78R → 54.49R |
| Local pivot | -0.031R | -0.053R | -0.021R | 38.78R → 56.45R |
| Hybrid | -0.031R | -0.056R | -0.025R | 38.78R → 58.95R |

## M1 replication
Exact M1 replay for 2024–2025 gives 100% outcome agreement with M5 for all tested branches/targets. Failure is not an M5 ordering artifact.

## Secondary BE-after-1R diagnostic
Only ATR 1.0× M5 with TP=2R + BE@+1R is mildly interesting:
- DEV +0.083R
- VAL +0.060R
- VAL CI [-0.205,+0.326]

WATCH only; no promotion.

## Interpretation
LAB009B predicted renewed progress relative to the old setup. LAB010 asks the fresh-trade question: from the new entry price, can price deliver +1.5 fresh R before -1R? OOS: no.

The likely problem is execution timing: after 30-minute HIGH confirmation, a meaningful part of the available excursion is already consumed.

# Verdict
`FRESH_GEOMETRY_1P5R_REENTRY_REJECTED`

Next clean diagnostic: `STRUCT_BREAK_REENTRY_EARLY_TRANSITION_HAZARD_LAB_011`, using only already validated response variables on a 5m/15m rolling event clock and freezing thresholds on DEV.