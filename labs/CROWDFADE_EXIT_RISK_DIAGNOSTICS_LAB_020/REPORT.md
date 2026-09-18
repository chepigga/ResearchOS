# CROWDFADE_EXIT_RISK_DIAGNOSTICS_LAB_020

Purpose: answer three isolated exit/risk questions without changing signal discovery:
1. wide vs narrow vs adaptive stop
2. breakeven after fixed R
3. continuous trailing updated at the finest available path resolution

Frozen signal/entry: Z 2.50/2.50, M15 confirm 0.25 ATR, retrace 0.60 ATR, limit-only TTL20m, TP10 ATR, max hold24h, max3/day, inherited 1 ATR anti-repeat gate.

Baseline parity passed exactly: historical N1227 and 2026 N136.

## Stop geometry

| Stop | Hist EV | Hist PF | Hist DD | Hist SumR | 2026 EV | 2026 PF | 2026 DD | 2026 +months |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Wide 4.5 ATR | +0.1064 | 1.210 | 13.50R | +130.60R | +0.2111 | 1.467 | 6.49R | 6/6 |
| Narrow 2.5 ATR | +0.1696 | 1.250 | 24.34R | +231.31R | +0.2137 | 1.323 | 12.37R | 5/6 |
| Adaptive 3.0/4.5 ATR | +0.1421 | 1.253 | 28.21R | +179.67R | +0.2007 | 1.405 | 9.10R | 6/6 |

Narrow stop generates more R historically because the unchanged TP10 ATR becomes a larger R target and positions recycle faster. But risk-path quality deteriorates sharply. In 2026 it nearly doubles MaxDD and August becomes negative.

The tested adaptive multiplier does not dominate the wide stop: historical DD is worse and 2026 EV/PF/SumR are lower than baseline.

For a prop-oriented low-risk deployment, 4.5 ATR remains the robustness anchor.

## Path diagnostics

Wide baseline historical:
- 1216 / 1227 trades (99.10%) had some adverse excursion after entry
- 571 reached +1R
- 287 reached +2R

Wide baseline 2026:
- 135 / 136 trades (99.26%) had some adverse excursion after entry
- 95 reached +0.5R
- 64 reached +1R
- 44 reached +1.5R
- 34 reached +2R

This means CrowdFade entries normally experience at least small adverse movement. A tight-stop assumption that good trades should move immediately is inconsistent with observed paths.

## Breakeven

| BE trigger | Hist EV | Hist PF | Hist DD | Hist SumR | 2026 EV | 2026 PF | 2026 SumR |
|---|---:|---:|---:|---:|---:|---:|---:|
| No BE | +0.1064 | 1.210 | 13.50R | +130.60R | +0.2111 | 1.467 | +28.71R |
| +0.5R | +0.0344 | 1.108 | 15.50R | +45.99R | +0.1530 | 1.569 | +22.64R |
| +1.0R | +0.0673 | 1.155 | 16.32R | +84.70R | +0.1896 | 1.498 | +25.97R |
| +1.5R | +0.1001 | 1.207 | 17.44R | +123.42R | +0.2358 | 1.559 | +32.07R |
| +2.0R | +0.1058 | 1.210 | 13.50R | +129.87R | +0.2186 | 1.492 | +29.72R |

Early BE at 0.5R or 1R is clearly harmful historically.

BE at 1.5R is the only interesting watch candidate because 2026 improves, but it still loses historical EV/SumR and worsens historical DD. Do not promote without fresh validation.

BE at 2R is almost behaviorally identical to no BE; too few trades are changed.

## Continuous trailing

Historical updates are on completed 1m bars. 2026 updates are on completed 1-second OHLC bars, effective on the next second to avoid same-second ordering hindsight. This is a close proxy, not true exchange tick sequence.

| Trail | Hist EV | Hist PF | Hist DD | Hist SumR | 2026 EV | 2026 PF | 2026 SumR | +months |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| No trail | +0.1064 | 1.210 | 13.50R | +130.60R | +0.2111 | 1.467 | +28.71R | 6/6 |
| 1R trail after +1R | +0.0588 | 1.136 | 14.61R | +76.31R | +0.1324 | 1.332 | +18.67R | 5/6 |
| 2R trail after +1R | +0.0899 | 1.182 | 14.22R | +111.08R | +0.1824 | 1.416 | +24.80R | 5/6 |

The 1R continuous trail increases historical win rate to ~52.2%, but destroys expectancy and total R. This is classic winner truncation.

## Verdict

- STOP: keep wide 4.5 ATR as frozen robustness anchor.
- ADAPTIVE STOP: tested regime multiplier is not superior.
- BE: OFF. +1.5R is research-watch only, not production.
- CONTINUOUS TRAILING: OFF. Per-second proxy confirms the same right-tail truncation seen in prior trailing work.

No production parameter is changed by LAB020.