# LAB016 post-run parity correction

The first clean replay exposed one benchmark-only implementation mismatch after outcomes were already generated:

- preregistered `FIXED_CLOCK_RAW` was required to reproduce LAB015 `RAW_PRICE_PATH`;
- LAB015 defines fixed-clock drawdown as `maximum.accumulate(post_break_x) - post_break_x`, beginning at break+1;
- the initial LAB016 implementation accidentally inherited the event-phase drawdown origin and included the break-close x in the running maximum for the fixed-clock benchmark.

Correction: only `FIXED_CLOCK_RAW dd_t` is restored to the LAB015 definition. EVENT_ALIGNED features, target, learner, routing threshold, entry, economics, gates and holdout embargo are unchanged.

This correction is parity/benchmark-only and is documented before the corrected replay.
