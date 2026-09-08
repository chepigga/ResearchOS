# BTC_RETAIL_FLOW_REACCEPTANCE_EXTENSION050_VS_SECOND_FAILURE_FIRST_PASSAGE_LAB_032

## Question
After frozen FULL_REACCEPT from LAB030, does a further +0.5 ATR directional extension occur before a second two-close failure, and does that state leave positive residual drift to original signal +12h?

## Frozen lineage
- Exact LAB030 `failure_recovery_stream.csv`.
- Use only `full_reaccept == true`.
- Pre-Aug expected lineage: 701; Aug reused audit only.
- Frozen levels:
  - origin = original flow signal close.
  - acceptance entry = original + side * 0.5 ATR.
  - extension050 level = acceptance entry + side * 0.5 ATR.
- ATR is the same frozen signal ATR carried through the lineage.

## Primary OCO after FULL_REACCEPT
Start on the first M15 bar strictly after `full_reaccept_time` and observe until original `signal_time + 12h`.

### EXTENSION050_FIRST
The first bar whose high/low touches the frozen extension050 level in the flow direction.

### SECOND_FAIL_FIRST
The first occurrence of two consecutive completed M15 closes through the original signal price against the flow direction.

### AMBIGUOUS
If extension050 touch and the second failure close occur on the same M15 bar, ordering is unknowable at M15 resolution. Exclude from primary state comparison.

### NONE
Neither state occurs before original +12h.

## Anti-tautology residual
- EXTENSION050_FIRST residual starts from the exact extension050 threshold, not from the reaccept price and excludes the +0.5 ATR move used to define the state.
- SECOND_FAIL_FIRST residual starts from the actual second-failure M15 close.
- Outcome endpoint remains original signal +12h close.
- No TP, stop, entry simulation, or state rescue in the primary test.

## Windows
2021, 2022, 2023, 2024, 2025H1, 2025H2, 2026 Jan-Jul, Aug 2026 reused audit, HIST, RECENT, ALL_PRE_AUG.
Report LONG/SHORT and 2022 SHORT separately.

## Support statistics
- 7-day cluster bootstrap, 5000 draws, fixed seed.
- Compare EXTENSION050_FIRST residual minus SECOND_FAIL_FIRST residual.
- Report state frequencies, time from reaccept to classification, residual mean/t/PF/win rate, and post-class MAE/MFE.

## Gates
1. Exact LAB030 full-reaccept pre-Aug lineage >=690.
2. EXTENSION050_FIRST N>=200 pre-Aug.
3. SECOND_FAIL_FIRST N>=50 pre-Aug.
4. Ambiguous rate <=10% of classified states.
5. EXTENSION050 residual >0 pre-Aug.
6. SECOND_FAIL residual < EXTENSION050 residual.
7. Residual gap >=0.50 ATR.
8. 7d bootstrap 95% CI lower >0.
9. Recent EXTENSION050 N>=40.
10. Recent EXTENSION050 residual >0.
11. 2025H2 and 2026 EXTENSION050 residual both >0.
12. 2022 SHORT EXTENSION050 N>=15 and residual >0.
13. LONG and SHORT EXTENSION050 residual both >0.
14. EXTENSION050 win rate >55%.

PASS requires >=11/14 and critical gates 1,5,8,9,10,11. WATCH if overall extension state is positive but transfer is incomplete. Otherwise FAIL.

## Guardrails
- No threshold search: extension is exactly +0.5 ATR inherited from LAB031 audit.
- No alternate close count, horizon, side-specific threshold, calendar router, or later qualifying event rescue.
- Same-bar ambiguity is not guessed.
- This is reused research lineage, not fresh prospective OOS.
- Live allocation = 0.