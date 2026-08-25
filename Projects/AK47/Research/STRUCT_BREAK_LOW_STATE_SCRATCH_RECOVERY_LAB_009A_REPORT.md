# STRUCT_BREAK_LOW_STATE_SCRATCH_RECOVERY_LAB_009A

**Date:** 2026-08-25  
**Status:** COMPLETED — diagnostic before re-entry  
**Verdict:** `SCRATCH_BEATS_IMMEDIATE_EXIT__BUT_NOT_HOLD_OOS`

## Question

LAB008 established that a 30-minute LOW state is genuinely bad:
- weak/no net progress,
- high MAE,
- repeated closes back through the broken level,
- negative future EV.

The next question was:

> If LOW is already around -0.2R to -0.4R, is it better to exit immediately, or wait for price to recover to approximately 0R and scratch the trade?

Re-entry is deliberately excluded from this subtest.

## Frozen LOW trigger

Exactly the same LAB008 30m response classifier was reconstructed:
- standardized logistic regression,
- `C = 0.3`,
- trained on DEV 2019–2022,
- LOW = bottom DEV score tertile,
- only trades alive and still below +1R at 30m.

This reproduces LAB008 exactly:

VAL LOW:
- N = 200
- P(+1R) = 37.0%
- final EV = -0.271R
- NET at 30m ≈ -0.256R
- MFE ≈ +0.169R
- MAE ≈ 0.494R.

## Primary test: wait for recovery to 0R

Policy:
1. detect LOW at 30m;
2. do not market-exit at the current negative price;
3. wait for price to recover to entry;
4. if entry is touched before the canonical exit, close at 0R gross / -0.06R net cost;
5. if price never recovers, keep the canonical outcome.

### LOW population only

| Split | Canonical HOLD | EXIT NOW | WAIT FOR 0R | vs EXIT NOW | vs HOLD |
|---|---:|---:|---:|---:|---:|
| DEV N=186 | -0.302R | -0.258R | **-0.240R** | **+0.017R** | **+0.062R** |
| VAL N=200 | **-0.271R** | -0.316R | -0.299R | **+0.017R** | **-0.028R** |

So the user's intuition is correct in one precise sense:

> **Once LOW is recognized, waiting for a recovery/scratch is better than crystallizing the current -0.25R to -0.35R loss immediately.**

This relation transfers DEV -> VAL by about +0.017R per LOW trade.

But:

> **Scratch-to-zero does not beat canonical HOLD OOS.**

The VAL paired bootstrap for scratch-minus-HOLD is approximately:
- mean = -0.028R
- 95% CI ≈ [-0.191R, +0.130R]
- not significant.

## Portfolio effect

Applying the policy only to LOW30 states:

| Split | Policy | EV/trade | Max DD |
|---|---|---:|---:|
| DEV | canonical | +0.0155R | 39.44R |
| DEV | immediate LOW exit | +0.0262R | 31.21R |
| DEV | scratch 0R | **+0.0304R** | **32.64R** |
| VAL | canonical | **-0.0315R** | **38.78R** |
| VAL | immediate LOW exit | -0.0443R | 51.43R |
| VAL | scratch 0R | -0.0395R | 49.09R |

Therefore scratch-alone is not promotable.

## Why does scratch fail against HOLD?

This is the key result.

Among VAL LOW trades:

### Never recovered to entry
- N = 49
- eventual SL = **49 / 49**
- eventual BE = 0
- eventual full TP = 0

These are genuine failed moves.

### Recovered to entry after LOW
- N = 134
- eventual SL = 68
- eventual BE = 35
- eventual full TP 2.3R = **31**

So recovery is not equivalent to failure.

A scratch policy correctly avoids many future SLs, but it also cuts **31 future +2.3R winners**.

That lost right tail is why scratch-alone cannot beat HOLD.

This is exactly the economic reason re-entry is needed.

## Recovery timing

For VAL trades that recover to 0R after LOW:
- median recovery time ≈ 15 min after the LOW decision,
- 75% recover within ≈ 35 min,
- 90% within ≈ 64 min.

But recovery time alone is not monotonic enough to separate winners and losers robustly.

## Small sensitivity family

A small diagnostic grid also tested recovery at:
- -0.10R
- 0R
- +0.10R

with 60m / 120m / unlimited waiting windows.

The best pooled VAL cell was:

`recover to +0.10R, max wait 60m`

LOW-only:
- DEV improvement vs HOLD: +0.052R
- VAL improvement vs HOLD: +0.027R

Portfolio VAL:
- base EV -0.0315R
- policy EV -0.0237R

However this is **not validated**:
- selected from a small diagnostic grid,
- paired CI crosses zero,
- 2024 materially worsens,
- VAL max DD increases slightly (38.78R -> 40.19R).

Treat it only as a seed, not a rule.

## M1 execution check

The 2024–2025 calculation was repeated on exact M1 data.

The scratch and +0.10R/60m outcomes were effectively identical to the M5 calculation, so the conclusion is not a same-M5-bar ordering artifact.

# Formal verdict

## `SCRATCH_BEATS_IMMEDIATE_EXIT__BUT_NOT_HOLD_OOS`

Confirmed:
1. LOW is detected before SL, not after it.
2. Immediate market exit from LOW is too crude.
3. Waiting for recovery to ~0R is consistently better than immediately realizing the LOW loss.
4. A subset that never recovers after LOW is extremely poor.
5. Scratch alone loses too much upside because many recovered trades later become full winners.

Rejected:
- `LOW -> immediate exit`
- `LOW -> scratch 0R -> setup finished`

## Consequence

The next test is no longer optional:

### `STRUCT_BREAK_LOW_EXIT_REARM_REENTRY_LAB_009B`

The core question becomes:

> Can we scratch/cheap-exit the LOW state, keep the original structural thesis armed, and recover the 31 future winners by re-entering only when a new IMPULSE state appears?

That is the mechanism required for the adaptive system to beat HOLD rather than merely reduce the size of some losses.
