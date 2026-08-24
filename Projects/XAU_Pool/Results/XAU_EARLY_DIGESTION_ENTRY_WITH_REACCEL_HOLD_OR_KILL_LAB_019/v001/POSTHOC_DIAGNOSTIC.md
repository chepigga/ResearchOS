# LAB019 post-hoc balance diagnostic — does not change frozen verdict

Frozen verdict remains `NO_HOLD_KILL_MANAGEMENT_EDGE`.

## Why the 5m timer fails

The timer is not merely too early/late on average; **absence of the frozen MICRO_REACCEL signal is not equivalent to a dying trade**.

Among Confirmation FUTURE_MICRO events:
- MICRO wait <=3 min: N 518, managed = baseline EV +0.343R (no timer damage).
- wait 4–5 min: N 292, +0.405R (no damage).
- wait 6 min: N 79, +0.576R (no damage).
- wait 7–10 min: N 234, baseline +0.234R but managed -0.184R; timer delta -0.418R.
- wait >10 min: N 37, baseline +0.385R but managed -0.317R; delta -0.702R.

Thus late-but-healthy reacceleration is systematically killed before it becomes observable.

## More important: winners exist without MICRO_REACCEL

Within NO_FUTURE_MICRO Confirmation events:
- 1,005 eventual baseline SL trades: management improves them by about +0.319R on average.
- but 157 eventual baseline TP trades also have no frozen MICRO_REACCEL: management destroys about -1.403R per trade on average.

TIME_KILL specifically:
- saves 441 eventual SLs by about +0.757R each;
- but cuts 252 eventual TPs from baseline +1.462R to about +0.042R, costing about -1.420R each.

This winner destruction offsets the saved losers.

## Degradation-only

`DEGRADE_ONLY` is the least harmful management sensitivity:
- serial EV -0.1745R vs baseline -0.1806R;
- paired lift only about +0.0012R, CI crosses zero.

So old-level degradation alone is not enough to create an edge either.

## Interpretation

LAB012's future-MICRO split was useful as a *latent health label*, but LAB019 shows it is not a complete causal management state. The absence of that one trigger cannot justify killing a live trade because:
1. some healthy trades reaccelerate later than the fixed timer;
2. some profitable trades reach TP without ever satisfying the frozen MICRO_REACCEL definition.

A future management study, if pursued, should model the **live post-entry path / MFE-MAE / acceptance deterioration / progress-to-TP jointly**, rather than using `no MICRO_REACCEL yet` as a kill condition.
