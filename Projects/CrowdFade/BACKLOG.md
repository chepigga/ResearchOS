# CrowdFade Research Backlog

_Last updated: 2026-09-18_

## Scope

This backlog is the canonical research-state summary for the **CRYPTO BOT — CrowdFade** branch.

Do not mix this branch with GC/COMEX, GC→XAU, BTC AEIF, XAU systems, or unrelated EAs.

Active repo branch:

`lab/crowdfade-execution-5y-positive-005`

---

## Frozen production-oriented core

Current frozen candidate logic:

- Signal source: Binance BTCUSDT Global Long/Short crowd ratio.
- Rolling normalization: 72 observations.
- Contrarian direction:
  - high positive Z = crowd LONG → CrowdFade SHORT;
  - high negative Z = crowd SHORT → CrowdFade LONG.
- `ZLong = 2.50`
- `ZShort = 2.50`
- M15 confirmation = `0.25 ATR`, completed close.
- Confirmation TTL = `60m`.
- Passive limit retrace = `0.60 ATR`.
- Limit TTL = `20m`.
- Market fallback = OFF.
- Maker cost proxy = `0.5 bps`.
- Max trades/day = `3`.
- SL = `4.5 ATR`.
- TP = `10 ATR`.
- Max hold = `24h`.
- Breakeven = OFF.
- Trailing = OFF.
- Inherited anti-repeat gate = `1 ATR` ON.
- All weekdays ON.
- All UTC hours ON.
- No side/time veto in production candidate.

Important parity behavior:

`if has and abs(sig-last) < 1 ATR: skip`

This inherited anti-repeat/pause gate materially changes the sequential system and must not be removed casually.

---

## Frozen baseline

### Historical 2021–2025

- N = **1227**
- ~20.45 trades/month
- EV = **+0.106435R**
- PF = **1.210426**
- MaxDD = **13.4977R**
- SumR = **+130.596R**
- R/DD = **9.675**
- positive years = **5/5**

Annual:

- 2021: +26.340R
- 2022: +27.135R
- 2023: +20.455R
- 2024: +40.103R
- 2025: +16.562R

### 2026 seconds forward-shadow / stress

- N = **136**
- ~22.67 trades/month
- EV = **+0.211108R**
- PF = **1.467315**
- MaxDD = **6.4893R**
- SumR = **+28.711R**
- positive months = **6/6**

Monthly:

- Mar +6.814R
- Apr +6.401R
- May +10.007R
- Jun +3.065R
- Jul +2.315R
- Aug +0.108R

Methodology warning:

- 2021–2025 is discovery / in-sample.
- 2026 has been reused across multiple LABs; it is forward-shadow/stress, **not pristine OOS**.
- Historical data is Binance futures proxy, not broker-native execution.
- Passive touch fills are optimistic and remain a transfer-risk item.

---

# Completed recent LABs

## LAB016 — Side threshold asymmetry

**Result: FAIL / no promotion**

Keep:

- `ZLong = 2.50`
- `ZShort = 2.50`

Do not promote v1.93 asymmetric `2.50 / 2.75`.

---

## LAB017 — Fri / Sat causal veto

**Result: FAIL**

All weekdays remain ON.

Negative post-hoc weekday buckets did not survive full causal rerun because removing trades changes:

- eligibility,
- anti-repeat state,
- occupancy,
- max-per-day,
- reachable signals.

---

## LAB018 — Coarse time-window veto

Tested:

- veto 04–07 UTC,
- veto 18–20 UTC,
- both.

**Result: FAIL**

All UTC hours remain ON.

Important interaction clue:

- 2026 removing 04–07 harmed LONG side strongly.
- This motivated side × time testing.

Note: numbering collision exists with an older queue/fill LAB018 idea. Future queue/fill work must use a new descriptive LAB number.

---

## LAB019 — Side × time causal interaction

Atomic tests only:

- VETO_LONG_04_07
- VETO_SHORT_04_07
- VETO_LONG_18_20
- VETO_SHORT_18_20

**Production verdict: no side×time veto promoted.**

Key conclusions:

- LONG 04–07: false/in-sample edge; rejected by 2026.
- SHORT 04–07: not robust.
- LONG 18–20: no forward benefit.
- SHORT 18–20: only surviving watch candidate.

SHORT 18–20 watch candidate:

Historical:
- EV +0.10935R
- PF 1.2161
- DD 15.37R
- SumR +130.67R
- 5/5 years

2026:
- EV +0.22012R
- PF 1.4917
- DD 6.489R
- SumR +29.717R
- 6/6 months

Why not promote:
- historical DD worsens;
- historical R/DD falls;
- historical gain is tiny;
- 2026 is reused forward-shadow.

---

## LAB020 — Exit risk diagnostics: stop / BE / continuous trailing

### Stop geometry

| Stop | Hist EV | Hist PF | Hist DD | Hist SumR | 2026 EV | 2026 PF | 2026 DD |
|---|---:|---:|---:|---:|---:|---:|---:|
| Wide 4.5 ATR | +0.1064 | 1.210 | 13.50R | +130.60R | +0.2111 | 1.467 | 6.49R |
| Narrow 2.5 ATR | +0.1696 | 1.250 | 24.34R | +231.31R | +0.2137 | 1.323 | 12.37R |
| Vol-adaptive 3→4.5 ATR | +0.1421 | 1.253 | 28.21R | +179.67R | +0.2007 | 1.405 | 9.10R |

