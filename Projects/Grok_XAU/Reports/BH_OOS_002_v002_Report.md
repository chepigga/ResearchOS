# BH_OOS_002 v2 — OOS Validation Report

**Project:** Grok_XAU / AK47_FT  
**Date:** 2026-07-24  
**Status:** COMPLETED / VALIDATED  
**Formal verdict:** PASS — DEMO ONLY  
**Live deployment:** PROHIBITED pending forward month

## 1. Objective

Validate the frozen `BH_SWEEP` module from `AK47_FT_EA_156.mq5` on unseen
XAUUSD M15 data for 2026-05-01 through 2026-07-23 without parameter tuning.

## 2. Frozen configuration

- Fractal depth: 5
- Swing maximum age: 96 M15 bars
- Pattern window: 0..3 bars
- BeltHold body: >= 0.60 × range
- Opposite shadow: <= 0.05 × range
- EMA context: EMA20 reversal
- Entry: next M15 open
- SL: sweep-to-signal extremum +/- 0.25 × ATR14
- TP: 2.0R
- Time stop: 96 actual M15 bars
- Same-bar collision: SL priority
- Cost correction: -0.05R per trade
- Portfolio/live gates: excluded

No parameter was changed after OOS inspection.

## 3. Inputs and provenance

### Frozen engine

- `AK47_FT_EA_156.mq5`
- SHA256: `838b3e180a139008c69792c0f122f3da66a590ef5e6ee98056056f0938311b65`
- BH module: v1.55 inside EA v1.56

### Step 0 reference

- `XAUUSD_M5.csv`
- SHA256: `cd2e3285c0e4660786a019999fb3e746257c2cbd4d400fe48092cdbbc7760a80`
- Coverage: 2025-01-01 23:00 through 2026-04-21 23:45
- Reference wide basket SHA256: `5a31437ac73c561a32a9a294c6dd1bccf29332ba21e95923fbfcf3c019279847`
- Reference tight basket SHA256: `8aa002b11369e312c2571e855ed26e58110d805026950fc95e1b9ab19d1d0f21`

### OOS data

- `XAUUSD_M15_202412020100_202607232345.csv`
- SHA256: `7a03c7eca6d333981cc9f30c783f83c31ec15bed46d6b44ae2164a756574f1f3`
- Rows: 38,742
- First bar: 2024-12-02 01:00:00
- Last bar: 2026-07-23 23:45:00
- Duplicate timestamps: 0
- Invalid OHLC rows: 0
- Median spread field: 24 points
- 95th percentile spread field: 55 points

The export begins on 2024-12-02 rather than 2024-12-01, but contains far more
than the required 112 warmup bars before the first evaluated trade.

## 4. Step 0 — reproduction control

The original M5 reference was resampled to M15 and replayed using the exact
`ProcessBeltHold()` ordering.

### Result

| Metric | Target | Reproduced |
|---|---:|---:|
| Trades | 88 | 88 |
| BUY | 52 | 52 |
| SELL | 36 | 36 |
| Legacy net EV | +0.276R | +0.275780R |
| Entry-time/direction matches | 88 | 88 |
| Exit mismatches | 0 | 0 |

The canonical parent is **`BeltHold_trades_regen_wide-2026-07-05.csv` plus
EMA20 reversal context**. The `tight` file is the EMA10 sensitivity basket
(N=56), not the N=88 canonical basket.

Per-trade comparison against the wide file:

- entry max absolute difference: 0.000000
- SL/TP max absolute difference: 0.005000, caused by reference CSV rounding
- net-R max absolute difference: 0.000498, caused by reference CSV rounding
- exit-reason differences: 0

Applying the newly frozen fixed `-0.05R` cost to the same control basket gives
EV `+0.258370R`, a drift of `-0.017630R` versus the historical +0.276R target.
This is inside the preregistered EV tolerance of 0.02R and is fully explained
by the changed cost convention.

**Step 0 verdict: PASS.**

## 5. Step 1 — OOS result

Window: 2026-05-01 through 2026-07-23.

| Metric | Result |
|---|---:|
| Trades | 14 |
| BUY / SELL | 8 / 6 |
| TP / SL / TIMESTOP | 6 / 8 / 0 |
| Win rate | 42.86% |
| EV raw | +0.285714R |
| EV net | **+0.235714R** |
| Sum net R | **+3.300R** |
| Profit factor net | 1.393 |
| Max drawdown | 3.300R |
| Unresolved trades | 0 |

### Monthly stability

| Month | N | BUY/SELL | EV net | Sum net R |
|---|---:|---:|---:|---:|
| 2026-05 | 5 | 4 / 1 | +0.150R | +0.750R |
| 2026-06 | 4 | 1 / 3 | +0.450R | +1.800R |
| 2026-07 | 5 | 3 / 2 | +0.150R | +0.750R |

All three OOS months were positive.

### Direction split

| Direction | N | EV net | Sum net R | TP / SL |
|---|---:|---:|---:|---:|
| BUY | 8 | +0.450R | +3.600R | 4 / 4 |
| SELL | 6 | -0.050R | -0.300R | 2 / 4 |

The SELL leg was slightly negative, but disabling or modifying it is forbidden
post hoc. It remains part of the frozen demo-forward configuration.

## 6. Formal preregistered verdict

PASS requires:

- N >= 8
- EV_net >= 0

Observed:

- N = 14
- EV_net = +0.235714R

**FORMAL VERDICT: PASS.**

`InpBH_Enable=true` is allowed on **demo only**. Live trading remains prohibited
until one complete forward month is collected and reviewed.

## 7. Practical deployment decision

- Enable only the BH module on demo using the frozen defaults.
- Keep risk at `InpBH_RiskPct=0.30%`; do not increase risk.
- Preserve all portfolio and prop-firm safety gates in the integrated EA.
- Record signal, fill, spread, slippage, SL/TP and time-stop lifecycle.
- Do not optimize BUY/SELL separately after this 14-trade OOS sample.
- Reassess after one full forward month.

## 8. Limitations

- OOS sample size is modest despite passing the preregistered N gate.
- M15 bar replay uses conservative same-bar SL priority.
- The fixed -0.05R cost is a standardized correction, not tick-level execution.
- Same-broker history shows timestamp-convention differences between historical
  M5 and later direct M15 exports; internal chronological replay is unaffected,
  but timestamps are retained exactly as supplied in each source.
