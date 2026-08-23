# XAU_ORDERED_STORYLINE_BIAS_ENGINE_v001

**Status:** PROMOTED_FROM_LAB009 / PRE_HOLDOUT / BIAS_ONLY  
**Source:** `XAU_POST_BREAK_ORDERED_STATE_PATH_AND_BIAS_LAB_009` v001  
**Promotion date:** 2026-08-23  
**Holdout opened:** `false`

## Purpose

This engine is the canonical XAU post-break **Bias Engine**. It does not generate entries. Its sole job is to estimate whether the market is likely to continue accepting the new side of a broken objective level after observing the chronological post-break storyline.

The engine output is a continuous probability:

`p_accept = P(ACCEPTANCE_PERSISTS | ordered post-break state path)`

where `ACCEPTANCE_PERSISTS = 1` means at least 20 of the next 30 completed M1 closes remain on the breakout side of the contemporaneous dynamic level.

This probability is a **directional context / bias score**, not a market-order signal and not a prediction of another fixed ATR extension from the current price.

## Validated scope

Primary validated level family: LAB009 `VWAP_VOLUME` dynamic MID/HIGH/LOW lines.

LAB009 also showed a nearly identical effect on the anchored-mean control. Therefore the mechanism is interpreted as a **generic post-break acceptance storyline**, not as VWAP-specific alpha. This engine is validated on those two objective level constructions only; arbitrary support/resistance generators are not automatically authorized.

## Primary clock

Primary decision clock: **T+15 minutes after break**.

The first 15 minutes after break are split into three non-overlapping completed 5-minute blocks:
- block 1: minutes 1–5
- block 2: minutes 6–10
- block 3: minutes 11–15

The engine preserves the exact chronological order of the three block states.

Secondary research clock: T+30 with six 5-minute blocks. T+30 is validated as a bias diagnostic but is not the default engine clock.

## Frozen state alphabet

Each 5-minute block receives exactly one token, in this fixed priority order:

1. `RECLAIM`
   - ending signed distance `<= -0.05 ATR_touch`, OR
   - fraction of closes on breakout side `< 0.40`.

2. `FAILED_RECOVERY`
   - at least one close reaches `<= -0.05 ATR_touch`,
   - block ends `>= +0.05 ATR_touch`,
   - at least 60% of closes are on breakout side.

3. `EXPAND`
   - at least 80% of closes are on breakout side,
   - end-minus-start signed distance `>= +0.10 ATR_touch`,
   - block maximum signed distance exceeds start by `>= +0.15 ATR_touch`.

4. `TEST`
   - at least one close comes within `±0.05 ATR_touch` of the dynamic level,
   - block ends on breakout side,
   - at least 60% of closes are on breakout side.

5. `HOLD`
   - at least 80% of closes are on breakout side,
   - minimum signed distance is `> -0.05 ATR_touch`.

6. `CHOP`
   - all remaining blocks.

Signed distance:

`x_t = break_dir * (Close_t - Level_t) / ATR_touch`

Positive values mean price is on the breakout side.

## Frozen probability estimator

Training source: Discovery only (`break_time < 2024-01-01`). No Confirmation fitting.

Probability for a state cell uses Beta(1,1) smoothing:

`p = (successes + 1) / (N + 2)`

For T+15 ordered paths:
1. exact 3-state path if Discovery N >= 50;
2. otherwise last-two-state ordered path if N >= 50;
3. otherwise final-state snapshot probability.

No threshold optimization is part of the Bias Engine.

## Engine I/O contract

### Required inputs
- `break_time`
- `break_dir` (`+1` upward break, `-1` downward break)
- `level_source`
- dynamic level values for all required post-break minutes
- `ATR_touch`
- contiguous completed M1 OHLC for the first 15 minutes after break

### Outputs
- `ordered_path`: e.g. `EXPAND>HOLD>EXPAND`
- `p_accept`: calibrated Discovery probability after frozen backoff
- `backoff_level`: `EXACT_3`, `LAST_2`, or `SNAPSHOT`
- `bias_direction`: the original break direction; the probability quantifies confidence that acceptance persists in that direction
- `decision_time`: `break_time + 15m`
- `research_validity_horizon`: next 30 completed M1 bars

The engine does **not** output `entry_price`, `stop`, `take_profit`, lot size, or market/limit order instructions.

## Promotion evidence from LAB009

Confirmation T+15, N = 12,027:
- SNAPSHOT_STATE AUC: 0.8083
- BAG_OF_STATES AUC: 0.8114
- ORDERED_PATH AUC: **0.8250**
- ORDERED − SNAPSHOT: **+0.0167**, weekly 95% CI **[+0.0133, +0.0202]**
- ORDERED − BAG: **+0.0136**, weekly 95% CI **[+0.0106, +0.0164]**
- ORDERED Brier: **0.1670**, lower than both snapshot and bag
- calibration top-vs-bottom quintile spread: **+72.61 percentage points**
- T+30 ordered AUC: **0.8709**

Breadth:
- BUY AUC 0.8220
- SELL AUC 0.8278
- HIGH 0.8277
- LOW 0.8311
- MID 0.8169
- 2024 0.8183
- 2025 H1 0.8398

All LAB009 frozen gates G0..G10 passed.

## Interpretation rule

The canonical interpretation is:

> `p_accept` answers: “Given the ordered post-break storyline observed so far, how likely is the market to keep accepting the new side of the broken level over the next 30 minutes?”

It does **not** answer:

> “Should I enter now?”

or

> “Will price travel another +0.50 ATR from the current price?”

LAB008 explicitly showed that the latter extension question is approximately unpredictable from this storyline.

## Downstream integration rules

1. Bias formation and entry timing must remain separate modules.
2. Any LAB or EA consuming this engine must use the frozen LAB009 state definitions and probability table/backoff logic unless a new preregistered Bias Engine version is created.
3. Downstream entry research must compare the **same entry universe** with and without this bias score/router.
4. No entry threshold on `p_accept` may be retroactively chosen from LAB009 Confirmation outcomes. Thresholds belong to a new preregistered integration LAB.
5. No direct market chase is authorized from a high `p_accept` score.
6. Holdout `>=2025-07-01` remains sealed until a later integrated system passes its preregistered internal gates and a one-time holdout opening is explicitly authorized.

## Canonical status

`XAU_POST_BREAK_ORDERED_STATE_PATH_AND_BIAS_LAB_009` is hereby frozen as the evidence base for:

**`XAU_ORDERED_STORYLINE_BIAS_ENGINE_v001`**

Role: **BIAS / CONTEXT ONLY**  
Live allocation: **0**  
Entry authorization: **NONE**
