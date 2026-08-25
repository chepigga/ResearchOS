# STRUCT_BREAK_LOW_RESET_X_SECOND_BREAK_LAB_013 — preregistration

Date: 2026-08-25
Branch: lab/btc-struct-break-regime-004
Status: FROZEN BEFORE OUTCOMES

## Hypothesis
After a canonical STRUCT_BREAK v002 trade enters frozen LAB008 LOW30 and later recovers to the old entry level, the old setup is reset. A genuinely NEW post-reset structural break, built only from bars that did not exist before the reset, may have better fresh 1.5R hazard than merely re-entering on renewed impulse.

## Population
- Canonical STRUCT_BREAK v002 trades only.
- DEV: 2019-09 through 2022-12.
- VAL: 2023-01 through 2025-12.
- 2026 excluded from verdict.
- Frozen LAB008 LOW30 classifier unchanged.
- Eligible only if LOW30 later recovers/scratches at the old entry.

## Reset
RESET time = first post-LOW recovery/scratch to the old entry level as already reconstructed in LAB009A/B. The scratch bar itself is excluded from all new-structure calculations.

## Primary NEW STRUCTURE clock
M5, causal pivot 3-3.
A pivot is usable only after its right-side 3 bars have closed.
All pivots used by BREAK2 must have pivot timestamps strictly after RESET.

### BUY sequence
1. After RESET, form a confirmed M5 pivot HIGH H2.
2. Then form and confirm a subsequent M5 pivot LOW L2 after H2.
3. BREAK2 = first later M5 close above H2 by at least 0.10 x ATR14(M5), using ATR known at that close.
4. ACCEPTANCE is the BREAK2 close itself; no future bar is used.
5. RETEST window = next 12 M5 bars.
6. ENTRY2 = limit at H2 on the first retest bar whose low touches H2.
7. Fresh STOP2 = L2.
8. Require STOP2 < ENTRY2 and fresh stop distance between 0.30 and 6.0 ATR14(M5) at entry.

### SELL sequence
Symmetric:
1. confirmed M5 pivot LOW L2;
2. subsequent confirmed pivot HIGH H2;
3. BREAK2 close below L2 by >= 0.10 x ATR14(M5);
4. retest within next 12 M5 bars;
5. ENTRY2 limit at L2;
6. STOP2 = H2;
7. require valid direction and 0.30–6.0 ATR stop distance.

Only the first valid BREAK2/RETEST/ENTRY2 after each RESET is allowed. Search horizon after RESET = 12 hours. No second attempt if the first valid BREAK2 fails to retest.

## Fresh trade payoff
Primary: TP2 = +1.5R from ENTRY2, SL2 = -1R at fresh structural STOP2.
Secondary: TP2 = +2.0R, same stop.
No BE, trailing, or partial exits in primary.
Maximum holding horizon = 24h; unresolved trades exit at the last close and are marked TIME.
Round-turn cost = 0.06R.
If SL and TP are both touched in one M5 bar, adverse ordering is assumed (SL first). Exact M1 replication for 2024–2025 will check ordering.

## Comparators
1. SECOND_BREAK fresh 1.5R hazard/EV.
2. The same eligible events' original FIRST entry evaluated as a simple fresh 1.5R/-1R trade with its original structural stop, no BE, same 0.06R cost and 24h horizon.
3. Unconditional canonical FIRST entries at 1.5R as descriptive context only.

## Primary promotion gates
All must pass on VAL:
- second-break N >= 40;
- EV >= +0.10R;
- bootstrap 95% CI lower bound > 0;
- resolved TP-before-SL probability above cost-adjusted fair probability for 1.5R;
- positive EV in at least 2 of 3 VAL years;
- paired SECOND_BREAK minus same-event FIRST_ENTRY mean improvement > 0, with bootstrap 95% CI lower bound > 0.

## Diagnostics allowed but cannot promote
- M15 replication using the same causal pivot3 -> pullback pivot -> 0.10 ATR break -> 12-bar retest logic.
- BUY/SELL split.
- timing from RESET to structure, break, and retest.
- stop distance in ATR.
- outcome decomposition by first-trade eventual canonical outcome.
- no threshold optimization on VAL.

## Falsification rule
If primary gates fail, do not tune pivot width, acceptance buffer, retest window, stop-distance bounds, RR, or reset definition on VAL. Any altered geometry becomes a new LAB.
