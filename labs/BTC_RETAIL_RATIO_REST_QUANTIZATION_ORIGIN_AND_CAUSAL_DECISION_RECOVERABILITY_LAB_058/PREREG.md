# BTC_RETAIL_RATIO_REST_QUANTIZATION_ORIGIN_AND_CAUSAL_DECISION_RECOVERABILITY_LAB_058

## Purpose
Determine whether Binance REST `globalLongShortAccountRatio` is merely a quantized representation of the archive `count_long_short_ratio`, and whether a live causal interval around the REST value can recover the frozen archive decision `BUY / SHORT / NEUTRAL` without false certainty.

This is a transport-layer audit only. Frozen SHORT v1 alpha, thresholds, cooldown, HIGH_RESPONSE, ACCEPT, SL/TP, management, costs, and sizing are untouched.

## Inputs — frozen from LAB057
- Fixed REST alignment: **REST timestamp -5 minutes**.
- Canonical thresholds: LAB057 strictly-prior archive q20/q80.
- Canonical decision: archive `delta_ls_12` vs the same q20/q80.
- Overlap: LAB057 archive-vs-REST 30d dataset.

## A. Pure quantization-origin hypotheses
Test deterministic transforms of the archive value against observed REST value:
1. round-to-nearest 4 decimals;
2. floor/truncate to 4 decimals (ratios are positive, so floor=truncate);
3. ceil to 4 decimals.

No transform is selected using trading outcomes.

`PURE_QUANTIZATION_CONFIRMED` only if one transform reproduces observed REST on >=99.0% of raw overlap rows exactly to 4-decimal lattice precision.
Otherwise: `PURE_QUANTIZATION_REJECTED`.

## B. Causal residual-envelope construction
Pure quantization may be insufficient because the archive and REST snapshots can differ slightly even after the fixed -5m alignment.

To avoid using future information:
- split the raw overlap chronologically 50/50;
- first half = CALIBRATION;
- second half = EVALUATION;
- define residual `e = archive_ratio - REST_ratio` on calibration only;
- live ratio interval is frozen before evaluation as:
  - `e_lo = min(calibration residual) - 0.0001`
  - `e_hi = max(calibration residual) + 0.0001`
- 0.0001 is one REST 4-decimal quantum and is fixed before evaluation.

For each REST ratio `r`:
`true_ratio ∈ [r + e_lo, r + e_hi]`.

For `delta_ls_12 = ratio_t - ratio_{t-12}`:
- `delta_lo = ratio_lo_t - ratio_hi_{t-12}`
- `delta_hi = ratio_hi_t - ratio_lo_{t-12}`.

## C. Transport freshness gate
A live M15 decision is eligible for certainty only if the aligned REST stream contains the expected final 5m sample for BOTH:
- current M15 bin (`time + 10m`), and
- lag-12 M15 bin (`time - 180m + 10m`).

If either expected 5m sample is missing, classify `UNCERTAIN`.
This is a data-integrity rule, not a trading filter.

## D. Causal interval decision
Using frozen archive q20/q80:
- `CERTAIN_SHORT` iff `delta_lo >= q80`;
- `CERTAIN_BUY` iff `delta_hi <= q20`;
- `CERTAIN_NEUTRAL` iff `delta_lo > q20` AND `delta_hi < q80`;
- otherwise `UNCERTAIN`.

No midpoint guessing is allowed.

## E. Evaluation metrics
On the chronological EVALUATION half only:
1. residual-envelope coverage of canonical archive ratio;
2. eligible M15 N;
3. certainty coverage = non-UNCERTAIN / all eligible rows;
4. exact accuracy among CERTAIN rows vs canonical archive class;
5. SHORT precision and SHORT recall;
6. BUY precision and BUY recall;
7. number and details of any false-certain decisions;
8. uncertainty concentration vs distance to q20/q80.

## F. Stateful 12h clock diagnostic
Separately, apply the original 12h non-overlap event clock to:
- canonical archive class stream;
- recovered CERTAIN stream, treating UNCERTAIN as no event.

Use a 24h preroll after evaluation starts before event matching.
Report all-side and SHORT union match.
This clock diagnostic is NOT allowed to change the pointwise recoverability verdict.

## Pre-registered gates
### Pointwise causal recoverability PASS
All must hold:
- evaluation comparable M15 N >= 1000;
- evaluation ratio-envelope coverage >= 99.5%;
- certainty coverage >= 95.0%;
- exact accuracy among CERTAIN >= 99.9%;
- CERTAIN_SHORT precision >= 99.5%;
- canonical SHORT recall by CERTAIN_SHORT >= 98.0%;
- CERTAIN_BUY precision >= 99.5%;
- canonical BUY recall by CERTAIN_BUY >= 98.0%.

Verdict: `PASS_CAUSAL_DECISION_RECOVERABILITY_WITH_ABSTENTION` or `FAIL_CAUSAL_DECISION_RECOVERABILITY`.

### Stateful clock diagnostic
- all-side event union match >=95% => `CLOCK_PARITY_PASS`, else `CLOCK_PARITY_FAIL`;
- SHORT event union match >=95% => `SHORT_CLOCK_PARITY_PASS`, else `SHORT_CLOCK_PARITY_FAIL`.

## Guardrails
- No threshold adjustment after seeing evaluation.
- No new alpha filter.
- No PnL is used in LAB058.
- No REST-live allocation is authorized by this LAB alone.
- Frozen SHORT v1 remains archive-canonical until transport and native execution parity are separately established.