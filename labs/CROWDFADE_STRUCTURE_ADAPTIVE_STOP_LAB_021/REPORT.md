# CROWDFADE_STRUCTURE_ADAPTIVE_STOP_LAB_021

## Question

Can trend alignment or a causal level breakout improve stop selection versus the frozen 4.5 ATR stop?

## Frozen core

- ZLong = 2.50
- ZShort = 2.50
- M15 confirm = 0.25 ATR
- passive retrace = 0.60 ATR
- limit-only TTL = 20m
- TP = 10 ATR
- max hold = 24h
- max 3/day
- inherited 1 ATR anti-repeat gate

Only stop selection changes.

## Structural definitions

Trend aligned:
- LONG: close > EMA50 and EMA50 > EMA50 four M15 bars ago
- SHORT: mirror

Breakout aligned:
- LONG: close > prior 20-M15 high
- SHORT: close < prior 20-M15 low

Stop choices are fixed:
- narrow = 3.0 ATR
- wide = 4.5 ATR

## Tested mappings

1. Wide 4.5 baseline
2. Narrow 3.0 when trend aligned, otherwise 4.5
3. Narrow 3.0 when breakout aligned, otherwise 4.5
4. Narrow 3.0 when trend AND breakout aligned, otherwise 4.5
5. Wide 4.5 when trend aligned, otherwise 3.0
6. Wide 4.5 when breakout aligned, otherwise 3.0
7. Fixed 3.0 control

## Baseline parity

Exact parity passed:
- historical 2021-2025 N = 1227
- 2026 seconds N = 136

## Main results

| Mode | Hist EV | Hist PF | Hist DD | Hist R/DD | 2026 EV | 2026 PF | 2026 DD | 2026 +months |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Wide 4.5 baseline | +0.1064 | 1.210 | 13.50R | 9.68 | +0.2111 | 1.467 | 6.49R | 6/6 |
| Trend -> narrow 3 | +0.1621 | 1.277 | 21.89R | 9.53 | +0.1899 | 1.341 | 9.43R | 5/6 |
| Breakout -> narrow 3 | +0.1324 | 1.247 | 16.74R | 9.89 | +0.1409 | 1.285 | 9.41R | 5/6 |
| Trend -> wide 4.5 else 3 | +0.1092 | 1.199 | 20.86R | 6.60 | +0.2322 | 1.484 | 10.55R | 5/6 |
| Breakout -> wide 4.5 else 3 | +0.1442 | 1.245 | 19.71R | 9.50 | +0.2929 | 1.546 | 10.80R | 5/6 |
| Fixed 3.0 control | +0.1751 | 1.282 | 23.38R | 9.93 | +0.2103 | 1.361 | 10.80R | 5/6 |

## Interpretation

### Narrowing because structure supports the trade does NOT work robustly

Both trend-aligned and breakout-aligned narrowing improve some historical return metrics but fail 2026:
- lower 2026 EV/PF than wide baseline
- materially higher DD
- August turns negative
- consistency falls from 6/6 to 5/6 positive months

Therefore the intuitive rule 'good structure means a tighter stop is safe' is rejected.

### Mirror logic is more interesting, especially for breakouts

Leaving 4.5 ATR on breakout-aligned trades and using 3 ATR elsewhere gives:

Historical:
- EV +0.1442R
- PF 1.245
- DD 19.71R
- 5/5 positive years

2026:
- EV +0.2929R
- PF 1.546
- SumR +41.30R
- DD 10.80R
- 5/6 positive months

This materially outperforms the fixed 3.0 control in 2026:
- EV 0.2929 vs 0.2103
- PF 1.546 vs 1.361
- same ~10.80R DD
- SumR 41.30 vs 29.87R

But it does NOT dominate the fixed 3.0 control historically:
- lower EV 0.1442 vs 0.1751
- lower PF 1.245 vs 1.282
- lower SumR
- only modestly lower DD

Therefore the breakout interaction is real enough to watch, but not cross-period stable enough for promotion.

### Trend interaction is weaker

Trend-wide-else-3 modestly helps 2026 return, but historical PF and R/DD are inferior. No production edge.

## Structural frequency

Historical baseline trade contexts:
- trend aligned: 826 / 1227
- breakout aligned: 334 / 1227
- both: 311 / 1227

2026 baseline:
- trend aligned: 101 / 136
- breakout aligned: 27 / 136
- both: 27 / 136

In 2026 every breakout-aligned baseline trade was also trend-aligned. The breakout sample is therefore a relatively small strong-trend subset.

## Verdict

NO stop rule is promoted.

Frozen production-oriented stop remains:

    SL = 4.5 ATR

Research watch candidate only:

    if breakout aligned with trade direction:
        keep wide 4.5 ATR
    else:
        3.0 ATR

Why not promote:
- DD is materially higher than wide baseline
- 2026 consistency falls to 5/6 months
- historical improvement is not superior to fixed 3.0 control
- 2026 breakout sample is small

## Research implication

Trend/breakout information appears more promising as a regime/risk-quality feature than as a direct stop-distance switch.

A future clean test could keep SL fixed at 4.5 ATR and test whether breakout context should change risk size or entry confirmation, without altering the stop.