Conclusion:

- narrow stops increase absolute R but materially worsen DD;
- current volatility-adaptive rule does not dominate fixed wide stop;
- **4.5 ATR remains robustness anchor for prop-oriented use**.

Path diagnostic:

- 1216 / 1227 historical trades had some adverse excursion after entry = **99.10%**.
- 135 / 136 in 2026 = **99.26%**.

Interpretation:

CrowdFade normally needs room after entry. The assumption “good entry should immediately move positive” is false for this system.

### Breakeven

| BE trigger | Hist EV | Hist DD | Hist SumR | 2026 EV | 2026 SumR |
|---|---:|---:|---:|---:|---:|
| OFF | +0.1064 | 13.50R | +130.60R | +0.2111 | +28.71R |
| +0.5R | +0.0344 | 15.50R | +45.99R | +0.1530 | +22.64R |
| +1.0R | +0.0673 | 16.32R | +84.70R | +0.1896 | +25.97R |
| +1.5R | +0.1001 | 17.44R | +123.42R | +0.2358 | +32.07R |
| +2.0R | +0.1058 | 13.50R | +129.87R | +0.2186 | +29.72R |

Conclusion:

- BE 0.5R = harmful.
- BE 1.0R = harmful.
- BE 2.0R changes almost nothing.
- **BE 1.5R = watch-only research candidate**, because 2026 improves but historical risk efficiency worsens.
- Production candidate remains **BE OFF**.

Future idea:

Instead of universal BE, investigate a **failure-after-profit detector**:
- trades that reach +1R / +1.5R,
- then reverse toward SL,
- distinguish them causally from trades that continue toward TP.

### Continuous trailing

Historical update frequency: completed 1m bars.
2026 proxy: completed 1-second OHLC, stop effective next second.

| Trail | Hist EV | Hist SumR | 2026 EV | 2026 SumR |
|---|---:|---:|---:|---:|
| OFF | +0.1064 | +130.60R | +0.2111 | +28.71R |
| 1R trail after +1R | +0.0588 | +76.31R | +0.1324 | +18.67R |
| 2R trail after +1R | +0.0899 | +111.08R | +0.1824 | +24.80R |

Conclusion:

- continuous trailing raises apparent WR in some variants but truncates the right tail;
- **trailing remains OFF**.

---

## LAB021 — Structure-adaptive stop

Goal:

Test whether stop distance should depend on causal trend or level-break structure.

Fixed structure proxies only; no period optimization:

Trend:
- LONG: close > EMA50 and EMA50 > EMA50[-4]
- SHORT mirror

Breakout:
- LONG: close > prior 20-M15 high
- SHORT: close < prior 20-M15 low

Stops:
- narrow = 3.0 ATR
- wide = 4.5 ATR

Key result:

The intuitive rule:

> strong trend / breakout supports trade → use narrower stop

**does not survive 2026.**

Best watch interaction was the mirror:

> breakout aligned → keep 4.5 ATR  
> otherwise → 3 ATR

Historical:
- EV +0.1442R
- PF 1.245
- DD 19.71R
- 5/5 years

2026:
- EV +0.2929R
- PF 1.546
- SumR +41.30R
- DD 10.80R
- 5/6 months

But fixed 3 ATR control historically remained stronger in EV/PF, so the breakout rule is not stable enough to promote.

Conclusion:

- no adaptive stop promoted;
- fixed 4.5 ATR remains production-oriented stop;
- trend/breakout information looks more promising for **entry quality or risk sizing** than direct stop switching.

---

## LAB022 — H1 / H4 trend × crowd alignment

Purpose:

Determine whether the crowd is trading with or against higher-timeframe trend, and whether CrowdFade therefore trades with or against trend.

Trend definition:

H1 / H4:
- UP = completed close > EMA50 and EMA50 slope over 4 bars > 0
- DOWN = mirror
- otherwise NEUTRAL

Strong trend:
- H1 and H4 both non-neutral,
- both aligned in the same direction.

### H1

Historical:

- crowd WITH H1 trend / CrowdFade countertrend:
  - N 425
  - EV +0.0873R
  - PF 1.171

- crowd AGAINST H1 trend / CrowdFade WITH trend:
  - N 630
  - EV **+0.1325R**
  - PF **1.263**

2026:

- crowd WITH H1:
  - N 40
  - EV +0.1881R
  - PF 1.395

- crowd AGAINST H1 / CrowdFade WITH H1:
  - N 69
  - EV **+0.3182R**
  - PF **1.776**

### H4

Historical:

- crowd WITH H4 / CrowdFade countertrend:
  - N 625
  - EV +0.0575R
  - PF 1.112

- crowd AGAINST H4 / CrowdFade WITH H4:
  - N 519
  - EV **+0.1616R**
  - PF **1.320**

2026:

- crowd WITH H4:
  - N 66
  - EV +0.1821R
  - PF 1.352

- crowd AGAINST H4 / CrowdFade WITH H4:
  - N 63
  - EV **+0.2851R**
  - PF **1.772**

### Strong H1 + H4 aligned

Historical:

- crowd WITH aligned trend → CrowdFade countertrend:
  - N 369
  - EV +0.0631R
  - PF 1.121

- crowd AGAINST aligned trend → CrowdFade WITH trend:
  - N **438**
  - EV **+0.1609R**
  - PF **1.320**
  - SumR +70.48R

2026:

- crowd WITH aligned trend → CrowdFade countertrend:
  - N 31
  - EV +0.2216R
  - PF 1.457

