# LAB161 — PRICE → CROWD → OI → PROFILE
Frozen before fitting and inspecting results, 2026-10-10. Parent LAB160d dbc99709494b47d38464d7e450fffd880a0debb6.

Scope BTCUSDT Jan2021–available OHLCV/flow intersection. Same regular M5 complete-case rows for all models; no old setup gates. Price means OHLCV, including past volume, so adding profile tests volume location beyond aggregate volume. Close observations only; reference ATR last closed H1 SMA14 true range. Flow timestamp shifted +5min as inherited assumed publication delay, no forward fill over missing flow. Profile trailing24h,40 bins, uniform high-low volume reconstruction, inherited LAB160 function.

Models: fixed HistGradientBoostingClassifier multiclass NONE/UP/DOWN, max_iter120, max_leaf_nodes15, learning_rate.05,min_samples_leaf300,l2_regularization10,early_stoppingFalse,random_state161. No hyperparameter/model-family search. Nested feature groups PRICE, PRICE_CROWD, PRICE_CROWD_OI, PRICE_CROWD_OI_PROFILE. Training fixed UTC quarter-hour observations (reduce duplication); score every eligible M5 row. Missing feature rows excluded identically. No time/year or future pivot features.

Label: within next24h, future CLOSE reaches +3 referenceATR before -1.5ATR = UP, mirror = DOWN, otherwise NONE. Entire future24h must have valid closes; right-censored observations excluded. Mutually exclusive up/down labels. This is signal quality, not SL/TP replay. Also record unconstrained directional max close excursion, adverse excursion, terminal24h, and +3ATR reached regardless of adverse path.

Expanding chronological folds:
- test2024: train2021–2022, calibration2023;
- test2025: train2021–2023, calibration2024;
- test2026 available: train2021–2024, calibration2025.
Purge24h at training and calibration ends. All periods previously used for related exploration: temporal held-out predictions, NOT pristine project OOS. 2026 partial year identified.

Signal score=max(P(UP),P(DOWN)); side=argmax. Global6h cooldown across both sides, independent of outcomes, max theoretical4/day. Threshold calibrated using ONLY calibration score distribution, to approach .5/1/2 signals per calendar day; choose closest rate from fixed quantile grid, conservative higher threshold on ties. Freeze threshold for following test. Report achieved rates (no claim equal actual test rates). Primary comparison1/day; .5 and2 sensitivity, no choosing best rate after results. Probability quality additionally measured on all shared M5 test rows and fixed24h anchors, with paired weekly bootstrap of incremental Brier error.

Independent waves: exact LAB160d close-pivot legs>=3 startingATR, reversal1ATR; fixed2ATR sensitivity. Wave starts, peaks and confirmation must lie within fold test and eligible label interval. Report whole price-wave denominator and observable-wave denominator (>=1 shared eligible M5 decision inside leg before peak). A recognized wave has a same-side signal at/after start and strictly before peak, with >=1 signal-timeATR remaining to peak. Also2/3ATR thresholds. One wave counted once, first qualifying signal determines remaining move and delay. No signals before retrospective start included in primary matching. This differs from LAB160d actual carried-position coverage; report legacy raw signals under identical new matching on2024 separately.

False signal (primary): predicted direction does not satisfy3-before-1.5 in24h. Separate never-reaches3, reaches3 only after adverse barrier, clean3-before1.5. Remaining-to-peak is retrospective descriptive potential, NOT earned R. Coverage/counts and predictive precision must be read together.

Benchmarks: training class frequencies Brier; legacy raw OLD_PROFILE2024 matched with same wave metric; deterministic daily/12h/48h UTC signals with trailing6h price direction, same shared eligibility, for rough schedule reference. No live bot changes. Export row-level emitted signals, wave matching, summaries/year, model errors, paired weekly uncertainty, data audit and frozen features/models. Reproducible source hashes and software versions. Check causal prefix invariance, label fixtures, purge, nested features and matching consistency.

Matching clarification fixed before inspecting model results: wave peak must occur no later than24h after matched signal, consistent with forecast horizon; candidates earlier than peak-24h cannot recognize that peak. Observable wave denominator requires at least one common eligible timestamp in [max(start,peak-24h),peak). Last24h of each test fold also excluded so outcome labels remain within that fold. No probability recalibration, threshold is a frequency selector rather than a calibrated confidence claim.
