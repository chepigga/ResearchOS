# CROWDFADE_FRI_SAT_VETO_FORWARD_LAB_017

## Purpose

Causally validate the LAB015 weekday observation that Friday and Saturday looked weak.

This LAB does **not** delete Friday/Saturday trades from an already-produced trade list. It re-runs the full stateful strategy while preventing new signal arming on the selected UTC weekday(s). This preserves interactions with:

- open-position blocking / sequential trade path
- max 3 trades/day
- inherited 1 ATR anti-repeat gate
- confirmation and passive-limit timing

## Frozen core

- ZLong = 2.50
- ZShort = 2.50
- M15 completed-close signal path
- confirm = 0.25 ATR
- confirm TTL = 60m
- passive retrace = 0.60 ATR
- limit-only
- limit TTL = 20m
- SL = 4.50 ATR
- TP = 10.0 ATR
- max hold = 24h
- max trades/day = 3
- cost proxy = 0.5 bps
- BE = OFF
- trailing = OFF
- inherited anti-repeat gate = 1 ATR

Weekday semantics are intentionally frozen to LAB015:
**UTC weekday of the original M15 signal bar start**.

Tested:

1. BASELINE
2. VETO_FRI
3. VETO_SAT
4. VETO_FRI_SAT

Sunday is always enabled.

## Baseline parity

Exact parity passed.

Historical 2021-2025:

- N = 1227
- EV = +0.106435R
- PF = 1.210426
- MaxDD = 13.497689R
- SumR = +130.595940R
- 5/5 positive years

2026 seconds forward-shadow:

- N = 136
- EV = +0.211108R
- PF = 1.467315
- MaxDD = 6.489290R
- SumR = +28.710706R
- 6/6 positive months

## 2021-2025 causal results

| Mode | N | Trades/mo | EV | PF | MaxDD R | SumR | + years | Worst year |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **BASELINE** | **1227** | **20.45** | **+0.1064** | **1.210** | **13.50** | **+130.60** | **5/5** | **+16.56R** |
| VETO_FRI | 1114 | 18.57 | +0.1159 | 1.227 | 15.89 | +129.07 | 5/5 | +14.11R |
| VETO_SAT | 1126 | 18.77 | +0.0953 | 1.183 | 13.40 | +107.28 | 5/5 | +5.25R |
| VETO_FRI_SAT | 972 | 16.20 | +0.1092 | 1.206 | 16.33 | +106.15 | 5/5 | +11.44R |

### Historical interpretation

Friday-only veto superficially increases EV and PF:

- EV +0.1064 -> +0.1159R
- PF 1.210 -> 1.227

But it does not improve the risk/return path:

- SumR falls by 1.53R
- MaxDD worsens by 2.39R
- worst year falls from +16.56R to +14.11R
- frequency falls by 113 trades / ~1.88 trades per month

Saturday veto is clearly harmful:

- EV falls by ~0.0112R
- PF falls by ~0.0275
- SumR falls by ~23.31R
- worst year collapses to +5.25R

Combined Friday+Saturday veto is also not an improvement:

- only +0.0028R EV
- slightly lower PF
- MaxDD worsens by +2.83R
- SumR falls by 24.45R
- frequency falls from 20.45 to 16.20 trades/month

## 2026 seconds forward-shadow

| Mode | N | Trades/mo | EV | PF | MaxDD R | SumR | + months |
|---|---:|---:|---:|---:|---:|---:|---:|
| **BASELINE** | **136** | **22.67** | **+0.2111** | **1.467** | **6.49** | **+28.71** | **6/6** |
| VETO_FRI | 124 | 20.67 | +0.2010 | 1.436 | 6.39 | +24.92 | 5/6 |
| VETO_SAT | 117 | 19.50 | +0.1641 | 1.367 | 6.27 | +19.20 | 5/6 |
| VETO_FRI_SAT | 104 | 17.33 | +0.1626 | 1.352 | 6.94 | +16.91 | 5/6 |

### 2026 interpretation

All vetoes underperform the baseline.

Friday-only:

- EV -0.0101R
- PF -0.0309
- SumR -3.79R
- only 5/6 positive months
- August becomes slightly negative

Saturday-only:

- EV -0.0470R
- PF -0.1004
- SumR -9.51R
- only 5/6 positive months

Friday+Saturday:

- EV -0.0485R
- PF -0.1151
- MaxDD worsens by +0.45R
- SumR -11.80R
- only 5/6 positive months

## Side interaction

The historical Friday-only veto improves per-trade EV on both sides somewhat, but this does not translate into better total system robustness.

2026 Friday-only:

- LONG EV improves from +0.2150R to +0.2646R
- SHORT EV falls from +0.2080R to +0.1551R

This is important: Friday weakness is not a uniform structural defect. Removing Friday changes the sequential opportunity set and hurts the SHORT contribution in forward-shadow.

Saturday removal is worse on both aggregate forward metrics and total opportunity capture.

## Key methodological finding

LAB015 showed negative **conditional/post-hoc** Friday and Saturday buckets.

LAB017 shows that those buckets are **not valid causal veto rules**.

Why:

CrowdFade is stateful and sequential. Removing one trade changes:

- when the next signal becomes eligible
- anti-repeat state
- position occupancy
- max-trades/day usage
- which later signals are reached at all

Therefore:

**negative weekday bucket != profitable causal weekday veto**

This LAB is a useful anti-overfitting result.

## Verdict

**FAIL Friday/Saturday veto hypothesis for production promotion.**

Keep all weekdays enabled.

Frozen production-oriented research candidate remains:

    ZLong = 2.50
    ZShort = 2.50
    M15 confirm 0.25 ATR
    retrace 0.60 ATR
    limit-only TTL20m
    SL4.5 ATR
    TP10 ATR
    max hold 24h
    no BE
    no trailing
    max3/day
    cost proxy 0.5bps

Do **not** add:

- Friday veto
- Saturday veto
- Friday+Saturday veto
- blanket weekend veto

Sunday remains enabled.

## Research status

2021-2025 is discovery / in-sample.

2026 seconds remains forward-shadow/stress, not pristine OOS.

A genuinely untouched forward period is still required after final model selection.
