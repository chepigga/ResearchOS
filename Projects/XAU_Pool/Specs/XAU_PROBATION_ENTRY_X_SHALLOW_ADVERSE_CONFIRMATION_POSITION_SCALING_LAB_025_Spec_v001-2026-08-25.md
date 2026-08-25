# XAU_PROBATION_ENTRY_X_SHALLOW_ADVERSE_CONFIRMATION_POSITION_SCALING_LAB_025 — Spec v001

Date: 2026-08-25
Status: PRE-OUTCOME PREREGISTRATION
Holdout: >= 2025-07-01 SEALED

## Purpose
Test whether the strongest causal information from LAB023 can be monetized as staged risk allocation rather than as an entry filter or a full-size kill rule.

Frozen thesis:
- LAB009 strong accepted-side bias provides direction/context.
- Frozen LAB012 digestion next-open remains the earliest executable market entry.
- LAB023 showed a strong 5-minute same-side shallow adverse-event split at 0.10 ATR.
- Do not wait for full reacceleration before entry.
- Buy information with a small starter, then promote risk only if the early path remains healthy.

## Frozen universe / lineage
Rebuild exact LAB012 universe with exact parent runner hash:
`09931377bb6258051e6de76b8bd3b56f92bf3cd06ea8ff2ec54751c72aea993a`

Canonical XAU M1 SHA-256:
`db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b`

Primary universe:
- strong_accept == true
- digestion_found == true
- baseline_entry_i >= 0
- no causality violation
- break_time < 2025-07-01
- exact LAB012 serial dedupe rules for portfolio statistics

Splits:
- Discovery: < 2024-01-01
- Confirmation: 2024-01-01 through 2025-06-30
- Holdout >= 2025-07-01 remains sealed

## Frozen baseline trade
Entry: LAB012 digestion next M1 open.
Direction: frozen dir.
Original risk distance: 0.50 ATR from starter entry.
Absolute SL and TP coordinates are frozen from the original early-entry trade:
- SL = starter_entry - dir * 0.50 ATR
- TP1.5 = starter_entry + dir * 0.75 ATR
- TP2.0 = starter_entry + dir * 1.00 ATR
Maximum holding horizon: frozen LAB012 60 minutes.
Bid/Ask execution and $0.05 price-equivalent commission lineage preserved.

## Primary staged-risk strategy: PROBATION_25_TO_100
### Starter
At frozen early market entry open:
- allocate 0.25R risk budget.
- starter lot factor = 0.25 of frozen full-risk baseline lot.

### Probation window
Observe exactly the first 5 completed M1 bars beginning with baseline_entry_i.

Frozen same-side shallow adverse event at depth 0.10 ATR:
- BUY signal: AskLow <= starter_entry - 0.10 * ATR0
- SELL signal: BidHigh >= starter_entry + 0.10 * ATR0

Frozen acceptance degradation during probation:
- signed close relative to the broken old level <= +0.05 ATR.

No future information beyond each completed M1 bar may be used.

### If adverse/degradation occurs during probation
- Do NOT add risk.
- Close the 0.25R starter at the next contiguous executable M1 open:
  - BUY exits at BidOpen
  - SELL exits at AskOpen
- If frozen absolute SL is reached before that next-open execution, SL has priority.
- If frozen TP and an adverse/degradation signal are both observable in the same M1 bar, adverse/degradation is conservatively treated as first; exit is next-open unless SL occurs first.

### If probation passes
Pass requires:
- no 0.10 ATR same-side adverse event during all 5 probation bars;
- no acceptance degradation during all 5 bars;
- starter position still alive after bar 5.

Promotion occurs at the next contiguous M1 open after probation bar 5.
The remaining tranche receives exactly 0.75R risk budget to the SAME absolute frozen SL.
Therefore its lot factor relative to the original full-risk lot is:
`0.75 * original_risk_distance / distance(promotion_entry, frozen_SL)`.
No hindsight price improvement is allowed.

After promotion:
- starter + promoted tranche share the same frozen absolute SL and TP coordinate;
- each tranche is marked independently from its own fill;
- total worst-case SL risk after promotion is approximately 1.0R before commissions.

If TP/SL is reached before promotion, only the starter participates and no promotion occurs.

## Controls
1. FULL_IMMEDIATE: frozen full-size LAB012 baseline.
2. STARTER_ONLY_25: 0.25R starter at early entry held to frozen TP/SL/time; no promotion.
3. PROBATION_25_TO_100: primary staged strategy.

## Secondary sensitivity — diagnostic only
Starter fractions: 0.10, 0.25, 0.50 with complementary promotion risk to total 1R.
Probation lengths: 3m, 5m, 10m.
Adverse depth remains 0.10 ATR for primary family.
No winner-selection from sensitivity is allowed.

## Accounting
All P&L is reported in units of the original full-risk 1R budget.
Commission scales linearly with relative lot factor.
For staged strategy also report:
- promotion_rate
- adverse_exit_rate
- mean_risk_budget_used (0.25 if never promoted; 1.0 after promotion)
- total_R / sum(risk_budget_used) = risk-efficiency
- promoted/non-promoted frozen-baseline cohort EV and TP rate
- actual promoted-trade staged EV

Serial portfolio occupancy uses earliest entry through final exit exactly as the staged strategy actually executes.

## Primary frozen gates
G0 DATA/CAUSALITY: PASS only with exact hashes, no holdout read, no future-clock violations.
G1 POWER: Confirmation primary serial N >= 300 and >= 3 trades/week.
G2 POSITIVE ECONOMICS: Confirmation serial EV > 0 and PF > 1.0.
G3 WEEKLY ROBUSTNESS: week-clustered 95% CI of staged EV mean has lower bound > 0.
G4 RISK EFFICIENCY: Confirmation total_R / sum(risk_budget_used) > 0.
G5 PROMOTION SELECTIVITY: promoted cohort frozen baseline EV > non-promoted cohort frozen baseline EV and > 0.
G6 PROMOTED EXECUTION: actual promoted staged-trade EV > 0.
G7 DISCOVERY TRANSFER: Discovery staged independent EV > 0 and same sign as Confirmation.
G8 DIRECTION BREADTH: BUY EV > 0 and SELL EV > 0 on Confirmation.
G9 2R SURVIVAL: same architecture with frozen TP2.0 has EV > 0.
G10 COST STRESS: +$0.10 equivalent stress EV > 0.
G11 PROP DD PROXY: worst day > -4R, max DD materially below baseline and no pathological loss clustering.
G12 BEATS FULL IMMEDIATE: paired weekly staged-minus-full baseline CI lower bound > 0 OR staged absolute EV positive with materially lower drawdown and positive risk-efficiency.

Promotion is NOT authorized if only total drawdown improves because less risk was used while risk-efficiency remains negative.

No threshold rescue, no post-result starter fraction selection, no holdout opening, no EA/live authorization in LAB025.
