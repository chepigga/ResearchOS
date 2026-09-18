# CROWDFADE_RISK_TIERING_LAB_026

## Purpose

Test whether LAB025 quality states can improve portfolio-level return / drawdown by changing **risk only**, while keeping the exact same baseline trade sequence.

No trade is filtered.

No change to:
- crowd signal,
- Z threshold,
- confirmation,
- passive entry,
- stop,
- target,
- hold time,
- max trades/day,
- anti-repeat,
- occupancy,
- reachable signals.

## Fixed quality states

### HIGH

- H1 and H4 aligned and non-neutral;
- CrowdFade trade is WITH the aligned trend;
- crowd is therefore AGAINST trend;
- crowd-direction maximum excursion before confirmation <= 0.75 ATR.

### LOW

- H1 and H4 aligned and non-neutral;
- crowd-direction maximum excursion before confirmation > 0.75 ATR.

### NORMAL

All remaining baseline trades.

## Tested risk maps

1. BASELINE:
   - HIGH 1.00x
   - NORMAL 1.00x
   - LOW 1.00x

2. HIGH-only control:
   - HIGH 1.50x
   - NORMAL 1.00x
   - LOW 1.00x

3. Tiered 0.75:
   - HIGH 1.50x
   - NORMAL 1.00x
   - LOW 0.75x

4. Tiered 0.50:
   - HIGH 1.50x
   - NORMAL 1.00x
   - LOW 0.50x

---

# State counts

Historical 2021–2025:

- HIGH = 312 / 1227
- NORMAL = 670 / 1227
- LOW = 245 / 1227

2026 forward-shadow:

- HIGH = 32 / 136
- NORMAL = 77 / 136
- LOW = 27 / 136

---

# Historical full equity sequence

| Risk map | SumR | EV/trade | PF | MaxDD | R/DD | +years |
|---|---:|---:|---:|---:|---:|---:|
| 1 / 1 / 1 baseline | +130.60R | +0.1064 | 1.210 | 13.50R | 9.675 | 5/5 |
| 1.5 / 1 / 1 | +165.39R | +0.1348 | 1.238 | 14.46R | 11.438 | 5/5 |
| **1.5 / 1 / 0.75** | **+167.62R** | **+0.1366** | **1.254** | **13.39R** | **12.523** | **5/5** |
| 1.5 / 1 / 0.50 | +169.85R | +0.1384 | 1.273 | 14.10R | 12.049 | 5/5 |

Historical result:

**1.5 / 1 / 0.75 is the strongest risk-adjusted configuration.**

Versus baseline:

- SumR: +130.60 -> +167.62 = **+28.35%**
- EV: +0.1064 -> +0.1366 = **+28.35%**
- PF: 1.210 -> **1.254**
- MaxDD: 13.50 -> **13.39R** = slightly lower
- R/DD: 9.675 -> **12.523** = **+29.4%**
- positive years remain **5/5**

This is the first risk-sizing variant in the current research sequence that materially raises return while **not increasing historical MaxDD**.

## Historical annual 1.5 / 1 / 0.75

- 2021: +36.09R, DD 9.37R
- 2022: +32.17R, DD 11.06R
- 2023: +23.48R, DD 12.36R
- 2024: +44.53R, DD 13.39R
- 2025: +31.34R, DD 12.95R

All 5 years remain positive.

The 0.50x LOW version earns slightly more total R, but its sequence DD rises to 14.10R, so R/DD is lower than the 0.75x version.

---

# 2026 seconds forward-shadow / stress

| Risk map | SumR | EV/trade | PF | MaxDD | R/DD | +months |
|---|---:|---:|---:|---:|---:|---:|
| 1 / 1 / 1 baseline | +28.71R | +0.2111 | 1.467 | 6.49R | 4.424 | **6/6** |
| 1.5 / 1 / 1 | +35.98R | +0.2646 | 1.540 | 7.14R | 5.037 | 5/6 |
| **1.5 / 1 / 0.75** | **+35.85R** | **+0.2636** | **1.566** | **6.75R** | **5.313** | 5/6 |
| 1.5 / 1 / 0.50 | +35.72R | +0.2626 | 1.595 | 6.96R | 5.129 | 5/6 |

