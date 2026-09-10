# CONTEXT_INDICATOR_PUBLIC_SPEC_COMPONENT_PARITY_AND_STATE_TRANSITION_AUDIT_LAB_009

**Verdict: FUNCTIONAL_PROXY_WITH_PUBLIC_SPEC_GAPS**

- Public checklist: **29** items — exact **8**, proxy **14**, missing **7**.
- Causality: **PASS**; pre-cutoff changed columns: []
- Closed H4 clock: **PASS**
- Four-score + four-regime activation: **PASS**
- State-machine exact reconstruction: **PASS**, mismatches=0
- Next-context runner-up before transitions: N=858, match=0.931, unconditional-old-state baseline=0.734, lift=+0.197

## Exact public items
- PASS — EMA20_50_200_structure
- PASS — range24_compression
- PASS — ADX14_level
- PASS — ADX_decay
- PASS — three_bar_smoothing
- PASS — closed_HTF_availability_clock
- PASS — Current_Context_output
- PASS — direction_compatibility_layer

## Implemented only as proxies
- PROXY — EMA_slope
- PROXY — ATR14_relative_volatility
- PROXY — BOS
- PROXY — liquidity_sweep_failed_sweep
- PROXY — relative_volume_20bar_average
- PROXY — Expansion_score
- PROXY — Pullback_score
- PROXY — Reversal_score
- PROXY — Range_score
- PROXY — current_mode_inertia_bonus
- PROXY — minimum_hold
- PROXY — switch_gap
- PROXY — low_vol_wider_gap
- PROXY — high_vol_shorter_hold

## Missing public items
- GAP — D1_HTF_bias
- GAP — daily_inside_bar
- GAP — swing_pivots
- GAP — RSI14_EMA9_WMA45_rhythm
- GAP — session_contribution
- GAP — public_TF_mapping_M1_M15_M5_H1_M15_H4_H1_D1
- GAP — Next_Context_runner_up_output

## Regime counts
- PULLBACK: 9795
- EXPANSION: 2909
- RANGE: 1677
- REVERSAL: 41