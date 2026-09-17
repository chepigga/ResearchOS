# CROWDFADE_CONFIRMATION_ENTRY_REFINEMENT_LAB_004

Status: PREREGISTERED DISCOVERY-ONLY. No fresh OOS is consumed here.

Updated frozen test defaults:
- InpZThreshold = 2.50
- InpConfirmATR = 0.50
- InpStopATR = 1.50
- InpExitZ = 0.75
- InpPauseMode = ATR
- InpPauseATR = 1.00
- InpMaxTradesPerDay = 3
- TTL = 3h
- Hold = 6h
- BE = arm +0.50 ATR, lock +0.15 ATR
- Trail = arm +2.50 ATR, distance 0.50 ATR
- Entry parent = first causal market confirmation

ATR pause test semantics: after a closed trade, a new entry is allowed only after absolute price displacement from the prior entry is >= 1.00 frozen ATR. Daily cap counts executed entries by UTC date. This interpretation is explicit and can be rerun if live EA semantics differ.

Data discipline:
- Use only already-consumed Mar-Aug 2026 research data.
- No September/fresh data.
- No promotion from LAB004; winner, if any, is frozen for a later fresh OOS lab.

Primary objective: reduce same-bar / immediate-stop entries without materially destroying utilization or right-tail expectancy.

A. ENTRY TIMING ABLATION
A0: tick-touch entry control.
A1: enter at close of the M5 bar that first confirms, only if close still holds beyond confirm level.
A2: enter at close of the next full M5 bar, only if close still holds beyond confirm level.

B. ANTI-IMPULSE VETO
Apply to the best timing state using only completed M5 bars at entry.
Lookbacks: 2, 3, 4 completed M5 bars.
Thresholds: 0.75, 1.00, 1.25 ATR.
Veto if cumulative move is in crowd direction / against contrarian trade and exceeds threshold.

PRIMARY COMPARISONS
1. A0 vs A1 vs A2 without anti-impulse veto.
2. Best timing state vs same state + each anti-impulse veto.
3. All other parameters remain frozen.

SELECTION RULE
Timing candidate survives if aggregate EV >= parent EV, MaxDD <= parent, stop rate falls >=10% relative, retained trades >=60%, at least 4/6 months positive, and no month contributes >40% of total SumR.
Anti-impulse survives if EV improves >=0.02R OR MaxDD falls >=20%, retained trades >=70%, stop rate falls, and sign is positive in >=4/6 months.

Live allocation: 0%. Frozen live CrowdFade unchanged.