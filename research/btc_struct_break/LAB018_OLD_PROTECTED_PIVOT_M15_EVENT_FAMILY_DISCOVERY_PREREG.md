# OLD_PROTECTED_PIVOT_M15_EVENT_FAMILY_DISCOVERY_LAB_018 — preregistration

Date: 2026-08-25
Status: PREREGISTERED BEFORE RESULTS

## Goal
Search for additional M15 event families inside the same old-protected-pivot structural context, without ML and without optimizing PnL thresholds.

## Common frozen context
For a proposed directional entry at M15 bar t:
- stop anchor = latest confirmed opposite-side M15 pivot 5-5 available causally at entry;
- pivot age >= 22 M15 bars;
- pivot remains unviolated after confirmation and before entry;
- riskATR = abs(entry - stop) / ATR14(entry) > 3.72;
- 2026 excluded from verdict;
- DEV = 2019-2022; VAL = 2023-2025;
- cost = 0.06R round-turn;
- management = adverse-first same-bar ordering, BE after +1R, TP 2.3R, max hold 2000 M15 bars;
- one active position per family at a time.

## Event families
A. BREAK_RETEST_CONTROL
Exact LAB017 / LAB016 selected M15 lineage. This is the positive control and is not rediscovered.

B. COMPRESSION_RELEASE
- prior 6 closed M15 bars before release;
- compression range <= 0.70 * median 6-bar range over the previous 48 completed bars;
- release close breaks the 6-bar compression extreme in trade direction;
- release body >= 0.50 of its full bar range;
- entry = first retest of broken compression extreme within next 8 M15 bars.

C. FAILED_RESPONSE_RELEASE
- within the previous 12 closed M15 bars, price makes an opposing 3-bar response away from a local directional extreme;
- response fails to close beyond the nearest confirmed M15 pivot-3 against the intended direction;
- subsequent close breaks the response origin / local directional extreme in intended direction;
- entry = first retest of that release level within next 8 M15 bars.

D. TWO_LEG_CORRECTION_RELEASE
- after a directional local impulse, two causal opposing pivot-3 correction legs are present: correction pivot A, directional bounce pivot B, correction pivot C;
- C does not violate the common protected pivot and does not exceed A in adverse direction;
- release close breaks B in intended direction;
- entry = first retest of B within next 8 M15 bars.

## Discovery controls
- No threshold tuning after seeing DEV or VAL PnL.
- All frozen thresholds above are structural heuristics fixed before results.
- Report each family independently on DEV and VAL.
- Report BUY/SELL, yearly EV/PF, 1.25x and 1.5x cost stress, MaxDD, and frequency.
- Compute event overlap with BREAK_RETEST_CONTROL and pairwise overlap among new families using a +/- 8 M15 bar window around entry.
- A family is interesting only if VAL EV > 0, PF > 1.15, >=2/3 positive VAL years, and its positive result is not explained almost entirely by >60% overlap with the control.
- This is a discovery lab; passing a gate creates a replication candidate, not production approval.
