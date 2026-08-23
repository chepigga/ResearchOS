# XAU_STRONG_BIAS_ACCEPTED_SIDE_INTERNAL_STRUCTURE_MAP_LAB_011 — v001 REPORT

**Verdict:** `DEEP_RETEST_ADVERSE_BUT_NO_INTERNAL_EDGE`  
**Holdout opened:** `false`

## Strong-bias universe

- Discovery: **2,700**
- Confirmation: **2,622**
- Confirmation resolved NEW_LEG vs LEVEL_FAILURE: **1,873**
- Confirmation unresolved: **28.6%**

## Old-level return is adverse

Discovery NEW_LEG rate: no LEVEL_RETEST **35.9%** vs any LEVEL_RETEST **11.0%** (gap +24.9 pp).

Confirmation: no LEVEL_RETEST **35.0%** vs any LEVEL_RETEST **10.2%** (gap +24.9 pp).

## Internal ordered-path prediction — resolved target

- SNAPSHOT AUC: **0.7916**
- BAG AUC: **0.8060**
- ORDERED_PATH AUC: **0.8151**
- ordered - snapshot: **+0.0234**, weekly CI **[0.007265368648426137, 0.03255618051606555]**
- ordered - bag: **+0.0090**, weekly CI **[0.005002498199772052, 0.01792867010838408]**
- ordered Brier: **0.1648**
- probability Q5-Q1 actual NEW_LEG gap: **+78.4 pp**

## Most frequent internal paths

- `DEEP_PULLBACK>DEEP_PULLBACK>DEEP_PULLBACK`: Discovery N 699, new-leg 26.3%; Confirmation N 658, new-leg 28.6%
- `EXPAND>DEEP_PULLBACK>DEEP_PULLBACK`: Discovery N 235, new-leg 26.8%; Confirmation N 265, new-leg 24.2%
- `DEEP_PULLBACK>LEVEL_RETEST>LEVEL_RETEST`: Discovery N 165, new-leg 1.8%; Confirmation N 165, new-leg 2.4%
- `LEVEL_RETEST>LEVEL_RETEST>LEVEL_RETEST`: Discovery N 167, new-leg 1.8%; Confirmation N 151, new-leg 4.0%
- `DEEP_PULLBACK>DEEP_PULLBACK>LEVEL_RETEST`: Discovery N 113, new-leg 7.1%; Confirmation N 135, new-leg 3.7%
- `EXPAND>EXPAND>DEEP_PULLBACK`: Discovery N 112, new-leg 40.2%; Confirmation N 98, new-leg 34.7%
- `DEEP_PULLBACK>EXPAND>DEEP_PULLBACK`: Discovery N 75, new-leg 28.0%; Confirmation N 86, new-leg 36.0%
- `HOLD>DEEP_PULLBACK>DEEP_PULLBACK`: Discovery N 89, new-leg 32.6%; Confirmation N 78, new-leg 35.9%
- `DEEP_PULLBACK>DEEP_PULLBACK>EXPAND`: Discovery N 82, new-leg 59.8%; Confirmation N 62, new-leg 58.1%
- `EXPAND>EXPAND>EXPAND`: Discovery N 71, new-leg 67.6%; Confirmation N 54, new-leg 70.4%
- `DEEP_PULLBACK>EXPAND>EXPAND`: Discovery N 42, new-leg 59.5%; Confirmation N 52, new-leg 51.9%
- `EXPAND>DEEP_PULLBACK>EXPAND`: Discovery N 38, new-leg 60.5%; Confirmation N 45, new-leg 53.3%

## Constructive paths passing frozen 70% / N>=100 transfer gate

- none

## Breadth

- BUY AUC: **0.8245**
- SELL AUC: **0.8059**
- MID/HIGH/LOW: **0.8059 / 0.7939 / 0.8522**
- 2024 / 2025 H1: **0.8095 / 0.8294**

## Frozen gates

- G0_DATA_CAUSALITY: PASS
- G1_POWER: PASS
- G2_LEVEL_RETEST_ADVERSE: PASS
- G3_INTERNAL_PATH_PREDICTIVE: PASS
- G4_ORDER_INCREMENTAL: PASS
- G5_ORDER_BEATS_BAG: FAIL
- G6_CONSTRUCTIVE_PATH_EXISTS: FAIL
- G7_DIRECTION_MIRROR: PASS
- G8_LEVEL_BREADTH: PASS
- G9_YEAR_TRANSFER: PASS
- G10_CALIBRATION: PASS

No entry/economics or holdout opening is authorized.
