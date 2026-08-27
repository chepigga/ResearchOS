# BTC_NATIVE_M15_MULTI_EVENT_FAMILY_ENGINE_DISCOVERY_LAB_033

Date: 2026-08-27

Goal: discover independent native M15 alpha engines that generate their own entries, not selectors of canonical BREAK_RETEST.

Frozen native families:
1. FAILED_RANGE_EXPANSION_ENGINE
2. BALANCE_BREAK_FAILURE_ENGINE
3. IMPULSE_EXHAUSTION_RECLAIM_ENGINE
4. VOLATILITY_SHOCK_MEAN_REENTRY_ENGINE

Common execution:
- M15-only causal signals.
- Entry = first retest of frozen event boundary within 8 completed M15 bars after trigger.
- Stop = latest confirmed opposite-side pivot5 available before fill.
- TP = 2.3R.
- Move stop to BE after +1R.
- Cost = 0.06R.
- One active position per family; adverse same-bar ordering.
- No side selection, no threshold tuning after results.

Family definitions:
FAILED_RANGE_EXPANSION_ENGINE:
- shock bar true range >=2.0x median prior20 TR;
- adverse close in outer quartile;
- within next 8 bars close reclaims shock midpoint;
- entry retest = shock midpoint.

BALANCE_BREAK_FAILURE_ENGINE:
- 12-bar balance range <= lagged trailing-20d median 12-bar range;
- adverse close outside balance boundary;
- within next 3 bars close back inside;
- entry retest = failed boundary.

IMPULSE_EXHAUSTION_RECLAIM_ENGINE:
- 3 consecutive adverse candles;
- displacement from pre-impulse close to third close >=1.5 ATR14;
- within next 8 bars close reclaims impulse midpoint;
- entry retest = midpoint.

VOLATILITY_SHOCK_MEAN_REENTRY_ENGINE:
- ATR14 / lagged median ATR96 >=1.5;
- shock closes outside prior 8-bar close range against trade direction;
- within next 8 bars close re-enters prior close range;
- entry retest = re-entry boundary.

Promotion gates per family on VAL 2023-2025:
- DEV EV > 0
- VAL N 90..300 (30..100/year)
- VAL EV >= +0.10R
- PF >=1.25
- >=2/3 positive VAL years
- 1.5x cost EV >0
- overlap with current BASE3 <=40%
- no single VAL year >70% of positive net contribution.

Portfolio target after survivor union with BASE3:
- 150..300 trades/year
- EV >=+0.15R
- PF >=1.35
- MaxDD <=10R
- >=60% profitable months
- Recovery >=2
- worst rolling 3m >=-3R.

2026 is shadow only.