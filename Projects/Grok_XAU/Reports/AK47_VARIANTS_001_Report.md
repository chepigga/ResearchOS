# AK47_VARIANTS_001 — source audit and 42-month comparison

**Date:** 2026-07-25  
**Data:** XAUUSD tester-stream M5, 2022-06-01..2026-07-23  
**Starting balance:** $100,000  
**Commission:** $5 round-turn per lot  
**Path integrity:** primary and mirror deterministic M5 intrabar paths  
**Overall decision:** **V15 M15 is the strongest challenge candidate, but no version is approved for live scaling without exact MT5 tick parity.**

## 1. Data audit

- M5 rows: `290,893`
- Coverage: `2022-06-01 01:05 .. 2026-07-23 23:40`
- SHA256: `40175d5d73fbbe01d26fd1813d1bc299854ef535c328fa1fdd1b883f90509ae4`
- Duplicates: `0`
- Invalid OHLC: `0`
- Non-positive spread rows repaired: `201`
- Repair method: centered 5,001-bar rolling median, no price or signal field modified

## 2. Exact source identities

| File | Source identity | Core behavior |
|---|---|---|
| `AK47-UPD.mq5` | V15.0 / `AK-47_SMART_MM` | 08–18, no candle filter, risk 1% then ×0.5, SL/TP 1500/3000, trail 8/3, **no OCO** |
| `AK47-UPD4.mq5` | V19.0 / `AK-47_V19_FILTER` | 10–14, candle 850–3700, risk 1/0.1/0.01, daily $1,000, OCO, SL/TP 1500/2700 |
| `AK-47 Scalper EA - MT5.mq5` | V1.00 | SELL-only, spread ≤5, SL/TP 3.5/7, lot formula is not stop-risk sizing |

`AK47-UPD4.mq5` is the exact V19 source that was missing during the first V19 oracle. Therefore this report supersedes the earlier TZ-only V19 estimate.

## 3. Core metrics

| Variant | TF | N range | WR range | EV actual-risk | EV base-1% | PF range | 14d pass-rate |
|---|---:|---:|---:|---:|---:|---:|---:|
| V15 | M15 | 26,735–26,753 | 97.90–97.91% | **+0.079..+0.081R** | +0.029..+0.030R | 5.37–5.63 | **62.03%..62.62%** |
| V15 | H1 | 9,599–9,603 | 98.01–98.02% | **+0.079..+0.081R** | +0.065..+0.066R | 6.37–6.67 | **21.32%..21.52%** |
| V19 | M15 | 1,113–1,120 | 96.43–96.50% | **+0.166..+0.173R** | **+0.086..+0.089R** | 6.00–6.35 | **5.25%..5.52%** |
| V19 | H1 | 1,001 | 97.50% | **+0.111..+0.115R** | **+0.069..+0.071R** | 5.73–5.89 | **0.00%** |
| Scalper | tick-driven | 53–63 | 92.06–98.11% | +0.143..+0.186R | n/a | 4.83–52.0 | no valid 42-month distribution |

`EV actual-risk` normalizes each trade by its attached initial SL risk.  
`EV base-1%` measures result against 1% of current balance and therefore includes survivor-mode and maximum-lot dilution.

## 4. V15 findings

### V15 M15

- Rolling 14-day pass-rate: **62.03–62.62%**
- Best modeled 14-day window: **+357%..+368%**
- First passing window starts `2022-06-16`
- Permutation mean pass-rate: **96.81–97.30%**
- Actual chronology is worse than random ordering, not supported by only a few lucky clusters
- Hedge fills because OCO is absent: **1,495–1,599**
- Average frequency: about **25 trades per active day**
- Early-half EV: about `+0.041R`
- Late-half EV: about `+0.119R`
- Every calendar year is positive, but edge strengthens sharply in 2025–2026

This is the best explanation of a two-week challenge pass. It is also the highest execution-risk version because the 3-point trailing stop is below or near realistic stop/freeze constraints and because opposite pending orders remain active.

### V15 H1

- Rolling 14-day pass-rate: **21.32–21.52%**
- Permutation p95: **13.86–15.72%**
- Actual pass-rate is above permutation p95: favorable periods are temporally clustered
- Hedge fills: **313–317**
- Early-half EV: about `+0.044R`
- Late-half EV: about `+0.116R`

H1 is slower and more regime-concentrated than M15.

## 5. Exact-source V19 revision

### V19 M15

- Actual-risk EV remains positive: `+0.166..+0.173R`
- Base-1% EV is only `+0.086..+0.089R`
- 14-day pass-rate: `5.25%..5.52%`
- Permutation p95: `5.05–5.38%`
- Actual pass-rate is slightly above p95 in both path conventions

Under the frozen V19 verdict rules this is **HOT-STREAK-ARTIFACT / NO SCALE**, not GO. The signal itself is positive, but the exact source caps risk cash at `$900`, reducing account-level base-1% EV as balance grows, and challenge passes are temporally concentrated.

### V19 H1

- Actual-risk EV: `+0.111..+0.115R`
- Base-1% EV: `+0.069..+0.071R`
- `0/1,489` rolling windows reach +10%

H1 is **NO-GO for a two-week challenge objective**.

## 6. Original Scalper

The original scalper is not the challenge bot for this XAU feed:

- only `5` valid M5 bars in the entire dataset had positive spread `≤5`;
- all modeled trades occurred on `2022-06-29`;
- N=`53–63`;
- total result only `+$276..+$306`;
- it is hard-coded SELL-only;
- `InpRisk=3` controls lots through free margin, not a 3% stop-risk calculation.

Verdict: **NO-GO on XAUUSD**.

## 7. Integrity limitations

1. M5 OHLC cannot reproduce exact tick-by-tick modification of a 3-point or 5-point trailing stop.
2. Position modification code does not verify broker `STOPLEVEL/FREEZE_LEVEL`; failed modifications are ignored in V15/V19.
3. V15 source does not remove the opposite pending after fill, so it can hedge.
4. V15 `CountOrders()` and `CountPositions()` use property getters without explicitly selecting each ticket, creating terminal-state ambiguity.
5. The large compounded dollar balances are not a deployment forecast; maximum-lot caps, execution capacity, prop consistency rules and slippage would dominate long before those values.

## 8. Decision

1. **Promote V15 M15 only to exact MT5 tick-parity testing.**
2. Do not deploy or scale V15 in current form.
3. Exact parity test must log every pending placement, fill, SL modification failure and opposite-order hedge.
4. Add no filters and change no parameters before parity.
5. V19 remains NO SCALE; H1 is unsuitable for a two-week target.
6. Scalper is rejected for XAUUSD.

The passed challenge is most plausibly explained by **V15 M15**, where the modeled 14-day pass probability is roughly `62%`, rather than by V19 M15 at roughly `5%`.
