# XAU_ACCEPTED_SIDE_INTERNAL_REACCELERATION_EXECUTION_LAB_012 — v001 REPORT

**Verdict:** `REACCEL_SELECTS_EDGE_BUT_WAITING_TOO_LATE`  
**Holdout opened:** `false`

## Primary Confirmation — MICRO_REACCEL / 1.5R / serial

- N: **977**
- trades/week: **12.55**
- EV: **-0.1426R**
- PF: **0.783**
- TP rate: **35.01%**
- gross EV: **-0.1051R**
- total: **-139.34R**
- max DD: **153.21R**
- worst day: **-5.23R**
- max consecutive losses: **17**
- +$0.10 stress EV: **-0.2176R**
- BUY EV: **-0.1678R**
- SELL EV: **-0.1174R**
- weekly 95% CI: **[-0.2158, -0.0704]R**

## Causal digestion baseline

Confirmation serial DIGESTION_BASELINE:
- N **2,036**
- EV **-0.1774R**
- PF **0.734**

MICRO_REACCEL improves the average trade somewhat, but the causal routed-minus-baseline weekly difference is not robust:
- mean **+0.0305R**
- 95% CI **[-0.0403, +0.1014]R**

## Selection vs timing decomposition

Future MICRO_REACCEL is a strong *selector* of healthy digestion setups, but its causal confirmation arrives too late for the frozen 0.50 ATR risk geometry.

Confirmation independent same-signal diagnostic:
- all causal DIGESTION entries: EV **-0.1721R**, PF **0.742**
- digestion setups that later produce MICRO_REACCEL: earlier digestion entry EV **+0.3541R**, PF **1.790**, TP rate **54.05%**
- digestion setups that never produce MICRO_REACCEL: earlier digestion entry EV **-0.6833R**, PF **0.224**, TP rate **13.15%**
- actual causal entry after MICRO_REACCEL on the selected subset: EV **-0.1512R**, PF **0.772**

Discovery transfers the same pattern:
- future-reaccel-selected earlier entry EV **+0.3798R**, PF **1.866**
- nonselected earlier entry EV **-0.6649R**
- actual delayed micro entry EV **-0.1964R**

Timing cost in Confirmation:
- median wait from digestion close to executable micro entry: **4.0 min**
- median directional entry deterioration: **0.305 ATR = 0.610R**
- mean deterioration: **0.388 ATR = 0.776R**
- paired MICRO minus earlier-entry EV: **-0.505R**; weekly bootstrap CI **[-0.578, -0.438]R**

Waiting for a full next 5-minute EXPAND block is even worse (Confirmation independent 1.5R EV about **-0.218R**), so additional delayed confirmation is not the solution.

## 2R

Confirmation serial:
- EV **-0.1558R**
- PF **0.783**
- N **974**

## Trigger census

- Discovery strong bias: **2,703**; digestion **2,423 (89.64%)**; micro-reaccel **1,180 (48.70% of digestion)**
- Confirmation strong bias: **2,630**; digestion **2,354 (89.51%)**; micro-reaccel **1,160 (49.28% of digestion)**
- median micro wait: **4 min** in both splits
- causality violations: **0**

## Frozen gates

- G0_DATA_CAUSALITY: PASS
- G1_POWER: PASS
- G2_CONFIRMATION_EV: FAIL
- G3_WEEK_CLUSTER_CI: FAIL
- G4_SPLIT_TRANSFER: FAIL
- G5_2R_SURVIVAL: FAIL
- G6_DIRECTION_BREADTH: FAIL
- G7_PROP_DD_PROXY: FAIL
- G8_COST_STRESS: FAIL
- G9_REACCEL_GATE_LIFT: FAIL
- G10_NO_OLD_LEVEL_DEPENDENCE: PASS

## Interpretation

LAB012 finds a high-value latent state but not a causal execution trigger:

> A digestion structure that will re-accelerate soon is highly profitable from the digestion-close location, while one that will not re-accelerate is extremely toxic. By the time re-acceleration is causally visible, the entry has deteriorated by roughly 0.6R median and the edge is gone.

This is not permission to enter earlier using future knowledge. It identifies the next research problem: predict the probability of future re-acceleration using only the **entire ordered story already available at the digestion close**, while preserving the earlier next-M1-open entry. More delayed confirmation is explicitly disfavored by this result.

No holdout opening or live/EA allocation is authorized.