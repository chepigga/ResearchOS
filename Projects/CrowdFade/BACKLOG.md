# CrowdFade Research Backlog

_Last updated: 2026-09-20_

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


### v200 integration after LAB032
Status: **DONE — working EA updated**

Applied to current `CrowdFadeMulti_v200.mq5`:
- ZLong/ZShort remain **2.05 / 2.05**.
- LAB032 promoted **flat risk**:
  - `InpUseQualityRisk=false`
  - HIGH/NORMAL/LOW defaults = `1.00 / 1.00 / 1.00`
  - quality state retained for logging only.
- default portfolio restored to:
  `BTCUSD:BTCUSDT;ETHUSD:ETHUSDT;SOLUSD:SOLUSDT`.
- signal/entry/exit unchanged:
  confirm .25 ATR, retrace .60 ATR, limit TTL20m, SL4.5, TP10, H24.
- pre-LAB032 build backed up locally as `CrowdFadeMulti_v200_before_LAB032_flatrisk.mq5`.
- static audit PASS; MetaEditor compile still required.
- exact working SHA-256:
  `815477f46968c2629ddca4c6aefd0982b4da119a58cd51aab16073c07e4d50d8`.


### v191 RISK_PARITY patch
Status: **LOCAL BUILD READY — COMPILE PENDING**

Purpose: keep v1.91 signal/confirmation/management unchanged and normalize broker economic risk.
Changes:
- reconstructed v1.91 from v1.93 lineage (v1.93 explicitly changed threshold asymmetry only);
- restored symmetric Z=1.00 and live confirm=0.30 ATR;
- BTC+ETH+SOL default portfolio;
- removed mandatory manual `InpMaxLot=50`; default now 0=disabled;
- raw sizing uses `OrderCalcProfit(1 lot, entry->SL)` in account currency;
- commission-aware sizing: auto FTMO 6.5bps RT / GetLeveraged 0bps;
- adaptive margin clamp instead of immediate MARGIN_BLOCK;
- logs broker contract size, raw/broker/actual lot, base units, requested and actual risk;
- broker `SYMBOL_VOLUME_MAX` remains authoritative; no child-order splitting.
Local SHA-256:
`70e191d91e6d2d9b4bb962c913fd9607ade0cec4c5a5016e9a569008fd8031d1`.


---

# LIVE AUDIT / ROADMAP — 2026-09-20

Source set:
- FTMO and GetLeveraged MT5 history reports through 2026-09-20;
- live journal `joirnal_20092026.rtf`;
- current v1.91 risk-parity lineage through v191c;
- current v200 flat-risk candidate;
- BTC/ETH/SOL price-path review across the report window;
- broker contract screenshots for FTMO / GetLeveraged / IC Markets.

This section records **observed weaknesses and planned research/code changes**.  
Do not silently promote hypotheses below into production logic without the stated LAB / forward validation.

## Broker role decision

### IC Markets — primary production/development candidate

Observed account specs supplied by user:

- commission: 0 on the tested crypto CFD account;
- contract size:
  - BTC = 1
  - ETH = 1
  - SOL = 1
- margin rate:
  - BTC = 0.20%
  - ETH = 0.20%
  - SOL = 0.50%
- max order:
  - BTC = 10
  - ETH = 10
  - SOL = 100
- SOL volume limit = 1000;
- crypto trading is near-24/7 but has short broker session pauses.

Reason to prefer:
- no commission;
- contract=1 across BTC/ETH/SOL;
- margin does not materially distort the EA risk target;
- zero short swap shown for BTC/ETH/SOL in supplied specs.

Open risk:
- real live spread/limit-fill quality must be measured from broker feed;
- SOL target exposure can exceed one-ticket max=100 and may need controlled child-order logic if research requires full notional parity.

### GetLeveraged — secondary / prop-forward venue

Observed account specs supplied by user:

- commission = 0;
- contract size BTC/ETH/SOL = 1;
- full 24/7 sessions;
- margin:
  - BTC / ETH = 6.67%
  - SOL = 33.33%;
- very high max order limits.

Main weakness:
- SOL margin is heavy and can become the binding position-size rule before stop-risk sizing.

### FTMO — benchmark/control only for CrowdFade crypto

Keep for:
- signal/execution comparison;
- broker divergence diagnostics;
- commission stress.

Do not treat as preferred production venue for CrowdFade crypto:
- 6.5 bps round-turn crypto commission materially converts small gross winners into net losers;
- broker contract/margin structure materially distorts execution compared with contract=1 venues.

---

# 2026-09-20 price-path audit — core findings

## Finding A — the bots do not simply “dislike volatility”

Main weakness is more specific:

> **rapid volatility expansion + strong directional impulse + regime transition**

High but stable volatility can be useful because:
- ATR scales stop geometry;
- large moves make TP reachable;
- the signal can still work if price response is orderly.

The failure mode appears when current volatility expands materially after the original signal and price continues hard in the crowd direction.

## Finding B — v191 is vulnerable to false reversal confirmation during impulse

Observed SOL example:
- BUY thesis armed near 110.21;
- M5 confirmation triggered;
- market BUY near 110.37;
- stop hit near 109.87;
- price continued materially lower before the later reversal area.

Interpretation:
- M5 / 0.30 ATR confirmation can be only a local bounce inside a larger directional impulse;
- market-after-confirmation is vulnerable to entering too early.

## Finding C — v200 entry architecture handles the same impulse better

Observed same SOL episode:
- v200 waited for M15 price response;
- then required passive retrace;
- order was placed around 108.1 rather than v191 around 110.37.

Interpretation:
- completed M15 response + passive retrace gives materially better entry geometry during impulse;
- do **not** replace v200 with v191-style market-after-confirmation.

## Finding D — v200 trade count is not simply “one signal”

On 2026-09-20 the journal shows:
- several v200 confirmation episodes;
- several pending BUY_LIMIT orders;
- only a small number were actually filled/closed by report time.

Therefore the apparent low trade count must be decomposed into:
1. signal generation;
2. confirmation pass rate;
3. pending-order placement;
4. passive-fill reachability;
5. TTL expiry;
6. still-open trades at report cutoff.

Current suspected bottleneck:
> `0.60 ATR` passive retrace + `20m` TTL may be too strict even when the core signal/confirmation is valid.

Do **not** loosen Z or confirmation first.

## Finding E — v191 stale confirmation-state inconsistency

Observed GetLeveraged SOL:
- original pending BUY thesis at `z=-2.50`;
- by actual confirmation/entry, current z had flipped to approximately `+2.30`;
- v191 still opened BUY;
- approximately one second later its own signal-exit logic closed the BUY.

Root cause:
- pending confirmation stores `confSide`;
- entry can proceed after the crowd state has become incompatible with that side;
- signal-exit then immediately contradicts the just-opened trade.

This is a state-machine consistency defect, not an alpha retune.

## Finding F — v200 also preserves original-event side through a later Z flip

Observed SOL:
- original v200 BUY event at `z=-2.50`;
- later pending BUY_LIMIT was still placed while current z was positive.

Difference versus v191:
- v200 signal-exit is OFF;
- therefore it intentionally trades the original event rather than immediately self-cancelling.

Do not label this a bug yet.
Need a dedicated causal test:
> original-event persistence vs cancel-on-Z-flip.

## Finding G — v191 BE shell is transaction-cost blind

Current v191:
- BE trigger = +0.50 ATR;
- BE lock = +0.15 ATR.

FTMO audit showed multiple trades that were positive by price but net negative after commission.

Therefore:
- fixed +0.15 ATR is not a true economic breakeven;
- any future BE rule must include spread + commission + slippage + safety buffer;
- IC / GetLeveraged remove commission but not spread/slippage risk.

## Finding H — v200 uses stale signal ATR during later confirmation/execution

Current v200 freezes `sigAtr/confAtr` at the original signal and uses it later for:
- confirmation distance;
- passive entry distance;
- SL;
- TP.

During volatility expansion:
- current ATR can be materially larger than signal ATR;
- the system can remain calibrated to the pre-expansion regime.

This is a primary volatility-regime research target.

---

# Planned changes — v191 lineage

Current implementation baseline for further work:
**v191c RISK_PARITY_NOTIONAL_CAP**

Already implemented:
- `OrderCalcProfit()` account-currency stop-risk sizing;
- commission-aware risk denominator;
- manual `InpMaxLot=0` by default;
- broker volume cap logging;
- adaptive margin under-sizing;
- hard one-position notional cap:
  - `InpMaxNotionalPctEquity = 15%`;
- hard new-trade margin cap:
  - `InpMaxNewTradeMarginPct = 5%`;
