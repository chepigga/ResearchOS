# LAB055B — CF191G 60M OVEREXTENSION HARD SKIP — PREREGISTRATION

## Frozen hypothesis

**B: skip a CF191g entry if signed 60-minute return in trade direction is > +1.0 ATR at entry.**

Threshold fixed before results: X = **+1.00 ATR**.
ret60_atr = side * (completed M5 close at entry - completed M5 close 60m ago) / current completed ATR snapshot at entry.
This matches LAB054's causal completed-M5 feature convention.

Interpretation: if price already travelled more than +1 ATR in the intended trade direction during the prior hour, classify entry as potentially overextended/exhausted.

No other signal, entry, exit, risk, pause, daily-cap, or management parameter changes.

## Frozen control

Exact OLD_v191g_POSITIVE_SKEW lineage from LAB053:
- Z threshold 1.00
- M5 confirmation +0.30 ATR
- max confirmation window 45m
- max adverse 0.75 ATR
- same-side crowd at confirm
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

The gate is evaluated only after the existing confirmation passes and immediately before entry.
If ret60_atr > +1.00: signal skipped; no position; day count and last-entry state are not updated; future reachability changes naturally.

Therefore this is a full stateful rerun.

## Evaluation

Report separately: 2021–2025 and 2026 Mar–Aug.
Primary metrics: N, WR, EV, PF, SumR, MaxDD_R, R/DD, max consecutive losses, positive years/months, skip count.

Period PASS requires: EV improves; PF improves; MaxDD does not worsen; R/DD improves; positive-period count does not worsen.
Overall promotion requires PASS in both periods.

No X-threshold search after results.