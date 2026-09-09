# BTC_RETAIL_RATIO_ARCHIVE_VS_REST_DECISION_PARITY_AND_THRESHOLD_MARGIN_LAB_057

**Verdict: FAIL_REST_DECISION_PARITY — 6/8 gates**

## Frozen comparison
Archive `count_long_short_ratio` vs REST `globalLongShortAccountRatio`, fixed REST timestamp shift **-5m**, same strictly-prior archive q20/q80 threshold at each M15 timestamp.

## Decision parity
- Comparable M15 rows: **2869** (2026-08-10 02:45:00+00:00 → 2026-09-08 23:45:00+00:00)
- All-class BUY/SHORT/NEUTRAL parity: **99.7909%**
- SHORT binary parity: **99.8954%**
- BUY binary parity: **99.8954%**
- SHORT archive rows: **432**; REST SHORT rows: **433**
- SHORT false positives: **2 (0.0821%)**
- SHORT false negatives: **1 (0.2315%)**
- All decision flips: **6**; SHORT-specific flips: **3**

## Frozen 12h FLOW event parity
- Event evaluation starts after 24h preroll: **2026-08-11 02:45:00+00:00**
- All-side event union match: **85.3659%** (archive 38, REST 38, union 41)
- SHORT event union match: **94.7368%** (archive 18, REST 19, union 19)

## Transport error / threshold margin
- Raw 5m overlap N: **8637**; max |ratio diff|: **0.00052469**
- M15 median |delta diff|: **0.00015328**; p99: **0.00067808**; max: **0.01241246**
- Median normalized delta error / (q80-q20): **0.001870**; p99: **0.007975**
- Median nearest-threshold / transport-error ratio: **170.83x**

## Gates
- PASS — `comparable_m15_n_ge1500`
- PASS — `all_class_pointwise_parity_ge99pct`
- PASS — `short_binary_parity_ge99_5pct`
- PASS — `short_false_positive_rate_le0_5pct`
- PASS — `short_false_negative_rate_le0_5pct`
- FAIL — `all_side_flow_event_union_match_ge95pct`
- FAIL — `short_flow_event_union_match_ge95pct`
- PASS — `no_tuning`

## Guardrail
This LAB contains no PnL and no outcome-conditioned tuning. PASS would authorize REST only as a separately controlled shadow-monitor transport; archive daily metrics remain canonical fresh evidence until separately changed by preregistration.