- hard projected total-account margin cap:
  - `InpMaxAccountMarginPct = 12%`;
- under-risking allowed rather than inflating economic exposure.

## v191 P0 — CONFIRM_SIDE_CONSISTENCY

Status: **IMPLEMENTED in v191d — COMPILE / FORWARD CHECK PENDING**

Implementation:
- source: `CrowdFadeMulti_v191d_Confirm_CONSISTENCY_VOL_DIAG.mq5`;
- preserve v191c signal/risk shell unchanged;
- store original confirmation Z snapshot (`confZ`);
- when price confirmation fires, re-check current crowd state before order send;
- cancel only if the intended trade would already satisfy the existing `SIGNAL_EXIT` rule:
  - BUY cancelled when current `z >= +InpExitZ`;
  - SELL cancelled when current `z <= -InpExitZ`;
- if `InpExitZ<=0`, this consistency gate is disabled together with signal-exit semantics;
- new execution-log events:
  - `CONFIRM_OK`;
  - `CONFIRM_CANCEL_Z`;
- diagnostics:
  - original Z;
  - current Z;
  - confirmation age;
  - signal ATR;
  - current ATR;
  - `ATRExpansion = currentATR / signalATR`.

Explicitly unchanged:
- Z threshold = 1.00;
- confirm = 0.30 ATR;
- M5 confirmation architecture;
- SL = 1.50 ATR;
- ExitZ = 0.75;
- score;
- trailing / BE logic;
- risk sizing;
- notional and margin caps.

Purpose:
remove logically self-contradictory entries without retuning alpha.

v191d SHA-256:
`163a6c3e5fa0278f22b407ed22fd3394f804f0eb0815c8d71aef29ba39e44686`

## v191 P0 — COST_AWARE_BE

Status: **RESEARCH REQUIRED BEFORE PROMOTION**

Current fixed lock `+0.15 ATR` is not broker-neutral economic breakeven.

Test:
- BE OFF control;
- current BE;
- cost-aware lock floor:
  `expected round-turn cost + current spread + slippage allowance + small positive buffer`.

Important:
- do not assume FTMO cost structure for IC/GetLeveraged;
- use broker-native execution cost;
- if cost-aware BE still truncates right tail, disable BE rather than forcing it.

## v191 P1 — volatility-expansion confirmation robustness

Do not simply increase confirmation globally.

Test current M5 confirmation against:
- completed-bar confirmation;
- stronger confirmation only in volatility-expansion state;
- failed-continuation / reclaim confirmation after extreme impulse.

Primary question:
> can v191 avoid false local bounces without losing its useful higher-frequency role?

v191 remains the faster control bot; do not turn it into v200.

---

# Planned research / changes — v200

## Freeze before new LABs

Do not change production-oriented core yet:

- ZLong / ZShort = 2.05 / 2.05;
- M15 completed-close confirmation = 0.25 ATR;
- passive retrace = 0.60 ATR;
- limit TTL = 20m;
- SL = 4.5 ATR;
- TP = 10 ATR;
- hold = 24h;
- BE OFF;
- trailing OFF;
- signal exit OFF;
- LAB032 flat risk = 1 / 1 / 1;
- quality state remains diagnostic only.

Reason:
the 2026-09-20 forward sample is too small to justify directly weakening the core.

## LAB033 — V200_PASSIVE_RETRACE_REACHABILITY

Purpose:
determine whether v200 is losing valid trades at the **execution reachability** layer rather than the signal layer.

Freeze:
- Z2.05;
- M15 confirm 0.25 ATR;
- SL4.5;
- TP10;
- H24;
- flat risk;
- same canonical signals.

Test retrace:
- 0.60 ATR — baseline;
- 0.45 ATR;
- 0.40 ATR;
- 0.30 ATR.

Test TTL:
- 20m baseline;
- 30m.

Primary candidate to examine:
> 0.40 ATR + 30m

This is a hypothesis, **not promoted**.

Required outputs:
- confirmation episodes;
- pending orders;
- fill rate;
- TTL expiry rate;
- missed-winner rate;
- trades/month;
- EV;
- PF;
- MaxDD;
- SumR;
- MAE/MFE after fill;
- entry improvement versus confirmation close;
- broker-specific fill divergence;
- full causal sequential rerun.

Do not add market fallback in the candidate set except as a control.

## LAB034 — VOLATILITY_EXPANSION_AND_IMPULSE_RESPONSE

Purpose:
test the hypothesis that the real weak regime is **volatility expansion / directional impulse**, not high volatility itself.

Stage A — diagnostics only.

For every signal/confirmation/fill record:
- signal ATR;
- current ATR at confirmation;
- current ATR at fill;
- `ATRExpansion = currentATR / signalATR`;
- rolling normal ATR reference;
- crowd-direction excursion (`crowdExc`);
- 1h directional impulse in ATR units;
- H1/H4 state;
- confirmation age;
- outcome / MFE / MAE.

Predefined `crowdExc` diagnostic buckets:
- <0.50 ATR;
- 0.50–1.00 ATR;
- 1.00–1.50 ATR;
- >1.50 ATR.

Do not optimize thresholds from one day.

Stage B — test one intervention at a time:

1. **Dynamic execution ATR**
   - baseline: frozen signal ATR;
   - candidate: `EffectiveATR = max(signalATR, currentATR)`.

2. **Impulse confirmation**
   - baseline 0.25 ATR response;
   - for extreme continuation, test failed-continuation / reclaim requirement before accepting reversal.

3. **Risk response**
   - baseline 1.00x;
   - extreme expansion diagnostic candidates 0.75x and 0.50x;
   - no hard veto first.

4. **Retrace after valid reversal**
   - test whether confirmed strong reversals need *less* passive retrace (0.30–0.40 ATR) because waiting 0.60 ATR misses the move.

Goal:
distinguish:
- fast but orderly market;
- expanding volatility;
- one-direction impulse against the contrarian thesis.

## LAB035 — ORIGINAL_EVENT_PERSISTENCE_VS_Z_FLIP_CANCEL

Purpose:
resolve whether v200 should preserve the original contrarian event after current crowd Z flips.

Freeze all other logic.

Compare:
- BASE: preserve original `confSide` exactly as current v200;
- CANCEL_ON_SIGN_FLIP;
- CANCEL_ON_OPPOSITE_THRESHOLD only.

Required:
- full causal rerun;
- trade reachability;
- EV/PF/DD/SumR;
- missed right-tail winners;
- losses avoided;
- confirmation-age interaction;
- volatility-regime split.

Do not implement a Z-flip cancellation rule before this LAB.

## LAB036 — IC_MARKETS_VS_GETLEVERAGED_EXECUTION_AUDIT

Purpose:
select the preferred production venue using actual execution data rather than specification sheets.

Run same v200 build / canonical signal IDs on:
- IC Markets;
- GetLeveraged.

FTMO may remain as benchmark only.

Collect continuously:
- bid / ask;
- spread in USD;
- spread in bps;
- spread / ATR;
- contract size;
- margin required for target notional;
- session availability;
- limit placement success;
- limit fill / no-fill;
- time-to-fill;
- slippage;
- basis to canonical Binance price;
- rejected orders;
- swap if position crosses rollover.

Minimum:
- 24h continuous audit;
- preferably enough signals to cover BTC/ETH/SOL and at least one volatile episode.

Decision metrics:
- net R after all costs;
- fill reachability;
- execution parity to canonical signals;
- margin distortion;
- missed trades;
- operational uptime.

---

## v200a — BROKER_PARITY_VOL_DIAG

Status: **IMPLEMENTED — METAEDITOR COMPILE / FORWARD CHECK PENDING**

Source:
- `CrowdFadeMulti_v200a_BROKER_PARITY_VOL_DIAG.mq5`
- derived byte-for-byte from canonical v200 SHA-256:
  `815477f46968c2629ddca4c6aefd0982b4da119a58cd51aab16073c07e4d50d8`

Frozen strategy core explicitly unchanged:
- ZLong / ZShort = 2.05 / 2.05;
- M15 completed-close confirmation = 0.25 ATR;
- passive retrace = 0.60 ATR;
- limit TTL = 20m;
- SL = 4.5 ATR;
- TP = 10 ATR;
- hold = 24h;
- BE OFF;
- trailing OFF;
- signal exit OFF;
- LAB032 flat risk = 1 / 1 / 1.

Implemented execution/risk shell:
- auto broker cost profile:
  - FTMO = 6.5 bps round-turn;
  - IC Markets = 0;
  - GetLeveraged = 0;
  - unknown broker falls back to manual `InpCommissionRoundTurnBps`;
