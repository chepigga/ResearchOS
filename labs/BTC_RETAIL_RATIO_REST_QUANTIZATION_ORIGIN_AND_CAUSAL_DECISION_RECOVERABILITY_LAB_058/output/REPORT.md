# BTC_RETAIL_RATIO_REST_QUANTIZATION_ORIGIN_AND_CAUSAL_DECISION_RECOVERABILITY_LAB_058

**Quantization origin: PURE_QUANTIZATION_REJECTED**
**Pointwise recoverability: FAIL_CAUSAL_DECISION_RECOVERABILITY**
**All-side clock: CLOCK_PARITY_FAIL**
**SHORT clock: SHORT_CLOCK_PARITY_FAIL**

## Pure quantization origin
- best deterministic transform: **ceil4**
- best exact share: **21.477%**

## Causal calibration
- calibration raw N: **4318**
- evaluation raw N: **4319**
- frozen residual envelope: **[-0.00062469, +0.00060694]**
- evaluation envelope coverage: **100.000%**

## Pointwise causal recovery
- evaluation M15 N: **1440**
- transport fresh: **99.931%**
- certainty coverage: **98.194%**
- accuracy among CERTAIN: **100.000%**
- false-certain decisions: **0**
- SHORT precision: **100.000%**
- SHORT recall: **96.296%**
- BUY precision: **100.000%**
- BUY recall: **94.382%**

## Threshold-margin concentration
- UNCERTAIN median distance to nearest threshold: **0.00054512**
- CERTAIN median distance to nearest threshold: **0.02743465**

## Stateful 12h clock diagnostic
- all-side union match: **61.111%** (11/18)
- SHORT union match: **70.000%** (7/10)

## Decision
LAB058 is transport-only. Frozen SHORT v1 is unchanged. No PnL was used and live/prop allocation remains 0.
