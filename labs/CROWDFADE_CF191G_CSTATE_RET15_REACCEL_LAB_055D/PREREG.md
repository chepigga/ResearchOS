# LAB055D — CF191G C-STATE + RET15_DIR RE-ACCELERATION TEST — PREREGISTRATION

## Frozen hypothesis D

Skip a CF191g entry only when ALL are true at causal entry time:
- ret60_atr > +1.00
- eff60 < +0.25
- ret15_dir <= 0.00

Only one new axis is added versus preregistered C: ret15_dir.

Definitions:
- ret60_atr = side * (completed M5 close at entry - completed M5 close 60m ago) / current completed ATR snapshot.
- eff60 = side * net 60m completed-M5 displacement / sum(abs(diff(completed M5 closes))) over same path.
- ret15_dir = side * (completed M5 close at entry - completed M5 close 15m ago) / current completed ATR snapshot.

Interpretation:
- C-state identifies large displacement + weak 60m efficiency.
- D asks only whether the most recent 15m has failed to re-accelerate in the trade direction.
- ret15_dir <= 0 is the natural sign boundary; no threshold search.

## Frozen control

Exact OLD_v191g_POSITIVE_SKEW lineage from LAB053/055A/B/C.
Parity targets:
- 2021–2025: N=5297, SumR=+700.3704107793633
- 2026 Mar–Aug: N=544, SumR=+35.49784078156513

## Causal semantics

Gate is evaluated only after existing CF191g confirmation passes and immediately before entry.
If all three conditions are true, skip candidate without updating day count or anti-repeat last-entry state.
Future reachability evolves naturally; full stateful replay required.

## Evaluation

Report separately for 2021–2025 and 2026 Mar–Aug:
- N
- SumR
- EV
- PF
- MaxDD_R
- R/DD
- positive years/months
- max consecutive losses
- skip count

Period PASS requires:
- SumR not lower
- EV improves
- PF improves
- MaxDD does not worsen
- R/DD improves
- positive-period count does not worsen
- max consecutive losses does not worsen

Overall promotion requires PASS in both periods.

No OI, no confirm-age, no additional threshold, no post-result tuning inside this LAB.