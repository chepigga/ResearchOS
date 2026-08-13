# SELL_CORE_012 — H4_BEAR_AGE_TOPOLOGY_TRANSFER

## Verdict

**PARTIAL PASS as a transferable negative-age topology / veto signal; FAIL as a standalone positive SELL market clock.**

The leave-one-year-out topology ranking transferred weakly but consistently at 48h: TRAIN-predicted TOP ages beat TRAIN-predicted BOTTOM ages in 2024, 2025 and 2026, and the direction survived sigma=8 smoothing. However, TOP itself was negative in 2024 and 2025, confidence intervals crossed zero, and the effect disappeared at 72h. The most robust transferable information is that TRAIN-predicted BOTTOM ages are bad for SELL, not that TOP ages are independently profitable.

## Frozen methodology

- Canonical H4 Supertrend ATR10×3, U05 BAR_OPEN lag1.
- H4 ST DOWN only.
- Primary age grid 0..80; >80 tail diagnostic.
- Every H4 boundary is a SELL candidate.
- Entry next M1 open; SL 1.5×completed H1 ATR14; no TP; cost $27.5/BTC.
- 48h primary, 72h sensitivity.
- LOYO 2024/2025/2026: train on two years, hold one year out.
- Gaussian-smoothed training EV(age), sigma=4 H4 bars primary; sigma=8 sensitivity.
- TRAIN age scores only are ranked into fixed-count BOTTOM/MID/TOP terciles.
- Inference cluster-bootstrapped by continuous bearish H4 ST episode.
- No age subrange discovered here may be promoted as a fixed trading rule.

## Primary 48h LOYO TOP minus BOTTOM

| Held year | Delta R | P(delta>0) | Delta price% | P(delta price>0) |
|---:|---:|---:|---:|---:|
| 2024 | +0.210R | 75.1% | +0.586% | 95.9% |
| 2025 | +0.194R | 66.8% | +0.253% | 71.2% |
| 2026 | +0.485R | 86.7% | +0.179% | 69.8% |
| POOLED OOS | +0.236R | 83.4% | +0.311% | 88.8% |

All signs are positive, but all 95% CIs cross zero. Therefore this is not a formal positive-selector PASS.

Sigma=8 retained the same positive sign in all held years and pooled OOS; pooled delta was +0.273R / +0.414% price, still not a clean 95% PASS.

## Actual held-year bucket outcomes, sigma=4

### BOTTOM — stable negative SELL zone

- 2024: -0.417R, PF0.54, price -0.727%.
- 2025: -0.261R, PF0.71, price -0.307%.
- 2026: -0.234R, PF0.70, price -0.079%.

This is the cleanest transferable feature: the ages predicted as BOTTOM from the other two years are negative 3/3 in both R and price space.

### TOP — not a positive SELL state

- 2024: -0.207R, PF0.75, price -0.141%.
- 2025: -0.067R, PF0.91, price -0.054%.
- 2026: +0.251R, PF1.32, price +0.100%.

Pooled TOP: -0.064R, -0.061% price.

### MID — unexpectedly strongest held-out bucket

- 2024: +0.290R, PF1.41, price -0.122%.
- 2025: +0.175R, PF1.24, price -0.078%.
- 2026: +0.263R, PF1.35, price +0.342%.

Pooled MID: +0.239R and +0.021% price. This is descriptive only; MID was not preregistered as the expected profitable bucket and cannot be promoted from this lab.

## Curve transfer strength

Train-vs-held age-curve correlations were positive but modest:

- 2024 Spearman R +0.348 / price +0.459.
- 2025 +0.325 / +0.513.
- 2026 +0.191 / +0.308.

Thus age contains some transferable ordering information, but the exact peak/trough topology migrates materially.

## 72h sensitivity

The 48h age-ranking effect disappears at 72h:

- 2024 TOP-BOTTOM -0.033R.
- 2025 -0.038R.
- 2026 +0.021R.
- pooled OOS -0.062R.

Therefore H4 bearish age is not a robust multi-horizon standalone SELL engine.

## Broad lifecycle migration diagnostic

Fixed broad bins confirm regime migration:

- 2024: 28-50 and 51-80 mildly positive in R, but negative in price space.
- 2025: 12-27 strongly positive (+0.781R), while 28-50 and 51-80 are negative.
- 2026: 28-50 strongly positive (+1.293R), while 0-27 and 51-80 are negative.

The location of the best SELL phase is not fixed across years.

## Frozen conclusion

1. **Reject a fixed B3/age window as the SELL core.**
2. **Age topology has real but weak transfer information at 48h.**
3. The strongest transferable use is as a **negative-zone / veto model**: TRAIN-predicted BOTTOM ages were negative 3/3 years in R and price space.
4. There is no validated positive SELL state from age alone: TOP was negative in 2024/2025 and pooled OOS.
5. The effect is horizon-specific and disappears at 72h.
6. Do not promote MID, 12-27, 28-50, or any other age window post hoc. Any use of topology as a dynamic veto or selector needs a separate preregistered forward/rolling validation.

Workflow run: `31699632288`  
Artifact: `9180704086`  
Artifact SHA256: `3440b1fe1ee422c480700a2974e181a9e7464b6ae75e151fa57454f8b64f0063`
