# CROWDFADE_CROWD_TREND_PRICE_RESPONSE_LAB_025

## Purpose

Test the interaction:

**crowd extreme × H1/H4 trend × causal price response before CrowdFade entry confirmation**

without retuning the frozen crowd signal.

Frozen core remains unchanged:

- ZLong = 2.50
- ZShort = 2.50
- M15 confirmation = 0.25 ATR
- confirmation TTL = 60m
- passive retrace = 0.60 ATR
- limit TTL = 20m
- SL = 4.5 ATR
- TP = 10 ATR
- max hold = 24h
- max 3/day
- inherited 1 ATR anti-repeat gate

## Trend state

H1/H4 use completed bars only.

UP:
- close > EMA50
- EMA50 > EMA50 four bars ago

DOWN: mirror.

Aligned trend:
- H1 and H4 both non-neutral
- H1 and H4 same direction

Relation:

- WITH_TREND = CrowdFade trade follows aligned H1/H4; crowd is against trend
- COUNTERTREND = CrowdFade trade opposes aligned H1/H4; crowd is with trend
- MIXED = H1/H4 not aligned

## Price-response state

At the original crowd-extreme signal, measure the maximum excursion in the **crowd direction** before the frozen contrarian M15 confirmation occurs.

This is fully causal at confirmation time.

Buckets were fixed before seeing results:

- FAIL: crowd-direction excursion <= 0.25 ATR
- CONTESTED: >0.25 and <=0.75 ATR
- CONTINUATION: >0.75 ATR

Also measured confirmation speed:

- 1 M15 bar
- 2 M15 bars
- 3–4 M15 bars

---

# Stage A — Diagnostic interaction

Baseline parity passed exactly:

Historical 2021–2025:
- N 1227
- EV +0.106435R
- PF 1.210426
- SumR +130.596R
- MaxDD 13.498R

2026 seconds:
- N 136
- EV +0.211108R
- PF 1.467315
- SumR +28.711R
- MaxDD 6.489R

## Strong aligned trend: CrowdFade WITH trend

Historical:

| Crowd price response before confirm | N | EV | PF | SumR |
|---|---:|---:|---:|---:|
| <=0.25 ATR | 167 | +0.1677R | 1.331 | +28.01R |
| 0.25–0.75 ATR | 145 | **+0.2867R** | **1.648** | +41.57R |
| >0.75 ATR | 126 | **+0.0072R** | **1.013** | +0.90R |

2026:

| Crowd price response before confirm | N | EV | PF | SumR |
|---|---:|---:|---:|---:|
| <=0.25 ATR | 18 | **+0.4993R** | **2.847** | +8.99R |
| 0.25–0.75 ATR | 14 | +0.3967R | 1.993 | +5.55R |
| >0.75 ATR | 18 | **+0.0557R** | **1.129** | +1.00R |

Interpretation:

The best state is not necessarily "crowd moves price zero distance."

The robust distinction is:

> if crowd can push price more than about 0.75 ATR in its own direction before our contrarian confirmation, the edge collapses.

## Combined WITH_TREND and crowd excursion <=0.75 ATR

Historical:

- N = 312
- EV = **+0.2230R**
- PF = **1.468**
- SumR = **+69.58R**
- DD = 13.67R
- positive contribution in every historical year

Annual SumR:

- 2021 +22.25R
- 2022 +8.47R
- 2023 +4.45R
- 2024 +11.48R
- 2025 +22.93R

2026:

- N = 32
- EV = **+0.4544R**
- PF = **2.390**
- SumR = **+14.54R**
- DD = 3.03R

This is materially stronger than the full WITH_TREND state from LAB022.

## All aligned H1/H4, crowd excursion <=0.75 ATR

Historical:

- N = 562
- EV = **+0.1827R**
- PF = **1.383**
- SumR = **+102.70R**
- DD = **9.99R**
- 5/5 historical years positive

2026:

- N = 54
- EV = **+0.4052R**
- PF = **2.094**
- SumR = **+21.88R**
- DD = 4.55R

## All aligned H1/H4, crowd excursion >0.75 ATR

Historical:

- N = 245
- EV = **-0.0364R**
- PF = **0.938**
- SumR = **-8.93R**
- DD = 22.39R

2026:

- N = 27
- EV = **+0.0197R**
- PF = **1.040**
- SumR = +0.53R
- DD = 6.59R

This is the cleanest diagnostic separation in LAB025.

## Countertrend + crowd continuation >0.75 ATR

