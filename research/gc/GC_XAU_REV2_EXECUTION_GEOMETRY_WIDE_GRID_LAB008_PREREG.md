# GC_XAU_REV2_EXECUTION_GEOMETRY_WIDE_GRID_LAB008_PREREG

Status: PREREGISTERED_WIDE_GEOMETRY_SURFACE_NOT_PRODUCTION_OPTIMIZATION

Purpose: map the executable SL/TP geometry of the frozen LAB007D REV2 signal across a wide ATR grid to identify movement boundaries and robust plateaus, not a single best parameter.

## Frozen signal
- exact LAB007D DOMINANCE_REVERSAL REV2 clocks
- direction = reversal direction at REV2
- no signal retuning, no additional filters

## Execution
- FTMO XAU raw quote ticks
- first executable quote at or immediately after REV2 t0
- LONG entry at Ask, exits evaluated on Bid
- SHORT entry at Bid, exits evaluated on Ask
- spread embedded
- ATR = prior completed XAU M1 ATR14
- hard timeout = REV2 + 300s; if neither SL nor TP hits, exit at executable quote and realize signed move in R using that row's SL distance

## Wide grid
- SL ATR: 0.25,0.50,0.75,1.00,1.25,1.50,1.75,2.00
- TP ATR: 0.50 through 4.00 in 0.25 increments
- only cells with TP/SL >=1.50

## Report per TRAIN / VALID / POST_CHECK / FULL
- N
- EV in R
- PF
- win rate
- TP rate
- SL rate
- timeout rate
- cumulative R
- max drawdown in R using chronological trade sequence
- max consecutive losses

## Robustness views
- cells positive EV in TRAIN and VALID
- cells PF>=1.10 in TRAIN and VALID
- cells positive EV in TRAIN, VALID, and POST_CHECK
- contiguous/neighbor plateau diagnostics across SL/TP surface

No production winner is selected in LAB008. This is a descriptive geometry surface. Any candidate geometry must be frozen and audited separately.