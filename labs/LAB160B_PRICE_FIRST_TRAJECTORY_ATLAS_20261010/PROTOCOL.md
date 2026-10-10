# LAB160b — PRICE FIRST TRAJECTORY × CROWD × OI × PROFILE STATE ATLAS
Frozen 2026-10-10 before LAB160b trajectory-class calculations. Reuses the same previously researched history; never called pristine out-of-sample.

## Question and scope
What price paths occur at EVERY closed M5, on EACH of 1/3/6/12/24/48 hours? What observable states precede their different forms? No entries, no stop/target race, no fixed tradability filter, no gate relaxation as primary objective.
Reference is current closed M5 close and last fully closed H1 SMA14 true-range ATR (LAB158 lineage). Future starts on the next M5. Keep ALL eligible price rows, including missing flow/profile. Conditional overlay has its own explicit coverage denominator. Time assumed UTC bar-open in source. Flow assumed available timestamp+5m; no backward filling.

## Continuous future path descriptors
Signed close change; up/down excursion; time of extremes; worst opposite excursion before each directional extreme (lower/upper bounds excluding/including extreme candle); adverse-first recovery time; terminal retention of dominant excursion; normalized close path at 16 equal horizon fractions; close-path efficiency; max close-to-close drawdown/runup; total high-low span. Record largest close-path drawdown as a path descriptor, not a trading stop. Ambiguous within-candle ordering is explicit. Keep signed displacement and magnitude separate from shape.

## Fixed descriptive taxonomy, no profit optimization
Let U/D be maximum up/down excursions from reference, M=max(U,D), E=terminal signed move in reference ATR.
1. QUIET: M<0.5.
2. SMALL: 0.5<=M<1.
3. TWO_SIDED: U>=1 and D>=1 and abs(E)<0.5*M.
4. ROUND_TRIP_UP/DOWN: remaining M>=1 and terminal does not retain >=50% of the dominant excursion in its direction.
5. For remaining retained directional paths: UP/DOWN determined by dominant excursion. AFTER_PULLBACK if opposite excursion strictly before dominant extreme >=0.5 ATR; DIRECT if even including extreme candle it is <0.5; ORDER_UNCERTAIN if this classification depends on unknown intrabar order.
Dominant-extreme ties assigned by terminal sign; exact zero uses UP deterministically and marked tie.
Example -1.2 ATR followed by +5 ATR and end +4 => AFTER_PULLBACK_UP, regardless of any hypothetical stop.
Continuation/reversal is a SEPARATE relation to already-known past6h direction (>0.5/<-0.5 ATR); never used to select observations. No future class used as a predictor.
Magnitude buckets [0,.5,1,2,3,5,infinity], reported separately. Sensitivity retains shape definitions but also publishes continuous quantities, so labels do not hide alternate paths.

## State overlay
Reuse causal LAB160 state rows, including full continuous Z, Z slope, OI quantity/value, POC/VAH/VAL, density and POC migration. Add closed price1h/24h return and trailing24h price location for context. Primary joint cells = past6h trend × signed crowd (Z<=-1, abs(Z)<1, Z>=1) × OI quantity4h (falling<-0.35%, stable +/-0.35%, rising>0.35%) × profile shape × value location.
Also publish marginal signed-Z finer bins, OI value, migration direction, density, price regime and amplitude-class relations. These are descriptive associations.
For each horizon/class/cell report raw N, event counts, probability, same-period unconditional and trend-parent lifts, and incremental lift against same trend/crowd/OI parent without profile. Report discovery2021–23, validation2024, retrospective check2025–26 separately. Purge48h before boundaries.
Sparse cells are retained in full tables and identified. Candidate shortlist per horizon and path class: discovery N>=500 and validation N>=150, at least10 distinct weeks each, event counts>=50 and >=20, unconditional and trend-parent lift positive on discovery and validation, unconditional lift>=3pp both. Rank by min(discovery trend-parent lift,validation trend-parent lift); top3 per class/horizon frozen BEFORE checking later period. Does not require profile lift. No claim of adjusted significance for mined cells.

## Dependence and validation
Raw M5 counts are not trades. Publish fixed non-overlapping anchors every horizon from UTC epoch (unbiased clock sampling), plus greedy same-class retrospective nonoverlap episode examples. Episodes selected using future class are illustrative labels, never causal triggers.
Candidate state counts and event rates on fixed anchors, and week-block bootstrap intervals where support permits, expose overlap. Require >=30 check anchors and >=10 check weeks for a supported descriptive candidate; sparse candidates not confirmed.
Median paths and exemplars selected mechanically (closest to median 16-point normalized path among nonoverlap check rows), not best P/L. Validate prefix-invariance of features and synthetic path classification, including delayed -1.2→+5 trajectory, round-trip and ambiguous extreme candle.

## Legacy coverage
Recover original A/B3_HIGH/R48_HIGH/EARLY_EPISODE timestamps if executable. Legacy scripts are TRAIN-only through2024, use their own original timestamp/missing-data rules; do not infer no signals in2025–26. Report exact same-direction entry-time overlap and whether a raw signal falls before the observed directional peak inside disjoint retrospective episodes. This is historical opportunity overlap, NOT captures of profits. If recovery fails, state explicitly that exact bot coverage remains unavailable; no threshold-only proxy called the bot.

## Outputs and boundaries
All-row six-horizon parquet atlas; price-class/magnitude/time/anatomy tables; state-conditioned tables and temporal shortlist; examples and plots; recovery notes; reproducible scripts and hashes. LAB161 handles predictive direction modeling; LAB162 entries; LAB163 costs/risk/portfolio. No P/L or live changes here.