Historical:

- N 119
- EV **-0.0826R**
- PF **0.864**
- SumR -9.83R

2026:

- N 9
- EV **-0.0522R**
- PF **0.915**
- SumR -0.47R

This is negative in both periods, although 2026 sample is small.

---

# Confirmation speed

WITH_TREND historical:

- confirm in 1 M15 bar: N252, EV +0.2065R, PF 1.415
- confirm in 2 bars: N95, EV +0.1405R, PF 1.284
- confirm in 3–4 bars: N91, EV +0.0559R, PF 1.106

2026:

- 1 bar: N27, EV +0.3317R
- 2 bars: N6, EV +0.3838R
- 3–4 bars: N17, EV +0.2521R

Interpretation:

Fast confirmation is supportive historically, but the 2026 split is too small to justify a speed filter.

No confirmation-speed rule is promoted.

---

# Stage B — Full causal gating

Because post-hoc buckets can be misleading, a full stateful rerun was performed.

The gate is known at confirmation time and rejects the signal before passive limit entry.

Tested:

1. BASELINE
2. VETO_ALIGNED_GT_0P75
3. VETO_WITH_TREND_GT_0P75
4. VETO_COUNTERTREND_GT_0P75

## Historical causal results

| Mode | N | EV | PF | SumR | DD | R/DD | +years |
|---|---:|---:|---:|---:|---:|---:|---:|
| Baseline | 1227 | +0.1064 | 1.210 | +130.60 | **13.50** | **9.675** | 5/5 |
| Veto aligned >0.75 | 1053 | +0.1277 | 1.260 | +134.46 | 16.27 | 8.266 | 5/5 |
| Veto with-trend >0.75 | 1152 | +0.1226 | 1.246 | +141.25 | 19.28 | 7.327 | 5/5 |
| Veto countertrend >0.75 | 1131 | +0.1172 | 1.236 | +132.55 | 13.98 | 9.481 | 5/5 |

Historical EV/PF can improve, but DD and/or R/DD do not dominate baseline.

## 2026 causal results

| Mode | N | EV | PF | SumR | DD | R/DD | +months |
|---|---:|---:|---:|---:|---:|---:|---:|
| Baseline | 136 | **+0.2111** | 1.467 | **+28.71** | **6.49** | **4.424** | **6/6** |
| Veto aligned >0.75 | 119 | +0.1660 | 1.360 | +19.76 | 10.32 | 1.915 | 5/6 |
| Veto with-trend >0.75 | 125 | +0.1584 | 1.336 | +19.81 | 8.29 | 2.388 | 5/6 |
| Veto countertrend >0.75 | 129 | +0.2259 | 1.512 | +29.14 | 8.29 | 3.517 | 5/6 |

All veto variants lose the 6/6 positive-month property.

The strongest-looking diagnostic bucket therefore does **not** translate into a robust hard entry veto.

Reason:

Removing trades changes:
- occupancy,
- anti-repeat eligibility,
- timing of future entries,
- max-per-day state,
- reachable signals.

This repeats the lesson from weekday/time veto research.

---

# Main conclusion

**Crowd × trend × price-response is a real quality signal, but currently it is better interpreted as a risk-quality feature than as a binary entry filter.**

Strongest high-quality state:

> H1 + H4 aligned  
> CrowdFade trade WITH trend  
> crowd is against trend  
> crowd-direction excursion before confirm <=0.75 ATR

Historical:
- N312
- EV +0.223R
- PF 1.468
- positive contribution 5/5 years

2026:
- N32
- EV +0.454R
- PF 2.390

Weak state:

> H1 + H4 aligned  
> crowd-direction excursion >0.75 ATR before confirm

Historical:
- EV -0.036R
- PF 0.938

2026:
- EV +0.020R
- PF 1.040

But hard veto is rejected.

---

# Research implication

The next logical use of LAB025 is **risk scoring without changing trade reachability**.

Candidate hierarchy for a separate preregistered LAB:

- HIGH quality:
  - H1/H4 aligned
  - CrowdFade WITH trend
  - crowd excursion <=0.75 ATR
  - candidate risk boost, e.g. 1.50×

- NORMAL quality:
  - mixed / neutral or other baseline states
  - 1.00×

- LOW quality:
  - aligned H1/H4
  - crowd excursion >0.75 ATR
  - candidate reduced risk, e.g. 0.50–0.75×

Do not hard-veto LOW quality yet.

Fresh untouched forward is required before production promotion.
