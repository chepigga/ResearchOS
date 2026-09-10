# CONTEXT_REVERSAL_ORDERED_EVENT_CHAIN_AND_STAGE_STATE_MACHINE_LAB_014 — PREREG

## Objective
Audit whether Reversal behaves more like an ordered causal event chain than a same-bar weighted state, without changing any frozen LAB010 score weights or state-machine constants.

## Frozen parent
- Parent logic/data: LAB010/LAB013 BTCUSDT H4 context stream, 2020-01 through 2026-07.
- Parent expected regime counts: PULLBACK 7641 / EXPANSION 4568 / RANGE 2184 / REVERSAL 29.
- Parent Reversal score must reconstruct exactly from the six frozen components.

## Ordered stage definitions (frozen before outcomes)
Stage A — SETUP. Fires when either:
- swing_sweep == true, OR
- rejection_wick >= 0.45.

Stage B — RESPONSE. Fires when any of:
- RSI turn (same LAB010 definition),
- RSI EMA9/WMA45 rhythm turn,
- ADX14 decay.

Stage C — CONFIRMATION. Fires when either:
- EMA20 cross, OR
- structural failure proxy: BOS against the currently available directional bias (BULL + bos_dn, or BEAR + bos_up).

All events are causal and only use information available at the H4 bar close.

## Chain machine
A valid ordered chain requires A -> B -> C in chronological order. Same-bar advancement is allowed only from the stage already active entering that bar; a single bar cannot retroactively satisfy all three stages at once.

Fixed timeouts:
- A may wait up to 2 subsequent H4 bars for B.
- After B, C may arrive within the next 2 H4 bars.
- If timeout expires, reset to IDLE.
- A new A while waiting for B refreshes the A timestamp but does not skip B.
- A new A while waiting for C does not reset the chain.
- Completed C emits one CHAIN_COMPLETE event and resets to IDLE on the next bar.

## Primary comparisons
1. Frozen Reversal transition recall: proportion of the 9 clean parent transitions preceded by CHAIN_COMPLETE in the prior 0-3 H4 bars.
2. Chain precision: proportion of CHAIN_COMPLETE events followed by parent Current Context=REVERSAL within 0-3 H4 bars.
3. Enrichment versus Stage-A-only candidates: conversion within 0-3 bars after A compared with conversion after CHAIN_COMPLETE.
4. Lead time distribution from CHAIN_COMPLETE to parent Reversal transition.
5. Year stability of chain completion and conversions.
6. Stage attrition A -> B -> C and time-to-next-stage distributions.

## Negative controls
- unordered 3-bar union candidate from LAB013 (descriptive comparator only; no threshold changes),
- Stage-A-only candidate,
- Stage-B-only candidate,
- Stage-C-only candidate.

## Causality/parity gates
- Parent regime-count parity must match exactly.
- Frozen Reversal-score reconstruction must match exactly.
- Future-data perturbation must leave all stage/chain outputs unchanged for bars whose H4 close is <= cutoff.

## Preregistered support gates
`ORDERED_STAGE_MACHINE_SUPPORTED` requires ALL:
- G1 parent parity PASS,
- G2 Reversal score reconstruction PASS,
- G3 causality PASS,
- G4 transition recall >= 4/9,
- G5 chain precision >= 5% for Current Context=REVERSAL within 0-3 bars,
- G6 chain precision / Stage-A-only precision >= 2.0x,
- G7 median lead time <= 2 H4 bars among converted chain events,
- G8 chain completions occur in >= 5 calendar years.

If G1-G3 pass and 5-7 of G4-G8 pass: `WEAK_ORDERED_STAGE_SIGNAL`.
If G1-G3 pass and <=4 of G4-G8 pass: `ORDERED_STAGE_MACHINE_NOT_SUPPORTED`.
No frequency target is used. No weights or state-machine constants may be altered after outcomes.

## Interpretation
This is an indicator-architecture audit, not a trading-edge test. A positive result authorizes a later separate LAB to test replacing/augmenting Reversal score aggregation. A negative result leaves the frozen same-bar Reversal architecture unchanged.