- per-position economic notional cap:
  - `InpMaxNotionalPctEquity = 15%`;
- one-new-trade margin cap:
  - `InpMaxNewTradeMarginPct = 5%`;
- projected total-account margin cap:
  - `InpMaxAccountMarginPct = 12%`;
- sizing chain:
  `raw risk lot -> broker/manual volume cap -> notional cap -> margin cap -> actual lot`;
- actual requested/realized risk and exposure are logged.

Implemented LAB034 diagnostics only:
- original Z snapshot;
- current Z at confirmation;
- Z sign-flip flag;
- signal ATR;
- current ATR;
- `ATRExpansion = currentATR / signalATR`;
- confirmation age;
- `CONFIRM_OK` / `CONFIRM_TIMEOUT` execution events.

New audit CSVs:
- `CrowdFade_signals_v200a_broker_vol_diag.csv`;
- `CrowdFade_execution_v200a_broker_vol_diag.csv`.

Explicitly **NOT** implemented before LAB validation:
- no cancel-on-Z-flip;
- no dynamic EffectiveATR;
- no retrace 0.40 ATR;
- no TTL 30m;
- no impulse/reclaim entry logic;
- no IC SOL child-order split.

v200a SHA-256:
`c608b3fed647e943319a4d89ecee3f2c62ceb99ff76e03076773a84bb7ddabe3`


---

# SEQUENTIAL CHANGE LABS — 2026-09-20

Runner:
`labs/CROWDFADE_V200_SEQUENTIAL_CHANGE_LABS_033_035/run.py`

Frozen during the sequence:
`Z2.05 -> M15 confirm .25 ATR -> SL4.5 -> TP10 -> H24 -> flat risk`

Data:
- 2021–2025 Binance USD-M BTCUSDT M1 monthly archives;
- 2026 Mar–Aug BTCUSDT second OHLC;
- exact `BTCUSDT_flow_2021-01-2026-08` CrowdFade flow archive.

Important:
- 2021–2025 remains discovery/in-sample;
- 2026 Mar–Aug remains reused forward-shadow/stress, not pristine OOS;
- BTC only; ETH/SOL transfer is not yet proven.

## LAB033A — PASSIVE RETRACE REACHABILITY
Status: **DONE — KEEP 0.60 ATR**

TTL frozen at 20m.

| Retrace | Hist N | Hist EV | Hist PF | Hist DD | Hist R/DD | 2026 N | 2026 EV | 2026 PF | 2026 DD | 2026 R/DD |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **0.60** | 1642 | +0.0745R | 1.151 | **19.83R** | **6.174** | 176 | **+0.0972R** | **1.198** | 8.34R | **2.051** |
| 0.45 | 1780 | +0.0795R | 1.167 | 27.96R | 5.061 | 187 | +0.0496R | 1.100 | 8.33R | 1.114 |
| 0.40 | 1818 | +0.0746R | 1.157 | 31.29R | 4.336 | 190 | +0.0842R | 1.176 | **8.12R** | 1.970 |
| 0.30 | 1880 | +0.0734R | 1.155 | 36.84R | 3.748 | 198 | +0.0089R | 1.018 | 13.42R | 0.131 |

Interpretation:
- relaxing retrace does increase fill rate materially;
- this is **not free frequency**;
- historical DD expands strongly as entry is moved closer;
- 0.40 is the least damaging relaxation but still lowers historical R/DD ~30%;
- 0.30 nearly destroys the 2026 edge.

Decision:
**do not change 0.60 ATR to 0.40 ATR.**

## LAB033B — PENDING TTL 20m vs 30m
Status: **DONE — KEEP 20m**

Using retrace 0.60 ATR.

20m:
- historical N1642, EV +0.0745R, PF 1.151, DD 19.83R, R/DD 6.174;
- 2026 N176, EV +0.0972R, PF 1.198, DD 8.34R, R/DD 2.051.

30m:
- historical N1725, EV +0.0745R, PF 1.152, DD **30.39R**, R/DD 4.230;
- 2026 N182, EV +0.0663R, PF 1.136, DD 9.65R, R/DD 1.251.

Interpretation:
30m adds fills, but the extra fills worsen path risk and DD materially.

Decision:
**TTL remains 20m.**

## LAB034A — VOLATILITY EXPANSION DIAGNOSTIC
Status: **DONE — SIMPLE “HIGH VOL = BAD” HYPOTHESIS NOT SUPPORTED**

2026 baseline split by `currentATR / signalATR` at confirmation:

- 0.90–1.10: N133, EV +0.101R, PF 1.204;
- 1.10–1.25: N28, EV +0.039R, PF 1.087;
- 1.25–1.50: N10, EV +0.435R, PF 2.018;
- >=1.50: N2, EV +0.326R, PF 1.649.

The >=1.25 samples are small, but the available evidence does **not** show monotonic deterioration as ATR expands.

Crowd-direction excursion is also non-monotonic:
- <0.50 ATR: N112, EV +0.046R;
- 0.50–1.00: N39, EV +0.174R;
- 1.00–1.50: N13, EV **-0.198R**;
- >=1.50: N12, EV **+0.646R**.

Interpretation:
- volatility magnitude alone is not the correct veto variable;
- intermediate directional continuation may be problematic;
- extreme continuation can also precede strong mean reversion;
- do not create a simple high-ATR filter from this sample.

## LAB034B — DYNAMIC EXECUTION ATR
Status: **DONE — NO PROMOTION**

Candidate:
`EffectiveATR = max(signalATR, currentATR at confirmation)`
for retrace / SL / TP only. Confirmation threshold itself remains frozen.

Baseline:
- historical: N1642, EV +0.0745R, PF 1.151, DD 19.83R, R/DD 6.174;
- 2026: N176, EV +0.0972R, PF 1.198, DD 8.34R, R/DD 2.051.

Dynamic ATR:
- historical: N1556, EV +0.0794R, PF 1.167, DD 19.56R, R/DD 6.313;
- 2026: N164, EV +0.1154R, PF 1.249, **DD 10.19R**, R/DD **1.857**;
- 2026 positive months fall from 4 to 3.

Interpretation:
dynamic ATR improves some point estimates but worsens forward-shadow risk efficiency and reduces reachability.

Decision:
**v200 keeps frozen signal ATR geometry.**

## LAB035 — ORIGINAL EVENT PERSISTENCE vs Z-FLIP CANCEL
Status: **DONE — CANCEL_SIGN_FLIP IS A STRONG RESEARCH CANDIDATE; NOT YET PRODUCTION-PROMOTED**

Full causal rerun:

| Mode | Hist N | Hist EV | Hist PF | Hist DD | Hist R/DD | 2026 N | 2026 EV | 2026 PF | 2026 DD | 2026 R/DD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| PRESERVE | 1642 | +0.0745R | 1.151 | 19.83R | 6.174 | 176 | +0.0972R | 1.198 | 8.34R | 2.051 |
| **CANCEL_SIGN_FLIP** | 1617 | **+0.0845R** | **1.173** | **18.81R** | **7.261** | 172 | **+0.1321R** | **1.276** | **8.01R** | **2.836** |
| CANCEL_OPPOSITE_THRESHOLD | 1638 | +0.0749R | 1.152 | 19.83R | 6.186 | 174 | +0.1143R | 1.236 | 8.01R | 2.481 |

CANCEL_SIGN_FLIP:
- historical SumR: +122.40R -> **+136.62R**;
- historical R/DD: 6.174 -> **7.261**;
- historical 5/5 years remain positive;
- improves 4/5 historical years; 2022 is worse;
- 2026 SumR: +17.12R -> **+22.72R**;
- 2026 R/DD: 2.051 -> **2.836**;
- 2026 max consecutive losses: 9 -> **8**;
- forward cancellations: 8 confirmation episodes.

Direct 2026 baseline filled sign-flip trades:
- 5 trades;
- 4 were approximately -1R losses;
- 1 was a +2.21R winner;
- direct SumR = **-1.83R**.

Therefore sign-flip cancellation is not “all stale trades are bad”; it can remove right-tail winners too. Its full-sequence benefit also comes from changing later reachability.

Year contribution warning:
- 2021 improves;
- 2022 worsens;
- 2023 improves strongly;
- 2024 improves;
- 2025 improves.

Forward:
- Mar improves;
- Apr unchanged;
- May improves;
- Jun unchanged;
- Jul improves;
- Aug improves from -1.07R to approximately flat.

Decision:
**promote CANCEL_SIGN_FLIP to the next validation candidate, not directly to production.**

Required before final promotion:
- paired/stability audit of sign-flip episodes;
- fresh forward after 2026-09-20;
- ETH/SOL transfer check;
- keep one control instance with original persistence logic.

