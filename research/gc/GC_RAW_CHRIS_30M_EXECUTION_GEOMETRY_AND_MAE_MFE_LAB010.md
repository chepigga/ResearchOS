# GC RAW CHRIS 30M EXECUTION GEOMETRY AND MAE/MFE LAB010

**Status:** `HISTORICAL_EXECUTION_GEOMETRY_CANDIDATE_NOT_OOS_NOT_XAU_CERTIFIED`

## Purpose

Take the surviving frozen RAW Chris/AEIF SHORT family from LAB009 and audit the 30-minute execution geometry without changing signal thresholds.

This LAB is descriptive/historical. It uses GC raw Last-price ticks for path/first-passage. It does **not** yet model FTMO XAU Bid/Ask, spread, commission, slippage, stop-level/freeze-level constraints, or live latency.

## Frozen inputs

- Chris/AEIF signal: unchanged from LAB003/LAB009.
- Long-history quality segmentation: unchanged from LAB008H/LAB009.
- Events: **234**, exact parity with LAB009.
- Evaluation horizon: **30 minutes from entry**.
- Raw ticks inside event windows: **651,147** extracted from the compact AMP/CQG @GCE directional history.

No new signal selector or score was introduced.

## 1. MAE / MFE geometry

For SHORT trades, MFE is downward favorable excursion from entry in seed-ATR units; MAE is upward adverse excursion.

### MAE distribution

- P10: **0.454 ATR**
- P25: **0.979 ATR**
- Median: **2.189 ATR**
- P75: **3.775 ATR**
- P90: **6.207 ATR**
- P95: **7.977 ATR**

### MFE distribution

- P10: **0.506 ATR**
- P25: **1.346 ATR**
- Median: **2.812 ATR**
- P75: **4.947 ATR**
- P90: **7.689 ATR**
- P95: **10.285 ATR**

### Timing

Time to maximum favorable excursion inside 30m:

- P25: **4.71m**
- Median: **14.79m**
- P75: **24.12m**
- P90: **27.85m**

Time to maximum adverse excursion:

- P25: **3.87m**
- Median: **11.99m**
- P75: **23.38m**
- P90: **28.59m**

This is consistent with LAB009: a large part of the useful move develops late in the 30-minute window.

## 2. Winners and losers separate cleanly in MAE/MFE

Using the frozen LAB009 +30m endpoint classification:

### +30m winners

- N = **113**
- median MAE = **1.103 ATR**
- P75 MAE = **1.909 ATR**
- P90 MAE = **3.139 ATR**
- median MFE = **4.407 ATR**
- P75 MFE = **6.308 ATR**
- median time-to-MFE = **24.02m**

### +30m losers

- N = **107**
- median MAE = **3.767 ATR**
- P75 MAE = **5.644 ATR**
- P90 MAE = **7.990 ATR**
- median MFE = **1.537 ATR**
- P75 MFE = **2.623 ATR**
- median time-to-MFE = **4.89m**

Interpretation: true winners often tolerate some adverse movement, but losers exhibit much larger adverse excursions and their favorable excursion tends to peak early and then fail.

This suggests that **dynamic failure logic may ultimately be more promising than an ultra-tight fixed stop**, but that requires a separate causal LAB.

## 3. Hard-stop / hard-target first-passage audit

All first-passage tests use actual GC Last-tick sequence. If TP or SL is reached first, the trade closes there; otherwise it exits at the 30m timeout. All tested pairs respect the user rule TP >= 1.5x SL.

| SL ATR | TP ATR | R:R | EV R | Positive-return rate | Max consecutive negative | Positive windows |
|---:|---:|---:|---:|---:|---:|---:|
| 0.75 | 1.50 | 2.0 | +0.136R | 38.0% | 9 | 5/9 |
| 1.00 | 1.50 | 1.5 | +0.147R | 46.2% | 8 | 5/9 |
| **1.00** | **2.00** | **2.0** | **+0.178R** | **40.2%** | **8** | **5/9** |
| 1.50 | 2.25 | 1.5 | +0.152R | 47.0% | 7 | 6/9 |
| 1.50 | 3.00 | 2.0 | +0.150R | 41.0% | 7 | 5/9 |

### SL 1.0 / TP 2.0 ATR candidate

