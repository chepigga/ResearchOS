# GC → XAU COMPREHENSIVE RESEARCH BACKLOG / RECOVERY STATE 007

Updated: 2026-09-23
Scope: GC futures / AMP MT5 → FTMO XAUUSD only.

## Frozen Q65 reversal branch
- 5s post-signed impulse >= 0.0521
- 30s aligned volume >= 20.60
- entry = REV2 + 30s
- SL = 2.25 ATR
- TP = 4.50 ATR
- max hold = 300s
- risk = 0.25%
- FTMO commission model = 0.0007% notional per side
- status = FORWARD DEMO / NOT PRODUCTION PROVEN

Infrastructure PASS:
- AMP sensor live
- FILE_COMMON bridge live
- FTMO demo executor live
- survives RDP/Mac disconnect
- real demo XAU order opened and timeout-closed successfully

## LAB012 — LIVE_MISSED_OPPORTUNITY_AUDIT_20260923
23.09:
- 286 BASE_SIGNAL
- 97 episodes
- 3 causal REV2
- 0 Q65 ACCEPT
- 2 final DOMINANCE_REVERSAL
- both final DOMINANCE_REVERSAL were caught live => 2/2 recall that day

## LAB013 — FINAL_CLASS_OTHER_MISSED_EDGE_AUDIT_20260923
95 OTHER:
- MIXED_START 53
- MONO 29
- DOM_REV1_ONLY 12
- DOM_REV2_OTHER 1

Single-day discovery suggested MONO continuation, requiring historical causal replication.

## LAB014 — MONO_CONTINUATION_CAUSAL_EDGE
Historical:
- 15,206 unique MARKET_NOW signals
- 5,341 anchored episodes
- 1,973 final MONO episodes

Causal prefix MONO1–4 fail on exact LAB005 5m FTMO outcomes.
MONO5:
- FULL N=18
- Hold300 EV ≈ +0.861 ATR
- G20 EV ≈ +0.333R / PF ≈ 1.60
- insufficient sample

Episode-final all-MONO:
- 1,919 priced episodes
- FULL +5m EV ≈ +0.016 ATR / PF 1.02
- FULL +15m EV ≈ +0.037 / PF 1.03
- FULL +30m EV ≈ +0.155 / PF 1.10
=> generic MONO rejected

N=3 completed MONO / +30m is gross-positive across TRAIN / VALID / POST, but:
- 0.2 spread + commission => VALID ≈ -0.009 ATR
- 0.4 spread + commission => FULL ≈ -0.047 ATR
=> NO PRODUCTION CANDIDATE

## Critical interpretation
LAB013 was a real strong-trend-day observation, but LAB014 shows it does not generalize into a generic MONO edge.
Frozen Q65 remains unchanged.

## Open parity issue
Current live sensor uses:
first2 same + latest2 consecutive opposite.

Frozen LAB007D REV2 is:
second occurrence of reversal direction after initial dominance, not necessarily consecutive.

Historical REV2:
- 161/173 at signal index 4
- 12/173 at signal index 5

Must fix/audit before production claims.

## P0
- Keep Q65 demo running unchanged
- collect fresh ACCEPT forward sample
- no threshold loosening
- correct REV2 causal parity and rerun historical parity audit

## P1 — LAB015 MONO_LONG_HISTORY_REPLICATION
Use long GC compact 2025-01-01 → 2026-09-15.
Predeclare:
- final MONO
- N=1/2/3/4/5+
- clock = anchor + 300s
- no outcome-driven tuning

Targets:
- MONO5 replication
- N=3 / 30m replication

## P1 — LAB016 MONO_VOLUME_SPACING_MECHANISM
Raw AMP directional ticks:
- cumulative directional volume
- median/total spacing
- cumulative impact deterioration
- attack volume acceleration/deceleration
- session descriptive only initially

TRAIN-derived thresholds only; freeze before VALID/OOS.

## P1 — LAB017 MONO_N3_EXACT_EXECUTION
Only if LAB015 survives:
- exact FTMO bid/ask
- commission
- spread distribution
- slippage sensitivity
- executable entry after finalization
- SL/TP >= 1:1.5
- predeclared timeout grid
- DD/streak/Monte Carlo

## P1 — live shadow MONO logger
Log only:
- final class
- N
- direction
- cumulative impact
- volume
- spacing
- XAU price at finalization
- +1/+3/+5/+15/+30m virtual outcomes

NO MONO orders.

## Overall
Infrastructure: PASS
Bridge: PASS
Demo execution: PASS
Frozen Q65: FORWARD DEMO / NOT PRODUCTION PROVEN
MONO: REJECT GENERIC STRATEGY / WATCHLIST ONLY