## Current v200 decision after LAB033–035

Keep unchanged:
- Z = 2.05 / 2.05;
- M15 confirm = 0.25 ATR;
- retrace = **0.60 ATR**;
- limit TTL = **20m**;
- SL = 4.5 ATR;
- TP = 10 ATR;
- H24;
- flat risk;
- frozen signal ATR execution geometry.

Do **not** promote:
- 0.40 ATR retrace;
- TTL30;
- dynamic `max(signalATR,currentATR)`;
- simple high-volatility veto.

Next candidate:
> **cancel pending v200 event if current crowd Z has crossed sign relative to original signal Z before order placement.**

This changes trade reachability and therefore needs fresh forward / transfer validation before replacing the v200a control.

# Planned code changes after LAB validation

## v191

Implement first because they are consistency/risk-shell issues:

1. **CONFIRM_SIDE_CONSISTENCY**
   - cancel self-contradictory stale confirmation before order send.

2. **Broker-native cost-aware BE or BE OFF**
   - only after LAB confirms economic benefit.

3. **Volatility diagnostics in logs**
   - signal ATR;
   - current ATR;
   - ATR expansion ratio;
   - confirmation age.

Do not import v200 passive-entry architecture wholesale into v191.

## v200

No immediate strategy-code relaxation.

Only after LAB results:

1. promote retrace/TTL change if LAB033 improves fill reachability without degrading EV/DD;
2. add dynamic `EffectiveATR` only if LAB034 survives historical + 2026 + fresh forward;
3. add impulse/reclaim logic only if it improves the extreme-expansion state without killing normal-state edge;
4. change original-event persistence only if LAB035 supports it;
5. add broker-specific execution shell for IC Markets / GetLeveraged after LAB036.

Potential IC Markets execution feature:
- controlled SOL child-order split only if target lot > `SYMBOL_VOLUME_MAX`;
- maximum two child orders initially;
- total notional/risk must stay under the same parent risk cap;
- never use splitting to bypass broker total volume limit;
- must preserve one logical signal_id / parent trade_id.

---

# Immediate priority order

1. **v191 CONFIRM_SIDE_CONSISTENCY fix**
2. **LAB033 — v200 retrace / TTL reachability**
3. **LAB034 — volatility expansion / impulse response**
4. **LAB035 — v200 original-event persistence vs Z flip**
5. **LAB036 — IC vs GetLeveraged execution audit**
6. cost-aware BE study for v191
7. only then consider production promotion of any relaxed v200 entry rule

Core principle:

> Do not solve volatility by simply blocking high ATR.  
> First identify whether the market is merely volatile or is **expanding and continuing directionally against the CrowdFade thesis**.

## LAB035B — SIGN_FLIP_STABILITY_AND_PAIRED_EVENT_AUDIT
Status: **DONE — PASS RESEARCH PROMOTION GATE / NOT YET PRODUCTION**

Frozen geometry:
`Z2.05 -> M15 confirm .25 ATR -> retrace .60 ATR -> TTL20 -> SL4.5 -> TP10 -> H24 -> flat risk`

Headline:
- historical PRESERVE: N1642, EV +0.0745R, PF 1.151, Sum +122.40R, DD 19.83R, R/DD 6.174;
- historical CANCEL_SIGN_FLIP: N1617, EV +0.0845R, PF 1.173, Sum +136.62R, DD 18.81R, R/DD 7.261;
- forward PRESERVE: N176, EV +0.0972R, PF 1.198, Sum +17.12R, DD 8.34R, R/DD 2.051;
- forward CANCEL_SIGN_FLIP: N172, EV +0.1321R, PF 1.276, Sum +22.72R, DD 8.01R, R/DD 2.836.

Paired decomposition:
- historical baseline-only removed: 68 trades, SumR -10.91R;
  - 41 are direct sign-flip fills, SumR **-15.53R**;
- historical candidate-only replacements: 43 trades, SumR **+3.31R**;
- 1574 common trades are exactly identical entry and PnL;
- total historical delta reconciles exactly to **+14.216R**.

Forward:
- baseline-only removed: 9 trades, SumR +2.70R;
  - 5 direct sign-flip fills, SumR **-1.835R**;
- candidate-only replacements: 5 trades, SumR **+8.306R**;
- 167 common trades identical;
- total forward delta: **+5.609R**.

Direct sign-flip event audit on PRESERVE sequence:
Historical:
- 88 confirmed sign-flip events;
- 41 filled (46.6%);
- filled EV **-0.379R**;
- SumR **-15.53R**;
- PF **0.427**;
- WR 24.4%;
- max consecutive losses 8.

Forward:
- 8 confirmed sign-flip events;
- 5 filled (62.5%);
- EV **-0.367R**;
- SumR **-1.835R**;
- PF 0.546;
- WR 20%.

Sign-flip strength historical:
- abs(current Z) <0.5: N15 fills, EV **-0.727R**;
- 0.5–1.0: N8, EV **-0.574R**;
- 1.0–2.05: N10, EV +0.117R;
- >=2.05: N8, EV -0.150R.
Do not derive a sub-threshold filter from these small cells yet.

Historical delta by year:
- 2021 +2.969R
- 2022 **-3.795R**
- 2023 +8.908R
- 2024 +4.328R
- 2025 +1.806R

Leave-one-year-out remains positive for every omitted year:
- excl 2021 +11.247R
- excl 2022 +18.011R
- excl 2023 +5.308R
- excl 2024 +9.888R
- excl 2025 +12.410R

2026 forward monthly delta:
- Mar +1.735R
- Apr 0
- May +1.200R
- Jun 0
- Jul +1.644R
- Aug +1.030R

Concentration:
- removing top 3 positive historical weeks still leaves **+5.433R**;
- top 3 weeks = 28.2% of total positive contribution.

4-week moving-block bootstrap:
- historical observed +14.216R, median +14.905R, 95% resampled interval [-2.717R, +32.647R], P(delta>0)=**94.9%**;
- forward observed +5.609R, median +6.314R, interval [+2.674R, +9.916R], P(delta>0)=**99.9%**.

Interpretation:
1. The benefit is **not** caused only by sequence reshuffling. Direct filled sign-flip setups are structurally weak in both historical and forward samples.
2. Sequence replacement adds additional value: canceling stale events frees future reachability.
3. Effect is not concentrated entirely in 2023; every leave-one-year-out historical total remains positive.
4. 2022 is a genuine negative transfer year and prevents treating the filter as universal truth.
5. Historical bootstrap CI still crosses zero, so this is a strong candidate, not pristine proof.
6. Forward sample is reused shadow, not fresh OOS.

Decision:
**CANCEL_SIGN_FLIP passes the LAB035B research promotion gate.**

Do not replace production control yet.
Next:
- ETH/SOL transfer replication;
- then fresh post-2026-09-20 forward with v200 control vs candidate;
- if transfer does not fail catastrophically, create v200b candidate with exactly one strategy change: cancel event before pending order when current Z has opposite sign to original signal Z.


---

# FREQUENCY EXPANSION LABS — 2026-09-20

Goal:
increase v200 trade frequency toward v191 without silently degrading the validated v200 execution geometry.

Research candidate foundation:
- Z2.05;
- M15 confirm 0.25 ATR;
- retrace 0.60 ATR;
- pending TTL20m;
- SL4.5;
- TP10;
- H24;
- flat risk;
- CANCEL_SIGN_FLIP enabled as LAB035B research candidate.

Baseline BTC frequency:
- historical: 1617 trades / 60 months = **26.9 trades/month**;
- 2026 Mar-Aug: 172 / 6 = **28.7 trades/month**.

## LAB037A — GLOBAL Z FRONTIER
Status: **DONE — LOWERING Z GLOBALLY REJECTED**

| Z | Hist trades/mo | Hist EV | Hist DD | Hist R/DD | 2026 trades/mo | 2026 EV | 2026 DD | 2026 R/DD |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **2.05** | 26.9 | **+0.0845R** | **18.81R** | **7.261** | 28.7 | **+0.1321R** | 8.01R | **2.836** |
| 1.75 | 30.1 | +0.0234R | 35.39R | 1.193 | 31.3 | +0.0870R | **6.10R** | 2.682 |
| 1.50 | 32.6 | +0.0550R | 27.06R | 3.977 | 33.2 | +0.0450R | 11.05R | 0.811 |
| 1.25 | 34.0 | +0.0513R | 25.83R | 4.048 | 35.3 | **-0.0236R** | 17.68R | -0.283 |
| 1.00 | 35.5 | +0.0483R | **39.92R** | 2.582 | 37.3 | **-0.0435R** | **25.11R** | -0.388 |