- N = 234
- EV = **+0.178R**
- 2025 EV = **+0.222R**
- 2026 EV = **+0.124R**
- max consecutive negative outcomes = **8**
- event bootstrap P(EV>0) = **97.0%**
- 95% bootstrap CI = **[-0.007R, +0.364R]**

This is the strongest EV of the deliberately small geometry set, but the 95% lower bound still touches negative territory. Therefore it is a **candidate geometry, not a certified stop/target**.

The narrow 0.75 ATR stop is especially problematic for prop use: it is hit first in about 62% of events and produces a nine-loss maximum historical negative run.

## 4. Pullback-limit entry audit

Because the preferred trading rule is to wait for confirmation and use limits where possible, a simple SHORT pullback-limit was tested:

- anchor = original frozen Chris entry
- order = SHORT LIMIT above anchor by fixed ATR offset
- expiry = **5 minutes**
- if unfilled: no trade
- if filled: exit at the original +30m horizon
- no SL/TP here; this subtest isolates entry geometry only

| Limit offset | Fill rate | EV/fill ATR | WR | EV/signal ATR | Median fill delay |
|---:|---:|---:|---:|---:|---:|
| +0.25 ATR | 80.3% | +0.524 | 54.3% | +0.421 | 0.38m |
| **+0.50 ATR** | **69.2%** | **+0.612** | **55.6%** | **+0.424** | **0.89m** |
| +0.75 ATR | 55.6% | +0.523 | 51.5% | +0.291 | 1.27m |
| +1.00 ATR | 42.7% | +0.658 | 52.0% | +0.281 | 1.97m |

### +0.50 ATR / 5m limit robustness

- fills = **162 / 234**
- fill rate = **69.2%**
- EV/fill = **+0.612 ATR**
- WR = **55.6%**
- 2025 EV/fill = **+0.556 ATR**
- 2026 EV/fill = **+0.675 ATR**
- positive windows = **6/9**
- bootstrap P(EV>0) = **96.9%**
- 95% bootstrap CI still crosses zero

Important: the limit improves average entry quality **per filled trade**, but signal-level EV (~+0.424 ATR) is almost the same as the immediate raw +30m edge (~+0.432 ATR). In other words, the limit mainly exchanges trade count for better fill quality; it does not magically create extra total edge.

## 5. Path-order diagnostics

Across all 234 events:

- +0.5 ATR favorable before -0.5 ATR adverse: **53.4%**
- +1.0 ATR favorable before -0.5 ATR adverse: **38.9%**
- +1.0 ATR favorable before -1.0 ATR adverse: **53.4%**
- +1.5 ATR favorable before -1.0 ATR adverse: **45.3%**

The path is therefore not an immediate one-way collapse. A material fraction of winning 30m trades first retrace against the SHORT entry.

## Decision

1. **RAW Chris 30m remains viable as a historical execution candidate.**
2. **Do not use an ultra-tight 0.75 ATR stop.** It cuts too many delayed winners and creates long stop streaks.
3. The best fixed pair in this bounded audit is **SL 1.0 ATR / TP 2.0 ATR**, EV ~+0.178R, but it is not yet production-certified.
4. A **+0.50 ATR SHORT LIMIT valid for 5m** is a particularly interesting entry candidate: lower trade count, higher quality per fill, positive in both 2025 and 2026.
5. However the pullback-limit and hard-stop tests have not yet been combined. Combining them now and selecting the best result on the same sample would create another optimization layer.
6. The next valid step is therefore a **preregistered XAU transfer/execution LAB** with a small frozen candidate set, not another unconstrained GC sweep.

## Recommended freeze for next LAB

Carry only two entry modes forward:

- **A — immediate:** frozen Chris entry, SL 1.0 ATR, TP 2.0 ATR, max hold 30m.
- **B — pullback candidate:** SHORT LIMIT at +0.50 seed ATR, 5m expiry; stop/target geometry must be preregistered before looking at XAU outcomes.

The XAU LAB must use executable Bid/Ask, include spread + commission + slippage stress, enforce one-position logic, and report prop-compatible drawdown at **0.25% risk** first.

**Research status:** `CANDIDATE_EXECUTION_GEOMETRY_FOUND — NOT OOS — NOT FTMO XAU CERTIFIED`.
