# CROWDFADE_H1_H4_RISK_MULTIPLIER_LAB_023

## Purpose

Test risk scaling only for the LAB022 high-quality state:

    H1 and H4 non-neutral and aligned
    crowd positioned against that trend
    CrowdFade trade direction therefore with the aligned H1+H4 trend

Signal, entry, SL, TP, hold, max trades/day and anti-repeat remain unchanged.

Risk multipliers tested:
- 1.00x
- 1.25x
- 1.50x
- 2.00x

R is expressed in base-risk units. Example: if ordinary trade risk = 0.10%, then 1.50x target trade risk = 0.15%.

Full chronological equity and drawdown paths are saved in:
- output/equity_sequence_2021_2025.csv
- output/equity_sequence_2026.csv

## Target state

Historical 2021-2025:
- target trades = 438 / 1227 = 35.70%
- raw target EV = +0.1609R
- PF = 1.320
- SumR = +70.48R

2026 seconds forward-shadow:
- target trades = 50 / 136 = 36.76%
- raw target EV = +0.3109R
- PF = 1.852
- SumR = +15.54R

## Historical full equity sequence

| Mult | SumR | EV/trade | PF | MaxDD base-R | R/DD | +years |
|---:|---:|---:|---:|---:|---:|---:|
| 1.00x | +130.60 | +0.1064 | 1.210 | 13.50 | **9.675** | 5/5 |
| 1.25x | +148.22 | +0.1208 | 1.219 | 15.33 | 9.669 | 5/5 |
| 1.50x | +165.84 | +0.1352 | 1.227 | 17.16 | 9.664 | 5/5 |
| 2.00x | +201.08 | +0.1639 | 1.239 | 20.82 | 9.657 | 5/5 |

Historical interpretation:
- SumR rises almost linearly with the multiplier.
- MaxDD also rises almost linearly.
- R/DD does NOT improve; it very slightly deteriorates.
- Therefore historical data does not show a free risk-efficiency gain from boosting this state.

Important stress point:
- 2023 baseline: SumR +21.02, DD 8.54R
- 2023 at 2.0x: SumR +22.32, DD 18.41R

That year demonstrates clustering risk: larger sizing can amplify drawdown without adding much return.

## 2026 seconds full equity sequence

| Mult | SumR | EV/trade | PF | MaxDD base-R | R/DD | +months |
|---:|---:|---:|---:|---:|---:|---:|
| 1.00x | +28.71 | +0.2111 | 1.467 | 6.49 | 4.424 | 6/6 |
| 1.25x | +32.60 | +0.2397 | 1.494 | 7.07 | 4.612 | 6/6 |
| 1.50x | +36.48 | +0.2683 | 1.517 | 7.65 | 4.771 | 6/6 |
| 2.00x | +44.25 | +0.3254 | 1.555 | 8.85 | **5.003** | 6/6 |

2026 interpretation:
- all 6 months remain positive at every multiplier
- PF improves monotonically
- SumR rises faster than DD
- R/DD improves from 4.424 to 5.003 at 2.0x

However 2026 is reused forward-shadow, not pristine OOS.

## Drawdown in account percent

If base risk = 0.10%:
- 1.00x historical DD ~1.35%
- 1.25x ~1.53%
- 1.50x ~1.72%
- 2.00x ~2.08%

If base risk = 0.15%:
- 1.00x ~2.02%
- 1.25x ~2.30%
- 1.50x ~2.57%
- 2.00x ~3.12%

If base risk = 0.25%:
- 1.00x ~3.37%
- 1.25x ~3.83%
- 1.50x ~4.29%
- 2.00x ~5.21%

These are sequence max drawdowns, not daily drawdowns.

## Verdict

Risk scaling is directionally valid, but historical evidence does not justify aggressive scaling.

Best research/deployment compromise:

    1.50x multiplier on target state

Why 1.50x:
- historical SumR +27.0%
- historical DD +27.1%: risk efficiency essentially unchanged
- all 5 historical years remain positive
- 2026 SumR +27.1%
- 2026 DD only +17.9%
- 2026 R/DD improves ~7.8%
- all 6 2026 months remain positive

2.00x is not rejected, but is too aggressive for promotion because:
- historical R/DD does not improve
- 2023 DD more than doubles with little extra return
- 2026 is not pristine OOS

## Prop-oriented interpretation

For a base risk of 0.10%:
- normal trade = 0.10%
- aligned target state at 1.50x = 0.15%

For base risk 0.15%:
- normal = 0.15%
- target = 0.225%

For base risk 0.25%:
- normal = 0.25%
- target = 0.375%

Current recommendation: keep 1.50x as the maximum research candidate until fresh untouched forward data validates the state.