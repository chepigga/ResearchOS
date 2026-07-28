# AK47_POST_M3_AUCTION_RHYTHM_VALIDATION_LAB_001

**Date:** 2026-07-29  
**Rule status:** frozen before this validation  
**Frozen rule:** `0.50 < pre30_alternation <= 4/7`  
**Verdict:** **IN-SAMPLE STATISTICAL PASS / RESEARCH WATCH**

## 1. Dataset
- Post-M3 episodes: **116**
- WATCH matches: **36**
- Other post-M3 entries: **80**
- Period: 2026-01-02 16:31:12 to 2026-07-15 16:04:37
- Source: native M1 Bid/Ask bars; no new MT5 run.

## 2. Frozen profile result
- WATCH EV: **+0.529R**
- WATCH PF: **2.42**
- WATCH WR: **58.3%**
- WATCH Sum: **+19.06R**
- OTHER EV: **-0.262R**
- Delta EV: **+0.791R**

## 3. Statistical validation
- One-sided permutation p-value: **0.00175**
- Episode bootstrap 95% delta CI: **[+0.248, +1.354]R**
- Month-block bootstrap 95% delta CI: **[+0.176, +1.444]R**
- Winsorised WATCH EV: **+0.529R**
- Winsorised OTHER EV: **-0.266R**
- Top-3 winning trades share of WATCH gross positive R: **24.3%**

## 4. Stability
- BUY: N=18, EV=+0.610R, PF=2.80
- SELL: N=18, EV=+0.449R, PF=2.11
- Positive WATCH months: **4/7**
- Leave-one-month-out remained positive in every exclusion.

## 5. Non-M3 comparison
Using the same frozen rule on all 354 available entries:

| post_m3 | group | N | EV_R | Sum_R | WR | Median_R | PF |
|---|---:|---:|---:|---:|---:|---:|---:|
| False | OTHER | 180 | +0.081 | +14.53 | 47.2% | -0.177 | 1.16 |
| False | WATCH | 57 | +0.269 | +15.35 | 47.4% | -0.359 | 1.53 |
| True | OTHER | 80 | -0.262 | -20.96 | 32.5% | -1.004 | 0.58 |
| True | WATCH | 37 | +0.522 | +19.32 | 59.5% | +0.172 | 2.44 |

Difference-in-differences for WATCH uplift, post-M3 versus non-M3: **+0.596R**.

The rhythm profile therefore appears specifically valuable after M3, not merely as a generic entry-quality filter.

## 6. Interpretation
The frozen profile remains economically strong and passes all internal statistical controls. However, it was discovered on this same 2026 canonical run. These tests validate robustness, not true out-of-sample generalisation.

## 7. Verdict
- Internal statistical validation: **PASS**.
- Research status: **WATCH**.
- Production implementation: **NOT ALLOWED YET**.

## 8. Required next test
Reconstruct the unchanged rule on an independent 2022–2025 Python replay or another canonical EA run. Only after independent PASS should the filter be implemented in MT5 for one confirmation run.
