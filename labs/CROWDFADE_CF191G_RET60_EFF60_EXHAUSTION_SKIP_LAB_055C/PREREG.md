# LAB055C — CF191G OVEREXTENSION × WEAK EFFICIENCY SKIP — PREREGISTRATION

## Frozen hypothesis

Skip a CF191g entry only when BOTH are true at the actual causal entry time:
- ret60_atr > +1.00
- eff60 < +0.25

Thresholds are fixed before results.

Definitions:
- ret60_atr = side * (completed M5 close at entry - completed M5 close 60 minutes ago) / current completed ATR snapshot at entry.
- eff60 = side * (completed M5 close at entry - completed M5 close 60 minutes ago) / sum(abs(diff(completed M5 closes))) across the same 60-minute path.
- All inputs use completed M5 information available no later than entry.

Interpretation: price has already travelled >1 ATR in the intended trade direction, but the 60m path is inefficient/choppy enough to suggest exhaustion rather than clean continuation.

## Frozen control

Exact OLD_v191g_POSITIVE_SKEW lineage from LAB053 / LAB055A/B:
- Z threshold 1.00
- M5 confirmation +0.30 ATR
- confirmation window 45m
- max adverse before confirm 0.75 ATR
- same-side crowd consistency
- |confirm Z| >= 0.75
- response ratio >= 0.50
- SL 1.5 ATR
- BE arm 3.0 ATR / lock 2.25 ATR
- trail arm 3.5 ATR / gap 0.5 ATR
- max hold 6h
- anti-repeat 1 ATR
- max 3/day
- 0.5 bps research cost proxy

Parity targets:
- 2021–2025 control: N=5297, SumR=+700.3704107793633
- 2026 Mar–Aug control: N=544, SumR=+35.49784078156513

## Causal semantics

The gate is evaluated only after the existing CF191g confirmation passes and immediately before entry.
If ret60_atr > 1.0 AND eff60 < 0.25:
- skip the candidate
- do not open a position
- do not increment day trade count
- do not update last-entry anti-repeat state
- allow future reachability to evolve naturally

This must therefore be a full stateful replay, not post-hoc trade deletion.

## Evaluation

Report separately:
1. 2021–2025
2. 2026 Mar–Aug shadow/stress

Report versus control:
- N
- SumR
- EV
- PF
- MaxDD_R
- R/DD
- positive years/months
- max consecutive losses
- number of skipped candidates

Period PASS requires:
- SumR not lower
- EV improves
- PF improves
- MaxDD does not worsen
- R/DD improves
- positive-period count does not worsen
- max consecutive losses does not worsen

Overall promotion requires PASS in both periods.

No threshold search or combination with A/B after results inside this LAB.