Interpretation:
- even v191-like Z=1.00 increases BTC frequency only ~32% under the still-strict v200 execution layer;
- forward edge becomes negative at Z1.25 and Z1.00;
- Z1.75 adds only ~12% frequency while historical risk efficiency collapses.

Decision:
**keep global Z2.05.**

## LAB037B — MID-Z H1+H4 TREND LANE
Status: **DONE — NO PROMOTION**

Design:
- high-Z core |Z|>=2.05 unchanged;
- lower-Z trades only if H1 and H4 both align with CrowdFade direction;
- same M15 confirm / passive entry / exit shell.

Results:
- lane >=1.75: hist 28.5/mo, R/DD 5.193; 2026 29.5/mo, R/DD 2.338;
- lane >=1.50: hist 29.9/mo, R/DD 4.465; 2026 31.0/mo, R/DD 2.086;
- lane >=1.25: hist 30.8/mo, R/DD 3.518; 2026 32.7/mo, R/DD 0.855;
- lane >=1.00: hist 31.5/mo, Sum +159.49R, R/DD 6.308; 2026 EV only +0.0052R, R/DD 0.070.

Decision:
**no mid-Z M15/passive lane promoted.**
Trend alignment alone does not rescue the lower-Z population under this architecture.

## LAB037C — M15 CONFIRM THRESHOLD
Status: **DONE — KEEP 0.25 ATR**

On the surviving core architecture:

- 0.25 ATR:
  - hist 26.9/mo, EV +0.0845R, DD 18.81R, R/DD 7.261;
  - 2026 28.7/mo, EV +0.1321R, R/DD 2.836.
- 0.20 ATR:
  - hist 27.2/mo, EV +0.0702R, **DD 32.88R**, R/DD 3.481;
  - 2026 29.3/mo, EV +0.1821R, R/DD 3.999.
- 0.15 ATR:
  - hist 27.5/mo, EV +0.0613R, **DD 30.15R**, R/DD 3.354;
  - 2026 29.2/mo, EV +0.2030R, R/DD 4.433.

Interpretation:
forward likes easier confirmation, but 5-year history does not.
Trade count barely changes because passive reachability / occupancy dominate after confirmation.

Decision:
**keep 0.25 ATR.**

## LAB038A — CONFIRMATION TTL 60–180m
Status: **DONE — KEEP 60m**

Extending confirmation wait:
- does almost nothing for trade frequency;
- sharply worsens historical DD/RDD.

Historical:
- 60m: 26.9/mo, EV +0.0845R, DD 18.81R, R/DD 7.261;
- 90m: 27.1/mo, DD 30.46R, R/DD 3.608;
- 120m: 27.4/mo, DD 45.57R, R/DD 1.673;
- 180m: 27.5/mo, DD 43.16R, R/DD 1.729.

Decision:
**confirmation TTL remains 60m.**

## LAB038B — MAX HOLD / OCCUPANCY
Status: **DONE — SHORTER HOLD RAISES FREQUENCY BUT DOES NOT SURVIVE ROBUSTNESS GATE**

| Hold | Hist trades/mo | Hist EV | Hist DD | Hist R/DD | 2026 trades/mo | 2026 EV | 2026 DD | 2026 R/DD |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **24h** | 26.9 | **+0.0845R** | **18.81R** | **7.261** | 28.7 | **+0.1321R** | 8.01R | **2.836** |
| 18h | 29.4 | +0.0518R | 28.94R | 3.154 | 31.5 | +0.1301R | **7.39R** | **3.330** |
| 12h | 33.1 | +0.0580R | 23.58R | 4.890 | 36.3 | +0.0667R | 11.80R | 1.233 |
| 8h | 37.0 | +0.0408R | 26.25R | 3.450 | 42.2 | +0.0591R | 10.98R | 1.361 |
| 6h | **39.2** | +0.0223R | **41.53R** | 1.265 | **45.2** | +0.0549R | 10.62R | 1.401 |

Key point:
**H6 gets much closer to v191 frequency**, but it destroys much of v200's historical risk efficiency.

## LAB038C — v191-LIKE TIMING INTERACTION
Status: **DONE — FAIL**

The closest timing shell:
- confirm TTL 180m;
- hold 6h;
- while retaining v200 Z/confirm/retrace/SL/TP.

Historical:
- 40.4 trades/month;
- EV **-0.0005R**;
- PF 0.999;
- Sum -1.12R;
- DD 61.99R.

2026:
- 44.7 trades/month;
- EV +0.0677R;
- PF 1.244;
- DD 10.78R.

Decision:
**do not make v200 globally v191-like by timing changes.**

## Frequency research conclusion

The evidence now separates two goals:

1. **v200 core quality**
   - depends on Z2.05 + M15 confirmation + deep passive retrace + H24 right-tail capture;
   - global relaxation consistently sacrifices historical robustness.

2. **v191-like frequency**
   - comes from a genuinely different fast architecture:
     - Z1.0 state;
     - M5 decision rhythm;
     - 3h confirmation window;
     - market-after-confirm;
     - H6 / active management.

Therefore the next rational architecture is **not a globally weakened v200**.

Next LAB:
**HYBRID CORE + FAST LANE**
- preserve v200 high-quality core unchanged;
- add a separately measured v191-like fast lane;
- independent lane attribution;
- initially lower risk on fast lane;
- common portfolio exposure cap;
- test whether the combined equity curve adds frequency without contaminating v200 core.


## LAB039 — V200_CORE_PLUS_V191_FAST_LANE
Status: **DONE — NAIVE HYBRID FAILS; FAST ENTRY POPULATION NEEDS DISCRIMINATION**

Architecture:
- CORE unchanged:
  `|Z|>=2.05 -> M15 confirm .25 ATR -> retrace .60 -> TTL20 -> SL4.5 -> TP10 -> H24 -> CANCEL_SIGN_FLIP`.
- FAST incremental lane only:
  `1.0<=|Z|<2.05`;
  M5 cadence;
  M15 ATR;
  confirm .30 ATR;
  confirmation window <=3h;
  market after confirmation;
  ATR pause 1.0;
  max 3/day.
- FAST entry is tested with:
  A) canonical v191-style management;
  B) v200 exit geometry.
- combined portfolio uses CORE 1.0 risk unit and FAST 0.50x / 0.40x.
- independent lanes may overlap; max simultaneous risk is audited.

Canonical v191 source basis:
- Z=1.00;
- confirm=.30 ATR;
- confirm max=36 M5;
- market after confirm;
- SL=1.50 ATR;
- H6;
- ExitZ=.75;
- BE .50 -> lock .15;
- trail .50 ATR, arm 2.50;
- ATR pause=1.0;
- max 3/day.

### Standalone lanes

Historical 2021–2025:
- CORE: N1617 = 26.9/mo, EV **+0.0845R**, PF 1.173, Sum +136.62R, DD 18.81R, R/DD 7.261.
- FAST mid-Z + v191 exits: N5396 = **89.9/mo**, EV **-0.0416R**, PF 0.877, Sum **-224.37R**, DD 250.67R.
- FAST mid-Z + v200 exits: N2492 = **41.5/mo**, EV **+0.0127R**, PF 1.026, Sum +31.68R, DD **44.27R**, R/DD 0.716.
- v191-like full reference: N5405 = 90.1/mo, EV -0.0577R, PF 0.831, Sum -311.98R.

2026 Mar–Aug reused forward-shadow:
- CORE: N172 = 28.7/mo, EV **+0.1321R**, PF 1.276, Sum +22.72R, DD 8.01R, R/DD 2.836.
- FAST mid-Z + v191 exits: N552 = **92.0/mo**, EV **-0.0419R**, PF 0.862, Sum -23.14R.
- FAST mid-Z + v200 exits: N266 = **44.3/mo**, EV **-0.1028R**, PF 0.810, Sum -27.35R.
- v191-like full reference: N552 = 92.0/mo, EV -0.0545R, PF 0.817.

### Combined portfolio

CORE + FAST/v191 exits:
- 0.50x FAST:
  - hist 116.9 trades/mo, Sum +24.43R, DD 50.61R, R/DD 0.483;
  - 2026 120.7/mo, Sum +11.15R, DD 14.90R, R/DD 0.748.
- 0.40x FAST:
  - hist 116.9/mo, Sum +46.87R, DD 42.52R, R/DD 1.102;
  - 2026 120.7/mo, Sum +13.47R, DD 13.18R, R/DD 1.022.