2026 result:

Again, **1.5 / 1 / 0.75 has the best R/DD** among tested maps.

Versus baseline:

- SumR +24.9%
- EV +24.9%
- PF improves 1.467 -> **1.566**
- DD rises only 4.0%: 6.49 -> 6.75R
- R/DD improves 4.424 -> **5.313** = **+20.1%**

However positive-month consistency falls:

- baseline = 6/6
- all HIGH=1.5 configurations = 5/6

August becomes negative.

## Why August changes

Raw August 2026 state contributions:

- HIGH: N4, SumR **-0.82R**
- NORMAL: N11, SumR **-3.98R**
- LOW: N8, SumR **+4.91R**

Baseline August:
- approximately +0.11R

At 1.5 / 1 / 0.75:
- HIGH losses are amplified;
- LOW rescue contribution is reduced;
- August becomes **-1.53R**.

At LOW 0.50x it becomes worse:
- August **-2.76R**.

Interpretation:

LOW is a weak state on average across the full sample, but not uniformly weak in every local regime.

Therefore:
- hard veto is wrong;
- aggressive 0.50x de-risking is too strong;
- 0.75x is the better compromise.

---

# State contributions

Historical baseline state contributions:

- HIGH: +69.58R
- NORMAL: +69.94R
- LOW: -8.93R

Historical 1.5 / 1 / 0.75:

- HIGH: +104.37R
- NORMAL: +69.94R
- LOW: -6.70R

2026 baseline:

- HIGH: +14.54R
- NORMAL: +13.64R
- LOW: +0.53R

2026 1.5 / 1 / 0.75:

- HIGH: +21.81R
- NORMAL: +13.64R
- LOW: +0.40R

---

# Prop-oriented risk examples

If base risk = 0.10%:

- HIGH = 0.15%
- NORMAL = 0.10%
- LOW = 0.075%

Historical sequence DD for 1.5 / 1 / 0.75:
- ~1.34% account equity

2026 sequence DD:
- ~0.67%

If base risk = 0.15%:

- HIGH = 0.225%
- NORMAL = 0.15%
- LOW = 0.1125%

Historical sequence DD:
- ~2.01%

2026:
- ~1.01%

If base risk = 0.25%:

- HIGH = 0.375%
- NORMAL = 0.25%
- LOW = 0.1875%

Historical sequence DD:
- ~3.35%

2026:
- ~1.69%

These are sequence MaxDD approximations in fixed base-risk units, not exact broker equity/daily-DD simulations.

---

# Verdict

## Leading candidate

**HIGH 1.50x / NORMAL 1.00x / LOW 0.75x**

This is currently the strongest quality-aware risk map.

Why:

- historical SumR +28.35%;
- historical MaxDD slightly lower than baseline;
- historical R/DD +29.4%;
- 5/5 years positive;
- 2026 SumR +24.9%;
- 2026 DD only +4.0%;
- 2026 R/DD +20.1%;
- PF improves in both periods;
- 0.75x LOW is superior to 0.50x on sequence efficiency.

## Important limitation

It loses the baseline property of 6/6 positive 2026 months because August turns negative.

This is caused by a local regime inversion:
- HIGH and NORMAL lose in August;
- LOW is strongly positive and rescues baseline.

Therefore the quality states should be interpreted probabilistically, not deterministically.

## Status

**Freeze as leading Candidate v2, not production-proven.**

Do not retune HIGH/LOW thresholds or multipliers immediately.

Next required validation:

1. leave-one-year-out / rolling stability;
2. block bootstrap / state clustering;
3. daily-DD prop audit;
4. fresh untouched forward;
5. broker-native execution / fill realism.

Full equity sequences:

- `output/equity_sequence_2021_2025.csv`
- `output/equity_sequence_2026.csv`
