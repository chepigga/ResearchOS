# GC_XAU_REPEATED_FAILED_ATTACK_CAUSAL_EXECUTION_LAB005_PREREG

Status: PREREGISTERED_CAUSAL_EXECUTION_AUDIT_NOT_OOS

Purpose: convert the LAB004B reverse-discovery precursor `repeated_failed_attack` into a fully causal GC->XAU signal and measure whether XAU CFD execution has enough time before a large move.

## Causal signal
- GC is divided into non-overlapping 30-second windows.
- For each candidate clock t0, attack #1 = [t0-60s,t0-30s), attack #2 = [t0-30s,t0).
- Each attack uses explicit AMP/CQG directional trades only.
- crowd_dir = sign(delta) in each 30s attack.
- crowd impact = crowd_dir * (last-first) / prior completed GC M1 ATR14.
- signal if attack #1 and #2 have the same nonzero crowd_dir AND attack #2 crowd impact <= attack #1 crowd impact.
- predicted XAU direction = opposite crowd_dir.
- No future XAU direction, future GC data, large-move label, session filter, volume threshold, delta threshold, or hindsight selector enters the signal.
- Signal clocks are every 30 seconds. After an accepted signal, impose a frozen 60-second cooldown.

## Causal XAU context
- Primary subset: QUIET_START = absolute XAU mid-price move during prior 30s <=0.25 prior-completed XAU M1 ATR.
- Also report ALL signals. QUIET_START is frozen from LAB004B and is causal at t0.
- FTMO broker clock = GC UTC +180 minutes.

## Frozen execution variants
1. MARKET_NOW: first executable quote at t0.
2. LIMIT_005_15S: predicted LONG -> buy limit at initial Ask -0.05 ATR; predicted SHORT -> sell limit at initial Bid +0.05 ATR; expiry 15s; no chase.
3. LIMIT_005_30S: same depth, expiry 30s.
4. LIMIT_010_15S: depth 0.10 ATR, expiry 15s.
5. LIMIT_010_30S: depth 0.10 ATR, expiry 30s.

LONG entry uses Ask / SHORT entry uses Bid. Exits use executable Bid/Ask. Quoted spread is embedded.

## Timing diagnostics from t0
- first passage in predicted direction to +0.25,+0.50,+1.00,+2.00,+3.00 XAU ATR
- first passage adverse to -0.25,-0.50,-1.00 ATR
- time to first +0.25,+0.50,+1.00 ATR
- MFE/MAE through 5 minutes
- probability of reaching +2 ATR and +3 ATR within 5 minutes
- missed-winner rate for each limit variant: signal reaches +2 ATR within 5m but limit never fills

## Frozen R:R execution geometries
- G15: SL 0.50 ATR / TP 0.75 ATR = 1:1.5
- G20: SL 0.50 ATR / TP 1.00 ATR = 1:2
- hard timeout at t0+5m
- no trailing, BE, dynamic exit, or geometry sweep.

## Discovery split
- TRAIN: before 2026-08-20 00:00 UTC
- VALID: 2026-08-20 00:00 UTC through 2026-09-06 22:00 UTC
- POST_CHECK: after VALID; descriptive only.

## Execution viability questions
- Is median time to +0.50 ATR >=20s on winning +2 ATR signals?
- Do 0.05/0.10 ATR limits fill often enough without missing most +2 ATR winners?
- Does any frozen execution variant have positive fixed 5m EV in TRAIN and VALID?
- Does any frozen R:R geometry achieve PF>=1.10 and EV>0 in VALID with at least 30 fills?

No production promotion from LAB005 alone. Historical causal execution audit only; not independent OOS certification.
