# LAB025 post-hoc diagnostic — does not change frozen verdict

Frozen verdict: `PROBATION_SELECTS_HEALTH_BUT_EXECUTION_NOT_POSITIVE`.

## What transferred from LAB023
The exact same-side 0.10 ATR / 5m event parity is reproduced: 1,839 event and 515 no-event Confirmation setups. No-event baseline cohort remains strongly positive (+0.580R, TP 63.3%); event cohort remains strongly negative (-0.383R, TP 24.9%).

## Probation selects health
Primary promotion cohort (also requiring acceptance intact) has baseline EV +0.280R and TP 50.8%, versus non-promoted baseline EV -0.260R. Therefore the probation state is genuine information.

## Why promotion fails
Among 382 promoted Confirmation setups:
- median promotion price deterioration: 0.249 ATR in the bias direction;
- median added-tranche RR to the frozen TP/SL: 0.669;
- only 7.1% of added tranches still have RR >= 1.5;
- only 26.2% have RR >= 1.0;
- promoted cohort baseline EV is +0.280R, but actual staged EV after adding late is -0.064R.

The information is correct, but the 75% add is paid for after too much of the move has already been spent.

## Risk reduction is real, edge creation is not
Primary staged strategy improves full-immediate serial EV from -0.181R to -0.072R and max DD from ~375R to ~165R. Paired weekly lift is +0.104R with positive CI. But mean risk budget used is only 0.373R and risk-efficiency remains negative (-0.192R per risk-budget-R). Therefore the improvement is largely risk throttling, not positive edge.

## Direct full-size same-side event kill also fails (post-hoc)
To separate the signal from promotion mechanics, a diagnostic kept 100% risk at the early entry and used the same-side event only to exit next-open, with no late add. At 5m its Confirmation EV is -0.194R versus baseline -0.181R. Thus simply killing the event cohort next-open is also insufficient.

## Interpretation
We have a strong classification of path health, but neither of the obvious monetization actions is good enough:
1. wait 5m then add at market -> too late / RR collapse;
2. full-size early then kill event next-open -> event recognition is too late/expensive to rescue enough of the bad cohort.

The remaining structural question is whether, after passing probation, additional exposure can be acquired without chasing — e.g. a post-confirmation add-limit constrained by a minimum executable RR, while retaining the starter if no add fill occurs. This must be a new preregistered LAB; it is not a LAB025 rescue.
