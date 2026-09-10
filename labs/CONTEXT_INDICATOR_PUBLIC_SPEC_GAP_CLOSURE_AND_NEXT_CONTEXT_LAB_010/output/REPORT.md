# CONTEXT_INDICATOR_PUBLIC_SPEC_GAP_CLOSURE_AND_NEXT_CONTEXT_LAB_010

**Verdict: PUBLIC_SPEC_COMPONENT_CLOSURE_COMPLETE_WITH_PROPRIETARY_PROXIES**

- Checklist: 29/29 implemented; exact **13**, proxy **16**, missing **0**.
- Causality: **PASS**; changed=[]
- D1 closed clock: **PASS**
- Public TF map 4/4: **PASS**
- State-machine mismatches: **0**
- Next Context coverage: **100.000%**; pre-transition match **0.930**, baseline **0.767**, lift **+0.164**
- Reversal state count: LAB009 **41** → LAB010 **29** (descriptive only; no frequency target).

## Regimes
- PULLBACK: 7641
- EXPANSION: 4568
- RANGE: 2184
- REVERSAL: 29

## Exact components
- EMA20_50_200_structure
- daily_inside_bar
- range24_compression
- RSI14_EMA9_WMA45_rhythm
- ADX14_level
- ADX_decay
- relative_volume_20bar_average
- three_bar_smoothing
- public_TF_mapping_M1_M15_M5_H1_M15_H4_H1_D1
- closed_HTF_availability_clock
- Current_Context_output
- Next_Context_runner_up_output
- direction_compatibility_layer

## Proprietary/undisclosed proxies
- EMA_slope
- ATR14_relative_volatility
- D1_HTF_bias
- swing_pivots
- BOS
- liquidity_sweep_failed_sweep
- session_contribution
- Expansion_score
- Pullback_score
- Reversal_score
- Range_score
- current_mode_inertia_bonus
- minimum_hold
- switch_gap
- low_vol_wider_gap
- high_vol_shorter_hold