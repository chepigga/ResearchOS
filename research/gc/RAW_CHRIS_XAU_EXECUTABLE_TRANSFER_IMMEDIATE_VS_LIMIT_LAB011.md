# RAW CHRIS XAU EXECUTABLE TRANSFER — IMMEDIATE VS LIMIT LAB011

**Status:** `HISTORICAL_XAU_TRANSFER_BOTH_VARIANTS_FAIL_SMALL_SAMPLE_NOT_OOS`

Frozen transfer of LAB010 execution hypotheses to FTMO-Demo XAUUSD raw Bid/Ask ticks on the Aug-Sep 2026 GC/XAU overlap.

## Frozen variants

- A: immediate SHORT at XAU Bid; SL 1.0 XAU ATR; TP 2.0 XAU ATR; hard timeout 30m.
- B: SELL LIMIT at initial Bid +0.50 XAU ATR; expiry 5m; same SL/TP; hard timeout remains 30m from original GC entry clock.
- Clock mapping frozen at UTC+180m from prior LAB007.
- SHORT exits use XAU Ask. Spread is therefore embedded.
- Stop loss uses actual first Ask crossing; TP uses target price.
- No new filter or parameter sweep.

## Results

| Variant | Signals | Fills | Fill rate | EV/fill | Signal EV | PF | WR | SumR | MaxDD | Max neg streak | TP/SL/TO |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Immediate | 23 | 23 | 100.0% | -0.405 | -0.405 | +0.518 | 21.7% | -9.309 | +9.309 | 8 | 5/18/0 |
| Limit +0.50ATR/5m | 23 | 19 | 82.6% | -0.078 | -0.065 | +0.890 | 31.6% | -1.487 | +4.167 | 4 | 6/13/0 |

## Extra-cost stress

| Variant | +0.00R | +0.05R | +0.10R |
|---|---:|---:|---:|
| Immediate | -0.405 | -0.455 | -0.505 |
| Limit +0.50ATR/5m | -0.078 | -0.128 | -0.178 |

## Bootstrap

- Immediate: P(EV>0) = 7.0%; 95% CI [-0.902, +0.137] R.
- Limit +0.50ATR/5m: P(EV>0) = 39.1%; 95% CI [-0.714, +0.564] R.

## Monthly

### Immediate
- 2026-08: N=12, EV=-0.269R, Sum=-3.229R, WR=25.0%.
- 2026-09: N=11, EV=-0.553R, Sum=-6.080R, WR=18.2%.

### Limit +0.50ATR/5m
- 2026-08: N=9, EV=-0.364R, Sum=-3.278R, WR=22.2%.
- 2026-09: N=10, EV=+0.179R, Sum=+1.791R, WR=40.0%.

## Frozen gates

### Immediate
- PASS — `signals_ge20`
- PASS — `filled_ge20`
- FAIL — `gross_ev_pos`
- FAIL — `cost_005_ev_pos`
- FAIL — `gross_pf_ge110`
- PASS — `max_neg_streak_le8`

### Limit
- PASS — `signals_ge20`
- PASS — `filled_ge10`
- PASS — `fill_rate_40_85pct`
- FAIL — `gross_ev_fill_pos`
- FAIL — `gross_signal_ev_pos`
- FAIL — `cost_005_ev_fill_pos`
- FAIL — `gross_pf_ge110`
- PASS — `max_neg_streak_le8`

## Decision

Neither frozen LAB010 geometry passes the executable-XAU transfer gates on the available overlap. Do not rescue by tuning stop, target, limit depth, expiry, session, or spread filters on this same sample.

Exact commission is not assumed. Spread is embedded, and +0.05R/+0.10R extra-cost stress is shown separately.
