# BTC_M15_CONTEXT_M5_MULTI_EVENT_EXPANSION_LAB_031 — PREREG

Date: 2026-08-27

## Objective
Expand annual trade count toward 150–300 without abandoning the causal M15 context clock.

## Principle
M15 remains the frozen context/regime clock. M5 is only the event clock. This is not a mechanical M15→M5 rescaling.

## Frozen M15 contexts
Primary context pool is the LAB030 smooth-router context:
1. OLD_PROTECTED_BREAK context
2. COMPRESSION_SELL context
3. LOW_RV_BREAK context

POC_OPPOSED is diagnostic only due prior instability.

An M5 event can be admitted only while one of the primary M15 contexts is active/eligible. The event itself must be causal and based only on completed M5 bars.

## Frozen M5 event families
### F1 MICRO_BREAK_RETEST
- M5 pivot 3-left/3-right, confirmed only after right bars close.
- break = close beyond most recent opposite-side pivot.
- retest = first later M5 bar within 6 bars that straddles broken pivot level.
- direction follows the active M15 context.

### F2 COMPRESSION_RELEASE
- six completed M5 bars form compression.
- compression range <= 0.70 × trailing median six-bar range over prior 48 M5 bars.
- release body/range >= 0.50 and close beyond compression high/low in active M15 context direction.
- retest = first later M5 straddle of release boundary within 6 M5 bars.

### F3 FAILED_RESPONSE_RECLAIM
- within the active M15 context, price first closes through a recent M5 pivot against context direction, then within 6 completed M5 bars closes back through that pivot in context direction.
- entry = first later straddle of reclaimed pivot within 6 M5 bars.

## Execution
- Entry at frozen M5 event level.
- Stop = most recent confirmed M5 pivot on risk side at actual M5 fill.
- Reject if stop is on wrong side or risk distance <=0.
- TP = 2.3R.
- BE at +1R.
- Cost = 0.06R per completed trade.
- Adverse intrabar ordering if SL and TP touched in same M5 bar.
- One position globally in router evaluation.

## De-duplication
- One event per family/context episode until event expires or resulting position exits.
- No overlapping events from the same family are allowed to manufacture frequency.

## Evaluation windows
- 2024 = discovery/calibration because retained exact M5/M1 support is strongest there.
- 2025 = temporal replication.
- 2026 = shadow only; cannot promote.

## Standalone M5 family gates on 2025
- N >= 30
- EV >= +0.08R
- PF >= 1.20
- positive 1.5× cost EV
- H1 and H2 not both negative
- overlap with LAB030 3-stream router <= 50%

## Portfolio target gates (2024–2025 combined)
Candidate router = LAB030 3-stream router + any individually surviving M5 family/families, equal-risk, one global position.

Promotion target:
- 150–300 trades/year preferred; hard minimum 120/year
- EV >= +0.15R
- PF >= 1.35
- MaxDD <= 10R
- >=60% profitable months
- Recovery Factor >= 2
- worst rolling 3M >= -3R
- 1.5× cost EV > 0

## Research integrity
- No post-result threshold movement in this LAB.
- No side-only promotion learned from the same sample.
- No M5 event family may be redefined after results.
- 2026 is shadow only.