CORE + FAST entry / v200 exits:
- 0.50x FAST:
  - hist **68.5/mo**, Sum **+152.46R**, DD 30.52R, R/DD 4.996;
  - 2026 **73.0/mo**, Sum **+9.05R**, DD 13.42R, R/DD 0.674.
- 0.40x FAST:
  - hist 68.5/mo, Sum +149.29R, DD 28.00R, R/DD 5.332;
  - 2026 73.0/mo, Sum +11.78R, DD 12.14R, R/DD 0.971.

Max simultaneous planned stop-risk:
- CORE + FAST0.50 = 1.50 core-risk units;
- CORE + FAST0.40 = 1.40 core-risk units.

### Interpretation

1. Frequency can be raised dramatically:
   - CORE 26.9–28.7 BTC trades/month;
   - naive FAST can push total to ~69–121/month.

2. But **raw lower-Z FAST population has no robust alpha**.
   - v191 exit shell is clearly negative both historical and 2026.
   - v200 exit shell rescues historical FAST to barely positive EV, but 2026 becomes strongly negative.

3. The value of v200 is therefore not only its exit shell.
   The `|Z|>=2.05` selection itself is carrying substantial edge.

4. Naively adding FAST at reduced risk still damages the forward equity curve:
   - CORE alone 2026 Sum +22.72R / DD 8.01R / RDD 2.836;
   - best naive hybrid reported here is materially worse in forward risk efficiency.

5. Do **not** implement naive FAST lane in production.

6. v191-like full replay is negative in this reconstruction. This does not prove the live v191 EA is intrinsically negative because:
   - live v191 confirmation is timer/quote based;
   - replay uses raw close crossing as an approximation;
   - broker execution / BE / freeze-level / slippage differ;
   - score-based lot weighting is omitted.
   It is valid here as a frequency/architecture reference, not as exact v191 performance replication.

### Decision

Keep CORE unchanged.

FAST lane is **not rejected as a concept**, but raw `1.0<=|Z|<2.05` is rejected.

Next research:
**LAB040 — FAST_LANE_DISCRIMINATOR**
- keep the large fast candidate pool;
- identify causal subsets using:
  - exact Z band;
  - confirmation speed;
  - H1/H4 state;
  - crowd excursion before confirmation;
  - ATR expansion;
  - price response / reclaim quality;
- require the subset to improve both historical and 2026 EV/PF;
- then rerun full portfolio sequence at 0.40x–0.50x risk.


## LAB040 — FAST_LANE_DISCRIMINATOR
Status: **DONE — NO STRICT-GATE PASS; SEVERAL AGGREGATE-POSITIVE CANDIDATES IDENTIFIED**

Parity:
- exact LAB039 FAST population:
  - completed-M5 signal cadence;
  - first raw-price close crossing 0.30 ATR within 3h;
  - sign-flip cancel;
  - market entry;
  - v200 exit shell for attribution;
- raw FAST population:
  - 2021–2025 N=2492, EV +0.0127R, PF 1.026, Sum +31.68R, DD 44.27R;
  - 2026 Mar–Aug N=266, EV **-0.1028R**, PF 0.810, Sum -27.35R.

Method:
- causal features only, known before entry:
  - |Z| band;
  - confirmation speed;
  - H1/H4 state;
  - crowd excursion;
  - ATR expansion;
  - response ratio;
  - reclaim displacement;
- simple rule family only:
  - one-feature bin / 2-bin union;
  - two-feature AND;
- strict gate:
  - N>=20 in 2021–23 discovery, 2024–25 validation, and 2026;
  - EV>0 and PF>1 in all three;
  - validation EV>=+0.03R;
  - 2026 EV>=+0.05R.

Result:
**0 rules passed the strict gate.**

This is important:
there is no currently demonstrated FAST discriminator that is simultaneously frequent enough and stable enough to promote.

### Aggregate-positive candidates (2021–2025 AND 2026)

#### Candidate A — ONE_ALIGN + response >=2.50
- 2021–2025:
  - N105;
  - EV **+0.329R**;
  - PF 1.839;
  - Sum +34.51R.
- 2026:
  - N15;
  - EV **+0.077R**;
  - PF 1.184;
  - Sum +1.16R.
- 2021–23 EV +0.260R;
- 2024–25 EV +0.441R.

Interpretation:
very strong quality signal across both internal historical splits, but 2026 N=15 is too small for strict promotion.

#### Candidate B — ONE_ALIGN + response 0.50–1.00
- 2021–2025:
  - N134;
  - EV **+0.108R**;
  - PF 1.226;
  - Sum +14.51R.
- 2026:
  - N13;
  - EV **+0.073R**;
  - PF 1.145;
  - Sum +0.95R.
- 2021–23 EV +0.099R;
- 2024–25 EV +0.119R.

Interpretation:
less powerful but unusually consistent across discovery / validation / 2026; sample still too small.

#### Candidate C — BOTH_ALIGN + reclaim 0.35–0.50 ATR
- 2021–2025:
  - N397;
  - EV **+0.0365R**;
  - PF 1.073;
  - Sum +14.49R.
- 2026:
  - N19;
  - EV **+0.0551R**;
  - PF 1.098;
  - Sum +1.05R.
- 2021–23 EV +0.0255R;
- 2024–25 EV +0.0498R.

Interpretation:
largest reasonably coherent candidate population and the closest to the strict gate (forward N19 vs required N20), but edge is thin.

#### Candidate D — confirmation <=15m + MIXED_NEUTRAL
- 2021–2025:
  - N146;
  - EV +0.122R;
  - PF 1.279;
  - Sum +17.82R.
- 2026:
  - N14;
  - EV +0.252R;
  - PF 1.585;
  - Sum +3.53R.
- 2021–23 EV +0.159R;
- 2024–25 EV +0.043R.

Interpretation:
interesting fast-reversal phenotype; forward sample too small.

### Simple Z-band audit

Only one pure Z-band is aggregate-positive in both periods:

`|Z| = 1.50–1.75`
- 2021–2025 N437, EV **+0.0091R**, PF 1.018;
- 2026 N46, EV **+0.0101R**, PF 1.018;
- but 2021–23 EV **-0.029R** and 2024–25 EV +0.071R.

Decision:
**do not use Z1.50–1.75 alone.**
The apparent edge is too weak and regime-dependent.

### LAB040 conclusion

The FAST edge is **conditional on price response / trend-state interaction**, not on Z magnitude alone.

Most promising research phenotype:
> lower-Z crowd extreme + one timeframe aligned with trade + unusually strong response quality.

Most scalable near-pass phenotype:
> H1/H4 both aligned with trade + confirmation reclaim around 0.35–0.50 ATR.

No production promotion yet.

Next LAB should be:
**LAB041 — FAST_LANE_COMPOSITE_GATE_AND_PORTFOLIO_REPLAY**
- construct only 2–3 preregistered composite gates from the LAB040 candidates;
- test union / overlap without data-mining hundreds of combinations;
- rerun full CORE+FAST stateful portfolio;
- require 2026 portfolio SumR and R/DD not worse than CORE;
- test FAST risk 0.25x / 0.40x, not 0.50x initially.


## LAB041 — FAST_LANE_COMPOSITE_GATE_AND_PORTFOLIO_REPLAY
Status: **DONE — G1 RESPONSE HYBRID PASSES PRE-REGISTERED PORTFOLIO GATE; PRODUCTION PROMOTION PENDING STABILITY/OVERLAP AUDIT**

Preregistered stateful gates:
- G1 RESPONSE:
  `ONE_ALIGN AND (response 0.50–1.00 OR response >=2.50)`;
- G2 RESPONSE+RECLAIM:
  G1 OR `BOTH_ALIGN AND reclaim 0.35–0.50 ATR`;
- G3 FULL COMPOSITE:
  G2 OR `MIXED_NEUTRAL AND confirm <=15m`.

Stateful semantics:
- rejected FAST candidate does **not** consume pause, day quota, or H24 occupancy;
- accepted FAST trade does;
- therefore filtered sequence is recomputed causally, not filtered post-trade.
- This materially expands reachable FAST events relative to the static LAB040 candidate rows.

CORE baseline:
Historical:
- N1617 = 26.9/mo;
- EV +0.0845R;
- PF 1.173;
- Sum +136.62R;
- DD 18.81R;
- R/DD 7.261.

2026 Mar–Aug:
- N172 = 28.7/mo;
- EV +0.1321R;
- PF 1.276;
- Sum +22.72R;
- DD 8.01R;
- R/DD 2.836.

### Standalone gated FAST

