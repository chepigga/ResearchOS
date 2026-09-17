# GC_SHORT_FAILED_RECLAIM_DISCOVERY_LAB_001 — PREREG

Date: 2026-09-17
Scope: separate GC->XAU SHORT research lineage. Historical bounded discovery only; NOT independent OOS and NOT a production rule.

## Question
Does an extreme seller-driven GC breakdown become a more reliable SHORT continuation event when the market subsequently attempts to reclaim the broken level but closes back below it with negative order flow?

This explicitly tests a non-mirror mechanism:

`SELLER BREAKDOWN -> RECOVERY ATTEMPT -> FAILED RECLAIM -> SHORT`

No XAU entry/SL/TP tuning is allowed in this LAB. We first require a GC directional edge. If the GC mechanism fails, it is not transferred to XAU.

## Frozen source / construction
Reuse the existing `GC_M1_ORDERFLOW_EDGE_DISCOVERY_003` causal M1 construction and frozen source archives.

AMP archive SHA256:
`81d675597368a9f6c78eee726ed547737366ffd8d8e54aa976bce50111db752b`

Rithmic archive SHA256:
`b12465a783f36aac41b82a9f2a5c4e74bd2dcf7024ffc3636e8c41a8fd01e803`

All rolling references are shifted by one completed bar. Dual AMP aggressor flags remain excluded.

## Primary setup — FAILED_RECLAIM_SHORT_001

### Breakdown bar B
A completed GC M1 bar must satisfy all of:
1. `a_sell = delta_frac <= prior240 Q10(delta_frac)` AND `sell_vol >= prior240 Q75(sell_vol)`.
2. `low <= prior20_low`.
3. `close < prior20_low` — actual close acceptance below the old low, not only a sweep.
4. `close_pos <= 0.25`.
5. `body_atr < 0`.

Freeze `L = B.prior20_low`.

### Confirmation window
Look only at the next two completed M1 bars after B. The FIRST bar C satisfying all conditions confirms the setup:
1. `high >= L` — causal recovery/reclaim attempt reached the broken level.
2. `close < L` — reclaim failed by bar close.
3. `delta_frac < 0` — sellers again dominate trade flow on the confirmation bar.

No later bar may be substituted if an earlier bar already qualifies.

### Entry clock
The setup becomes actionable only after C is fully completed. Entry reference is the OPEN of the immediately following clock-contiguous GC M1 bar.

This guarantees that B, C, and all confirmation features are known before entry.

## Reference comparator — MIRROR_BREAKDOWN_SHORT_REF
Same Breakdown bar B, but entry occurs at the immediately following M1 open without waiting for failed-reclaim confirmation. This is diagnostic only and is not eligible for promotion in LAB001.

## Outcomes
SHORT normalized return, positive=favorable:

`R_h_ATR = (entry_price - future_close_h) / ATR14_at_confirmation`

Primary horizons: 5m, 15m, 30m after actionable entry.

No stops, targets, XAU transfer, or transaction-cost optimization in this discovery LAB.

## Frozen time partitions
Use the same discovery clocks as GC_M1_ORDERFLOW_EDGE_DISCOVERY_003:
- TRAIN: signal/confirmation time < 2026-08-20 00:00 UTC
- VALID: 2026-08-20 00:00 <= time < 2026-09-06 22:00 UTC
- LATE_CHECK: 2026-09-06 22:00 <= time <= 2026-09-11 12:46 UTC
- POST_CHECK: later AMP extension; descriptive only.

Rithmic is the historical discovery chronology. AMP same-clock overlap is feed-parity / reconstruction evidence, not independent market OOS.

## Primary gates
`FAILED_RECLAIM_SHORT_001` is a historical discovery candidate only if ALL are true:
1. Rithmic total confirmed N >= 30.
2. Rithmic VALID N >= 8.
3. Rithmic VALID 15m EV > 0.
4. Rithmic VALID 30m EV > 0.
5. Rithmic LATE_CHECK has N >= 3 and 15m EV > 0.
6. Rithmic LATE_CHECK 30m EV > 0.
7. AMP overlap VALID 15m EV > 0.
8. AMP overlap VALID 30m EV > 0.
9. Full-history Rithmic 15m EV > 0.
10. Full-history Rithmic 30m EV > 0.

These thresholds are frozen before seeing LAB001 results. No threshold/depth/window sweep is allowed in this LAB.

## Interpretation
PASS means only: `HISTORICAL_SHORT_MECHANISM_CANDIDATE_PASS_NOT_OOS` and permits a separate GC->FTMO XAU transfer LAB.

FAIL means this exact failed-reclaim definition is rejected. A later LAB may test a different preregistered bearish mechanism (for example absorption/exhaustion, recovery-failure duration, or post-break acceptance), but LAB001 thresholds are not adjusted after result visibility.
