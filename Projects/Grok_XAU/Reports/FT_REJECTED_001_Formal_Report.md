# FT_REJECTED_001 — Formal Frozen Report

**Date:** 2026-07-25  
**Status:** FORMAL FROZEN RUN COMPLETED  
**Primary verdict:** **CONFIRMS-REGIME**  
**Trading changes:** NONE

## Input audit

- M5 tester-stream SHA256: `40175d5d73fbbe01d26fd1813d1bc299854ef535c328fa1fdd1b883f90509ae4`
- M5 rows: `290,893`
- Coverage: `2022-06-01 01:05 .. 2026-07-23 23:40`
- Signal fixture SHA256: `a62a93a471cff3ce000bb237556125a9f54101c0b0ee33c5b0bca4605b0db7f2`
- Debug fixture SHA256: `f259dc513f4af46bdbff5d40b45101cd574e1587d2500e8beb50c736fe14a82e`
- EA source SHA256: `838b3e180a139008c69792c0f122f3da66a590ef5e6ee98056056f0938311b65`
- Frozen TZ SHA256: `45e6bed26e0a0e5d795d45eeefa4d70cf7ff02c88755ed0f4425d1fe42b5d89d`
- Candidates after excluding `DAILY_STOP`: `1,288`
- Missing M5 timestamps: `0`
- Closed hypothetical trades: `1,288`
- Fixed cost: `-0.05R/trade`
- Midpoint: `2024-10-11`

Two integrity-only fixes were applied before interpretation: calendar-date coverage accepts the first/last available tradable bars, and `NYBUY_SCORE_DETAIL` is shifted back one M5 bar to match the candidate entry timestamp. No signal, entry, SL, TP, cost, split, threshold or verdict rule changed.

## ACCEPT versus REJECT

| Population | Module | N | WR | EV_net | Sum R | PF |
|---|---|---:|---:|---:|---:|---:|
| ACCEPT | ALL | 161 | 44.10% | +1.3248R | +213.286R | 3.481 |
| ACCEPT | NYBUY | 121 | 43.80% | +1.5781R | +190.950R | 3.674 |
| ACCEPT | LONBUY | 40 | 45.00% | +0.5584R | +22.336R | 2.534 |
| REJECT | ALL | 1127 | 22.45% | +0.0442R | +49.781R | 1.056 |
| REJECT | NYBUY | 817 | 18.60% | +0.0663R | +54.150R | 1.078 |
| REJECT | LONBUY | 310 | 32.58% | -0.0141R | -4.369R | 0.976 |

The gates increase aggregate EV by about `+1.281R/trade` relative to the pooled rejected population. They materially discriminate quality.

## Frozen regime test

| Population | Period | N | EV_net | Sum R | PF |
|---|---|---:|---:|---:|---:|
| ACCEPT | 2023 | 22 | -0.4394R | -9.667R | 0.372 |
| REJECT | 2023 | 268 | -0.0320R | -8.572R | 0.960 |
| ACCEPT | EARLY | 60 | +0.2749R | +16.492R | 1.419 |
| REJECT | EARLY | 551 | -0.0722R | -39.785R | 0.910 |
| ACCEPT | LATE | 101 | +1.9485R | +196.794R | 5.220 |
| REJECT | LATE | 576 | +0.1555R | +89.567R | 1.204 |

The broad rejected population is negative in 2023 and in the EARLY half, then positive in the LATE half. Therefore the early weakness is not explained primarily by the narrow accepted/executed sample or by quality-gate calibration.

## Yearly pooled results

| Population | Year | N | EV_net | Sum R | PF |
|---|---:|---:|---:|---:|---:|
| ACCEPT | 2023 | 22 | -0.4394R | -9.667R | 0.372 |
| ACCEPT | 2024 | 50 | +1.3512R | +67.559R | 3.493 |
| ACCEPT | 2025 | 60 | +1.6529R | +99.171R | 4.324 |
| ACCEPT | 2026 | 29 | +1.9387R | +56.223R | 5.119 |
| REJECT | 2023 | 268 | -0.0320R | -8.572R | 0.960 |
| REJECT | 2024 | 336 | -0.0579R | -19.459R | 0.927 |
| REJECT | 2025 | 408 | +0.1382R | +56.403R | 1.181 |
| REJECT | 2026 | 115 | +0.1862R | +21.408R | 1.242 |

## Main reject reasons

| Reason | N | EV_net | PF | Frozen interpretation |
|---|---:|---:|---:|---|
| SL_TOO_TIGHT_USD | 508 | -0.1505R | 0.816 | Keep filter |
| SCORE_BLOCK | 318 | +0.2080R | 1.257 | GATE_LOOSEN_CANDIDATE only |
| FAR_FROM_SWING_HIGH | 245 | +0.1644R | 1.232 | GATE_LOOSEN_CANDIDATE only |
| SWEEP_TOO_SHALLOW | 17 | +0.3618R | 1.451 | N too small |
| SLATR_OUT_OF_RANGE | 15 | +0.9500R | 2.357 | N too small |
| LON_H1_NOT_BULL | 16 | +0.2334R | 1.491 | N too small |
| LON_RECLAIM_CP | 7 | -0.4661R | 0.106 | Keep evidence, N small |

Adjusted regression relative to ACCEPT remains negative for every main reject class. The model R² is only about `4.3%`, so reject reason is a population selector, not a complete outcome model.

## SCORE_BLOCK

- `<=69`: N=23, EV `-0.6775R`
- `70–79`: N=52, EV `+0.4500R`
- `80–92`: N=109, EV `+0.2120R`
- `93–99`: N=127, EV `+0.2407R`
- `>=100`: N=7, EV `+0.6643R`

All 297 NYBUY SCORE_BLOCK rows use exact qScore from debug. LONBUY debug does not emit qScore, so 21 LONBUY rows use the frozen mechanical reconstruction. The relationship is non-monotonic and supports a separate OOS hypothesis, not immediate gate removal.

## SL_TOO_TIGHT_USD

- 2023: N=207, EV `-0.1388R`
- 2024: N=175, EV `-0.0988R`
- 2025: N=120, EV `-0.3040R`
- 2026: N=6, EV `+1.0049R` — insufficient N

The filter is supported across the meaningful sample and remains unchanged.

## Frozen verdict

### CONFIRMS-REGIME

Triggered because rejected 2023 has N=`268` and EV=`-0.0320R`.

### GATE-ARTIFACT

Not triggered.

### GATE_LOOSEN_CANDIDATE

Research-only candidates for separate preregistered OOS work:

1. `ALL/FAR_FROM_SWING_HIGH`: N=245, EV `+0.1644R`
2. `ALL/SCORE_BLOCK`: N=318, EV `+0.2080R`
3. `LONBUY/FAR_FROM_SWING_HIGH`: N=91, EV `+0.3075R`
4. `NYBUY/SCORE_BLOCK`: N=297, EV `+0.2025R`

No candidate is approved for implementation. Do not loosen gates, optimize thresholds or increase FT risk on this data.