# FXArena Exit Policy Tournament v002 — P0–P7 Falsification Catalogue

**Status:** corrected provisional interpretation after DD-convention audit.  
**Caution:** exact RH6 gross-DD replay with the original sampler/seeds is still required.

| Policy | Class | Mechanism | Total net R | EV | Gross MaxDD | Net MaxDD | RH1 | RH2 gross | RH3 | RH4 | RH5 | RH6 gross estimate | Corrected provisional verdict |
|---|---|---|---:|---:|---:|---:|---|---|---|---|---|---|---|
| P0 | Baseline | TP2 / TO120 | 1848.87 | 0.5230 | 14.416 | 15.827 | — | Baseline | PASS | Baseline | — | — | BASELINE |
| P1 | Complex | Adaptive TP from MFE head | 1996.79 | 0.5649 | 14.416 | 15.827 | PASS | PASS | PASS | retrain required | PASS | FAIL est. | FAIL — tail stability |
| P2 | Complex | Adaptive timeout from time-to-MFE head | 1829.52 | 0.5175 | 14.790 | 16.201 | FAIL | PASS | PASS | retrain required | FAIL | FAIL est. | FAIL — economics, permutation, tail |
| P3 | Complex | Adaptive TP + timeout | 1988.10 | 0.5624 | 14.790 | 16.201 | PASS | PASS | PASS | retrain required | PASS | FAIL est. | FAIL — tail stability |
| P4 | Complex by frozen spec | TB flag → TP3; otherwise P0 | 2134.36 | 0.6038 | 14.416 | 15.827 | PASS | PASS | PASS | PASS | PASS | FAIL est. | FAIL — tail stability |
| **P5** | **Simple** | **BE@60; otherwise P0** | **1984.15** | **0.5613** | **13.572** | **15.812** | **PASS** | **PASS** | **PASS** | **PASS** | **N/A** | **PASS est.** | **PROVISIONAL WINNER; exact RH6 required** |
| P6 | Simple | 50% at +1R, remainder TP2 | 1500.27 | 0.4244 | 12.746 | 14.085 | FAIL | PASS | PASS | PASS | N/A | FAIL | FAIL — economics |
| P7 | Simple | P5 + P6 | 1643.97 | 0.4651 | 13.853 | 15.961 | FAIL | PASS | PASS | PASS | N/A | FAIL total | FAIL — economics |

## Adaptive-head negative result

The heads contain some predictive signal, but not enough to justify policy complexity:

| Head target | Mean OOS R² | Mean OOS Spearman |
|---|---:|---:|
| MFE | 0.099 | 0.315 |
| MAE | 0.058 | 0.228 |
| Time to MFE | 0.012 | 0.140 |

Interpretation:

- MFE prediction was useful enough for P1/P3 to improve Total R, but block-tail stability remained insufficient.
- Time-to-MFE was weak; P2 reduced Total and failed permutation evidence.
- P1 and P3 did not beat the simple P5 on a risk-adjusted, gate-complete basis.
- The frozen Occam rule therefore points to P5 if exact gross-DD RH6 confirms the estimate.

## Why this belongs in the falsified catalogue

The tournament answered a real question: the adaptive heads did not justify their implementation and model-risk cost. This result must remain visible even though the subsequent post-hoc P4b router has better full-sample economics.
