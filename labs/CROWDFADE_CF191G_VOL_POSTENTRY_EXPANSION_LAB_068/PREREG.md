# LAB068 — CF191G VOLATILITY × POST-ENTRY EXPANSION / DIRECTIONAL PERSISTENCE — PREREGISTRATION

## Purpose

Explain the LAB064 regime shift: in 2026 high entry volatility (P80–100) lost EV/right-tail without a proportional MAE explosion.

Diagnostic only. No entry filter, no risk change, no exit change.

## Frozen CF191g control parity
- 2021–2025: N=5297, SumR=+700.3704107793633
- 2026 Mar–Aug: N=544, SumR=+35.49784078156513

## Entry volatility — frozen from LAB064

`vol_metric = ATR14_M5 / close_M5` at fill.
`vol_percentile_7d` = causal percentile rank versus prior 2016 completed M5 bars, current bar excluded.

Focus regimes:
- MID = P40_60
- HIGH = P80_100

All five LAB064 buckets are still reported.

## Early post-entry window

Use exactly the first 15 completed 1m bars AFTER the canonical fill.
All early-state features become known only at t+15m.

### Expansion
`expansion15_atr = trade_side * (close_15m - entry_price) / entry_ATR`

### Directional efficiency
`eff15 = trade_side * (close_15m - entry_price) / sum(abs(1m close_t - previous_close))`

`eff15` is signed and bounded approximately in [-1,+1].

### Directional persistence
`persist15 = fraction of the 15 one-minute close-to-close changes whose sign matches trade_side`

## Frozen early-state labels

Natural thresholds, preregistered:
- EXPANSION_PERSISTENT: expansion15_atr >= +0.50 AND eff15 >= +0.25 AND persist15 >= 0.60
- FAILED_EARLY: expansion15_atr <= 0 OR eff15 <= 0
- MIXED: everything else

No threshold search inside LAB068.

## Post-15m outcomes

To avoid using the same first-15m move as both predictor and outcome, report outcomes after the early window:
- ret15_to_30_atr
- ret15_to_60_atr
- ret15_to_120_atr
- post15_MFE_to_60_atr measured from the 15m close
- post15_MAE_to_60_atr measured from the 15m close
- frozen final trade R
- frozen right-tail R >= +1.5

## Primary questions

### A. Why is 2026 high-vol weak?
Compare HIGH vs MID separately in 2021–2025 and 2026:
- mean expansion15_atr
- mean eff15
- mean persist15
- EXPANSION_PERSISTENT share
- FAILED_EARLY share

Primary regime-shift hypothesis:
- 2026 HIGH has LOWER expansion/persistence and LOWER EXPANSION_PERSISTENT share than 2026 MID;
- this penalty is materially larger than the historical HIGH-vs-MID difference.

### B. Is the high-vol penalty concentrated in failed early expansion?
Within HIGH volatility separately for each period compare:
- EXPANSION_PERSISTENT
- FAILED_EARLY
- MIXED

Expected ordering:
- EXPANSION_PERSISTENT has higher final EV/PF, higher post15 MFE, lower post15 MAE than FAILED_EARLY.

### C. Does high volatility itself remain harmful after early-state stratification?
Compare HIGH vs MID inside the SAME early-state label.
If HIGH and MID are similar once early state is fixed, volatility is context and the actionable mechanism is post-entry expansion failure, not high ATR itself.

## Guardrails

Diagnostic only.
No stateful exit/filter in LAB068.
No new thresholds after results.
Any management action requires a separate preregistered LAB.
BTCUSDT only; 2026 Mar–Aug remains reused shadow/stress, not pristine OOS.