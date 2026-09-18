# GC_XAU_CROWDFade_EFFORT_RESULT_DISCOVERY_LAB001

Status: HISTORICAL_BOUNDED_DISCOVERY_NOT_OOS

Question: can GC futures order flow signal XAU before the CFD has already expressed the predicted move?

| Candidate | Gate | Train N | Train EV5 | Valid N | Valid EV5 | Valid EV15 | StrictLead N | Strict EV5 | Strict EV15 | Valid median pre-move | Post EV15 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| FADE_OPPOSITE_BODY | FAIL | 90 | -0.047 | 96 | -0.628 | -0.257 | 16 | -0.939 | -0.453 | +0.195 | -0.691 |
| FADE_Q20 | FAIL | 153 | -0.221 | 183 | -0.295 | -0.078 | 95 | -0.125 | -0.105 | -0.006 | -0.211 |
| FADE_LOC_Q20 | FAIL | 31 | -0.400 | 44 | -0.497 | +0.037 | 16 | +0.318 | +0.277 | +0.174 | -0.631 |
| FADE_REJECTION | FAIL | 60 | -0.498 | 61 | -0.566 | -0.396 | 15 | -0.638 | -0.698 | +0.287 | -0.602 |
| CHASE_Q80 | FAIL | 153 | -0.126 | 183 | -0.271 | -0.195 | 0 | NA | NA | +1.729 | -0.004 |
| CHASE_BREAKOUT | FAIL | 192 | -0.109 | 231 | -0.155 | -0.074 | 0 | NA | NA | +1.208 | +0.156 |

Passing: NONE
Nominated: NONE

STRICT_LEAD means XAU had not yet moved in the predicted direction when the completed GC M1 signal became actionable.
LOOSE_LEAD allows up to +0.25 XAU ATR already expressed. Spread is embedded. POST_CHECK was not used for nomination.
This is discovery, not OOS certification or EA authorization.
