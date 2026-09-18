# CROWDFADE_SIDE_THRESHOLD_ASYMMETRY_LAB_016

## Purpose

Validate whether separate LONG/SHORT crowd Z thresholds improve the frozen CrowdFade candidate without changing execution or exit logic.

## Frozen core

- Entry TF: M15 completed close
- Confirmation: 0.25 ATR
- Confirmation TTL: 60 min
- Passive retrace: 0.60 ATR
- Limit TTL: 20 min
- Market fallback: OFF
- SL: 4.50 ATR
- TP: 10.0 ATR
- Max hold: 24h
- Max trades/day: 3
- Cost proxy: 0.5 bps
- BE: OFF
- trailing: OFF
- inherited LAB014/LAB015 anti-repeat gate: 1 ATR (kept for parity)

Only thresholds changed:

- LONG: 2.25 / 2.50 / 2.75
- SHORT: 2.50 / 2.75 / 3.00

## Historical 2021-2025

| ZLong | ZShort | N | trades/mo | EV | PF | MaxDD R | SumR | + years | worst year R |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2.25 | 2.50 | 1368 | 22.80 | +0.0709 | 1.137 | 22.34 | +96.96 | 5/5 | +6.91 |
| 2.25 | 2.75 | 1261 | 21.02 | +0.0510 | 1.097 | 26.76 | +64.29 | 4/5 | -2.10 |
| 2.25 | 3.00 | 1175 | 19.58 | +0.0302 | 1.056 | 28.31 | +35.43 | 3/5 | -8.85 |
| **2.50** | **2.50** | **1227** | **20.45** | **+0.1064** | **1.210** | **13.50** | **+130.60** | **5/5** | **+16.56** |
| 2.50 | 2.75 | 1104 | 18.40 | +0.0989 | 1.196 | 15.86 | +109.20 | 5/5 | +14.19 |
| 2.50 | 3.00 | 1001 | 16.68 | +0.0923 | 1.179 | 15.86 | +92.37 | 5/5 | +11.65 |
| 2.75 | 2.50 | 1103 | 18.38 | +0.0845 | 1.165 | 21.38 | +93.20 | 5/5 | +6.35 |
| 2.75 | 2.75 | 977 | 16.28 | +0.0840 | 1.165 | 19.18 | +82.06 | 5/5 | +5.71 |
| 2.75 | 3.00 | 852 | 14.20 | +0.0823 | 1.159 | 18.14 | +70.14 | 5/5 | +2.13 |

### Historical conclusion

Symmetric **2.50 / 2.50** is the clear robustness anchor:

- highest EV in the 3x3 grid
- highest PF
- highest SumR
- lowest historical MaxDD
- strongest worst-year result
- 5/5 positive years

Raising SHORT threshold does **not** improve the historical SHORT edge:

- ZShort 2.50: SHORT EV ~+0.075R
- ZShort 2.75: SHORT EV ~+0.066R (with ZLong fixed at 2.50)
- ZShort 3.00: SHORT EV ~+0.056R

So LAB015's weaker aggregate SHORT side does not imply that only more extreme SHORT signals are historically better.

## 2026 seconds forward-shadow / stress

| ZLong | ZShort | N | EV | PF | MaxDD R | SumR | + months |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 2.25 | 2.50 | 151 | +0.1324 | 1.269 | 11.83 | +19.99 | 4/6 |
| 2.25 | 2.75 | 141 | +0.0966 | 1.193 | 10.40 | +13.62 | 5/6 |
| 2.25 | 3.00 | 131 | +0.1470 | 1.312 | 7.27 | +19.26 | 5/6 |
| **2.50** | **2.50** | **136** | **+0.2111** | **1.467** | **6.49** | **+28.71** | **6/6** |
| 2.50 | 2.75 | 126 | +0.1559 | 1.337 | 7.28 | +19.64 | 4/6 |
| 2.50 | 3.00 | 116 | +0.2175 | 1.493 | 6.26 | +25.23 | 5/6 |
| 2.75 | 2.50 | 119 | +0.1725 | 1.370 | 7.28 | +20.53 | 5/6 |
| 2.75 | 2.75 | 105 | +0.1316 | 1.275 | 7.29 | +13.82 | 5/6 |
| 2.75 | 3.00 | 95 | +0.1832 | 1.403 | 5.26 | +17.41 | 5/6 |

### 2026 conclusion

The proposed EA asymmetry **2.50 / 2.75** degrades the forward-shadow:

- EV: +0.2111R -> +0.1559R
- PF: 1.467 -> 1.337
- MaxDD: 6.49R -> 7.28R
- SumR: +28.71R -> +19.64R
- positive months: 6/6 -> 4/6

It turns July and August negative.

**2.50 / 3.00** is interesting in 2026 alone (EV +0.2175R, PF 1.493, DD 6.26R), but it is not a better cross-period selection because historical EV/PF/SumR all fall and historical DD rises. This looks like a 2026-specific effect, not a robust threshold plateau improvement.

## Verdict

**FAIL asymmetry hypothesis for production promotion.**

Keep the frozen base:

    ZLong  = 2.50
    ZShort = 2.50

Do not promote the v1.93 default **2.50 / 2.75** based on LAB015 alone.

The next isolated research step remains:

**CROWDFADE_FRI_SAT_VETO_FORWARD_LAB_017**

Test:

- baseline
- Friday veto
- Saturday veto
- Friday + Saturday veto

Sunday stays enabled.

## Methodological status

2021-2025 remains discovery/in-sample.

2026 seconds is forward-shadow/stress, not pristine OOS, because it has already been reused across prior LABs. A fresh untouched forward period is still required after final model selection.
