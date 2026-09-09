# CROSS_MARKET_CAUSAL_CONTEXT_DIRECTION_COMPATIBILITY_INTERACTION_LAB_003

**Verdict: MIXED_CROSS_MARKET_DIRECTION_CONTEXT_INTERACTION**

> Preregistered reused-history interaction audit. No live sizing promotion is authorized.

## Frozen test

- `C = (Expansion + Pullback - Reversal - Range) / 200`
- BTC HIGH: `C > 0.525`; XAU HIGH: `C > 0.55`
- Primary: `(HIGH A-O) - (NON_HIGH A-O)`

| Market | N | HIGH A | HIGH O | HIGH premium | NONHIGH premium | Interaction | HP 95% CI | Interaction 95% CI | Time + | LOPO + | Verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| BTC | 327 | +0.4176 (n=28) | +0.1945 (n=32) | +0.2232 | +0.0091 | +0.2140 | [-0.3447, +0.7923] | [-0.4437, +0.8842] | 0/1 | 100% | MIXED_DIRECTION_CONTEXT_INTERACTION |
| XAU | 263,405 | +0.0136 (n=24611) | -0.0322 (n=22188) | +0.0458 | -0.0710 | +0.1168 | [-0.0509, +0.1381] | [+0.0089, +0.2247] | 4/5 | 100% | MIXED_DIRECTION_CONTEXT_INTERACTION |

## Gates

### BTC
- PASS — `G1_high_premium_gt_zero`
- FAIL — `G2_boot_high_premium_ci_lo_gt_zero`
- PASS — `G3_interaction_gt_zero`
- FAIL — `G4_boot_interaction_ci_lo_gt_zero`
- FAIL — `G5_time_transfer_75pct_min4`
- FAIL — `G6_lopo_80pct_both_positive`

### XAU
- PASS — `G1_high_premium_gt_zero`
- FAIL — `G2_boot_high_premium_ci_lo_gt_zero`
- PASS — `G3_interaction_gt_zero`
- PASS — `G4_boot_interaction_ci_lo_gt_zero`
- PASS — `G5_time_transfer_75pct_min4`
- PASS — `G6_lopo_80pct_both_positive`
- PASS — `G7_xau_tf_2of3_positive`
- PASS — `G8_xau_buy_sell_both_positive`
- PASS — `G9_xau_mechanics_70pct_median_positive`
- TF positive: 2/3
- Directions positive: 2/2
- Mechanics positive: 12/12 (100.0% if eligible)
- Median mechanic HIGH premium: +0.04123

## Interpretation

- A positive HIGH premium alone is insufficient: the difference-in-differences interaction must also survive weekly cluster bootstrap.
- XAU must additionally transfer across TF, BUY/SELL, and the frozen mechanic family rather than being carried by one subgroup.
- This is reused history. Even a full pass is discovery-grade and requires fresh sequential/OOS replication before risk modulation.