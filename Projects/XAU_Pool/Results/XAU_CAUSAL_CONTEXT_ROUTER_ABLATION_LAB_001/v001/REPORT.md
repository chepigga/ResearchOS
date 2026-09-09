# XAU_CAUSAL_CONTEXT_ROUTER_ABLATION_LAB_001

**Verdict: MIXED_EVENT_ENRICHMENT**

> Reused-history event enrichment only. Candidate events overlap by design; CumR/PF/DD are not portfolio metrics here. Router weights were copied unchanged from the BTC preregistration.

- Native SHA256: `db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b`
- Native M1 rows: **1,454,538** | 2022-06-01 01:05:00 → 2026-07-23 23:49:00
- Finite pool events: **266,297** | context eligible: **263,405** | warmup excluded: **2,892**

## Main ablation

| Variant | N | Retain | Mean excess | Median excess | P(excess>0) | Mean R | P(R>0) | 95% cluster CI excess |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| BASELINE | 263,405 | 100.0% | -0.0250R | -0.8370R | 30.6% | -0.1037R | 30.5% | [-0.0322, -0.0172] |
| PRIMARY_PULLBACK_EXPANSION | 232,427 | 88.2% | -0.0245R | -0.8370R | 30.7% | -0.1014R | 30.5% | [-0.0320, -0.0167] |
| STRICT_DIRECTION_MATCH | 84,488 | 32.1% | -0.0406R | -0.9256R | 32.5% | -0.0440R | 32.5% | [-0.0672, -0.0119] |
| NEG_CONTROL_REVERSAL_RANGE | 30,978 | 11.8% | -0.0282R | -0.8393R | 30.1% | -0.1208R | 29.9% | [-0.0518, -0.0039] |

## Gates
- PASS — `retention_ge_35pct`
- PASS — `mean_excess_gt_baseline`
- PASS — `mean_excess_gt_negative_control`
- PASS — `p_excess_pos_gt_baseline`
- PASS — `raw_mean_R_gt_baseline`
- FAIL — `cluster_ci_low_gt_zero`
- FAIL — `positive_excess_in_ge3_years_n100`

- Positive PRIMARY years with >=100 events: **0**

## Interpretation
PRIMARY is the only preregistered hard-gate test. STRICT_DIRECTION_MATCH is secondary diagnostic only. Passing event enrichment still requires a separately frozen executable-trade OOS test before any EA or risk allocation change.
