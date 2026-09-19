# GC_XAU_REV2_Q65_FROZEN_OOS_BOOTSTRAP_MONTECARLO_LOPO_COST_LAB011_PREREG

Status: PREREGISTERED_FROZEN_VALIDATION_NOT_PRISTINE_OOS

Purpose: validate the frozen LAB010 Q65 candidate with exact FTMO metals commission conversion, historical holdout, bootstrap, Monte Carlo sequence resampling, and leave-one-period-out diagnostics.

## Frozen candidate
- Signal: LAB009C Q65 intersection: 5s post_signed_impulse_atr >= frozen TRAIN Q65 AND 30s post_aligned_volume >= frozen TRAIN Q65.
- Entry: REV2 +30s, first executable XAU quote.
- Geometry: SL 2.25 ATR, TP 4.50 ATR (2.0R nominal).
- Timeout: 300s.
- No further threshold or geometry tuning.

## Exact CFD commission conversion
- FTMO Metals CFD commission: 0.0007% of traded notional per side.
- XAUUSD contract size: 100 oz per 1 lot.
- For USD account and USD profit currency, round-turn commission in R per trade:
  commission_R = [2 * 0.000007 * entry_price * contract_size * lots] / [SL_ATR * ATR * contract_size * lots]
  = 0.000014 * entry_price / (SL_ATR * ATR).
- Spread is already embedded in executable Bid/Ask.
- Currency conversion adjustment is not applied for XAUUSD on a USD account because profit currency = account currency.
- Slippage is not inferable exactly from historical quote ticks; separate stress layers remain diagnostic.

## Validation
- TRAIN / VALID / POST_CHECK using frozen candidate.
- POST_CHECK is historical holdout only, NOT pristine OOS because prior labs inspected it.
- Bootstrap 10000 IID trade resamples of exact-cost net R.
- Block bootstrap 10000 samples using chronological blocks of 3 trades.
- Monte Carlo 10000 random permutations of the exact trade ledger to measure path-dependent MaxDD/streak.
- Leave-one-calendar-week-out: recompute aggregate EV/PF after removing each ISO week.
- Leave-one-split-out: TRAIN-only, VALID-only, POST-only and aggregate minus each split.

## Metrics
- N, EV R, PF, CumR, WR, MaxDD R, MaxDD% at 0.25% risk, max consecutive losses.
- bootstrap P(EV>0), 95% CI EV.
- Monte Carlo median/p95/p99 MaxDD R and max losing streak.
- LOPO minimum remaining EV and minimum remaining PF.

No production promotion from LAB011; true independent OOS requires fresh future data.