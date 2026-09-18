# CROWDFADE_COARSE_TIME_WINDOW_VETO_LAB_018

## Purpose

Causally test whether the weak LAB015 hour clusters can be promoted into coarse UTC entry-arm veto rules.

This is a full stateful rerun. It does **not** delete trades from an already-produced trade list.

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

Time semantics are frozen to LAB015:

**UTC hour of the original M15 signal bar start**

Tested windows:

- A = 04:00-07:59 UTC
- B = 18:00-20:59 UTC

Modes:

1. BASELINE
2. VETO_04_07
3. VETO_18_20
4. VETO_BOTH

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
| BASELINE | 1227 | 20.45 | +0.1064 | 1.210 | **13.50** | +130.60 | 5/5 | +16.56R |
| VETO_04_07 | 1114 | 18.57 | +0.1221 | 1.246 | 18.90 | +136.01 | 5/5 | +18.94R |
| VETO_18_20 | 1180 | 19.67 | +0.1111 | 1.219 | 15.13 | +131.08 | 5/5 | +12.93R |
| VETO_BOTH | 1054 | 17.57 | **+0.1351** | **1.274** | 18.60 | **+142.41** | 5/5 | +20.22R |

### Historical interpretation

The combined veto is attractive **in-sample**:

- EV: +0.1064 -> +0.1351R
- PF: 1.210 -> 1.274
- SumR: +130.60 -> +142.41R
- all 5 years remain positive

But it pays for that with materially worse path risk:

- MaxDD: 13.50 -> 18.60R
- frequency: 20.45 -> 17.57 trades/month

VETO_04_07 alone has the same risk problem:

- EV improves to +0.1221R
- PF improves to 1.246
- SumR improves to +136.01R
- but MaxDD worsens sharply to 18.90R

VETO_18_20 is only a marginal historical change and also worsens DD.

## 2026 seconds forward-shadow

| Mode | N | Trades/mo | EV | PF | MaxDD R | SumR | + months |
|---|---:|---:|---:|---:|---:|---:|---:|
| **BASELINE** | **136** | **22.67** | **+0.2111** | **1.467** | 6.49 | **+28.71** | **6/6** |
| VETO_04_07 | 123 | 20.50 | +0.1715 | 1.386 | 6.53 | +21.10 | 5/6 |
| VETO_18_20 | 135 | 22.50 | +0.2081 | 1.457 | **6.49** | +28.10 | **6/6** |
| VETO_BOTH | 122 | 20.33 | +0.1679 | 1.375 | 6.53 | +20.49 | 5/6 |

### 2026 interpretation

The historical improvement does **not** survive forward-shadow.

VETO_04_07:

- EV: 0.2111 -> 0.1715R
- PF: 1.467 -> 1.386
- SumR: +28.71 -> +21.10R
- 6/6 -> 5/6 positive months
- August becomes negative (-1.26R)

VETO_BOTH is worse again:

- EV: 0.2111 -> 0.1679R
- PF: 1.467 -> 1.375
- SumR: +28.71 -> +20.49R
- 6/6 -> 5/6 positive months
- August becomes negative

VETO_18_20 is essentially neutral-to-worse:

- only one trade removed in 2026
- EV slightly lower
- PF slightly lower
- SumR slightly lower
- DD unchanged
- 6/6 positive months preserved

There is no forward evidence for promoting it.

## Side interaction

The largest warning comes from VETO_04_07 in 2026:

Baseline:

- LONG EV = +0.2150R
- SHORT EV = +0.2080R

VETO_04_07:

- LONG EV = +0.0592R
- SHORT EV = +0.2511R

The window veto strongly changes the state path and side composition. This is not a simple local removal of bad hourly trades.

For VETO_BOTH in 2026:

- LONG EV = +0.0274R
- SHORT EV = +0.2689R

This is a major side-path distortion and another reason not to promote a blanket time veto.

## Key methodological finding

LAB015 hour buckets were post-hoc diagnostics.

LAB018 shows that the attractive historical hour-filter result is not robust causally across periods.

Because CrowdFade is stateful, removing signals inside a time block changes:

- next eligible signal
- anti-repeat state
- position occupancy
- max-trades/day path
- side composition
- later reachable opportunities

Therefore:

**negative hour bucket != robust causal time veto**

and even

**historically improved causal veto != forward-robust production rule**

## Verdict

**FAIL coarse time-window veto for production promotion.**

Keep all UTC hours enabled.

Do not add:

- 04:00-07:59 UTC veto
- 18:00-20:59 UTC veto
- combined veto

Frozen candidate remains:

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
    all weekdays ON
    all UTC hours ON

## Research status

2021-2025 is discovery / in-sample.

2026 seconds remains forward-shadow/stress, not pristine OOS.

The historical VETO_BOTH improvement should be treated as a rejected in-sample optimization because it fails the 2026 forward-shadow test.