G1 RESPONSE:
Historical:
- N1006 = **16.8/mo**;
- EV **+0.0019R**;
- PF 1.004;
- Sum +1.92R;
- DD 43.98R;
- R/DD 0.044.
Year SumR:
- 2021 +14.35R;
- 2022 +13.35R;
- 2023 -3.80R;
- 2024 +6.47R;
- 2025 **-28.44R**.

2026:
- N97 = **16.2/mo**;
- EV **+0.1565R**;
- PF 1.366;
- Sum +15.18R;
- DD 7.26R;
- R/DD 2.090.
Monthly:
- Mar +7.21R;
- Apr +5.38R;
- May -3.33R;
- Jun +4.06R;
- Jul +4.88R;
- Aug -3.02R.

Interpretation:
G1 is **not a robust standalone alpha** historically. It is near-flat over 5 years and has a severe 2025 failure regime.
Its value in LAB041 is as a small-risk diversifying/additive lane inside CORE.

G2 RESPONSE+RECLAIM:
- hist N1993 = 33.2/mo, EV +0.0042R, Sum +8.39R, DD 36.84R;
- 2026 N174 = 29.0/mo, EV **-0.0426R**, Sum -7.42R, DD 25.09R.
Rejected.

G3 FULL COMPOSITE:
- hist N2065 = 34.4/mo, EV +0.0047R, Sum +9.71R, DD 37.38R;
- 2026 N187 = 31.2/mo, EV **-0.0289R**, Sum -5.41R, DD 21.45R.
Rejected.

### Combined portfolio

#### G1 RESPONSE + FAST risk 0.25x
Historical:
- N2623 = **43.7 trades/mo**;
- Sum +137.10R;
- DD 20.96R;
- R/DD 6.540;
- max planned concurrent risk = 1.25 CORE units.

2026:
- N269 = **44.8 trades/mo**;
- Sum **+26.52R**;
- DD **7.95R**;
- R/DD **3.337**;
- max risk = 1.25 units.

PASS preregistered portfolio gate.

#### G1 RESPONSE + FAST risk 0.40x
Historical:
- N2623 = **43.7 trades/mo**;
- Sum +137.38R;
- DD 22.25R;
- R/DD 6.174;
- max planned concurrent risk = 1.40 CORE units.

2026:
- N269 = **44.8 trades/mo**;
- Sum **+28.80R**;
- DD **7.91R**;
- R/DD **3.642**;
- max risk = 1.40 units.

PASS preregistered portfolio gate.

Relative to CORE:
- BTC frequency rises from ~27–29/mo to **~44–45/mo** (+56–62%);
- 2026 SumR improves +22.72R -> +26.52R at 0.25x or +28.80R at 0.40x;
- 2026 DD slightly improves 8.01R -> 7.95/7.91R;
- 2026 R/DD improves 2.836 -> 3.337 / 3.642;
- historical total R changes only marginally because G1 FAST is nearly flat over the full 5-year history;
- historical R/DD deteriorates 7.261 -> 6.540 / 6.174.

Approx annual weighted SumR for G1 0.40x:
- 2021 ~+48.54R;
- 2022 ~+30.03R;
- 2023 ~+10.97R;
- 2024 ~+34.87R;
- 2025 ~+12.97R.
All years remain positive because CORE absorbs the weak FAST regimes.

Approx 2026 monthly weighted SumR at 0.40x:
- Mar ~+15.37R;
- Apr ~+0.67R (FAST rescues negative CORE April);
- May ~+3.24R;
- Jun ~+5.21R;
- Jul ~+5.57R;
- Aug ~-1.25R.
5/6 months positive.

#### G2/G3 portfolios
Both 0.25x and 0.40x FAIL:
- 2026 SumR falls below CORE;
- 2026 R/DD falls below CORE.
Do not promote.

### LAB041 decision

Research winner:
**G1 RESPONSE hybrid only.**

Preferred risk for next validation:
- **0.25x FAST** = conservative candidate;
- 0.40x is a higher-return research variant but causes more historical DD/RDD degradation.

Do NOT yet embed G1 into production v200.
Required next:
1. overlap/conflict audit:
   - CORE + FAST simultaneous positions;
   - same-side vs opposite-side;
   - unintended hedge and aggregate symbol exposure;
2. G1 stability audit around 2025 failure regime;
3. ETH/SOL transfer;
4. fresh post-2026-09-20 forward.

If conflict audit is clean, forward-demo candidate should begin with:
- CORE risk 0.25%;
- FAST G1 risk = **0.25x CORE = 0.0625% per FAST trade**;
- hard existing portfolio notional/margin caps remain active.


## LAB041B — CORE_FAST_OVERLAP_CONFLICT_AND_2025_FAILURE_AUDIT
Status: **DONE — OVERLAP IS NOT THE FAILURE SOURCE; KEEP ALLOW_ALL; 2025 FAILURE IS A REGIME BREAK**

Frozen:
- CORE unchanged;
- G1 unchanged:
  `ONE_ALIGN AND (response 0.50–1.00 OR response >=2.50)`;
- FAST entry/exit geometry unchanged;
- no new alpha filter selected.

Conflict policies tested statefully at FAST entry:
1. ALLOW_ALL;
2. BLOCK_ANY_CORE_OPEN;
3. BLOCK_OPPOSITE_CORE_OPEN;
4. BLOCK_SAME_SIDE_CORE_OPEN.

Blocked FAST trades do not consume pause/day quota/occupancy. CORE is never blocked.

### Overlap audit — ALLOW_ALL

Historical G1 FAST:
- total N1006;
- entry with no CORE: N506, EV **-0.0096R**, Sum -4.87R;
- entry with same-side CORE: N374, EV ~0.000R, Sum -0.08R;
- entry with opposite-side CORE: N126, EV **+0.0545R**, Sum +6.87R.

Lifetime overlap:
- no CORE overlap during FAST lifetime: N181, EV **-0.336R**, Sum **-60.87R**, PF 0.531;
- some CORE overlap during FAST lifetime: N825, EV **+0.0761R**, Sum **+62.79R**, PF 1.170.

2026:
- no CORE at entry: N49, EV **+0.276R**, Sum +13.53R;
- same-side CORE at entry: N42, EV -0.0569R, Sum -2.39R;
- opposite CORE at entry: N6, EV **+0.675R**, Sum +4.05R.
Lifetime:
- no overlap N16, EV +0.314R;
- overlap N81, EV +0.125R.

Interpretation:
- opposite-side overlap is **not** demonstrably harmful;
- historical overlap is actually associated with much better FAST outcomes;
- CORE presence appears to act more like a regime/context proxy than a conflict source;
- lifetime overlap itself cannot be used as a causal entry filter because later CORE entries are future information.

### Stateful conflict-policy results

Standalone FAST historical / 2026:
- ALLOW_ALL: +1.92R / +15.18R;
- BLOCK_ANY_CORE_OPEN: **-8.45R** / +0.97R;
- BLOCK_OPPOSITE_CORE_OPEN: **-11.83R** / +10.56R;
- BLOCK_SAME_SIDE_CORE_OPEN: **-6.68R** / ~0R.

Every stricter policy makes historical FAST negative.

Preferred portfolio risk 0.25x:

ALLOW_ALL:
- hist 43.7 trades/mo, Sum +137.10R, DD 20.96R, R/DD 6.540;
- 2026 44.8/mo, Sum **+26.52R**, DD 7.95R, R/DD **3.337**.

BLOCK_ANY:
- hist 37.8/mo, Sum +134.50R, R/DD 6.749;
- 2026 39.3/mo, Sum +22.97R, R/DD 2.927.

BLOCK_OPPOSITE:
- hist 42.6/mo, Sum +133.66R, R/DD 6.573;
- 2026 44.3/mo, Sum +25.36R, R/DD 3.191.

BLOCK_SAME:
- hist 40.0/mo, Sum +134.95R, R/DD 6.287;
- 2026 41.3/mo, Sum +22.72R, R/DD 2.720.

All stricter policies FAIL the preregistered comparison against ALLOW_ALL G1@0.25.

Decision:
**do not add an entry-time CORE/FAST overlap veto.**
Keep ALLOW_ALL for the research candidate.

### 2025 failure audit

G1 2025:
- N215;
- EV **-0.1323R**;
- Sum **-28.44R**;
- PF 0.751;
- DD 43.98R.

The failure is strongly time-clustered:
- Jan–Jun 2025 combined: approximately **+12.46R**;
- Jul–Dec 2025 combined: approximately **-40.90R**.

Worst months:
- Jul: -13.20R, EV -0.660R;
- Nov: -7.32R, EV -0.431R;
- Dec: -9.55R, EV -0.415R.

It is **not** a BUY/SELL asymmetry:
- BUY -13.43R;
- SELL -15.01R.

