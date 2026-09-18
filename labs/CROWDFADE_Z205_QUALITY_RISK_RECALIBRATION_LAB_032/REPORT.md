# CROWDFADE_Z205_QUALITY_RISK_RECALIBRATION_LAB_032

## Purpose

Recalibrate risk only after lowering the CrowdFade threshold from Z=2.50 to **Z=2.05**.

The trade sequence is the exact LAB031 Z2.05 sequence. No change to:
- signal reachability
- confirmation
- passive retrace
- limit TTL
- SL / TP
- max hold
- max trades/day
- anti-repeat
- occupancy

Frozen execution:
`Z2.05 -> M15 confirm .25 ATR -> retrace .60 ATR -> limit20 -> SL4.5 -> TP10 -> H24`.

## Tested risk maps

| Mode | HIGH | NORMAL | LOW |
|---|---:|---:|---:|
| FLAT | 1.00 | 1.00 | 1.00 |
| Old LAB026 | 1.50 | 1.00 | 0.75 |
| Moderate tier | 1.25 | 1.00 | 0.75 |
| High-only moderate | 1.25 | 1.00 | 1.00 |
| Low-only reduction | 1.00 | 1.00 | 0.75 |

## State stability changed after Z2.05

### 2021–2025

- HIGH: N479, EV **+0.1169R**, PF 1.239
- NORMAL: N900, EV +0.0673R, PF 1.137
- LOW: N263, EV +0.0222R, PF 1.044

Historical ordering still resembles LAB026:
`HIGH > NORMAL > LOW`.

### 2026 Mar–Aug forward-shadow

- HIGH: N49, EV **-0.0126R**, PF **0.975**
- NORMAL: N101, EV **+0.1265R**, PF 1.252
- LOW: N26, EV **+0.1907R**, PF **1.464**

The ordering has inverted:
`LOW > NORMAL > HIGH`.

Therefore the old LAB026 multipliers are not transport-stable after the Z threshold change.

## Historical 2021–2025

| Risk map | SumR | EV | PF | MaxDD | R/DD | +years |
|---|---:|---:|---:|---:|---:|---:|
| Flat 1/1/1 | +122.40 | +0.0745 | 1.151 | 19.83 | 6.174 | 5/5 |
| Old 1.5/1/.75 | **+148.95** | +0.0907 | **1.167** | 23.31 | 6.391 | 5/5 |
| 1.25/1/.75 | +134.95 | +0.0822 | 1.161 | 21.02 | 6.421 | 5/5 |
| 1.25/1/1 | +136.40 | +0.0831 | 1.157 | 22.12 | 6.168 | 5/5 |
| 1/1/.75 | +120.94 | +0.0737 | 1.156 | **18.73** | **6.458** | 5/5 |

Historical-only, low-only reduction has the best R/DD, while the old map has the highest SumR.

The differences are modest compared with the forward instability.

## 2026 Mar–Aug forward-shadow

| Risk map | SumR | EV | PF | MaxDD | R/DD | +months |
|---|---:|---:|---:|---:|---:|---:|
| **Flat 1/1/1** | **+17.12** | **+0.0972** | **1.198** | **8.34** | **2.051** | 4/6 |
| Old 1.5/1/.75 | +15.57 | +0.0885 | 1.162 | 10.78 | 1.444 | 4/6 |
| 1.25/1/.75 | +15.72 | +0.0893 | 1.175 | 9.77 | 1.609 | 4/6 |
| 1.25/1/1 | +16.96 | +0.0964 | 1.183 | 9.36 | 1.813 | 4/6 |
| 1/1/.75 | +15.88 | +0.0902 | 1.190 | 8.76 | 1.813 | 4/6 |

Flat risk wins the forward-shadow on:
- SumR
- EV
- PF
- MaxDD
- R/DD

No tested tiered mode improves positive-month count.

## Old LAB026 versus flat risk

2026:

- SumR: **17.12 -> 15.57R** (-9.0%)
- PF: **1.198 -> 1.162**
- MaxDD: **8.34 -> 10.78R** (+29.2%)
- R/DD: **2.051 -> 1.444** (-29.6%)

This is a clear forward-shadow degradation.

## Prop-oriented DD scaling

For flat risk, 2026 sequence DD = **8.34R**.

Approximate normalized equity DD:
- base risk 0.10% -> **0.83%**
- base risk 0.15% -> **1.25%**
- base risk 0.25% -> **2.09%**

These are sequence approximations, not broker daily-DD simulations.

## Verdict

### Old LAB026 quality scaling
**FAIL to transport to Z2.05.**

Do not carry `HIGH 1.5 / NORMAL 1 / LOW .75` into the current v200 just because it was valid at Z2.50.

### Current leading risk configuration
**FLAT 1 / 1 / 1.**

Reason:
- all 5 historical years positive;
- best 2026 SumR / PF / DD / R-DD among preregistered maps;
- avoids multiplying a state whose forward behavior has inverted;
- simplest and least curve-fit configuration.

### Status

**PROMOTE FLAT RISK as the Z2.05 candidate.**

Do not invert the old quality map to overweight LOW based on only 26 forward trades. That would be reactive overfitting.

Recommended next validation:
1. keep Z2.05 and flat risk frozen;
2. run broker-native dual-broker forward;
3. separately audit daily-DD / simultaneous exposure on BTC+ETH+SOL;
4. only revisit quality sizing after a fresh forward sample.
