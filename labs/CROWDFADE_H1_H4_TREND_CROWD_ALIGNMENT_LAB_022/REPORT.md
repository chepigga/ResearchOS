# CROWDFADE_H1_H4_TREND_CROWD_ALIGNMENT_LAB_022

## Question

Does CrowdFade behave differently depending on whether the crowd is trading with or against the H1/H4 trend?

## Frozen system

Baseline CrowdFade only:
- ZLong = 2.50
- ZShort = 2.50
- M15 confirm 0.25 ATR
- retrace 0.60 ATR
- limit-only TTL20m
- SL 4.5 ATR
- TP 10 ATR
- max hold24h
- max3/day
- inherited 1 ATR anti-repeat gate

No trend filter is applied. This LAB is diagnostic only.

## Trend definition

H1 UP:
- completed H1 close > EMA50
- EMA50 > EMA50 four H1 bars ago

H1 DOWN: mirror.

H4 uses the same rule on completed H4 bars.

Strong trend:
- H1 and H4 are both non-neutral
- both point in the same direction

Because CrowdFade is contrarian:
- crowd LONG => our trade SHORT
- crowd SHORT => our trade LONG

Therefore crowd AGAINST trend means our trade is WITH trend.

## Baseline parity

Historical 2021-2025:
- N 1227
- EV +0.106435R
- PF 1.210426
- SumR +130.596R

2026 seconds forward-shadow:
- N 136
- EV +0.211108R
- PF 1.467315
- SumR +28.711R
- 6/6 positive months

## H1 relation

| State | Historical N | Hist EV | Hist PF | 2026 N | 2026 EV | 2026 PF |
|---|---:|---:|---:|---:|---:|---:|
| Crowd WITH H1 trend / we countertrend | 425 | +0.0873 | 1.171 | 40 | +0.1881 | 1.395 |
| Crowd AGAINST H1 trend / we with trend | 630 | **+0.1325** | **1.263** | 69 | **+0.3182** | **1.776** |
| H1 neutral | 172 | +0.0583 | 1.116 | 27 | -0.0285 | 0.945 |

## H4 relation

| State | Historical N | Hist EV | Hist PF | 2026 N | 2026 EV | 2026 PF |
|---|---:|---:|---:|---:|---:|---:|
| Crowd WITH H4 trend / we countertrend | 625 | +0.0575 | 1.112 | 66 | +0.1821 | 1.352 |
| Crowd AGAINST H4 trend / we with trend | 519 | **+0.1616** | **1.320** | 63 | **+0.2851** | **1.772** |
| H4 neutral | 83 | +0.1302 | 1.288 | 7 | -0.1817 | 0.683 |

## H1 + H4 same-direction strong trend

| State | Historical N | Hist EV | Hist PF | 2026 N | 2026 EV | 2026 PF |
|---|---:|---:|---:|---:|---:|---:|
| Crowd WITH strong trend / we countertrend | 369 | +0.0631 | 1.121 | 31 | +0.2216 | 1.457 |
| Crowd AGAINST strong trend / we WITH trend | 438 | **+0.1609** | **1.320** | 50 | **+0.3109** | **1.852** |
| Mixed / neutral H1-H4 | 420 | +0.0877 | 1.177 | 55 | +0.1145 | 1.224 |

Historical trend-following advantage ratio:
- EV 0.1609 vs 0.0631, about 2.55x

2026 forward-shadow:
- EV 0.3109 vs 0.2216
- PF 1.852 vs 1.457

## Directional asymmetry

Historical strong UP:

| Crowd / our side | N | EV | PF |
|---|---:|---:|---:|
| Crowd LONG, we SHORT against UP trend | 214 | **+0.0180** | **1.034** |
| Crowd SHORT, we LONG with UP trend | 227 | **+0.1974** | **1.398** |

This is the clearest structural finding in the historical sample.

In a strong H1+H4 uptrend, fading a long crowd by shorting BTC has almost no historical edge.

Historical strong DOWN:

| Crowd / our side | N | EV | PF |
|---|---:|---:|---:|
| Crowd SHORT, we LONG against DOWN trend | 155 | +0.1255 | 1.246 |
| Crowd LONG, we SHORT with DOWN trend | 211 | +0.1217 | 1.238 |

Historical downtrend behavior is much more symmetric.

2026 strong DOWN:
- crowd SHORT / we LONG countertrend: N14, EV +0.0532R, PF 1.093
- crowd LONG / we SHORT with trend: N24, EV +0.2971R, PF 1.787

2026 therefore favors following the downtrend, but the sample is small.

2026 strong UP:
- crowd LONG / we SHORT countertrend: N17, EV +0.3604R
- crowd SHORT / we LONG with trend: N26, EV +0.3236R

Both are profitable in the small 2026 sample, so historical UP asymmetry is not yet a production veto.

## Interpretation

The crowd is often not simply a trend-following cohort.

When the crowd is positioned AGAINST the prevailing H1/H4 trend, CrowdFade mechanically takes the trend-following side, and this state has the strongest cross-period expectancy.

The cleanest relationship is H4:
- historical EV +0.1616R when crowd is against H4 trend
- versus +0.0575R when crowd is with H4 trend

When H1 and H4 agree, the same relationship becomes stronger.

## Verdict

Trend direction clearly contains useful information for CrowdFade.

Current evidence supports this hierarchy:

1. Best context: crowd AGAINST aligned H1+H4 trend => CrowdFade trade WITH trend.
2. Intermediate: mixed / neutral trend state.
3. Weakest historical context: crowd WITH aligned H1+H4 trend => CrowdFade trade countertrend.

Most important warning state:

    Strong H1+H4 UP trend
    crowd LONG
    CrowdFade wants SHORT

Historical edge there is almost flat: EV +0.018R, PF 1.034.

Do NOT turn this into a production filter yet.

Next clean step, if desired, is a causal gating/risk test with only pre-registered states:
- baseline
- reduce risk when CrowdFade is countertrend to aligned H1+H4
- keep/full risk when CrowdFade is with aligned H1+H4
- optionally isolate the strong-UP crowd-LONG / we-SHORT state

No EMA period or threshold optimization should be done before that causal test.