It is **not** isolated to one G1 response branch:
- response 0.50–1.00: -17.30R;
- response >=2.50: -11.14R.

It is **not** solved by H1 vs H4 aligned side:
- H1-align: -18.29R;
- H4-align: -10.15R.

Overlap explains part of concentration but is not a usable fix:
- no CORE at FAST entry: -18.42R;
- same-side CORE: -8.00R;
- opposite CORE: -2.02R;
- no CORE overlap over entire trade lifetime: only N40 but **-21.26R**;
- some lifetime overlap: N175, -7.18R.
However lifetime overlap uses future information and entry-time overlap vetoes fail statefully.

The strongest causal diagnostic found in 2025 is Z location:
- |Z| 1.00–1.25: **+1.19R**;
- |Z| 1.25–1.50: **+3.11R**;
- |Z| 1.50–1.75: **-10.64R**;
- |Z| 1.75–2.05: **-22.10R**.

Thus the 2025 failure is concentrated in the **upper half of the FAST Z range (1.50–2.05)**, especially H2 2025.

This is diagnostic only.
Do **not** automatically add `|Z|<1.50` from the 2025 audit because that would be post-hoc curve fitting.

### LAB041B decision

1. **Overlap conflict hypothesis rejected.**
2. **ALLOW_ALL remains the preferred CORE+G1 portfolio behavior.**
3. 2025 is a genuine FAST regime failure, not primarily an execution-overlap problem.
4. The next clean hypothesis should be tested separately:
   **LAB041C — G1_Z_LOCATION_REGIME_STABILITY**
   - preregister `1.00–1.50` vs `1.50–2.05`;
   - test 2021–2024, 2025, 2026 separately;
   - then full CORE+FAST stateful replay;
   - no further threshold search.


## LAB041C — FAST_ENTRY_LATENESS_AND_FIRST_RESPONSE_AUDIT
Status: **DONE — ENTRY LATENESS CONFIRMED; 0.10 ATR EARLY RESPONSE IS THE NEXT STABILITY CANDIDATE**

Frozen baseline:
- G1 ALLOW_ALL from LAB041/041B;
- FAST `1.0<=|Z|<2.05`;
- ONE_ALIGN;
- response `0.50–1.00 OR >=2.50`;
- market entry at first raw close >= +0.30 signal ATR;
- SL4.5 / TP10 / H24.

First reversal definition:
- primary = first raw close >= +0.10 signal ATR in trade direction;
- first H/L touch +0.10 ATR also recorded.

### Lateness measurement

Historical 2021–2025:
- first +0.10 ATR touch:
  - median **1m**;
  - mean 5.21m.
- first +0.10 ATR close:
  - median **1m**;
  - mean 7.33m.
- current +0.30 confirmation:
  - median **5m**;
  - mean **17.07m**;
  - p90 53.5m.
- actual market-entry displacement:
  - median **0.387 ATR**;
  - mean **0.456 ATR**;
  - p90 0.661 ATR.
- pre-entry MFE:
  - median **0.461 ATR**;
  - mean 0.550 ATR.
- pre-entry MAE:
  - median 0.088 ATR;
  - mean 0.283 ATR.

2026 second-data shadow:
- first +0.10 close median **0.60m**;
- current +0.30 confirmation median **4.75m**;
- mean confirmation 10.87m;
- market-entry displacement:
  - median **0.320 ATR**;
  - mean **0.342 ATR**;
- pre-entry MFE median 0.327 ATR;
- pre-entry MAE median 0.096 ATR.

Interpretation:
the reversal is usually visible materially before the current 0.30-ATR market entry.
Historical M1 path exaggerates close-crossing overshoot relative to 2026 second data, so the live lateness penalty is smaller than the historical M1 penalty but still measurable.

### Paired same-signal oracle diagnostic
Important: uses baseline G1 membership known only at later 0.30 confirmation, therefore diagnostic / non-tradable as-is.

Historical same 1006 trades:
- entry at 0.30: +1.92R;
- hypothetical 0.25: +12.24R;
- 0.20: +21.97R;
- 0.15: +29.75R;
- **0.10: +37.68R**.
Paired improvement 0.10 vs current = **+35.76R**.

2026 same 97 trades:
- 0.30: +15.18R;
- 0.25: +16.01R;
- 0.20: +17.65R;
- 0.15: +18.13R;
- **0.10: +18.80R**.
Paired improvement = **+3.61R**.

This directly supports the price-lateness hypothesis on the same accepted signal population.

### Causal stateful early-response replay
Here G1 is evaluated using only information available at the earlier response threshold. Population and later sequence are allowed to change.

Historical:
- **0.10 ATR:** N1011, EV **+0.0625R**, PF 1.133, Sum **+63.14R**, DD **25.83R**, R/DD **2.444**;
- 0.15: +31.92R, EV +0.0316;
- 0.20: +43.31R, EV +0.0430;
- 0.25: +23.31R, EV +0.0230;
- current 0.30: +1.92R, EV +0.0019, DD 43.98R.

2026:
- **0.10 ATR:** N105, EV **+0.1071R**, PF 1.241, Sum **+11.25R**, DD 8.61R;
- 0.15: +7.53R;
- 0.20: -0.52R;
- 0.25: +6.30R;
- current 0.30: **+15.18R**, EV +0.1565, DD 7.26R.

Interpretation:
- 0.10 is dramatically more robust historically than current 0.30;
- 0.10 remains positive in 2026 but does **not** dominate the current 0.30 selection in 2026;
- therefore current confirmation has real selection value even though it enters later.

Core conclusion:
> **Entry is late, but confirmation is not useless.**
> The research problem is to preserve the information gained between 0.10 and 0.30 while avoiding paying the entire price move at entry.

### Retrace after 0.30 confirmation
Stateful, TTL20m.

Historical:
- retrace 0.10: EV -0.019R, Sum -19.12R, noFill 88;
- retrace 0.20: EV +0.0236R, Sum +22.82R, noFill 191;
- retrace 0.30: EV +0.0064R, Sum +5.97R, noFill 320.

2026:
- retrace 0.10: +8.65R;
- retrace 0.20: +4.89R;
- retrace 0.30: +3.39R;
versus current market +15.18R.

Decision:
**do not add passive retrace after FAST 0.30 confirmation.**
It misses too many winners and does not solve the problem.

### Is “slower confirmation = worse” universally true?
No.

Historical confirmation latency:
- <=5m EV +0.0127R;
- 5–15m EV **+0.0560R**;
- 15–30m EV -0.0413R;
- 30–60m ~flat;
- 60–120m -0.0986R;
- 120–180m -0.430R.

So very stale confirmations are clearly weak historically, but fastest is not automatically best.

2026:
- <=5m EV ~flat;
- 5–15m +0.257R;
- 15–30m **+0.706R** (N14);
- 30–60m ~flat.
Thus a simple “confirmation must be fast” veto is not transferable.

### 2025 failure and lateness
2025 H1:
- +12.46R;
- confirm mean 17.84m, median 6m.

2025 H2:
- **-40.90R**;
- confirm mean **13.55m**, median **4m**.

H2 failure actually confirmed *faster* than H1.
Therefore the 2025 regime failure is **not explained by slower clock-time confirmation**.

Entry displacement H1/H2 is almost identical:
- H1 mean 0.449 ATR;
- H2 mean 0.448 ATR.

So 2025 failure is not a simple overshoot/latency problem either.

### LAB041C decision

Supported:
1. User hypothesis is materially correct: the FAST engine often sees the first reversal well before it enters at 0.30 ATR.
2. On the exact same accepted signals, earlier entry improves PnL in both historical and 2026 samples.
3. A causal 0.10 response entry is positive in both samples and greatly improves historical robustness.
4. But 0.30 confirmation has selection value and remains stronger in 2026.
5. Waiting for a retrace *after* 0.30 is rejected.
6. 2025 failure is a separate regime problem, not merely entry latency.

Next clean LAB:
**LAB041D — EARLY_010_PROBE_PLUS_030_CONFIRM**
- at +0.10 ATR, take a small probe using only causal early-G1 information;
- at +0.30 ATR, validate / add / retain based on full G1 state;
- cancel/exit probe on sign-flip or confirmation timeout;
- compare probe risk 0.20x / 0.25x / 0.40x of FAST unit;
- preserve total portfolio cap;
- test whether this captures the price advantage of 0.10 while retaining 0.30 selection quality.

Alternative simpler validation before staged entry:
**LAB041D-A — CAUSAL_010_STABILITY_BY_YEAR_AND_PORTFOLIO**
to verify 0.10 by year, including 2025 H2, before adding staged complexity.

