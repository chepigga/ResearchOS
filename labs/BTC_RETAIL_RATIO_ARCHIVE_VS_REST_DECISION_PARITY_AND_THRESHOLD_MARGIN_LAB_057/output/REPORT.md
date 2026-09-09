# BTC_RETAIL_RATIO_ARCHIVE_VS_REST_DECISION_PARITY_AND_THRESHOLD_MARGIN_LAB_057

**Verdict: FAIL_REST_DECISION_PARITY — 7/8 gates**

## Frozen comparison
Archive `count_long_short_ratio` vs REST `globalLongShortAccountRatio`, fixed REST timestamp shift **-5m**, same strictly-prior archive q20/q80 threshold at each M15 timestamp.

## Decision parity
- Comparable M15 rows: **155** (2026-09-07 09:15:00+00:00 → 2026-09-08 23:45:00+00:00)
- All-class BUY/SHORT/NEUTRAL parity: **100.0000%**
- SHORT binary parity: **100.0000%**
- BUY binary parity: **100.0000%**
- SHORT archive rows: **39**; REST SHORT rows: **39**
- SHORT false positives: **0 (0.0000%)**
- SHORT false negatives: **0 (0.0000%)**
- All decision flips: **0**; SHORT-specific flips: **0**

## Frozen 12h FLOW event parity
- Event evaluation starts after 24h preroll: **2026-09-08 09:15:00+00:00**
- All-side event union match: **100.0000%** (archive 1, REST 1, union 1)
- SHORT event union match: **100.0000%** (archive 0, REST 0, union 0)

## Transport error / threshold margin
- Raw 5m overlap N: **500**; max |ratio diff|: **0.00028507**
- M15 median |delta diff|: **0.00014160**; p99: **0.00041611**; max: **0.00168086**
- Median normalized delta error / (q80-q20): **0.001937**; p99: **0.005710**
- Median nearest-threshold / transport-error ratio: **134.77x**

## Gates
- FAIL — `comparable_m15_n_ge1500`
- PASS — `all_class_pointwise_parity_ge99pct`
- PASS — `short_binary_parity_ge99_5pct`
- PASS — `short_false_positive_rate_le0_5pct`
- PASS — `short_false_negative_rate_le0_5pct`
- PASS — `all_side_flow_event_union_match_ge95pct`
- PASS — `short_flow_event_union_match_ge95pct`
- PASS — `no_tuning`

## Guardrail
This LAB contains no PnL and no outcome-conditioned tuning. PASS would authorize REST only as a separately controlled shadow-monitor transport; archive daily metrics remain canonical fresh evidence until separately changed by preregistration.
