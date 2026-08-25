# STRUCT_BREAK_LOW_EXIT_REARM_REENTRY_LAB_009B — preregistration

## Objective
Test whether a 30m LOW state can be handled by scratch/cheap exit and causal re-entry on a renewed impulse, recovering lost right-tail winners without re-admitting too many future losers.

## Frozen parent components
- Canonical STRUCT_BREAK v002 population and execution geometry.
- DEV = 2019–2022; VAL = 2023–2025; 2026 excluded from formal verdict.
- LOW30 classifier exactly as LAB008: logistic C=0.3, DEV-trained, bottom DEV score tertile.
- Scratch policy: after LOW30, exit first position at first recovery to original entry level (0R gross; -0.06R net). If no recovery before canonical exit, keep canonical outcome.
- One re-entry maximum per original setup.

## Re-arm and impulse trigger
After scratch, original structural setup remains armed for 12 hours.

A fresh 30-minute response window is evaluated every 5 minutes using the same LAB008 30m response feature definitions, now anchored at the scratch/original level and using the original structural R geometry.

The renewed-impulse score uses the same DEV-trained LAB008 30m classifier. HIGH = score above the frozen DEV q67 threshold. No re-entry outcome is used to train or tune this score.

Re-entry occurs at the next M5 bar open after the first fully closed 30m window classified HIGH, subject to:
- original structural stop still intact;
- original structural 2.3R target not already hit;
- prospective reward/risk to original target/stop >= 1.5;
- no more than one re-entry.

## Re-entry management
- stop: original structural stop;
- target: original structural 2.3R target;
- BE: after price reaches original +1R level, stop becomes re-entry price for the second leg;
- second-leg round-turn cost = 0.06R measured in original structural R units;
- first scratch leg cost = 0.06R;
- setup timeout for re-arm = 12h; once re-entered, manage until stop/BE/target or dataset end.

## Primary comparisons
1. Canonical HOLD.
2. LOW30 immediate exit.
3. LOW30 scratch at 0R, no re-entry.
4. LOW30 scratch + re-arm + renewed-HIGH re-entry.

## Primary gates
On frozen VAL 2023–2025, the re-entry policy must:
- improve portfolio EV versus canonical HOLD;
- improve EV versus scratch-only;
- have positive improvement in at least 2/3 VAL years;
- not increase max drawdown by >10% versus canonical;
- re-entry subgroup N >= 30;
- recover at least 25% of the full-TP trades that scratch-only would have cut, while re-entering fewer than 60% of recovered canonical losers.

No threshold search on VAL. Sensitivities (4h/24h re-arm horizon or alternate RR execution) are diagnostic only and cannot promote the policy.
