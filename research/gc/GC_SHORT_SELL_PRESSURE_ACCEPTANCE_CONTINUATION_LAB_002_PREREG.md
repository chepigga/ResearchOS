# GC SHORT SELL-PRESSURE ACCEPTANCE CONTINUATION — LAB002 PREREG

**Date:** 2026-09-17
**Status before results:** preregistered / historical bounded discovery / not OOS.

## Objective
Test a bearish mechanism that is deliberately different from LAB001 failed-reclaim:

`EXTREME SELL PRESSURE -> BREAK BELOW PRIOR20 LOW -> CLOSE/ACCEPT BELOW -> NEXT M1 ALSO ACCEPTS BELOW -> SHORT CONTINUATION`

No XAU execution parameters are optimized in this lab. This lab tests only whether the GC mechanism has a stable short-direction forward edge worth transferring to XAU in a later lab.

## Frozen causal construction
Reuse the exact GC M1 reconstruction/features from `gc_m1_orderflow_edge_discovery_003.py`.

A seed bar at M1 index t must satisfy all of:
1. `a_sell == True` (`delta_frac <= prior240 Q10` and `sell_vol >= prior240 Q75`);
2. `low <= prior20_low`;
3. `close < prior20_low`;
4. `close_pos <= 0.25`;
5. `impact > 0` under the existing SELL impact convention (`impact = -body_atr`), therefore bearish realized impact.

Confirmation bar t+1 must be clock-contiguous and satisfy all of:
1. `close < seed.prior20_low`;
2. `close_pos <= 0.50`;
3. `delta_frac < 0`.

The confirmation is intended to represent acceptance below the broken level and absence of an immediate recovery. It is not a reclaim/rejection pattern.

Entry clock: exact open of contiguous M1 bar t+2, after the confirmation bar is fully complete.
Direction: SHORT only.
ATR normalization: seed-bar ATR14.
Forward observations from entry: 5m, 15m, 30m close-to-entry return in ATR units, signed for SHORT.

## Frozen time partitions
Same discovery clocks as prior GC work:
- TRAIN: signal time < 2026-08-20 00:00 UTC
- VALID: 2026-08-20 00:00 UTC <= signal time < 2026-09-06 22:00 UTC
- LATE_CHECK: 2026-09-06 22:00 UTC <= signal time <= 2026-09-11 12:46 UTC
- POST_CHECK: > 2026-09-11 12:46 UTC (AMP extension only where available)

Rithmic is the discovery clock. AMP overlap is feed-parity/supportive evidence, not independent OOS.

## Frozen pass gates
Primary decision horizon = 15m and 30m.

PASS requires all:
- Rithmic FULL N15 >= 25;
- Rithmic TRAIN N15 >= 12;
- Rithmic VALID N15 >= 8;
- Rithmic TRAIN EV15 > 0;
- Rithmic TRAIN EV30 > 0;
- Rithmic VALID EV15 > 0;
- Rithmic VALID EV30 > 0;
- Rithmic FULL EV15 > 0;
- Rithmic FULL EV30 > 0;
- if Rithmic LATE_CHECK N15 >= 3, LATE_CHECK EV15 > 0 and EV30 > 0;
- AMP VALID EV15 > 0;
- AMP VALID EV30 > 0.

No threshold retuning after viewing results. If this exact definition fails, reject it and open a new preregistered bearish mechanism rather than modifying it post hoc.

## Interpretation rule
PASS = historical GC SHORT mechanism candidate only. It is **not** Demo-ready and does not authorize XAU trading. A PASS candidate must next undergo GC->XAU transfer/execution research.
