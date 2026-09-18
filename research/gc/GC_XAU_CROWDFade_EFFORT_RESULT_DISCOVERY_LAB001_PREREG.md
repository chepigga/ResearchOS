# GC_XAU_CROWDFade_EFFORT_RESULT_DISCOVERY_LAB001_PREREG

Status: PREREGISTERED_BOUNDED_DISCOVERY_NOT_OOS

Question: can causal COMEX GC order-flow information identify a directional XAUUSD move before the CFD has already expressed that move?

Data: canonical AMP/CQG GCEZ26 explicit-aggressor Aug-Sep 2026 overlap + frozen FTMO-Demo raw Bid/Ask ticks. Clock mapping GC UTC -> FTMO +180m.

Causal clock: completed GC M1 only; earliest XAU action = signal minute close / next minute first executable quote. No future data.

Bounded candidate families: FADE_OPPOSITE_BODY, FADE_Q20, FADE_LOC_Q20, FADE_REJECTION, CHASE_Q80, CHASE_BREAKOUT. No threshold sweep beyond these families.

XAU execution measurement: LONG Ask->Bid; SHORT Bid->Ask; spread embedded; horizons 1/3/5/10/15/30m.

Lead diagnostics: pre_move_atr is XAU move during the GC signal minute in the predicted direction. STRICT_LEAD = pre_move_atr <= 0.00. LOOSE_LEAD = pre_move_atr <= +0.25. These are diagnostics, not optimized filters.

TRAIN < 2026-08-20; VALID 2026-08-20 to 2026-09-06 22:00 UTC; POST_CHECK after that and not used for nomination.

Nomination gate: TRAIN N>=12, VALID N>=12, TRAIN/VALID EV5>0 and EV15>0, VALID STRICT_LEAD N>=5 with EV5>0 and EV15>0, VALID median pre_move_atr<=0.25.

Historical bounded discovery only; not OOS certification or production authorization.
