# GC_AMP_LIVE_BUYER_BREAKOUT_PARITY_LAB_013

Status: **INSUFFICIENT_FRESH_PARITY_SAMPLE**

Freeze: `2026-09-16T21:06:12+00:00` / `80334cb9550682a1d2e440f73ee4b70033f052e9`.

Realtime post-freeze snapshot and matching raw AMP/CQG tick files have not yet been supplied to the frozen LAB013 evaluator.

## Frozen PASS gate

- >= 500 paired warmup-valid completed GC M1 bars
- >= 5 rebuilt `BUYER_BREAKOUT_LONG_001` signals
- 100% `a_buy` parity
- 100% `signal_bool` parity
- exact live/rebuild signal timestamp set equality
- all 13 required numerical fields within preregistered tolerances
- zero missing bars in the scored common-clock interval

LAB013 is an implementation/data parity audit only. It does not certify profitability and does not promote E1 over E3.
