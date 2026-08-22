# XAU_VWAP_TOUCH_RESPONSE_VS_ACCEPTANCE_CAUSAL_MAP_LAB_002 — Spec v001

Date: 2026-08-22
Status: PREREGISTERED_CAUSAL_MAP / HOLDOUT_SEALED

## Research question

Using the podcast hypothesis as source framing, test the broader object that LAB001 did not cover: all causal anchored-VWAP touch episodes. The goal is to map which information available in the first 1–5 minutes after touch separates later REJECTION from ACCEPTANCE. This is a mechanism map, not an EA and not a final economic strategy.

Source framing preserved from `VWAP_IFVG_CAUSAL_ML_LAB_001`: the universe must begin from ALL VWAP touches rather than preselected VWAP+iFVG setups; the key causal variables are penetration, time beyond level, reclaim/failed recovery, response velocity, repeated respect and iFVG as a possible incremental feature.

## Data

Canonical XAUUSD M1 Bid/Ask OHLC + tick_volume:
`XAUUSD_M1_20220601_20260723_TICK_NATIVE.csv`
Expected SHA-256:
`db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b`
CSV delimiter: `;`.

## Partitions

- DISCOVERY: timestamp < 2024-01-01
- CONFIRMATION: 2024-01-01 <= timestamp < 2025-07-01
- SEALED HOLDOUT: timestamp >= 2025-07-01

LAB002 v001 must not read/report holdout outcomes.

## Anchored VWAP

Same causal reconstruction as LAB001:
- session anchor = 01:00 source/platform clock, corresponding to 18:00 New York under the documented FTMO platform-time convention;
- typical price = (BidHigh + BidLow + BidClose) / 3;
- weight = broker tick_volume available on the current M1 bar;
- causal cumulative weighted mean and weighted standard deviation within the session only;
- levels: MID = VWAP, HIGH = VWAP + 1.618 * weighted SD, LOW = VWAP - 1.618 * weighted SD.

HIGH/LOW are diagnostic proxy bands, not claimed to be an exact reconstruction of the protected podcast indicator.

ATR normalization:
- Wilder ATR14 on M15;
- only the last completed M15 ATR available at each M1 timestamp.

## Touch universe

For each of MID/HIGH/LOW separately, define a touch when the M1 Bid range intersects a proximity zone of +/-0.05 ATR around the contemporaneous causal level, after that level has been armed.

Re-arm rule (frozen): after a touch, no new episode at the same level until the absolute Bid-close distance from the contemporaneous level reaches >=0.25 ATR.

Episode direction is defined without future information:
- `arrival_side = sign(BidClose[t-1] - level[t-1])`;
- if the immediately prior close is too close to define a side, walk backward up to 5 completed M1 bars and take the first non-zero side;
- episodes without a definable arrival side are excluded.

## Early causal clocks

T0 = touch M1 bar close.

Feature snapshots use only bars known by:
- T+1m
- T+3m
- T+5m

Primary decision/map clock = T+5m.

No feature may use data after T+5m.

## Early feature families

Normalized to ATR at T0 unless stated otherwise:

1. VWAP geometry
- level_type MID/HIGH/LOW
- band_width_ATR
- VWAP slope over prior 5m
- touch distance at T0

2. Arrival
- signed prior 1m/5m return in arrival coordinates
- prior 5m path efficiency

3. Penetration / acceptance sequence
- max penetration beyond level during first 1/3/5m
- fraction of completed closes beyond level during first 1/3/5m
- number of closes beyond level
- cross_count around the dynamic level
- final signed distance to level at 1/3/5m

4. Reclaim / rejection sequence
- whether price penetrated beyond then reclaimed arrival side by T+1/T+3/T+5
- time_to_first_reclaim in minutes
- max response excursion back to arrival side by T+5

5. Repeated interaction telemetry
- touch_number_same_level_in_session
- minutes_since_previous_same_level_touch

6. iFVG telemetry
Use the already-frozen LAB001 mechanical confirmed-iFVG event definition. Record whether a confirmed iFVG decision occurs from T0 through T+5m and whether it is aligned with rejection direction, acceptance direction, or neither. iFVG is telemetry only in LAB002; no event selection is based on it.

## Future label

The first five minutes are strictly feature-building and therefore excluded from outcome labeling.

At T+5m, freeze the T0 causal level value and T0 ATR. Define:
- rejection direction = arrival_side;
- acceptance direction = -arrival_side.

From the first M1 bar after T+5m through T+60m:
- REJECTION if price first reaches `T0_level + arrival_side * 0.50 ATR`;
- ACCEPTANCE if price first reaches `T0_level - arrival_side * 0.50 ATR`;
- AMBIGUOUS if both barriers are touched in the same M1 bar;
- UNRESOLVED if neither barrier is reached.

Barrier evaluation uses Bid high/low because this LAB is mechanism mapping, not execution economics. AMBIGUOUS is excluded from binary rates but retained in census.

Sensitivity-only labels are also computed at 0.25 and 0.75 ATR. They are diagnostic and cannot replace the frozen 0.50 ATR primary label after results are viewed.

## Primary outputs

1. Event census by split, year, level, arrival side.
2. REJECTION / ACCEPTANCE / UNRESOLVED rates.
3. Causal sequence-state map at T+1/T+3/T+5.
4. Feature bucket maps for:
   - penetration depth;
   - fraction closes beyond;
   - final side distance;
   - arrival speed;
   - cross count;
   - touch number;
   - iFVG aligned/absent.
5. Discovery vs Confirmation transfer for each candidate state/bucket.
6. BUY/SELL-equivalent response separation and HIGH/MID/LOW separation.
7. Diagnostic iFVG incremental comparison conditional on the same early response state.

## Frozen sequence states at T+5

Using the first five completed M1 closes after T0 relative to the contemporaneous dynamic level and arrival coordinates:

- `EARLY_REJECTION`: final signed distance >= +0.05 ATR AND at least one prior close beyond the level.
- `EARLY_ACCEPTANCE`: final signed distance <= -0.05 ATR AND >=4 of 5 closes are beyond the level.
- `RECLAIM_CHOP`: at least one penetration beyond, final close on arrival side, but EARLY_REJECTION threshold not met, OR cross_count >=2.
- `NO_PENETRATION`: no completed close beyond the level.
- `OTHER`: everything else.

State priority: EARLY_ACCEPTANCE > EARLY_REJECTION > RECLAIM_CHOP > NO_PENETRATION > OTHER.

## Interpretation rules

This LAB is allowed to discover where conditional structure exists, but not to promote post-hoc hard thresholds. A useful finding requires:
- same directional tendency in Discovery and Confirmation;
- sufficient sample size (primary map cell N >= 100 in Confirmation for strong claims; N >= 40 is exploratory only);
- no claim based only on pooled statistics;
- no opening of the sealed holdout.

Potential verdicts:
- `CAUSAL_MAP_TRANSFERABLE`: one or more preregistered sequence states robustly separate rejection vs acceptance in both splits.
- `REGIME_OR_LEVEL_SPECIFIC`: separation exists only by level/direction/regime and is not universal.
- `WEAK_SEQUENCE_SIGNAL`: same tendency but weak separation / poor power.
- `NO_CAUSAL_SEPARATION`: early 1–5m sequence does not transfer.

## Explicit exclusions

No D1/H4 trend gate, RSI, ADX, news filter, COT, discretionary liquidity labels, post-hoc session filtering, threshold optimization, final-day VWAP, future swing information, or holdout inspection. No EA/live allocation from LAB002 alone.
