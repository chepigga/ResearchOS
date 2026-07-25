# V15-BUGFIX-RERUN-001 — formal rerun report

**Date:** 2026-07-25  
**Frozen TZ SHA256:** `bb410f78f4eb520c6405b6d48398c24719ef3cf901bc0491b35a5f29fb27efba`  
**v15.1 source SHA256:** `5ee4f6596cf932850beb8e996189b5c998d600d4cb0829187a6f7428197c1d37`  
**M5 SHA256:** `40175d5d73fbbe01d26fd1813d1bc299854ef535c328fa1fdd1b883f90509ae4`

## Primary finding

The OCO and ticket-selection fixes work: **hedge fills are zero in all four configurations**.

However, the frozen input set does not contain the broker values returned by:

- `SYMBOL_TRADE_STOPS_LEVEL`
- `SYMBOL_TRADE_FREEZE_LEVEL`

This is material because the source trailing distance is exactly `3` raw MT5 points. The behavior changes discontinuously when `max(STOPLEVEL, FREEZELEVEL)` moves from `3` to `4` points.

Therefore one unconditional CONFIRMED/DEGRADED/NO-GO label cannot be opened honestly from the supplied CSV alone. The preregistered verdict is conditional on the missing symbol metadata.

## Scenario A — max(STOPLEVEL, FREEZELEVEL) <= 3 points

| TF/path | N | EV actual-risk | EV base-1% | PF | MaxDD | Hedge | SL blocks | 14d pass | Perm p95 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| H1/mirror | 8,321 | +0.076R | +0.070R | 5.78 | 3.68% | 0 | 0 | 16.72% | 5.13% |
| H1/primary | 8,316 | +0.078R | +0.071R | 6.09 | 3.68% | 0 | 0 | 16.79% | 5.80% |
| M15/mirror | 24,841 | +0.083R | +0.031R | 6.34 | 2.99% | 0 | 0 | 62.69% | 98.07% |
| M15/primary | 24,126 | +0.082R | +0.032R | 5.85 | 2.77% | 0 | 0 | 57.30% | 97.01% |

**Conditional verdict: CONFIRMED.** All four configurations have EV actual-risk above +0.05R, N far above 90 and hedge fills below 20.

Relative to v15.0:

- hedge fills fall from `313–1,599` to `0`;
- M15 EV remains approximately `+0.082R`;
- H1 EV remains `+0.076..+0.078R`;
- 14-day pass-rate becomes `57.30–62.69%` on M15 and `16.72–16.79%` on H1.

## Scenario B — max(STOPLEVEL, FREEZELEVEL) >= 4 points

At four points, every 3-point trailing modification is rejected by the new source guard.

| TF/path | N | EV actual-risk | EV base-1% | PF | MaxDD | Hedge | SL blocks | Blocked trades | 14d pass |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| H1/mirror | 8,102 | -0.021R | -0.021R | 0.11 | 81.26% | 0 | 16,736 | 7,942 | 0.00% |
| H1/primary | 6,415 | +0.034R | +0.033R | 2.43 | 5.25% | 0 | 391,528 | 6,278 | 3.86% |
| M15/mirror | 22,831 | -0.019R | -0.017R | 0.08 | 97.83% | 0 | 66,617 | 22,428 | 0.53% |
| M15/primary | 13,364 | +0.036R | +0.035R | 2.31 | 8.39% | 0 | 707,517 | 13,077 | 13.06% |

This scenario fails the CONFIRMED gate on all four configurations. The frozen rules do not define the exact 2-positive/2-negative case; the correct label is **FROZEN VERDICT UNRESOLVED / FAILS CONFIRMED** until exact broker metadata is supplied.

## Interpretation

1. Hedge trades were not the main source of the apparent edge. With a permissive 0–3 point broker limit, removing all hedge fills preserves EV.
2. The previous v15.0 result was primarily dependent on successful ultra-tight 3-point trailing modifications.
3. If the actual FTMO tester reports a stop/freeze limit of four points or more, v15.1 cannot be promoted as canonical and should be treated as execution-falsified in its current form.
4. No parameter adjustment is authorized by this laboratory.

## Exact metadata required

Record `SYMBOL_TRADE_STOPS_LEVEL` and `SYMBOL_TRADE_FREEZE_LEVEL` inside the same Strategy Tester environment.

- `max value <= 3` → **CONFIRMED**;
- `max value >= 4` → **FAILS CONFIRMED**.
