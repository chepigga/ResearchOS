# GC_XAU_CROWDFade_STALL_XAU_DIVERGENCE_AND_5_30S_ENTRY_GATE_LAB004_PREREG

**Status:** PREREGISTERED_BOUNDED_GATE_AUDIT_NOT_OOS

## Frozen parent trigger
Exactly LAB003 30s_FADE_STALL. No GC trigger changes.

## Question
Can the XAU state during the first 5-30 seconds after a frozen GC crowd-stall distinguish real trapped-crowd events from false fades, and can a bounded limit or confirmation entry monetize the information edge?

## Frozen XAU state diagnostics
Measured from trigger-end mid, normalized by prior completed XAU M1 ATR:
- R5 = predicted-direction XAU mid return at +5s
- R10 = at +10s
- R30 = at +30s
- SLOPE_5_30 = R30 - R5

Bounded state families:
1. DIVERGE_EARLY: R5 > 0 and R10 > 0
2. STALL_THEN_GO: R5 <= 0.05 and R30 > R5
3. CROWD_PERSISTS: R5 < 0 and R10 < 0
4. REVERSAL_CONFIRM: R5 <= 0 and R30 > 0

No threshold sweep beyond these fixed definitions.

## Frozen entry variants
A. MARKET_5S: first executable quote at trigger+5s.
B. LIMIT_010_FROM_5S: at trigger+5s, place limit 0.10 ATR toward the crowd; expiry trigger+30s.
C. CONFIRM_010: enter when XAU mid reaches +0.10 ATR predicted-direction from trigger-end, if this occurs by trigger+30s.
D. CONFIRM_AFTER_NEGATIVE: only if XAU first trades <= -0.05 ATR against predicted direction within first 15s, then enter on recovery back through trigger mid before +30s.

All entries evaluated to hard trigger+120s and trigger+300s fixed holds.

## Frozen R:R diagnostics
G1 = SL 0.25 ATR / TP 0.50 ATR
G2 = SL 0.30 ATR / TP 0.45 ATR
First-passage on raw Bid/Ask.

## Discovery split
TRAIN < 2026-08-20
VALID 2026-08-20 through 2026-09-06 22:00 UTC
POST_CHECK after VALID and never used for selection.

## Candidate gate
A state x entry combination is a historical candidate only if:
- TRAIN fills >=10 and VALID fills >=10
- TRAIN and VALID hold120 EV >0
- VALID hold300 EV >=0
- VALID PF >=1.10 on at least one frozen R:R geometry
- POST_CHECK reported but not used to nominate

Historical bounded audit only; not OOS certification and not EA authorization.
