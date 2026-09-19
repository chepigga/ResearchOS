# GC_XAU_REV2_Q60_Q65_FROZEN_EXECUTION_GEOMETRY_EQUITY_COST_LAB010_PREREG

Status: PREREGISTERED_FROZEN_CANDIDATE_EXECUTION_AUDIT_NOT_OOS

Purpose: freeze the two LAB009C candidates (Q60 and Q65 impulse+aligned-volume intersections) and audit executable XAU geometry, chronological equity/DD, losing streaks, and cost sensitivity.

## Frozen candidates
- Q60: 5s post_signed_impulse_atr >= LAB009C TRAIN Q60 AND 30s post_aligned_volume >= LAB009C TRAIN Q60.
- Q65: same construction using TRAIN Q65 thresholds.
- Thresholds loaded from LAB009C output; no retuning in LAB010.

## Causal entry clock
- REV2 + 30 seconds, because aligned-volume confirmation uses the first 30s after REV2.
- First executable FTMO XAU quote at/after confirmation clock.
- LONG entry Ask / exit Bid; SHORT entry Bid / exit Ask.
- Spread embedded in raw quotes.

## Geometry grid
- SL ATR: 0.50 to 4.00 step 0.25.
- TP ATR: 0.75 to 8.00 step 0.25.
- keep only TP/SL >= 1.50.
- hard timeout 300s after entry.
- if neither SL nor TP hits, exit at last executable quote before timeout.

## Cost model
- Base raw execution: spread embedded, no extra commission/slippage.
- Stress costs deducted from every trade outcome in R: 0.02R, 0.05R, 0.10R, 0.15R.
- These are stress layers, not a claim about exact live FTMO commission; exact commission conversion depends on live symbol contract and lot sizing.

## Report per candidate / geometry / cost / split
- N, EV R, PF, WR, TP/SL/timeout rates, cumulative R.
- chronological max drawdown R.
- max consecutive losses.
- at 0.25% risk per trade: maxDD% = maxDD_R * 0.25%.

## Robust surface definition
- TRAIN EV>0 and VALID EV>0 at base cost.
- TRAIN PF>=1.10 and VALID PF>=1.10 at base cost.
- positive TRAIN+VALID at 0.05R stress.
- geometry neighborhood support: at least 2 adjacent positive TRAIN+VALID cells.

## Candidate-level robustness
- report plateaus, not a single best cell.
- POST_CHECK is descriptive only.
- no production promotion from LAB010.