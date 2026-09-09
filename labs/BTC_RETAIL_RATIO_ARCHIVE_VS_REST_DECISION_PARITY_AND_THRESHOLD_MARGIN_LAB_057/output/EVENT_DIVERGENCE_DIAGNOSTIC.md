# LAB057 event divergence diagnostic

This diagnostic does not alter the preregistered verdict or any gate.

## Pointwise result
Across 2,869 comparable M15 rows:
- all-class BUY/SHORT/NEUTRAL parity = 99.7909%
- SHORT binary parity = 99.8954%
- 3 SHORT pointwise flips total
- SHORT FP = 2; SHORT FN = 1

## Why event parity still failed
The frozen FLOW engine is stateful: any BUY or SHORT extreme starts a 12h non-overlap cooldown. Therefore one near-threshold pointwise mismatch can shift the event clock and affect later event selection even when later pointwise decisions are identical.

The causal divergence episode is:

Archive event stream:
- 2026-08-20 06:45 BUY
- 2026-08-20 18:45 BUY
- 2026-08-21 06:45 BUY

REST event stream:
- 2026-08-20 07:00 BUY
- 2026-08-20 19:00 BUY
- 2026-08-21 08:15 SELL

At 2026-08-20 06:45 the archive delta was only 0.000037076 beyond q20 while REST was 0.000192214 back inside NEUTRAL. That one boundary flip delayed the REST cooldown phase by 15 minutes. The phase difference persisted and eventually allowed the REST-only 08:15 SHORT on Aug 21 while archive was still in cooldown from its 06:45 BUY.

## Important nuance
SHORT-only event parity was 18/19 = 94.7368%:
- all 18 archive SHORT events were also present in REST;
- REST added 1 extra SHORT event;
- no archive SHORT event was missed at event level in this overlap.

The separate SHORT pointwise flips on Aug 16 and Aug 28 mostly occurred inside already-active cooldown windows and therefore did not create missing archive SHORT FLOW events.

## Interpretation
The live REST ratio is highly reliable as a pointwise state sensor, but it is not yet certified as a byte-equivalent driver for the frozen stateful 12h FLOW event clock. Tiny threshold differences can be amplified by cooldown phase.

Formal LAB057 verdict remains FAIL_REST_DECISION_PARITY. Archive daily metrics remain canonical.