# GC_SHORT_CHRIS_AEIF_BUY_FAILURE_LAB_003 — PREREG

**Scope:** GC futures order-flow SHORT discovery only. Historical bounded discovery; not OOS; no XAU execution tuning.

## Hypothesis

A SHORT reversal edge may appear when aggressive BUY effort is extreme near the upper auction, but price impact is weak, followed by a causal bearish confirmation within the next two completed M1 bars.

Mechanism:

`EXTREME BUY EFFORT -> UPPER LOCATION -> WEAK UPWARD RESULT -> BEARISH CONFIRMATION <=2 M1 -> SHORT`

This is the Chris/AEIF effort-vs-result idea, not a mirror of the LONG continuation rule and not a continuation-of-selling rule.

## Frozen seed definition

On completed GC M1 bar t:
- `a_buy = delta_frac >= prior240 Q90 AND buy_vol >= prior240 Q75`;
- upper location: `buy_loc >= prior240 Q75 buy_loc`;
- weak result: causal same-aggressor impact quantile exists and `impact <= prior BUY impact Q20`;
- no use of future bars in seed classification.

## Frozen confirmation

Search only t+1 then t+2, both completed M1 bars.
First bar satisfying all is confirmation:
- bearish body: `close < open`;
- `close < seed_close`;
- `close_pos <= 0.50`.

If neither t+1 nor t+2 confirms, no signal.

Entry = next clock-contiguous M1 open after confirmation. Therefore earliest entry is t+2 open and latest is t+3 open. No intrabar confirmation or close-fill.

## Evaluation

SHORT forward return normalized by seed ATR14 at 15m and 30m after entry.

Frozen periods inherited from GC discovery lineage:
- TRAIN: before 2026-08-20 00:00 UTC
- VALID: 2026-08-20 00:00 -> 2026-09-06 22:00 UTC
- LATE_CHECK: 2026-09-06 22:00 -> 2026-09-11 12:46 UTC
- POST_CHECK: after 2026-09-11 12:46 UTC (AMP extension only where available)

## Frozen gates

Candidate may advance to XAU transfer research only if all applicable gates pass:
1. Rithmic FULL N15 >= 25.
2. Rithmic TRAIN N15 >= 10.
3. Rithmic VALID N15 >= 8.
4. Rithmic TRAIN EV15 > 0.
5. Rithmic VALID EV15 > 0.
6. Rithmic VALID EV30 > 0.
7. Rithmic FULL EV15 > 0.
8. Rithmic FULL EV30 > 0.
9. If Rithmic LATE N15 >= 3, LATE EV15 > 0 and EV30 > 0.
10. AMP VALID EV15 > 0 and EV30 > 0.
11. No post-hoc threshold adjustment if the exact rule fails.

If gates fail, reject this exact Chris/AEIF definition and preregister a genuinely different mechanism rather than tuning these thresholds.
