# GC_XAU_LARGE_MOVE_TAIL_PRECURSOR_AUDIT_LAB004B_PREREG

Status: PREREGISTERED_TAIL_EVENT_AUDIT_NOT_OOS

Purpose: repeat LAB004 only on genuinely large XAU tail moves after observing that +/-1 ATR within 5m was too common.

Frozen large-move thresholds: +/-2.0 ATR and +/-3.0 ATR first passage within 5 minutes. Each threshold is reported separately; no threshold winner is selected.

De-cluster 5 minutes. Report ALL and QUIET_START where prior 30s absolute XAU move <=0.25 ATR.

Use the exact same GC precursor definitions and deterministic controls as LAB004: delta_flip, repeated_failed_attack, and all 1/2/5/10/30/60s extreme/stall/trapped/chase states.

Primary question: do delta_flip and repeated_failed_attack remain enriched before 2-3 ATR tail moves in TRAIN, VALID, and descriptive POST_CHECK?

No trading/execution optimization.