- crowd AGAINST aligned trend → CrowdFade WITH trend:
  - N **50**
  - EV **+0.3109R**
  - PF **1.852**
  - SumR +15.54R

Core interpretation:

> **The strongest context is H1 + H4 aligned, crowd positioned against that trend, CrowdFade trade therefore following the trend.**

Historical EV is about 2.55× larger than the opposite aligned context.

Important weak state historically:

> strong H1+H4 UP  
> crowd LONG  
> CrowdFade SHORT against uptrend

- N 214
- EV **+0.018R**
- PF **1.034**

Do not convert this directly into a veto yet because 2026 strong-UP sample did not reproduce the historical weakness cleanly.

---

## LAB023 — H1/H4 aligned trend risk multiplier

Target state:

> H1 and H4 aligned and non-neutral  
> crowd against trend  
> CrowdFade trade with trend

Risk multipliers tested only on target state:

- 1.00×
- 1.25×
- 1.50×
- 2.00×

All non-target trades remain 1.00×.

### Historical full equity sequence

Target trades:
- 438 / 1227 = 35.70%

| Mult | SumR | EV/trade | PF | MaxDD | R/DD | +years |
|---:|---:|---:|---:|---:|---:|---:|
| 1.00× | +130.60R | +0.1064 | 1.210 | 13.50R | **9.675** | 5/5 |
| 1.25× | +148.22R | +0.1208 | 1.219 | 15.33R | 9.669 | 5/5 |
| 1.50× | **+165.84R** | **+0.1352** | 1.227 | 17.16R | 9.664 | 5/5 |
| 2.00× | +201.08R | +0.1639 | 1.239 | 20.82R | 9.657 | 5/5 |

Historical interpretation:

- return rises almost linearly;
- DD rises almost linearly;
- R/DD does **not** improve;
- this is not a free risk-efficiency gain.

Important clustering warning:

2023:

- baseline: +21.02R, DD 8.54R
- 2.0×: +22.32R, DD **18.41R**

### 2026 full equity sequence

Target trades:
- 50 / 136 = 36.76%

| Mult | SumR | EV/trade | PF | MaxDD | R/DD | +months |
|---:|---:|---:|---:|---:|---:|---:|
| 1.00× | +28.71R | +0.2111 | 1.467 | 6.49R | 4.424 | 6/6 |
| 1.25× | +32.60R | +0.2397 | 1.494 | 7.07R | 4.612 | 6/6 |
| 1.50× | **+36.48R** | **+0.2683** | **1.517** | 7.65R | **4.771** | 6/6 |
| 2.00× | +44.25R | +0.3254 | 1.555 | 8.85R | 5.003 | 6/6 |

2026 shows improved risk efficiency, but this period is not pristine OOS.

### Current risk-scaling watch candidate

**1.50×** on target state.

Reason:

- historical SumR +27%;
- historical DD +27% → risk efficiency roughly unchanged rather than worse;
- 5/5 historical years remain positive;
- 2026 SumR +27%;
- 2026 DD +17.9%;
- 2026 R/DD improves;
- 6/6 months remain positive;
- less aggressive than 2×.

Not production-proven.

Risk examples:

If base risk = 0.10%:
- normal trade 0.10%
- target state at 1.5× = 0.15%

If base = 0.15%:
- target = 0.225%

If base = 0.25%:
- target = 0.375%

For prop-oriented use, do not promote 2× without fresh untouched forward validation.

Full sequence files:

- `labs/CROWDFADE_H1_H4_RISK_MULTIPLIER_LAB_023/output/equity_sequence_2021_2025.csv`
- `labs/CROWDFADE_H1_H4_RISK_MULTIPLIER_LAB_023/output/equity_sequence_2026.csv`

---

# Current production vs research state

## Keep frozen / production-oriented candidate

- Z 2.50 / 2.50
- M15 confirm 0.25 ATR
- passive limit retrace 0.60 ATR
- 4.5 ATR stop
- 10 ATR TP
- 24h max hold
- no BE
- no trailing
- no weekday veto
- no hour veto
- no side×time veto
- 1 ATR anti-repeat ON
- base risk remains unchanged in production candidate

## Research watch candidates only

1. **H1+H4 aligned + crowd against trend + CrowdFade with trend → 1.50× risk**
   - strongest current risk-sizing candidate;
   - not production-proven.

2. **BE at +1.5R**
   - 2026 positive;
   - historical risk profile weaker;
   - no promotion.

3. **SHORT 18–20 UTC veto**
   - tiny cross-period point-estimate improvement;
   - historical DD worsens;
   - no promotion.

4. **Breakout-aligned keep-wide / otherwise narrow**
   - interesting 2026 interaction;
   - historical control does not confirm dominance;
   - no promotion.

---

# Priority backlog

## P0 — Fresh untouched forward validation

After freezing any candidate rule, obtain a truly fresh period not reused in LAB006–023.

Required:
- no retuning after seeing results;
- report exact candidate parity;
- monthly sequence;
- broker/exchange execution differences;
- DD clustering;
- target-state frequency.

Highest-priority candidate for fresh validation:

> baseline + **1.50× risk only on H1+H4 aligned / crowd against trend / CrowdFade with trend**

---

## P0 — Passive fill realism / queue transfer risk

Major unresolved transfer risk.

Current passive fill model is optimistic because touch is treated as fill.

New LAB should test a robustness envelope, not optimize a best value.

