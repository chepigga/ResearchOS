# GC_XAU_MICRO_LEAD_LAG_FLOW_BURST_LAB002A_PREREG

Status: PREREGISTERED_INFORMATION_TIMING_DIAGNOSTIC_NOT_OOS

Purpose: separate pure GC->XAU information lead from FTMO Bid/Ask execution friction.

Frozen inputs:
- exact event ledger produced by LAB002; no event re-selection
- same direction, GC window, mechanism, TRAIN/VALID/POST labels
- same FTMO XAU raw ticks and +180m clock mapping

XAU information price = mid=(Bid+Ask)/2.

Diagnostics:
- predicted-direction mid return at +0.25s,+0.5s,+1s,+2s,+3s,+5s,+10s,+30s,+60s, normalized by prior completed XAU M1 ATR
- first passage within 60s to +0.05 ATR and -0.05 ATR from action-time mid
- predicted-side-first share among events hitting either threshold
- median first predicted response time

No candidate is promoted from this addendum. It only determines whether LAB002's negative executable returns are primarily spread/friction or absence of directional information lead.
