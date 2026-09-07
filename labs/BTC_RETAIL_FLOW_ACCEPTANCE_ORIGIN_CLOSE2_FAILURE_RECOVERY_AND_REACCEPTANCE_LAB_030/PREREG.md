# BTC_RETAIL_FLOW_ACCEPTANCE_ORIGIN_CLOSE2_FAILURE_RECOVERY_AND_REACCEPTANCE_LAB_030

## Question
After a frozen LAB029 `ORIGIN_CLOSE2` failure, is the failure terminal, or do some events causally recover and reaccept the original flow direction before the original +12h horizon? Does this recovery behavior explain the recent 2025H2-2026 degradation of the two-close exit?

## Frozen lineage
- Exact LAB029 `origin_close2_execution_stream.csv`.
- Exact flow direction, +0.5 ATR acceptance entry, original signal price, ATR clock, 12h horizon, and 5 bps convention.
- Analyze only ACCEPT events with `origin_close2_trigger == True`.
- No new flow thresholds, stop thresholds, horizon search, side rescue, or calendar filter.

## Frozen failure time
Failure time is the exact LAB029 second consecutive completed M15 close through the original flow-signal price (`origin_close2_time`).

## Causal recovery states after failure, before original signal +12h
All checks use completed M15 closes only and begin strictly after the frozen failure bar.

1. `ORIGIN_RECLAIM` — first completed M15 close back to the flow side of the original signal price:
   `side * (close - signal_close) > 0`.

2. `FULL_REACCEPT` — after failure, first completed M15 close back to the flow side of the original acceptance entry (`signal_close + side*0.5*ATR`):
   `side * (close - entry) > 0`.
   This is the PRIMARY recovery state.

3. `NO_REACCEPT` — no FULL_REACCEPT before original +12h.

No optimized waiting window is allowed; recovery may occur at any completed M15 close remaining before original +12h.

## Primary anti-tautology outcome
For `FULL_REACCEPT`, measure signed residual return from the reaccept close to the original +12h close, normalized by the original frozen ATR. The move needed to reaccept is excluded from this residual.
For `NO_REACCEPT`, measure signed return from the frozen failure close to original +12h.

Primary mechanism hypothesis:
- FULL_REACCEPT residual > 0;
- FULL_REACCEPT residual > NO_REACCEPT residual;
- NO_REACCEPT residual <= 0 or materially weaker.

## Recovery anatomy
Report:
- ORIGIN_RECLAIM rate;
- FULL_REACCEPT rate;
- median bars/hours failure->origin reclaim;
- median bars/hours failure->full reaccept;
- failure close excursion in ATR;
- post-failure MAE/MFE;
- whether full reaccept occurs after one or more extra closes below origin.

## Era test
Fixed windows:
- 2021
- 2022
- 2023
- 2024
- 2025 H1
- 2025 H2
- 2026 Jan-Jul
- Aug 2026 reused audit only
- HIST = 2021..2025H1
- RECENT = 2025H2..2026 Jul

Critical question: is RECENT characterized by a materially higher FULL_REACCEPT rate and/or stronger residual after FULL_REACCEPT than HIST?

## Sides
Report LONG and SHORT separately; 2022 SHORT is a fixed bearish stress-test.

## Diagnostic re-entry audit
For FULL_REACCEPT only, hypothetical re-entry at the completed reaccept close, 5 bps RT, no TP, exit at original +12h. No stop. This is diagnostic only and cannot be promoted to a trading rule in LAB030.

## Bootstrap
5000 resamples of 7-day clusters, fixed seed 20260907.
Primary statistic: mean residual FULL_REACCEPT minus NO_REACCEPT.

## PASS gates
1. exact LAB029 lineage and >=900 triggered failures pre-Aug;
2. FULL_REACCEPT N >= 200 pre-Aug;
3. FULL_REACCEPT residual > 0;
4. FULL_REACCEPT residual > NO_REACCEPT residual by >=0.50 ATR;
5. 7d bootstrap 95% CI lower bound for residual difference > 0;
6. NO_REACCEPT residual <= 0 OR at least 0.50 ATR below FULL_REACCEPT;
7. RECENT FULL_REACCEPT N >= 40;
8. RECENT FULL_REACCEPT residual > 0;
9. RECENT FULL_REACCEPT residual > RECENT NO_REACCEPT residual;
10. recent recovery rate >= historical recovery rate + 5 percentage points OR recent recovery residual >= historical recovery residual +0.25 ATR;
11. 2022 SHORT FULL_REACCEPT N>=20 and residual >0;
12. LONG and SHORT FULL_REACCEPT residual both >0.

PASS requires >=10/12 including gates 1,3,4,5,7,8,9. WATCH if the recovery state is strongly discriminative but recent transfer or bootstrap is incomplete. Otherwise FAIL.

## Guardrails
- Recovery thresholds are only the already frozen origin and acceptance levels.
- No stop/TP/horizon/number-of-closes optimization.
- No live promotion from this LAB.
- August 2026 is reused audit only.
- Live allocation remains 0.