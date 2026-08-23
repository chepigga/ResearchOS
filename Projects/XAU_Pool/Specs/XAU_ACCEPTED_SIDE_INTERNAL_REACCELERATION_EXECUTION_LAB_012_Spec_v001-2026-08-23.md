# XAU_ACCEPTED_SIDE_INTERNAL_REACCELERATION_EXECUTION_LAB_012 — Spec v001

**Status:** PREREGISTERED / HOLDOUT_SEALED  
**Date:** 2026-08-23  
**Parents:** LAB009 Bias Engine v001 → LAB010 → LAB011

## Motivation

LAB009 established a transferable ordered post-break Bias Engine. LAB010 showed that waiting for a deep return to the original broken level is adverse selection. LAB011 showed that, while strong acceptance remains intact, the *ordered internal structure built on the accepted side* predicts whether a new directional leg appears before failure; in particular, transitions that end in renewed expansion are much stronger than structures that decay into deep pullback. LAB012 tests whether that internal re-acceleration can be converted into executable economics **without waiting for a full 5-minute EXPAND block to complete**.

This LAB changes one explicit causal dimension: entry timing after accepted-side digestion.

## Canonical data / embargo

- canonical input: `XAUUSD_M1_20220601_20260723_TICK_NATIVE.csv`
- canonical SHA-256: `db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b`
- frozen break universe: LAB008 `break_census.csv`, `model_event=true`, family `VWAP_VOLUME`
- Discovery: break time `< 2024-01-01`
- Confirmation: `2024-01-01 <= break_time < 2025-07-01`
- sealed holdout: `>= 2025-07-01`

No post-holdout bars/events may be read.

## Frozen Bias Engine

Reconstruct `XAU_ORDERED_STORYLINE_BIAS_ENGINE_v001` exactly:
- T+15 decision clock;
- first 15 minutes split into three non-overlapping 5-minute blocks;
- state alphabet and priority unchanged from LAB009;
- Discovery-only Beta(1,1) empirical probability;
- exact 3-state path if Discovery N>=50, else last-two-state backoff if N>=50, else snapshot;
- `STRONG_ACCEPTANCE` if `p_accept >= 0.75`.

No LAB009 Confirmation fitting or threshold optimization.

## Accepted-side validity / degradation

After T+15, the original broken dynamic VWAP level is a **failure boundary**, not an entry target.

For every minute define:
`x_t = break_dir * (Close_t - Level_t) / ATR_touch`.

The accepted-side lifecycle remains valid only while completed closes stay `> +0.05 ATR_touch`.

The first completed close `<= +0.05 ATR_touch` is `ACCEPTANCE_DEGRADED`; after it:
- no new LAB012 trigger may form;
- the lifecycle ends for signal discovery.

This rule is frozen before replay and operationalizes LAB010/LAB011's old-level-return adverse-selection result.

## Frozen internal 5-minute state logic

Use the LAB011 accepted-side state definitions, evaluated only on completed, non-overlapping 5-minute blocks after T+15:
- block A: T+16..T+20
- block B: T+21..T+25
- block C: T+26..T+30
- block D: T+31..T+35

For each block, use signed close distances to the dynamic broken level and the directional high-water mark known before/inside the block.

States are unchanged in meaning from LAB011:
- `LEVEL_RETEST`
- `EXPAND`
- `SHALLOW_PULLBACK`
- `DEEP_PULLBACK`
- `BASE`
- `HOLD`

`DIGESTION = {SHALLOW_PULLBACK, DEEP_PULLBACK, BASE, HOLD}`.

A block classified `LEVEL_RETEST` immediately invalidates the lifecycle. A block classified `EXPAND` is not a digestion setup by itself.

## Primary setup — digestion then early micro re-acceleration

For each strong-bias break lifecycle:

1. Starting after T+15, find the **first completed 5-minute DIGESTION block** before T+35 while acceptance has not degraded.
2. Let `j` be that digestion-block close.
3. Define the directional close-extreme of the digestion block:
   `E = max(d * Close)` in directional coordinates (equivalently highest close for BUY, lowest close for SELL).
4. Observe at most the next **10 completed M1 bars** after `j`, but never beyond T+45.
5. The first bar `k` is `MICRO_REACCEL` if all are true:
   - acceptance still intact: `x_k > +0.05 ATR_touch`;
   - directional close breaks the digestion close-extreme by at least `+0.05 ATR_touch`;
   - directional real body `d*(Close_k-Open_k)/ATR_touch >= +0.03`;
   - the close is at least `+0.10 ATR_touch` on the accepted side of the dynamic broken level.
6. Entry is the next contiguous M1 open `k+1`:
   - BUY: `AskOpen[k+1]`
   - SELL: `BidOpen[k+1]`.
7. If no MICRO_REACCEL appears within the 10-minute window, skip.
8. Only the first qualifying digestion→micro-reaccel setup per break lifecycle is eligible.

No threshold may be changed after replay.

## Baselines / diagnostics

### A. DIGESTION_BASELINE — causal comparator
For every eligible first DIGESTION block, enter immediately at the next contiguous M1 open after the digestion block close, regardless of whether future re-acceleration occurs.

This tests whether the re-acceleration gate improves a generic accepted-side digestion entry.

### B. SAME_SIGNAL_EARLY_ENTRY — diagnostic only, not tradable selector
For only those events that later satisfy MICRO_REACCEL, also compute the hypothetical P&L from the earlier DIGESTION_BASELINE entry. This is a timing counterfactual using future knowledge to select the subset, therefore it cannot authorize live entry. It only decomposes selection benefit versus waiting cost.

