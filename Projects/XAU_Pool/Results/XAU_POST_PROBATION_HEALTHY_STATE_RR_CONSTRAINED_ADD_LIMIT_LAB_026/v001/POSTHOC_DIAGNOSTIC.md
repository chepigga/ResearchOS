# LAB026 post-hoc diagnostic — does not change frozen verdict

Frozen verdict remains `HEALTH_SIGNAL_PERSISTS_RR_LIMIT_NOT_ENOUGH`.

## Main mechanism
The 5m healthy probation selector remains valid, but a later pullback to an R:R-constrained add-limit is itself adverse selection.

On the independent Confirmation healthy cohort (N=382):
- ADD_FILLED N=191: frozen baseline EV 1.5R = -0.249R; LAB026 combined EV = -0.242R.
- ADD_UNFILLED N=191: frozen baseline EV 1.5R = +0.808R; LAB026 starter-only EV = +0.202R.

Thus the market does not reward buying the healthy cohort on a later retracement. The retracement changes the state.

## 2R persistence
The no-add/no-return cohort remains strong at a wider target:
- ADD_UNFILLED baseline 2R EV = +0.824R; TP2 = 57.1%.
- ADD_FILLED baseline 2R EV = -0.181R; TP2 = 25.7%.

This supports a continuation-without-return interpretation rather than a narrow 1.5R artifact.

## Add quality
All filled adds satisfy the frozen R:R requirement:
- median add R:R = 1.50
- mean add R:R = 1.528
- 100% have R:R >=1.5

Yet incremental add economics are negative (-0.179R vs a starter-only counterfactual on the same filled cohort). Therefore the failure is not because the add price violates the requested R:R; the fill event itself identifies a degrading path.

## Sensitivity
All preregistered secondary combinations remain negative:
- R:R 1.25 / 1.5 / 2.0
- expiry 3 / 5 / 10 minutes
- Confirmation EV range about -0.058R to -0.068R.
Longer expiry generally increases fill rate and worsens drawdown/EV, consistent with accumulating adverse selection.

## Research implication
Do not treat pullback after healthy probation as an opportunity to increase size. The strongest causal lineage is now:
1. strong ordered acceptance bias;
2. survive first 5m without shallow same-side adverse event;
3. continue without a second pullback toward the R:R add boundary.

The unresolved monetization question is how to earn enough from this fast no-return path without chasing it. A cleaner next test is not another add-limit; it is to keep the small early starter and change only winner monetization after the second no-return confirmation (e.g. wider target / trailing only on this cohort), while never adding risk at a worse price.
