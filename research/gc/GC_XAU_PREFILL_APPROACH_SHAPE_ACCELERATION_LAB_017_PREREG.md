# GC_XAU_PREFILL_APPROACH_SHAPE_ACCELERATION_LAB_017_PREREG

Frozen before results.

## Question

Does a **slow lifetime approach followed by faster recent downward motion** before D1 identify harmful XAU fills early enough to cancel the resting D1 order?

## Population

Exactly the causal executable D0.75 warning population from LAB016. No new market data.

## Frozen primary score

At the first actionable D0.75 warning:

- `lifetime_down_velocity = xau_approach_velocity_atr_per_sec`
- `recent_window_sec = max(min(30, warning_delay_sec), 1)`
- `recent_down_velocity30 = -xau_mom_30s_warning_atr / recent_window_sec`
- `acceleration_delta = recent_down_velocity30 - lifetime_down_velocity`

Higher `acceleration_delta` means the final approach into D1 is faster downward than the average approach since order start.

No alternate score, sign flip, feature subset, depth or warning-level sweep is allowed in this LAB.

## Walk-forward decision

- Chronological expanding walk-forward.
- First 45 warning-eligible fills = initial training window.
- Test blocks = 12.
- In each fold, cancel threshold = training 75th percentile of `acceleration_delta`.
- CANCEL if test score >= frozen threshold.
- No threshold search.

## Execution causality

Decision time is the LAB016 D0.75 warning timestamp, already required to lead D1 fill by >=250 ms. Cancellation therefore occurs before D1 touch in the historical path.

## Evaluation

Primary label = future SL vs non-SL for statistical discrimination.
Economic overlay is conservative: canceled historical fills contribute 0R; no later signals are reclaimed in LAB017.

## PASS gates

All must pass:

1. OOF AUC for `acceleration_delta` >= 0.60.
2. Veto share 10% to 40%.
3. Veto SL-rate enrichment >= 1.25x OOF baseline SL rate.
4. Overlay SumR > baseline SumR.
5. Overlay EV/original signal > baseline.
6. Overlay MaxDD <= baseline.
7. Late-half overlay EV/original signal > 0.

If any gate fails, acceleration cancel gate is rejected and frozen bare D1/E3 remains the LONG demo candidate.
