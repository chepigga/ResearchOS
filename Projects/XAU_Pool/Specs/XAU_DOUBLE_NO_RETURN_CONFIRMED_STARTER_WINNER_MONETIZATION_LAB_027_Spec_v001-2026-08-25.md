# XAU_DOUBLE_NO_RETURN_CONFIRMED_STARTER_WINNER_MONETIZATION_LAB_027 — Spec v001

Date: 2026-08-25
Status: PRE-OUTCOME FREEZE
Holdout >= 2025-07-01 remains SEALED.

## Purpose
Test whether the already-confirmed double-no-return starter can be monetized better by extending the winner target, without adding/chasing exposure.

## Frozen lineage
- Canonical XAU M1 dataset SHA256: db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b
- Frozen LAB026 event table is the sole health-state lineage.
- Early entry / first 5m probation / adverse/degrade handling are inherited from LAB025.
- Second no-return lineage is inherited from LAB026: primary_promoted=True and the RR>=1.5 add-limit is not touched during the next 5 M1 bars.
- No add tranche is ever opened in LAB027.

## Critical causality rule
A trade is DOUBLE_NO_RETURN_CONFIRMED only if it is still open after the full second 5-minute window (10 completed M1 bars from early entry) and:
1) first LAB025 probation survived with primary_promoted=True;
2) LAB026 RR>=1.5 add-limit was not touched during the second window;
3) neither the original SL nor original TP1.5 was reached before the second confirmation clock.
If TP1.5 was reached before confirmation, it stays a TP1.5 and cannot be retrospectively extended.

## Position sizing
Starter only: 25% risk-budget, entered at frozen early market entry.
No later add-ons.
Commission and stress scale with starter exposure only.

## Primary monetization
- Before second confirmation: frozen TP1.5 / SL1.0 absolute coordinates.
- At second confirmation close (t=entry+9 completed M1; action from next bar): if DOUBLE_NO_RETURN_CONFIRMED and still alive, change TP from 1.5R to 2.0R.
- SL absolute coordinate remains unchanged.
- Max horizon remains 60 minutes from early entry.

## Secondary diagnostics (cannot rescue primary verdict)
A) Same rule but TP2.5 after confirmation.
B) Causal structure-trail proxy after confirmation: no fixed profit target beyond 2.5R cap; exit next M1 open after a completed-bar break of the previous 5 completed M1 directional swing boundary (BUY close below prior-5 low; SELL close above prior-5 high). Frozen SL remains active and 2.5R hard cap remains.
C) Cohort accounting: confirmed-alive vs early TP1.5 vs second-window return vs early failure.

## Controls
1) LAB025 starter-only 25% control with original TP1.5 / SL1.0.
2) Frozen full-immediate baseline for context only.

## Primary gates
G0 causality / frozen lineage PASS.
G1 sufficient confirmed-alive sample: N>=30.
G2 primary starter strategy EV > 0 on Confirmation.
G3 primary confirmed-alive cohort incremental EV vs keeping TP1.5 > 0.
G4 week-cluster CI of primary strategy EV lower bound > 0.
G5 Discovery EV > 0 and Confirmation EV > 0.
G6 BUY and SELL both non-negative.
G7 stress10 EV > 0.
G8 prop DD proxy improved vs full immediate.
G9 TP2.5 diagnostic non-negative (secondary survival, not rescue).

No threshold optimization, no holdout opening, no live/EA authorization.