Suggested fixed ladder:

- touch baseline;
- require penetration 0.05 ATR;
- require penetration 0.10 ATR;
- require penetration 0.20 ATR;

or equivalent deterministic fill haircuts / delay assumptions.

Record:

- fill rate,
- rejected fills,
- trades/month,
- EV,
- PF,
- DD,
- SumR,
- historical annual,
- 2026 monthly,
- side split,
- effect on 1.50× target-state risk scaling.

2026 second data should be used for penetration/delay realism.

---

## P1 — LAB023 stability validation

For the fixed 1.50× target-state multiplier:

- leave-one-year-out sensitivity;
- annual contribution concentration;
- paired monthly / weekly block bootstrap;
- target-state clustering;
- worst streak of boosted losses;
- rolling 6m / 12m R/DD;
- compare 1.0× vs 1.5× only;
- no multiplier optimization.

Strict criterion:

Do not promote if improvement depends on one year / a few blocks or if DD concentration becomes materially worse.

---

## P1 — Daily drawdown / prop-sequence audit

Current LAB023 uses full equity MaxDD, not prop daily DD.

Need exact daily sequence at base risk examples:

- 0.10%
- 0.15%
- 0.25%

For 1.0× and 1.5× target-state scaling.

Report:

- worst closed-equity day,
- worst intraday equity day if possible,
- maximum 2-day / 3-day loss cluster,
- probability / empirical count of touching 4% daily DD at scaled risk,
- overall DD,
- max consecutive losses,
- boosted-loss clustering.

---

## P1 — Failure-after-profit detector

Instead of universal BE:

Study trades that:

1. reach +1.0R or +1.5R,
2. subsequently reverse strongly,
3. end at SL or poor time exit.

Goal:

Find a causal state variable that can exit failed winners without truncating healthy right-tail trades.

Do not retune signal simultaneously.

---

## P1 — Trend state as risk quality, not stop distance

LAB022/023 suggest H1/H4 state is more useful for sizing than stop switching.

Future clean tests:

- 1.0× normal;
- 1.5× only target state;
- optionally reduced risk when CrowdFade is countertrend to aligned H1+H4;
- avoid hard veto first.

Potential asymmetric risk test:

- CrowdFade with aligned H1+H4 = 1.50×
- mixed/neutral = 1.00×
- CrowdFade against aligned H1+H4 = 0.75× or 0.50×

This must be a separately preregistered LAB.

---

## P2 — Strong-UP weak-state causal audit

Historical warning state:

> H1 UP + H4 UP + crowd LONG + CrowdFade SHORT

Historical:
- N 214
- EV +0.018R
- PF 1.034

But 2026 did not confirm weakness.

Do not veto now.

Possible future validation:
- causal risk reduction only,
- no hard removal,
- leave-one-year-out + fresh forward required.

---

## P2 — Broker-native execution parity

Before production scaling:

- broker-native BTC symbol / CFD or exchange execution must be specified;
- spreads;
- commissions;
- maker/taker semantics;
- order types;
- stop/freeze level;
- min lot / volume step;
- slippage;
- latency;
- VPS;
- partial fills;
- limit-fill behavior.

Do not translate Binance research metrics directly to broker PnL without execution validation.

---

# Guardrails

Do not:

- optimize signal threshold together with exit/risk logic;
- remove inherited 1 ATR anti-repeat gate casually;
- promote post-hoc buckets directly into filters;
- use 2026 as pristine OOS;
- select 2× multiplier because it has highest SumR;
- treat 1-second OHLC as true exchange tick sequence;
- assume passive touch = guaranteed fill;
- add early BE/trailing merely to raise win rate.

Priority objective remains:

> stable equity curve, realistic execution, low drawdown, and robust prop-challenge survivability — not maximum backtest SumR.

---

## LAB024 — Continuous trailing distance 0.5R / 1.0R / 2.5R

Definition:

- hard SL remains 4.5 ATR = 1R;
- trailing activates after +1R MFE;
- trail distance tested: 0.5R, 1.0R, 2.5R;
- historical update resolution = completed 1m bars;
- 2026 = completed 1-second OHLC;
- full causal rerun because earlier exits change future reachable signals.

### Historical 2021–2025

| Mode | N | EV | PF | SumR | MaxDD | R/DD |
|---|---:|---:|---:|---:|---:|---:|
| No trail | 1227 | +0.1064R | 1.210 | +130.60R | 13.50R | 9.675 |
| Trail 0.5R | 1348 | +0.0451R | 1.105 | +60.75R | 15.00R | 4.050 |
| Trail 1.0R | 1298 | +0.0588R | 1.136 | +76.31R | 14.61R | 5.223 |
| Trail 2.5R | 1228 | +0.1027R | 1.204 | +126.15R | 14.44R | 8.738 |

### 2026 seconds forward-shadow

| Mode | N | EV | PF | SumR | MaxDD | R/DD | +months |
|---|---:|---:|---:|---:|---:|---:|---:|
| No trail | 136 | +0.2111R | 1.467 | +28.71R | 6.49R | 4.424 | 6/6 |
| Trail 0.5R | 150 | +0.0835R | 1.210 | +12.52R | 7.18R | 1.743 | 5/6 |
| Trail 1.0R | 141 | +0.1324R | 1.332 | +18.67R | 7.60R | 2.456 | 5/6 |
| Trail 2.5R | 136 | **+0.2191R** | **1.494** | **+29.80R** | **6.39R** | **4.665** | **6/6** |

