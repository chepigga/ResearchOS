# CROWDFADE_SIDE_TIME_CAUSAL_INTERACTION_LAB_019

## Purpose

Test whether the coarse UTC windows from LAB018 behave differently by trade side under a full stateful causal rerun.

No threshold, execution, exit, or risk parameter was changed.

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
- all weekdays ON

Time semantics: UTC hour of the original M15 signal bar start.

Windows:
- A = 04:00-07:59 UTC
- B = 18:00-20:59 UTC

Atomic tests only:
1. BASELINE
2. VETO_LONG_04_07
3. VETO_SHORT_04_07
4. VETO_LONG_18_20
5. VETO_SHORT_18_20

No combinations were tuned in this LAB.

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

## 2021-2025 results

| Mode | N | EV | PF | MaxDD R | SumR | + years | Worst year | R/DD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| BASELINE | 1227 | +0.1064 | 1.210 | 13.50 | +130.60 | 5/5 | +16.56R | 9.68 |
| VETO_LONG_04_07 | 1171 | +0.1205 | 1.242 | 14.59 | +141.16 | 5/5 | +12.46R | 9.68 |
| VETO_SHORT_04_07 | 1173 | +0.1034 | 1.205 | 16.37 | +121.32 | 5/5 | +8.72R | 7.41 |
| VETO_LONG_18_20 | 1214 | +0.1088 | 1.215 | 13.25 | +132.14 | 5/5 | +14.72R | 9.97 |
| VETO_SHORT_18_20 | 1195 | +0.1093 | 1.216 | 15.37 | +130.67 | 5/5 | +13.77R | 8.50 |

## 2026 seconds forward-shadow

| Mode | N | EV | PF | MaxDD R | SumR | + months | R/DD |
|---|---:|---:|---:|---:|---:|---:|---:|
| BASELINE | 136 | +0.2111 | 1.467 | 6.49 | +28.71 | 6/6 | 4.42 |
| VETO_LONG_04_07 | 130 | +0.1652 | 1.361 | 6.27 | +21.48 | 5/6 | 3.42 |
| VETO_SHORT_04_07 | 127 | +0.2135 | 1.487 | 6.52 | +27.12 | 5/6 | 4.16 |
| VETO_LONG_18_20 | 136 | +0.1992 | 1.434 | 6.49 | +27.09 | 6/6 | 4.17 |
| VETO_SHORT_18_20 | 135 | +0.2201 | 1.492 | 6.49 | +29.72 | 6/6 | 4.58 |

## Key findings

### LONG 04-07
Historical EV/PF/SumR improve, but this fails 2026 forward-shadow:
- EV falls from +0.2111R to +0.1652R
- PF falls from 1.467 to 1.361
- SumR falls by 7.23R
- positive months fall 6/6 to 5/6
Reject.

### SHORT 04-07
Not robust:
- historical EV/PF/SumR are worse
- historical DD rises from 13.50R to 16.37R
- 2026 EV/PF slightly improve but only 5/6 months remain positive
Reject.

### LONG 18-20
Historically modestly cleaner, but 2026 does not confirm benefit:
- EV falls by about 0.0119R
- PF falls by about 0.0335
- SumR falls by about 1.62R
Do not promote.

### SHORT 18-20
This is the only surviving watch candidate.

Historical:
- EV +0.1064 -> +0.1093R
- PF 1.210 -> 1.216
- SumR essentially unchanged
- 5/5 positive years retained

2026:
- EV +0.2111 -> +0.2201R
- PF 1.467 -> 1.492
- SumR +28.71 -> +29.72R
- MaxDD unchanged at 6.49R
- 6/6 positive months retained

But historical risk efficiency worsens:
- MaxDD 13.50R -> 15.37R
- R/DD 9.68 -> 8.50
- worst year +16.56R -> +13.77R

Therefore it is not enough for production promotion.

## Verdict

NO side x time veto is promoted.

Frozen candidate remains unchanged:

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

Research watchlist only:

    SHORT signal
    18:00-20:59 UTC
    veto new signal arming

Do not add it to the EA yet.

## Next validation

The right next step is a frozen stability test of SHORT 18-20 only using resampling / leave-one-year-out / trade-path contribution analysis, without changing the window.