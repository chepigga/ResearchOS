# XAU_POST_PROBATION_HEALTHY_STATE_RR_CONSTRAINED_ADD_LIMIT_LAB_026 — Spec v001

Date: 2026-08-25
Status: PRE-OUTCOME FREEZE

## Question
LAB025 showed that the 5m probation/no-adverse cohort is selectively healthy, but adding the remaining risk at market after probation destroys R:R. Test whether the same frozen healthy cohort can be monetized by placing a post-probation add-limit only at a price where the add tranche still has at least 1.5:1 reward:risk to the frozen TP/SL.

## Frozen lineage
- Same canonical XAU M1 dataset and LAB012/LAB025 early-entry universe.
- Same strong-bias / digestion definitions.
- Same early starter entry, frozen absolute SL and TP coordinates.
- Same LAB025 probation health logic: starter fraction 25%; 5 completed M1 bars; same-side 0.10 ATR adverse event or old-level degradation => starter exits at next M1 open; otherwise healthy.
- Holdout >= 2025-07-01 remains sealed.

## Primary architecture
1. Enter 25% risk starter at frozen early market entry.
2. Observe exactly 5 completed M1 probation bars.
3. If adverse event or degradation occurs, exit starter exactly as LAB025.
4. If probation is healthy, do NOT add at market.
5. Compute the add-entry boundary where a new tranche, using the SAME frozen absolute SL and TP, has exactly R:R = 1.5.
   In directional coordinates y = dir * price:
     y_limit = (y_TP + 1.5 * y_SL) / 2.5
   BUY limit price = +y_limit; SELL limit price = -y_limit.
6. Place a 75%-risk add-limit at that boundary for 5 completed M1 bars starting with the first bar after probation.
7. BUY add fills only if AskLow <= add_limit. SELL add fills only if BidHigh >= add_limit.
8. If not filled within 5 bars, cancel add; keep starter only.
9. If add fills, size add tranche so loss from add entry to frozen SL equals exactly 0.75R. Combined maximum planned risk after fill = 1.00R.
10. On the add-fill bar, SL has conservative precedence. TP for the add tranche is not credited on the fill bar; TP becomes eligible from the next M1 bar. Starter remains subject to its existing TP/SL throughout.
11. Frozen terminal horizon remains 60m from starter entry.

## Costs
Same LAB025 cost convention: commission-price 0.05 scaled by effective exposure; stress adds $0.10-equivalent price cost per exposure unit.

## Primary comparison
- FULL_IMMEDIATE baseline.
- STARTER_ONLY_25.
- LAB025 MARKET_PROMOTE_25_TO_100.
- LAB026 RR15_ADD_LIMIT_25_TO_100.

## Primary success gates
G0 causality/parity PASS.
G1 >=300 serial trades and >=3/week.
G2 LAB026 Confirmation EV > 0 and PF > 1.
G3 weekly EV 95% CI lower bound > 0.
G4 risk-efficiency > 0.
G5 healthy-cohort selectivity remains positive.
G6 filled add tranche economics > 0 and combined promoted cohort EV > 0.
G7 LAB026 materially beats LAB025 market-promotion with paired weekly CI lower bound > 0.
G8 Discovery and Confirmation EV both > 0.
G9 BUY and SELL both > 0.
G10 2R diagnostic > 0.
G11 stress EV > 0.
G12 prop DD proxy passes (worst day > -4R and DD < full-immediate baseline).

## Secondary diagnostics (cannot rescue primary)
- add-limit fill rate and expiry rate.
- realized add-entry R:R distribution.
- fill latency.
- filled vs unfilled healthy-cohort baseline/staged EV.
- sensitivity only: expiry 3m / 10m and min R:R 1.25 / 2.0. No winner selection from these.

No holdout opening, no EA/live authorization from LAB026 alone.
