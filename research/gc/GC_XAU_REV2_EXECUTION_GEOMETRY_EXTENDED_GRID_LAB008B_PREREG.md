# GC_XAU_REV2_EXECUTION_GEOMETRY_EXTENDED_GRID_LAB008B_PREREG

Status: PREREGISTERED_EXTENDED_GEOMETRY_BOUNDARY_AUDIT

Purpose: extend LAB008 because the least-negative cells sat on the maximum tested SL boundary (2.0 ATR). Map wider movement limits without selecting a production winner.

Frozen signal/execution: identical to LAB008.

Extended grid:
- SL ATR 0.25 to 4.00, step 0.25
- TP ATR 0.50 to 8.00, step 0.25
- only TP/SL >=1.50
- timeout 5 minutes

Primary question:
- Does EV turn positive beyond 2 ATR stop distance, or does performance merely asymptote toward the raw fixed-hold REV2 result?
- Identify the SL/TP boundary after which widening no longer improves worst-split EV.

No production promotion. Spread embedded; commission/slippage excluded in this geometry boundary map.