Verdict:

- **0.5R trailing = strong FAIL**
- **1.0R trailing = strong FAIL**
- **2.5R trailing = watch candidate only**
- production core remains **TRAILING OFF**

Why 2.5R is different:

At +1R activation, a 2.5R distance initially does not tighten beyond the original hard stop. It only becomes meaningfully protective after larger MFE, so it preserves most of the right tail.

2026 improves slightly, but historical 5-year metrics remain slightly inferior to no-trail baseline. Requires stability + fresh untouched forward before promotion.

---

## LAB025 — Crowd × Trend × Price-Response

Purpose:

Test whether CrowdFade edge depends on:

1. H1/H4 trend alignment;
2. whether crowd is with or against that trend;
3. how much price actually moves in the crowd direction before frozen contrarian confirmation.

Price-response is causal at confirmation time:

- FAIL: crowd-direction excursion <= 0.25 ATR
- CONTESTED: >0.25 and <=0.75 ATR
- CONTINUATION: >0.75 ATR

### Strongest diagnostic state

> H1 + H4 aligned  
> CrowdFade WITH trend / crowd AGAINST trend  
> crowd-direction excursion <=0.75 ATR before confirmation

Historical:
- N312
- EV **+0.2230R**
- PF **1.468**
- SumR +69.58R
- positive contribution 5/5 years

2026:
- N32
- EV **+0.4544R**
- PF **2.390**
- SumR +14.54R

### Broad aligned price-response split

Aligned H1/H4 + crowd excursion <=0.75 ATR:

Historical:
- N562
- EV **+0.1827R**
- PF **1.383**
- SumR +102.70R
- DD 9.99R
- 5/5 years positive

2026:
- N54
- EV **+0.4052R**
- PF **2.094**
- SumR +21.88R
- DD 4.55R

Aligned H1/H4 + crowd excursion >0.75 ATR:

Historical:
- N245
- EV **-0.0364R**
- PF **0.938**
- SumR -8.93R

2026:
- N27
- EV **+0.0197R**
- PF **1.040**
- SumR +0.53R

Countertrend + crowd continuation >0.75 ATR is negative in both samples:
- historical EV -0.0826R / PF 0.864
- 2026 EV -0.0522R / PF 0.915

### Confirmation speed

WITH_TREND historical:
- 1 M15 bar: EV +0.2065R
- 2 bars: EV +0.1405R
- 3–4 bars: EV +0.0559R

2026 remains positive across all speed buckets, so no speed filter is promoted.

### Stage B causal gate

Full stateful rerun tested hard veto when crowd continuation >0.75 ATR.

Result: **hard veto rejected**.

Historical VETO_ALIGNED_GT_0P75:
- EV +0.1277R
- PF 1.260
- SumR +134.46R
- DD 16.27R
- R/DD 8.27 vs baseline 9.68

2026:
- EV +0.1660R
- PF 1.360
- SumR +19.76R
- DD 10.32R
- R/DD 1.92
- only 5/6 positive months

VETO_COUNTERTREND_GT_0P75 was the least harmful veto but still did not dominate:
- historical R/DD 9.48 vs baseline 9.68
- 2026 R/DD 3.52 vs baseline 4.42
- 5/6 months

Conclusion:

**Price-response is a strong trade-quality signal, but should not currently be used as binary entry veto.**

Best interpretation:

- HIGH quality:
  - H1/H4 aligned
  - CrowdFade WITH trend
  - crowd excursion <=0.75 ATR
  - candidate for higher risk

- NORMAL quality:
  - mixed / other baseline states
  - base risk

- LOW quality:
  - aligned H1/H4
  - crowd excursion >0.75 ATR
  - candidate for reduced risk, not veto

Next priority LAB:

**risk-tiering without changing trade reachability**, e.g.
- HIGH = 1.50×
- NORMAL = 1.00×
- LOW = 0.50–0.75×

This should be tested as a separate preregistered sequence-risk LAB.

---

## LAB026 — Quality-state risk tiering

Purpose:

Use LAB025 quality states for **risk sizing only**, preserving the exact baseline trade sequence.

Fixed states:

- HIGH:
  - H1/H4 aligned;
  - CrowdFade WITH trend;
  - crowd excursion <=0.75 ATR.
- LOW:
  - H1/H4 aligned;
  - crowd excursion >0.75 ATR.
- NORMAL:
  - all other baseline trades.

Tested:

- 1 / 1 / 1 baseline
- 1.5 / 1 / 1
- 1.5 / 1 / 0.75
- 1.5 / 1 / 0.50

### Historical 2021–2025

| Risk map | SumR | EV | PF | MaxDD | R/DD | +years |
|---|---:|---:|---:|---:|---:|---:|
| 1 / 1 / 1 | +130.60R | +0.1064 | 1.210 | 13.50R | 9.675 | 5/5 |
| 1.5 / 1 / 1 | +165.39R | +0.1348 | 1.238 | 14.46R | 11.438 | 5/5 |
| **1.5 / 1 / 0.75** | **+167.62R** | **+0.1366** | **1.254** | **13.39R** | **12.523** | **5/5** |
| 1.5 / 1 / 0.50 | +169.85R | +0.1384 | 1.273 | 14.10R | 12.049 | 5/5 |

Historical best risk-adjusted result:
**HIGH 1.5 / NORMAL 1 / LOW 0.75**

