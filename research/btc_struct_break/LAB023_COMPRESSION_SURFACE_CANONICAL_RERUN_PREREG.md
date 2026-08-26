# LAB023 — COMPRESSION SURFACE CANONICAL RERUN

Date: 2026-08-26
Status: PREREGISTERED BEFORE CALCULATION

## Objective
Rerun the full M15 compression surface from scratch with complete provenance, replacing the non-reproducible LAB020 compression surface lineage.

## Canonical event definition
Use the frozen LAB018 compression definition exactly:
- compression window = six completed M15 bars before release;
- compression range = max(high)-min(low) over those six bars;
- baseline = median of all rolling six-bar ranges fully contained in the prior 48 bars;
- compression iff range <= 0.70 * baseline;
- BUY release: close above compression high; SELL release: close below compression low;
- release body/full range >= 0.50;
- retest starts on the next bar and remains valid for 8 M15 bars;
- retest level = compression high for BUY, compression low for SELL;
- event de-duplication and one active position use the pooled BUY+SELL family state.

## Pivot/risk context at fill
- latest confirmed opposite-side pivot-5 available before fill;
- pivot age measured in M15 bars from pivot center to fill;
- unviolated means pivot level has not been traded through after pivot confirmation and before fill;
- riskATR = abs(entry-stop)/ATR14(fill);
- stop on correct side of entry;
- TP 2.3R;
- BE after +1R;
- adverse same-bar stop/TP ordering;
- cost 0.06R.

## Frozen surface bins
Pivot age:
- <10
- 10–15
- 16–21
- 22–31
- 32+

riskATR:
- <2.5
- 2.5–3.0
- 3.0–3.72
- 3.72–5.0
- >5.0

Primary surface is SELL-only outcome reporting while preserving the pooled BUY+SELL queue/blocking state.

## Data split
- DEV: 2019–2022
- VAL: 2023–2025
- 2026: shadow only, excluded from verdict.

## Mandatory provenance artifacts
Persist before any interpretation:
1. all raw compression release events with side and release index/time;
2. retest/fill outcome for every event;
3. pivot index/age/unviolated/riskATR at fill;
4. exact rejection reason for non-trades;
5. pooled queue state and blocker reason;
6. all accepted trades with entry/stop/target/exit/R;
7. cell membership for every accepted SELL trade;
8. per-cell trade IDs for all 25 surface cells;
9. compute script used to produce the surface.

## Discovery discipline
This is a new discovery rerun, not validation of LAB020.
Do not choose or tune cell boundaries after seeing PnL.
The old LAB020 island (age 16–21, riskATR 2.5–3.0) may be compared descriptively but is not privileged in selection.

## Reporting
For each cell report DEV/VAL N, EV, PF, MaxDD, yearly EV, 1.5x cost EV, bootstrap CI, and 2026 shadow.
Also report overlap and portfolio impact only after all provenance files are written.
