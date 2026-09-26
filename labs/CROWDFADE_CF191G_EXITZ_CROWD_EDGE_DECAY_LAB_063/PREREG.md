# LAB063 — CF191G EXITZ / CROWD-EDGE DECAY MAP — PREREGISTRATION

## Purpose

Test whether post-fill decay or reversal of the original CrowdFade crowd edge contains causal management information.

Diagnostic only. No exit is executed in this LAB.
CF191g entry core and management remain frozen.

## Frozen control parity
- 2021–2025: N=5297, SumR=+700.3704107793633
- 2026 Mar–Aug: N=544, SumR=+35.49784078156513

## Crowd-edge definition

At every completed M5 bar after fill:
`crowd_edge = -trade_side * Z`

For BUY (trade_side=+1): negative Z supports the BUY crowd-fade thesis.
For SELL (trade_side=-1): positive Z supports the SELL crowd-fade thesis.

Natural states:
- STRONG_PERSIST = crowd_edge >= +0.75
- WEAK_PERSIST = 0 < crowd_edge < +0.75
- SIGN_FLIP = crowd_edge <= 0
- OPP_EXTREME = crowd_edge <= -0.75 (subset of SIGN_FLIP)

Threshold 0.75 is inherited from frozen CF191g confirmation min-|Z| and prior strict contradiction convention. Zero is the natural sign boundary.

## Fixed post-fill horizons

Classify crowd_edge at completed M5 horizons:
- 15m
- 30m
- 60m
- 120m

Also record the first causal transition time within the 6h hold to:
- below +0.75
- <= 0
- <= -0.75

No threshold search is allowed.

## Outcomes

For every canonical CF191g trade report:
- frozen final R / exit reason
- MFE/MAE 15/30/60/120m
- signed return 15/30/60/120m
- crowd_edge at entry and each fixed horizon
- first transition times

## Primary diagnostic

Primary horizon = 30m.
In BOTH 2021–2025 and 2026 test ordered deterioration:
- STRONG_PERSIST should have better EV/PF and MFE/MAE geometry than SIGN_FLIP
- OPP_EXTREME should not outperform STRONG_PERSIST

Report all state Ns. No production exit from LAB063.

## Next-step rule

If SIGN_FLIP or OPP_EXTREME is consistently toxic with meaningful sample in both periods, a later LAB may preregister exactly one stateful ExitZ action.
If not, ExitZ branch is not promoted.