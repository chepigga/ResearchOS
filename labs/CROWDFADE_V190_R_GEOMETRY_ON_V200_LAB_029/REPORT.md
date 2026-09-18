# CROWDFADE_V190_R_GEOMETRY_ON_V200_LAB_029

## Purpose

Test v190-style exit management on the frozen v200 entry while translating all price-management thresholds from ATR units into **initial R units**.

Frozen v200 entry/risk:

- Z = 2.50 / 2.50
- M15 confirmation = 0.25 ATR
- confirmation TTL = 60m
- passive retrace = 0.60 ATR
- limit TTL = 20m
- hard SL = 4.5 ATR = 1R
- max 3/day
- anti-repeat = 1 ATR
- LAB026 sizing:
  - HIGH 1.50x
  - NORMAL 1.00x
  - LOW 0.75x

v190-style exit geometry translated to R:

- BE trigger = +0.50R
- BE lock = +0.15R
- trail arm = +2.50R MFE
- trail distance = 0.50R from peak
- signal exit = opposite |Z| >= 1.00
- max hold = 6h
- no fixed TP

Equivalent ATR distances under v200 SL=4.5 ATR:

- BE trigger = +2.25 ATR
- BE lock = +0.675 ATR
- trail arm = +11.25 ATR
- trail distance = 2.25 ATR

---

# Historical 2021–2025

- N = **1604**
- WR = **54.55%**
- EV = **+0.03194R**
- SumR = **+51.23R**
- PF = **1.123**
- MaxDD = **14.12R**
- R/DD = **3.629**
- positive years = **5/5**

Annual:

- 2021: +19.94R
- 2022: +1.85R
- 2023: +5.85R
- 2024: +17.96R
- 2025: +5.64R

Exit mix:

- hard SL = 244
- BE/trail stop = 362
- signal exit = 489
- 6h time exit = 509

The R normalization fixes the mechanical over-tightening seen in LAB028, but the system remains materially weaker than the frozen TP10 + LAB026 configuration.

Reference TP10 + LAB026:

- N 1227
- EV +0.13661R
- Sum +167.62R
- PF 1.254
- MaxDD 13.39R
- R/DD 12.523

So historical R-geometry v190 exit gives:

- much lower EV;
- ~69% less SumR;
- slightly higher DD;
- ~71% lower R/DD.

---

# 2026 second-level forward-shadow

- N = **182**
- WR = **52.75%**
- EV = **-0.03119R**
- SumR = **-5.68R**
- PF = **0.881**
- MaxDD = **11.28R**
- R/DD = **-0.503**
- positive months = **2/6**

Monthly:

- March: -0.09R
- April: -2.18R
- May: +0.34R
- June: -2.29R
- July: +1.15R
- August: -2.62R

Exit mix:

- hard SL = 23
- BE/trail stop = 41
- signal exit = 53
- 6h time exit = 65

Reference TP10 + LAB026 2026:

- N 136
- EV +0.26359R
- Sum +35.85R
- PF 1.566
- MaxDD 6.75R
- R/DD 5.313
- 5/6 positive months

The requested v190 R-geometry configuration therefore fails forward-shadow decisively.

---

# Exit attribution

Historical weighted contribution:

- hard SL: **-254.43R**
- BE/trail stops: **+162.84R**
- signal exits: **-3.76R**
- 6h time exits: **+146.58R**

Historical signal exit is roughly neutral.

2026 weighted contribution:

- hard SL: **-24.16R**
- BE/trail stops: **+12.66R**
- signal exits: **-11.10R**
- 6h time exits: **+16.93R**

In 2026, signal exit becomes a major drag.

The 6h time exits themselves are positive on average (+0.260R weighted EV), so the failure cannot be blamed simply on the shorter hold.

---

# Quality-state inversion

Historical weighted state contribution:

- HIGH: +15.55R, EV +0.0386R
- NORMAL: +36.57R, EV +0.0413R
- LOW: -0.89R, EV -0.0028R

2026:

- HIGH: **-5.61R**, weighted EV **-0.1193R**
- NORMAL: -0.68R, EV -0.0068R
- LOW: **+0.61R**, weighted EV **+0.0175R**

This is crucial.

LAB026 quality ranking was discovered under the frozen TP10 / 24h exit architecture. Once the exit engine changes materially, the conditional value of HIGH/NORMAL/LOW also changes.

Therefore:

> LAB026 sizing is not proven to be exit-engine invariant.

Using HIGH=1.5x with the v190-style exit amplifies a state that is negative in 2026 under this new exit architecture.

This is a structural reason not to combine independently optimized entry/risk/exit components without integrated testing.

---

# Comparison to LAB028 literal ATR transfer

LAB028 literal ATR transfer:

Historical:
- EV +0.00484R
- Sum +8.17R
- PF 1.039

2026:
- EV -0.0111R
- Sum -2.08R
- PF 0.892

LAB029 R-geometry:

Historical:
- EV +0.03194R
- Sum +51.23R
- PF 1.123

2026:
- EV -0.03119R
- Sum -5.68R
- PF 0.881

So converting ATR thresholds to R **does correct the historical geometry mismatch**, but does not make the v190 exit architecture compatible with frozen v200 in the forward-shadow period.

---

# Verdict

**v190-style exit translated to R + frozen v200 entry + LAB026 = FAIL.**

The experiment answers two separate questions:

1. Was LAB028 bad only because ATR values were copied onto a wider stop?
   - **Partly.** R normalization improves historical expectancy substantially.

2. Does preserving v190 behavioral geometry create a better v200 system?
   - **No.** 2026 is negative and materially inferior to TP10 + LAB026.

Current robust reference remains:

> fixed TP 10 ATR + hard SL 4.5 ATR + 24h fallback + LAB026 sizing

Potential research implication:

- if dynamic exit is revisited, signal-exit should be isolated first;
- LAB026 sizing must be revalidated under any materially different exit engine rather than assumed portable.
