# FT_DEEP_001 — partial-depth diagnostic report

**Date:** 2026-07-25  
**Frozen specification:** TZ-FT-DEEP-001  
**Formal verdict:** **INCONCLUSIVE**

## 1. Input audit

Received `XAUUSD_M5_20220601_20260723.csv`.

- SHA256: `43a00406241ccad5136c111e9f58f06494abd2883507bbbf350eaa172d8be4c4`
- rows: `100,000`
- first bar: `2025-02-19 06:30:00`
- last bar: `2026-07-23 23:45:00`
- duplicates: `0`
- invalid OHLC rows: `0`
- median spread: `25` points
- p95 spread: `58` points

The requested export began at `2022-06-01`, but the file begins at `2025-02-19` and contains exactly `100,000` rows. This is consistent with a terminal/history limit truncating the single large `CopyRates` request. The file therefore provides only `17.05` calendar months, below the preregistered 24-month minimum and far below the requested 42 months.

Because EMA50 bias uses a 200-bar manual warmup plus the 3-bar slope lookback, D1 parity becomes warmup-complete only from `2025-12-03 01:05:00`. The reliable diagnostic suffix is only `7.62` months.

## 2. Step 0 parity status

| Module | Tester reference | Oracle | Delta | Count gate | Time overlap |
|---|---:|---:|---:|---|---|
| NYBUY | 17 | 18 | +1 | PASS | BLOCKED |
| LONBUY | 7 diagnostic reference | 7 | +0 | PASS | BLOCKED |

The count tolerance is satisfied. The required `>=80%` entry-time overlap cannot be computed because the tester 156-1 trade-time fixture / `AK47_ea_dryrun_signals.csv` was not supplied or found.

Therefore Step 0 is **COUNT_PASS / TIME_OVERLAP_BLOCKED**, not a formal parity PASS.

## 3. Warmup-complete diagnostic suffix

Window: `2025-12-03 01:05:00` through `2026-07-23 23:45:00`.

- N: `27`
- EV net: `+2.160244R`
- Sum: `+58.326586R`
- WR: `59.26%`
- PF: `6.050`

### Module split

| module | N | EV_net | sumR |
|---|---:|---:|---:|
| LONBUY | 7 | +0.189512 | +1.326586 |
| NYBUY | 20 | +2.850000 | +57.000000 |

### Monthly

| month | N | EV_net | sumR |
|---|---:|---:|---:|
| 2025-12 | 2 | +1.950000 | +3.900000 |
| 2026-01 | 12 | +2.056841 | +24.682095 |
| 2026-02 | 9 | +2.438277 | +21.944491 |
| 2026-03 | 0 | 0 | 0 |
| 2026-04 | 4 | +1.950000 | +7.800000 |
| 2026-05 | 0 | 0 | 0 |
| 2026-06 | 0 | 0 | 0 |
| 2026-07 | 0 | 0 | 0 |

### Halves

| half | start | end | N | EV_net | sumR |
|---|---|---|---:|---:|---:|
| EARLY | 2025-12-03 01:05 | 2026-03-29 12:25 | 23 | +2.196808 | +50.526586 |
| LATE | 2026-03-29 12:25 | 2026-07-23 23:45 | 4 | +1.950000 | +7.800000 |

### Concentration and inactivity

- zero-entry months: `4/8`
- top-3 months contribution: `93.31%` of total net R
- top months: `2026-01, 2026-02, 2026-04`
- March, May, June and July 2026 had zero trades.

The top-3 concentration exceeds the preregistered `70%` REGIME threshold. This is **diagnostic evidence of regime concentration**, but the formal REGIME verdict cannot be issued because the depth is below 24 months and N is below 90. Under the frozen hierarchy the result remains INCONCLUSIVE.

## 4. Reject funnel

| module | reject_reason | count |
|---|---|---:|
| LONBUY | HTF_BLOCK | 5927 |
| LONBUY | FAR_FROM_SWING_HIGH | 18 |
| LONBUY | LON_H1_NOT_BULL | 8 |
| LONBUY | SCORE_BLOCK | 5 |
| LONBUY | SL_TOO_TIGHT_USD | 4 |
| LONBUY | LON_RECLAIM_CP | 3 |
| LONBUY | LON_SWEEP_DEPTH | 1 |
| NYBUY | HTF_BLOCK | 5087 |
| NYBUY | SCORE_BLOCK | 76 |
| NYBUY | FAR_FROM_SWING_HIGH | 40 |
| NYBUY | SWEEP_TOO_SHALLOW | 9 |
| NYBUY | SL_TOO_TIGHT_USD | 4 |
| NYBUY | SLATR_OUT_OF_RANGE | 2 |

HTF gating dominates the reject stream. This is consistent with the hypothesis that the system can remain disabled for long bearish/neutral periods.

## 5. Formal decision

**INCONCLUSIVE**

Independent blockers:

1. available calendar depth `17.05` months `<24`;
2. warmup-complete evaluable depth `7.62` months `<24`;
3. N `27` `<90`;
4. Step 0 entry-time overlap unavailable.

No GO, REGIME or NO-GO decision is permitted from this file.

## 6. Required next inputs

1. Re-export with `XAUUSD_M5_DEEP_Exporter_v002.mq5`.
2. Required first bar: no later than `2022-06-01`.
3. Required last bar: at least `2026-07-23 23:45`.
4. Supply tester 156-1 `AK47_ea_dryrun_signals.csv` or equivalent NYBUY/LONBUY entry-time fixture.
5. Re-run Step 0; only then open the 42-month verdict.
