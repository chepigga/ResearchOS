# LAB047 — V191_DUAL_TOXIC_GATE_EXIT_GEOMETRY

Status: PRE-REGISTERED BEFORE EXECUTION

## Frozen signal / entry population

Use the exact SUPPORTED LAB046 causal lane:

- BTCUSDT only
- v191 crowd signal: |Z| >= 1.00, contrarian side
- freshness / confirm TTL <=45m
- confirm move = 0.30 ATR against crowd
- original v191d confirm-side consistency
- cancel if max pre-confirm adverse excursion >0.75 ATR
- causal RAPID_REPEAT_30 veto:
  skip if previous completed-M5 same-sign |Z|>=1 crowd extreme occurred <=30m ago
- causal HIGH_VOL veto:
  skip if completed-M15 ATR14 / completed-M5 close >= lagged 30-day M5 q67
- pause = 1.0 ATR
- max trades/day = 3
- flat cost proxy = 0.5 bps

No entry gate, signal threshold, volatility threshold, repeat threshold,
confirmation threshold, pause rule, day-cap or cost assumption may change in LAB047.

All variants MUST be replayed statefully from raw chronological data.
Exit timing changes occupancy and therefore future signal reachability.

## Baseline management control

CONTROL_V191:
- SL = 1.50 ATR
- fixed TP = OFF
- BE arm = +0.50 ATR
- BE lock = +0.15 ATR
- trailing arm = +2.50 ATR
- trailing gap = 0.50 ATR
- ExitZ = 0.75
- max hold = 6h

## Pre-registered exit/management variants

### A. Existing-management ablations
1. CONTROL_V191
2. EXITZ_OFF
   - identical to control except ExitZ disabled.
3. BE_OFF
   - identical to control except break-even logic disabled.
4. TRAIL_OFF
   - identical to control except trailing logic disabled.
   - BE remains active.

### B. Shorter time-stop scalp tests
5. HOLD_3H
   - identical control geometry, max hold = 3h.
6. HOLD_2H
   - identical control geometry, max hold = 2h.

### C. Compact fixed-profit tests
7. TP_1R
   - SL remains 1.50 ATR.
   - fixed TP = +1.0 initial R = +1.50 ATR from entry.
   - BE/trail/ExitZ/H6 remain as control.
8. TP_1P5R
   - SL remains 1.50 ATR.
   - fixed TP = +1.5 initial R = +2.25 ATR from entry.
   - BE/trail/ExitZ/H6 remain as control.

### D. Compact SL/TP scalp tests
9. SL1_TP1
   - SL = 1.00 ATR.
   - TP = +1.0R = +1.00 ATR.
   - BE arm/lock are expressed in ATR and remain +0.50/+0.15 ATR.
   - trail remains arm +2.50 ATR / gap0.50 ATR.
   - ExitZ0.75, H6 retained.
10. SL1_TP1P5
   - SL = 1.00 ATR.
   - TP = +1.5R = +1.50 ATR.
   - all other management as immediately above.

No interaction search between winning variants is allowed inside LAB047.

## Immutable reference
V192_CANONICAL_CONTROL remains unchanged and is replayed on the common frame.

## Samples
Historical:
- 2021-01-01 through 2025-12-31
- BTCUSDT 1-minute OHLC execution frame.

Forward shadow/stress:
- 2026-03-01 through 2026-08-31
- BTCUSDT second OHLC execution frame.

2026 is reused shadow/stress, not pristine OOS.

## Required metrics
For every candidate and v192:
- N
- WR
- EV
- PF
- SumR
- MaxDD_R
- R/DD
- max consecutive losses
- exit-reason counts
- historical yearly metrics
- 2026 monthly metrics
- full chronological trade ledger
- stateful reachability delta vs CONTROL_V191

Also report:
- median hold minutes
- p90 hold minutes
- winner median R
- loser median R
- share of trades exiting by each management rule.

## Decision rule

A candidate is SUPPORTIVE only if:
1. aggregate EV > 0 and PF > 1.0 in BOTH historical and 2026;
2. >=4/5 historical years have SumR > 0;
3. >=4/6 2026 months have SumR > 0;
4. historical and 2026 MaxDD_R are not both worse than CONTROL_V191;
5. candidate does not reduce trade count below 40% of CONTROL_V191 in either sample.

Among SUPPORTIVE candidates, no "winner" is chosen solely by maximum backtest EV.
Report the Pareto trade-off across EV, R/DD, DD and frequency.

FAILED:
- EV <=0 or PF<=1 in either aggregate sample.

MIXED:
- aggregate positive in both but one or more robustness criteria fail.

## Interpretation guardrail
LAB047 may identify whether the validated v191 lane behaves better with:
- existing management,
- weaker management,
- a shorter time-stop,
- or compact fixed-profit scalp geometry.

It does NOT authorize production promotion.
Any multi-parameter combination inferred from LAB047 requires a new preregistered LAB.