### C. FULL_5M_EXPAND_CONFIRM — secondary timing diagnostic
For the same accepted-side lifecycle, if the next completed 5-minute block after digestion meets LAB011 `EXPAND`, simulate entry at the following M1 open. This is secondary only and tests whether waiting for a full EXPAND block is too late.

## Economics

Frozen from LAB004–LAB010 for comparability:
- `1R = 0.50 * ATR_touch` from actual executable entry;
- hard SL = `1R`;
- primary TP = `1.5R`;
- secondary TP = `2.0R`;
- max hold = 60 minutes from entry;
- BUY entry uses AskOpen and exits on future Bid OHLC;
- SELL entry uses BidOpen and exits on future Ask OHLC;
- same-M1 TP+SL = conservative loss;
- no hit by horizon = executable quote at horizon, clipped to `[-1R, targetR]`.

Costs:
- spread embedded in Bid/Ask data;
- commission proxy = `$5 round-turn/lot` = `$0.05` XAU price-equivalent;
- stress = extra `$0.05` and `$0.10` price-equivalent round trip.

No SL/TP optimization in LAB012.

## Serial portfolio

Primary deployability = `MICRO_REACCEL / T+15 strong bias / 1.5R / serial`.

- chronological break lifecycles;
- when flat, accept the next strong-bias lifecycle;
- ignore overlapping break lifecycles while waiting for digestion/reacceleration or while in a trade;
- lifecycle expires at T+45, acceptance degradation, or completed trade exit;
- one position max;
- no hedging, pyramiding, averaging, martingale.

A separate serial DIGESTION_BASELINE uses the same one-lifecycle-at-a-time discipline.

## Frozen metrics

Discovery and Confirmation:
- strong-bias N;
- eligible digestion N/rate;
- MICRO_REACCEL N/rate and wait time;
- accepted-side degradation before trigger;
- BUY/SELL and MID/HIGH/LOW breadth;
- trigger-state provenance (`SHALLOW_PULLBACK / DEEP_PULLBACK / BASE / HOLD`);
- 1.5R and 2R EV, PF, TP rate, total R;
- max DD, worst day, max consecutive losses;
- trades/week;
- cost stress;
- yearly transfer;
- paired same-signal timing difference vs earlier digestion entry;
- causal routed-vs-DIGESTION_BASELINE weekly EV difference.

Calendar-week cluster bootstrap:
- 4000 resamples;
- seed `20260823`;
- primary Confirmation serial mean R;
- routed minus causal baseline weekly mean-R difference;
- same-signal delayed minus earlier-entry timing difference (diagnostic).

## Frozen gates

Primary = Confirmation / MICRO_REACCEL / 1.5R / serial.

- `G0_DATA_CAUSALITY`: canonical SHA valid, Bid/Ask present, holdout sealed, contiguous-bar checks pass.
- `G1_POWER`: Confirmation serial trades >= 300 and >= 3 trades/week.
- `G2_CONFIRMATION_EV`: EV > 0 and PF > 1.0.
- `G3_WEEK_CLUSTER_CI`: lower 95% weekly cluster CI for mean R > 0.
- `G4_SPLIT_TRANSFER`: Discovery and Confirmation primary EV both > 0.
- `G5_2R_SURVIVAL`: Confirmation 2R EV >= 0.
- `G6_DIRECTION_BREADTH`: Confirmation BUY EV > 0 and SELL EV > 0.
- `G7_PROP_DD_PROXY`: max DD <= 20R and worst day > -16R.
- `G8_COST_STRESS`: Confirmation 1.5R EV remains > 0 under extra $0.10 price-equivalent stress.
- `G9_REACCEL_GATE_LIFT`: MICRO_REACCEL EV > causal DIGESTION_BASELINE EV and lower 95% weekly routed-minus-baseline CI > 0.
- `G10_NO_OLD_LEVEL_DEPENDENCE`: primary trigger forms before any acceptance degradation by construction; violations = 0.

## Verdicts

- `EXECUTABLE_INTERNAL_REACCELERATION_EDGE`: all G0..G10 pass.
- `REACCEL_POSITIVE_BUT_NOT_PROP_READY`: G2/G3/G4 pass but one or more breadth/DD/stress/power gates fail.
- `REACCEL_SELECTS_EDGE_BUT_WAITING_TOO_LATE`: same-signal early-entry diagnostic is positive while actual MICRO_REACCEL entry fails G2.
- `DIGESTION_EDGE_REACCEL_NOT_INCREMENTAL`: causal DIGESTION_BASELINE positive but G9 fails.
- `NO_INTERNAL_REACCELERATION_EXECUTABLE_EDGE`: G2 fails and no positive transferable economics.
- `INVALID_DATA_CAUSALITY`: G0 fails.

No automatic holdout opening or live/EA allocation.

## Anti-overfit

No post-result tuning of:
- p_accept threshold 0.75;
- accepted-side degradation +0.05 ATR;
- digestion state set;
- first-digestion-only rule;
- 10-minute reacceleration window;
- +0.05 ATR micro-break;
- +0.03 ATR directional body;
- +0.10 ATR accepted-side close;
- 0.50 ATR stop;
- 1.5R/2R targets;
- 60-minute hold;
- commission/stress;
- BUY/SELL, level, time, session, volatility, or news subsets.

Any change requires a new preregistered LAB.
