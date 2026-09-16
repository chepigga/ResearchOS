# GC_XAU_D1_E1_VS_E3_FORWARD_SHADOW_LAB_012 — PREREG

Status at freeze: **PREREGISTERED / FORWARD COLLECTION ONLY / NO HISTORICAL RETUNING**.

This LAB continues the frozen GC→XAU lineage after LAB011. It is not a new discovery search.

## 1. Immutable forward cutoff

Only GC information events strictly later than:

- LAB011 result commit: `a8c74b568b85d6a4d195f6558860256a72a7319b`
- commit time / forward cutoff: `2026-09-16T19:29:45Z`

may enter LAB012 statistics.

Any row at or before that timestamp is rejected as exposed history.

## 2. Frozen sensor

Sensor label: `BUYER_BREAKOUT_LONG_001`.

On a fully completed GC M1 bar require all of:

1. buyer aggression A: `delta_frac >= causal prior240 Q90(delta_frac)`;
2. `buy_vol >= causal prior240 Q75(buy_vol)`;
3. `close > open`;
4. positive buyer impact / bullish body;
5. `high >= prior20_high`, where current bar is excluded from prior20;
6. `close_pos >= 0.75`.

Rolling references are shifted by one completed bar. No signal may exist before the M1 bar is fully closed. Aggressor direction remains exclusive BUY/SELL semantics from the frozen AMP loader.

No threshold, session, news, volatility, spread, trend, regime, or short-side filter may be added in LAB012.

## 3. Two declared execution candidates

### A — incumbent

`GCXAU_D1.00_E3M_SL1.5_TP3_ONEACTIVE_001`

- XAU BUY LIMIT = contemporaneous executable Ask minus `1.00 × XAU ATR14(M1)`;
- expiry = 3 minutes;
- SL = `1.50 × ATR` below fill;
- TP = `3R = 4.50 × ATR` above fill;
- one active setup at a time.

### B — forward-only challenger

`GCXAU_D1.00_E1M_SL1.5_TP3_ONEACTIVE_CHALLENGER_001`

Identical to A except expiry = 1 minute.

### Timeout freeze for LAB012

To isolate **expiry** as the only intentional execution difference, both candidates use the incumbent operational convention:

`hard timeout = signal timestamp + 30 minutes`.

This keeps E3 semantically continuous with LAB009/010. LAB012 therefore explicitly declares E1's previously-open timeout choice as **30 minutes from original signal** before the first eligible forward observation.

No alternate timeout is scored as a candidate in LAB012.

## 4. Quote/execution semantics

For LONG shadow execution:

- first executable XAU quote after GC information time is the market reference;
- limit touch/fill is based on actual FTMO **Ask**;
- SL / TP / timeout path is based on actual FTMO **Bid**;
- timestamps are millisecond UTC internally;
- server time is logged separately;
- stale quote or data gap is flagged, never silently interpolated;
- unfilled setup = `0R` in EV per original GC signal;
- one-active rejection = `0R` in EV per original GC signal.

One-active state is maintained **independently for E1 and E3**. Every eligible forward GC signal is nevertheless recorded for both candidates so the paired difference is defined on the same original signal set.

## 5. Cost bookkeeping

Quoted FTMO spread is naturally embedded through Ask entry / Bid exit.

For every filled shadow trade log separately:

- explicit commission in R, if known;
- explicit slippage in R, if measured/defined;
- `R_quote_only`;
- `R_actual_cost` when explicit cost fields are available;
- continuity stress `R_stress005 = R_quote_only - 0.05R` for a fill, and 0R for unfilled/blocked signals.

`R_stress005` is retained only for comparability with LAB009–011; it is not a substitute for target-account commission/slippage. No production claim is allowed until current broker/prop specifications are reconfirmed.

## 6. Append-only forward ledger

Canonical ledger:

`research/gc/GC_XAU_D1_E1_VS_E3_FORWARD_SHADOW_LAB_012_LEDGER.csv`

Each eligible GC signal must have two rows, one per candidate. Existing rows must not be rewritten after outcomes become known. Corrections require a new `record_version`, explicit `correction_of`, and reason; the evaluator uses the latest non-void version while preserving the prior record.

Required groups:

- GC sensor raw values and causal thresholds;
- exact GC signal UTC ms;
- XAU signal quote, spread, ATR, limit, start/expiry;
- one-active acceptance/rejection;
- first touch/fill timestamp and delay;
- SL/TP, MFE/MAE at 1/3/5/15/30m;
- first passage, timeout/exit, R before and after explicit costs;
- data-gap and stale-quote flags.

## 7. Forward maturity gate — frozen before outcomes

Do not select a winner before all are true:

- at least **100** eligible post-freeze GC signals;
- at least **15** distinct UTC trading days;
- at least **30 filled trades in E1**;
- at least **30 filled trades in E3**.

Before maturity the only permitted verdict is `INSUFFICIENT_FRESH_FORWARD_SAMPLE` plus descriptive metrics.

## 8. Candidate health gates after maturity

Reported separately for E1 and E3 using the full original-signal denominator:

- `EV/signal > 0` under `R_stress005`;
- PF > 1.20 on filled outcomes under `R_stress005`;
- late-half EV/signal >= 0;
- no single UTC day contributes >=50% of total positive R;
- observed MaxDD at 0.25% risk <4.0% of equity, equivalent to MaxDD <16R.

Actual-cost metrics are always reported where available. **Live/production eligibility additionally requires EV/signal >0 after real spread + reconfirmed commission + measured/logged slippage.**

## 9. Paired E1 vs E3 promotion rule

Primary paired variable per original GC signal:

`D = R_stress005(E1) - R_stress005(E3)`.

At maturity compute mean D and a UTC-day block bootstrap 95% CI.

E1 may replace E3 as the preferred research execution candidate only if:

1. E1 passes all candidate health gates; and
2. lower bound of paired day-block bootstrap CI95 for D is `> 0`.

If both candidates pass their health gates but the paired CI includes zero, result is `E1_VS_E3_INCONCLUSIVE` and E3 remains the incumbent by governance rather than by claimed superiority.

If E3 passes and E1 fails, E3 survives forward challenge. If neither passes, neither is promoted toward live execution.

## 10. Risk convention

Forward equity diagnostics use **0.25% risk per filled trade** only. No 0.5% production sizing is evaluated as acceptable in this LAB because LAB010 historical dependency bootstrap showed p95 drawdown around 7–8% at 0.5% risk.

## 11. Prohibited actions

- no use of Aug–Sep exposed data to change parameters;
- no 0.93/1.07 ATR depth search;
- no extra expiry values;
- no seller/SHORT mirror;
- no confirmation/reclaim branch;
- no volatility-scale selection;
- no removal of losing forward observations;
- no retrospective change to this acceptance gate.

Any future change creates a new candidate/LAB version and cannot rewrite LAB012.
