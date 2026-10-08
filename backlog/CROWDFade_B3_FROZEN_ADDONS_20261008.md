# CrowdFade — Frozen B3 Add-on Definitions

**Frozen:** 2026-10-08  
**Parent baseline:** `baseline/crowdfade-engine-a-20261008`  
**Purpose:** preserve the two LAB133 B3 definitions exactly before portfolio-combination testing.

## Engine A remains unchanged

Canonical Engine A is still:
`CORE_CONT + REACCEL`

Do not mutate the Engine A signal definition. B3 is an add-on candidate engine.

## B3 shared context

- BTC research field: `count_long_short_ratio`
- H4 trend: causal EMA50 + EMA50 lag6 logic
- H4 trend age >= 4 bars
- fresh `|Z| >= 1` with crowd direction opposite H4 trend
- countertrend attack reaches exactly the tested `0.50 H1 ATR` depth within 6h
- by depth hit:
  - crowd Z retains attack sign
  - `|Z|` strengthens by at least `+0.25`
  - OI rises from signal to depth hit
- divide attack into five causal `0.10 H1 ATR` milestone segments:
  - d01, d02, d03, d04, d05
- reclaim: first M5 close back through the previous 0.10 ATR milestone (start of final attack wave)
- entry: next M5 open in H4 trend direction
- execution: SL = 1 H1 ATR, TP = 3R, max hold 48h, stop-first

## Frozen B3-BALANCED

`B3_BALANCED = depth 0.50 ATR + POSITIVE_SLOPE`

Definition:
- linear slope of milestone durations `[d01,d02,d03,d04,d05]` is > 0

LAB133 BTC TRAIN @2.81bps:
- N = 215
- ~4.48 trades/month
- EV ~= +0.266R
- PF ~= 1.38
- WR ~= 34.0%

Stress @7.5bps:
- EV ~= +0.190R
- PF ~= 1.26

## Frozen B3-HIGH

`B3_HIGH = depth 0.50 ATR + TERMINAL_TWO_STEP`

Definition:
- `d04 > d03`
- AND `d05 > d04`

LAB133 BTC TRAIN @2.81bps:
- N = 42
- ~0.88 trades/month
- EV ~= +0.705R
- PF ~= 2.25
- WR ~= 45.2%

## Scientific status

These are **TRAIN-frozen candidate definitions**, not validated production engines.
BTC OOS was intentionally not used for selection in LAB132/LAB133.

Next step is portfolio combination against frozen Engine A:
- A only
- A + B3_BALANCED
- A + B3_HIGH
- A + B3_BALANCED with HIGH tagged as quality subset

Portfolio test must use one-position chronology and report:
- overlap
- incremental unique trades/month
- PF / EV / R-month
- MTM or at minimum realized DD
- stress costs 7.5bps

Do not tune B3 definitions during portfolio testing.