Versus baseline:
- SumR +28.35%
- EV +28.35%
- PF improves
- MaxDD slightly lower
- R/DD +29.4%
- 5/5 years remain positive

### 2026 seconds forward-shadow

| Risk map | SumR | EV | PF | MaxDD | R/DD | +months |
|---|---:|---:|---:|---:|---:|---:|
| 1 / 1 / 1 | +28.71R | +0.2111 | 1.467 | 6.49R | 4.424 | 6/6 |
| 1.5 / 1 / 1 | +35.98R | +0.2646 | 1.540 | 7.14R | 5.037 | 5/6 |
| **1.5 / 1 / 0.75** | **+35.85R** | **+0.2636** | **1.566** | **6.75R** | **5.313** | 5/6 |
| 1.5 / 1 / 0.50 | +35.72R | +0.2626 | 1.595 | 6.96R | 5.129 | 5/6 |

2026:
- 1.5 / 1 / 0.75 again gives best R/DD.
- SumR +24.9%.
- DD only +4.0%.
- R/DD +20.1%.
- But monthly consistency drops from 6/6 to 5/6.

### August regime inversion

August 2026 raw state contributions:

- HIGH: -0.82R
- NORMAL: -3.98R
- LOW: +4.91R

Therefore LOW was the rescue state in August.

Consequences:
- LOW cannot be treated as deterministic bad state;
- hard veto remains rejected;
- LOW 0.50x is too aggressive;
- LOW 0.75x is the better compromise.

### Current status

**Leading Candidate v2: HIGH 1.50x / NORMAL 1.00x / LOW 0.75x**

Do not tune further yet.

Not production-proven because:
- 2026 is reused forward-shadow;
- positive-month property drops from 6/6 to 5/6;
- quality-state behavior can invert locally;
- execution/fill realism remains unresolved.

Required next validation:
- leave-one-year-out / rolling stability;
- block bootstrap;
- daily-DD prop audit;
- fresh untouched forward;
- broker-native execution / passive fill realism.

---

## LAB027 — Integrated v200 decision matrix

Purpose:

Test the current v200 strategy as a full causal system rather than combining isolated LAB conclusions.

Matrix:

- TP10 vs no fixed TP
- trailing OFF vs 2.5R trail
- flat risk vs LAB026 tiers

### Historical 2021–2025

| Mode | SumR | MaxDD | R/DD |
|---|---:|---:|---:|
| TP10 flat | +130.60R | 13.50R | 9.675 |
| **TP10 + LAB026** | **+167.62R** | **13.39R** | **12.523** |
| TP10 + trail2.5 + LAB026 | +164.29R | 15.11R | 10.873 |
| NoTP + trail2.5 + LAB026 = current v200 full | +183.24R | 19.33R | 9.479 |

### 2026 seconds

| Mode | SumR | MaxDD | R/DD | +months |
|---|---:|---:|---:|---:|
| TP10 flat | +28.71R | 6.49R | 4.424 | 6/6 |
| **TP10 + LAB026** | **+35.85R** | 6.75R | **5.313** | 5/6 |
| TP10 + trail2.5 + LAB026 | **+37.07R** | **6.68R** | **5.552** | 5/6 |
| **Current v200 full: NoTP + trail2.5 + LAB026** | **+15.16R** | **11.82R** | **1.282** | **4/6** |

### Verdict

- **LAB026 sizing = PASS**
- **removing fixed TP = FAIL**
- **2.5R trail = mixed/watch**
- **BE OFF = keep**
- **partial OFF = keep**
- **signal exit OFF = keep**
- fixed TP 10 ATR remains the robust production-oriented exit anchor.

Why no-TP fails:

- positions live longer;
- occupancy blocks later signals;
- trade count falls;
- TIME exits increase sharply;
- wide 2.5R trail protects only very large MFE and does not replace the fixed target effectively.

Current v200 no-TP configuration should not be treated as validated.

### Code parity warning

Current v200 calls ATR-pause twice:
1. at original signal arming;
2. after confirmation before limit placement.

Research anti-repeat gate is defined at original signal state.

This second live check can create sequence divergence and requires a dedicated parity audit before treating the EA as exact research parity.

---

## LAB028 — Literal v190 exit engine on frozen v200 entry

Transferred from actual v1.90 source code:

- BE trigger +0.50 ATR
- BE lock +0.15 ATR
- trail arm +2.50 ATR
- trail distance 0.50 ATR
- signal exit at opposite |Z| >= 1.00
- time exit 6h
- no fixed TP

Kept frozen v200:
- Z2.50/2.50
- M15 confirm 0.25 ATR
- passive retrace 0.60 ATR
- hard SL 4.5 ATR
- LAB026 sizing

### Historical

Exact v190 exit + LAB026:
- N1689
- WR 81.23%
- EV **+0.00484R**
- Sum **+8.17R**
- PF **1.039**
- DD 13.80R
- only **3/5 positive years**

### 2026 seconds

Exact v190 exit + LAB026:
- N187
- WR 81.82%
- EV **-0.0111R**
- Sum **-2.08R**
- PF **0.892**
- only **3/6 positive months**

Exit mix 2026:
- hard SL 8
- BE/trail stop **145**
- signal 25
- time 9

### Root cause

v190 uses SL = 1.0 ATR, so its exit geometry is roughly:
- BE at 0.5R
- lock 0.15R
- trail arm 2.5R
- trail distance 0.5R

