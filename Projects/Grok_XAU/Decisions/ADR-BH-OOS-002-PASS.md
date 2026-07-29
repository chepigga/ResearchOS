# ADR-BH-OOS-002 — Enable BH_SWEEP on demo after OOS PASS

**Date:** 2026-07-24  
**Status:** ACCEPTED  
**Scope:** Grok_XAU / AK47_FT

## Decision

Set `InpBH_Enable=true` only for a controlled demo forward month using the
unchanged v1.56 BH defaults and `InpBH_RiskPct=0.30`.

Live enablement is not approved.

## Evidence

- Step 0 reproduced N=88, BUY=52, SELL=36 and EV=+0.276R.
- Frozen OOS produced N=14 and EV_net=+0.235714R.
- All three OOS months were positive.
- No OOS trades were unresolved.

## Constraints

- No post-hoc SELL removal despite SELL EV=-0.05R.
- No parameter optimization.
- Preserve prop-firm portfolio safety gates.
- Complete and review one forward month before any live decision.

## Reversal condition

Disable the demo module and reopen research if forward execution shows:
material signal drift, missing/duplicate signals, cost materially above the
registered convention, or rule-breaking drawdown behaviour.
