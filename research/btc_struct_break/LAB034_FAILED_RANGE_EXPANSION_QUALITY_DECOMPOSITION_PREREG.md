# BTC_FAILED_RANGE_EXPANSION_QUALITY_DECOMPOSITION_LAB_034

Status: PREREGISTERED BEFORE CALCULATION
Date: 2026-08-27

## Objective
Decompose the native M15 FAILED_RANGE_EXPANSION engine from LAB033 to identify causal quality components that can improve expectancy and drawdown while retaining material frequency.

## Frozen parent engine
- Native FAILED_RANGE_EXPANSION_ENGINE from LAB033.
- M15 event clock.
- Reclaim midpoint trigger, retest up to 8 bars, latest confirmed pivot5 stop, TP 2.3R, BE at +1R, cost 0.06R.
- No change to parent trigger/execution in this LAB.

## Frozen diagnostics / bins
1. SHOCK_TR_MULTIPLE = shock true range / trailing median TR20:
   - 2.0-2.5
   - 2.5-3.0
   - >3.0
2. SHOCK_CLOSE_EXTREME:
   - extreme <=10% / >=90%
   - moderate 10-25% / 75-90%
3. RECLAIM_SPEED_BARS:
   - 1-2
   - 3-4
   - 5-8
4. RETEST_DELAY_BARS:
   - 1-2
   - 3-4
   - 5-8
5. FIRST_ATTEMPT_RECLAIM:
   - true if first bar after shock already reclaims midpoint
6. ATR_REGIME = ATR14 / lagged median ATR96:
   - <0.9
   - 0.9-1.1
   - >1.1
7. PRIOR_BALANCE_DISTANCE_ATR = distance from reclaim level to nearest edge of prior 12-bar range / ATR14:
   - <=0.5
   - 0.5-1.0
   - >1.0
8. PIVOT_DISTANCE_ATR = entry to latest confirmed stop pivot / ATR14:
   - <2.5
   - 2.5-3.72
   - >3.72
9. BUY/SELL split is diagnostic only and cannot be selected as primary in LAB034.

## Frozen evaluation
DEV: <=2022
VAL: 2023-2025
2026: shadow only

A simple component/bin becomes a replication seed only if:
- DEV EV > 0
- VAL N >= 450 total over 3 years (>=150/year target)
- VAL EV >= +0.12R
- VAL PF >= 1.30
- at least 2/3 VAL years positive
- VAL 1.5x cost EV > 0
- VAL MaxDD <= 15R standalone
- overlap with BASE3 <= 40%
- no single year >70% of positive contribution

Portfolio admission diagnostic with BASE3:
- 150-300 trades/year
- EV >= +0.15R
- PF >= 1.35
- MaxDD <= 10R
- profitable months >=60%
- Recovery >=2

No threshold movement, no ML, no conjunction search beyond single frozen components/bins in this LAB.