On v200 SL = 4.5 ATR, literal ATR transfer becomes:
- BE at 0.111R
- lock 0.033R
- trail arm 0.556R
- trail distance 0.111R

This massively over-tightens the wider-stop v200 system.

Verdict:
**literal ATR transfer = FAIL**.

Possible next test:
translate v190 exit geometry in R onto v200:
- BE +0.50R = +2.25 ATR
- lock +0.15R = +0.675 ATR
- trail arm +2.50R = +11.25 ATR
- trail distance 0.50R = 2.25 ATR
- signal exit |Z|>=1 opposite
- hold 6h

---

## LAB029 — v190 R-geometry exit on frozen v200

Tested exact requested geometry:

- BE +0.50R
- lock +0.15R
- trail arm +2.50R
- trail distance 0.50R
- signal exit opposite |Z|>=1.0
- hold 6h
- no fixed TP

Frozen:
- v200 entry
- SL 4.5 ATR = 1R
- LAB026 HIGH1.5 / NORMAL1 / LOW0.75

### Historical 2021–2025

- N1604
- WR 54.55%
- EV **+0.03194R**
- Sum **+51.23R**
- PF **1.123**
- DD **14.12R**
- R/DD **3.629**
- 5/5 years positive

### 2026 seconds

- N182
- WR 52.75%
- EV **-0.03119R**
- Sum **-5.68R**
- PF **0.881**
- DD **11.28R**
- only **2/6 positive months**

Exit attribution 2026:
- hard SL -24.16R
- BE/trail +12.66R
- signal exit **-11.10R**
- 6h time exits +16.93R

Quality-state inversion 2026:
- HIGH: **-5.61R**
- NORMAL: -0.68R
- LOW: **+0.61R**

Conclusion:

- translating v190 ATR thresholds into R fixes much of LAB028's historical geometry mismatch;
- but the v190-style exit architecture still fails forward-shadow;
- LAB026 quality ranking is **not exit-engine invariant**;
- combining a new exit engine with old risk tiers can invert which states are actually best.

Verdict:
**v190 R-geometry + frozen v200 + LAB026 = FAIL**.

Reference remains:
**TP10 + SL4.5ATR + 24h fallback + LAB026**.

---

# LIVE EXECUTION PARITY ROADMAP — 2026-09-18

Source evidence: same-day v1.91 runs on FTMO and GetLeveraged, crypto only (BTC/ETH/SOL; gold excluded).

Observed:
- exact matched signal IDs usually enter within the same second;
- broker BTC quotes differ systematically by tens of USD;
- local broker price/ATR paths cause different confirmations and different signal sets;
- trailing/SL triggers can diverge even when entries are nearly identical;
- FTMO crypto commission materially converts many tiny gross winners into net losers;
- FTMO can reject otherwise valid ETH trades on margin while GetLeveraged takes them.

## Execution order — DO NOT SKIP / DO NOT COMBINE

### STEP 1 — Restore robust v200 exit baseline
Status: DONE

Return v200 from experimental no-TP wide-trail mode to the validated integrated reference:
- SL = 4.5 ATR
- TP = 10 ATR
- max hold = 24h
- BE OFF
- trailing OFF
- signal exit OFF
- LAB026 risk tiers ON:
  - HIGH 1.50x
  - NORMAL 1.00x
  - LOW 0.75x

Reference:
- historical TP10 + LAB026: Sum +167.62R, DD 13.39R, R/DD 12.52
- 2026 stress: Sum +35.85R, DD 6.75R, R/DD 5.31

### STEP 2 — Remove double ATR-pause
Status: DONE

Current v200 calls CanEnterByPauseAndDay twice:
1. at original signal arm;
2. again after confirmation before pending order placement.

Research sequence applies the inherited anti-repeat/pause gate at original signal state.

Action:
- keep gate at signal arm;
- remove second gate after confirmation;
- retain HasAny/exposure/day checks required at order placement.

Goal:
exact research/live reachability parity.

### STEP 3 — Canonical Binance price/ATR/confirmation
Status: DONE — implemented in local v200 parity build; MetaEditor compile pending

Problem:
v191/v200 crowd state is Binance-derived but price confirmation/ATR currently uses broker-local crypto candles.

This produces:
- different ATR;
- different confirmation pass/fail;
- different signal IDs / reachable trades across brokers.

Target architecture:
Binance Futures canonical market-data layer for:
- signal reference price;
- M15 OHLC;
- ATR14;
- confirmation close;
- crowd-direction excursion;
- H1/H4 trend quality state where feasible.

Broker feed remains authoritative ONLY for:
- executable bid/ask;
- spread gate;
- passive limit placement;
- SL/TP tick normalization;
- lot/margin;
- actual fills.

Required audit fields:
- canonical Binance price/ATR;
- broker bid/ask;
- broker-vs-Binance basis;
- canonical confirm timestamp;
- signal ID identical across brokers.

### STEP 4 — Margin-adaptive lot instead of hard MARGIN_BLOCK
Status: DONE — implemented in local v200 parity build; MetaEditor compile pending

Problem:
FTMO can block desired crypto size even when signal is otherwise valid.

Target:
- calculate desired risk lot;
- calculate maximum lot allowed by current free margin;
- reduce to broker-normalized maximum executable lot;
- preserve requested risk multiplier in audit;
- reject only if executable lot < broker minimum or below configured minimum risk fraction.

Log:
requested lot, margin-limited lot, actual risk %, margin needed/free, clamp reason.



