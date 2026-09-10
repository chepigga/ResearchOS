# CONTEXT_REVERSAL_ORDERED_EVENT_CHAIN_AND_STAGE_STATE_MACHINE_LAB_014

**Verdict: WEAK_ORDERED_STAGE_SIGNAL**

- Parent parity: **PASS** {'PULLBACK': 7641, 'EXPANSION': 4568, 'RANGE': 2184, 'REVERSAL': 29}
- Reversal score reconstruction: **PASS**
- Causality: **PASS** changed=[]
- Frozen Reversal transitions: **9**
- Chain completions: **837**
- Chain transition recall: **0/9 = 0.000**
- Chain precision 0-3 bars: **0.001** vs Stage-A **0.005**, ratio **0.22x**
- Median lead among converted chains: **0.00 H4 bars**
- Calendar years with chain completions: **7**
- Gates: {'G1_parent_parity': True, 'G2_score_reconstruction': True, 'G3_causality': True, 'G4_recall_ge_4of9': False, 'G5_precision_ge_5pct': False, 'G6_precision_ratio_ge_2x': False, 'G7_median_lead_le2': True, 'G8_years_ge5': True}

No frozen Context score weights or state-machine constants were changed. Structural failure is the preregistered causal proxy: BOS against available directional bias.