### STEP 4b — Contract-size / lot-cap parity hardening
Status: DONE — implemented in local v200 parity build; MetaEditor compile pending

Fix:
- global manual cap default changed from `InpMaxLot=50` to `InpMaxLot=0` (disabled);
- sizing order is now:
  `raw risk lot -> broker SYMBOL_VOLUME_MAX / optional manual cap -> margin clamp -> final stepped lot`;
- added `VOLUME_CLAMP` logging;
- added `InpMinVolumeLotFrac=0.25`: skip with `VOLUME_UNDERSIZE_SKIP` if broker/manual limits would leave <25% of raw requested lot;
- signal audit now records raw desired, broker-capped and final actual lot separately;
- actual risk % is measured against raw requested risk, so silent under-sizing is visible.

Exact local v200 SHA-256 after fix:
`6492b13536fe0fb4472cd21c0ec5d377c05ee679dff0044092936e80bf53cfbe`

### STEP 5 — Transaction-cost-aware live audit
Status: DONE — parity signal/execution CSV implemented; MetaEditor compile pending

Do not use cost to retune the signal yet.

Log per setup/trade:
- signal_id
- Binance source timestamp
- Z
- canonical price / ATR
- broker bid/ask / basis / spread
- confirmation timestamp
- H1/H4 quality state
- HIGH/NORMAL/LOW
- requested vs actual risk / lot
- commission estimate and actual commission
- entry / SL / TP
- fill slippage
- MFE / MAE
- exit reason
- gross R
- net R after commission/swap

Goal:
compare identical signal IDs broker-by-broker rather than comparing account PnL only.

### STEP 6 — Dual-broker forward A/B
Status: READY AFTER METAEDITOR COMPILE

Run the SAME v200 candidate on:
- FTMO demo
- GetLeveraged demo

Keep v191 running as control if resources allow.

Primary parity metrics:
- same signal ID rate
- same confirmation rate
- same direction rate
- entry basis/slippage
- exit divergence
- gross R divergence
- net R divergence
- skipped signals by reason (spread/margin/exposure/pause)

Do not tune from the first few trades.

Current local v200 parity build SHA-256:
`cbb5fc20fc0f60dee2a0ab080f8c1a2a189f239abf16b596bbb40334794a056b`

Implementation notes:
- fixed TP10 restored;
- double pause removed;
- Binance USD-M canonical M15/ATR/H1/H4 implemented;
- broker quote used only for executable basis/spread/order placement;
- margin-adaptive lot implemented;
- live audit includes signal_id, basis, desired/actual lot, MFE/MAE, exit reason, gross/net R and actual costs.




### LAB031 — TREND_TRANSITION_AND_REVERSAL_RISK
Status: **DONE — stale-H4 de-risk hypothesis FAIL**

Current candidate tested:
`Z=2.05 -> M15 confirm .25 ATR -> retrace .60 ATR -> limit20 -> SL4.5 -> TP10 -> H24`.

Key findings:
- `CONFLICT_FOLLOW_H4` is **not toxic**:
  - 2021-25: N65, EV +0.1389R, PF 1.279.
  - 2026 Mar-Aug: N4, EV +0.6048R, PF 2.203 (small sample).
- `CONFLICT_ONSET` is positive in both samples; do not boost due small 2026 N.
- de-risking/vetoing stale-H4 conflict reduces return and R/DD.
- more important: inherited LAB026 sizing does **not** transport cleanly after lowering Z from 2.50 to 2.05.
  - Z2.05 flat 2026: Sum +17.12R, PF 1.198, DD 8.34R, R/DD 2.051.
  - old LAB026 sizing: Sum +15.57R, PF 1.162, DD 10.78R, R/DD 1.444.

Next: `CROWDFADE_Z205_QUALITY_RISK_RECALIBRATION_LAB_032`.
Freeze signal/entry/exit; recalibrate risk only. Candidate grid:
`1/1/1`, old `1.5/1/.75`, `1.25/1/.75`, `1.25/1/1`, `1/1/.75`.


### LAB032 — Z205_QUALITY_RISK_RECALIBRATION
Status: **DONE — FLAT RISK PROMOTED**

Frozen trade sequence:
`Z2.05 -> confirm .25 ATR -> retrace .60 ATR -> limit20 -> SL4.5 -> TP10 -> H24`.

Tested risk maps:
- `1/1/1`
- old `1.5/1/.75`
- `1.25/1/.75`
- `1.25/1/1`
- `1/1/.75`

Key result:
- old LAB026 quality ordering does not transport after lowering Z from 2.50 to 2.05.
- 2026 state inversion:
  - HIGH N49 EV -0.0126R PF .975
  - NORMAL N101 EV +0.1265R PF 1.252
  - LOW N26 EV +0.1907R PF 1.464
- **FLAT 1/1/1 wins 2026 forward-shadow**:
  - Sum +17.12R
  - PF 1.198
  - DD 8.34R
  - R/DD 2.051
- old LAB026:
  - Sum +15.57R
  - PF 1.162
  - DD 10.78R
  - R/DD 1.444
- all 5 historical years remain positive under flat risk.

Decision:
**Current Z2.05 candidate should use flat risk. Retire inherited HIGH1.5/NORMAL1/LOW.75 from the live candidate.**
Do not invert weighting to favor LOW from the small 2026 sample.

Next:
- update v200 candidate to flat risk only;
- dual-broker forward;
- broker-specific daily-DD / simultaneous BTC+ETH+SOL exposure audit.
