# XAU / AK47 Project — Master Research Backlog

**Date:** 2026-07-28  
**Branch:** `xau-ak47-research`  
**Target:** XAUUSD, FTMO-style $100K prop challenge

## Executive conclusion

The project has moved from testing isolated XAU setups to understanding three separate layers:

1. signal edge;
2. trade lifecycle and M3 exit behaviour;
3. market-regime permission before a new entry.

The strongest current conclusion is that the EA reacts to price geometry but does not understand whether the market is in continuation, reversal, balance, exhaustion, or failed acceptance. Two-sided OCO is therefore often used as a substitute for directional and regime understanding.

## What has been researched

### MorrisCandle / BeltHold setup

Frozen M15 engine:

- fractal depth 5;
- swing age up to 96 bars;
- sweep of an unconsumed swing;
- same-bar reclaim;
- BeltHold confirmation within 3 bars;
- body >= 0.60 range;
- opposite shadow <= 0.05 range;
- EMA20 context;
- SL at extremum ± 0.25 ATR14;
- TP 2R;
- time stop 96 M15 bars.

Deep test over about 42 months:

- N=135;
- EV about +1.12R;
- PF about 2.76.

But regime split was unstable:

- 2023-01 to 2024-10: N=54, EV about 0;
- 2024-10 to 2026-07: N=81, EV about +1.88R.

Conclusion: promising but regime-dependent, not validated as universal.

### AK47 H1 OCO line

Recent frozen geometry:

- SL=3700;
- TP=9700;
- Padding=5;
- RS001 OFF;
- Breakeven OFF;
- Trailing OFF;
- M3 Adaptive Giveback ON.

The OCO architecture currently means:

```text
H1 range exists
→ place BUY STOP and SELL STOP
→ first trigger defines direction
```

This is structurally weak in balance and post-exhaustion regimes.

### M3 giveback research

M3 activates after about 1R MFE and exits after a closed H1 bar gives back to roughly 40% of peak MFE.

Optimiser behaviour often preferred huge TP values, implying that M3, not TP, was the practical exit. Therefore optimiser output represented the interaction of entry geometry, SL size, and M3 path dependency rather than a classical SL/TP optimum.

### Immediate post-M3 re-entry

Observed behaviour:

```text
M3 closes position
→ no position exists
→ OCO permission immediately returns
```

The EA does not assess whether the market is still valid for breakout trading.

Tested and rejected:

- one-hour lock;
- directional lock;
- structural reset;
- fresh-bar re-arm.

Episode Boundary Lab:

- 119 M3 episodes;
- 119 next entries;
- 119 next outcomes;
- 828 H1-state observations.

Descriptive split:

- entry before any new H1 close: N=81, avg -$32.25, total -$2,612.28, WR 35.8%;
- entry after at least one H1 close: N=38, avg +$20.45, total +$776.97, WR 52.6%.

Fresh-bar re-arm then failed causally:

- Trades 326;
- Net -$964.84;
- PF 0.983;
- Max Equity DD 7.21%;
- baseline M3: 364 trades, +$4,664.50, PF 1.091, DD 6.54%.

Lesson: natural delay was a regime marker, not a causal rule.

## What we know

- XAU edge is regime-dependent.
- Timing alone does not fix re-entry.
- Path dependency is material.
- M3 changes the entire strategy distribution.
- Large TP optimisation means M3 is the real exit layer.
- OCO is not a regime model.
- Retrospective trade deletion cannot replace a real EA rerun.
- Simple structural boundaries are insufficient.

## What we do not know

- Why the original signal became strong only after late 2024.
- Whether MorrisCandle/BeltHold survives another feed.
- Whether M3 truly improves identical baseline trades.
- When post-M3 continuation is valid.
- When reversal is valid.
- When both directions must be skipped.
- Whether one-sided pending orders beat OCO.
- Exact sensitivity to spread, commission, slippage, rollover, feed and VPS latency.
- Whether one module can produce 100–300 quality trades or a multi-module portfolio is required.

## Closed branches

Keep closed unless new structural evidence appears:

- fixed one-hour cooldown;
- same-direction lock;
- opposite-direction lock;
- structural reset;
- fresh-bar-only re-arm;
- arbitrary H1 waits;
- continuation-close as direct entry permission.

## Highest-priority next research

### P1 — `AK47_H1_POST_M3_VOLATILITY_STATE_LAB_001`

Primary question:

> Is the market currently suitable for breakout trading at all?

Target states:

- TREND_EXPANSION;
- BALANCED_VOLATILITY;
- COMPRESSION;
- EXHAUSTION;
- TWO_SIDED_INSTABILITY.

Features available before entry:

- ATR14 and ATR change;
- range/ATR;
- average range over 3–5 H1 bars;
- overlap over 2–4 bars;
- directional efficiency;
- side switches;
- high/low breaks;
- close location;
- wick/body structure;
- distance travelled in ATR;
- previous-trade MFE and giveback;
- expansion duration;
- climax-range flag.

Required causal control:

- matched volatility states without prior M3 exit.

### P2 — `AK47_H1_M3_EXIT_CAUSAL_LAB_001`

Compare on identical baseline entries:

- original SL/TP;
- M3 full exit;
- M3 50% partial + runner;
- M3 70% partial + runner;
- post-M3 MFE/MAE;
- eventual TP/SL.

### P3 — `RS001_PERDIR_LOOKBACK_001`

Calibrate per-direction lookback because 200/10 was inherited from combined BUY+SELL flow and is too slow after directional split.

### P4 — Original signal regime decomposition

Explain early-flat versus late-strong periods using ATR percentile, trend persistence, overlap, directional efficiency and higher-timeframe state.

### P5 — Rejected-candidate control

Verify that accepted setups truly outperform rejected candidates.

### P6 — Execution survival

Mandatory before live:

- spread sweep;
- commission;
- slippage Monte Carlo;
- rollover widening;
- delayed OCO cancellation;
- feed variation;
- VPS latency.

## Future architecture

```text
RS001 strategy health
→ local volatility/auction state
→ directional setup
→ one-sided entry or skip
→ causal trade management
→ portfolio risk governor
```

The project should move away from:

```text
every H1 range
→ two-sided OCO
→ manage whatever triggers
```

and toward:

```text
market state understood
→ valid directional hypothesis
→ selective entry
→ controlled lifecycle
```

## Immediate next action

1. Build Python-first `AK47_H1_POST_M3_VOLATILITY_STATE_LAB_001`.
2. In parallel, build `AK47_H1_M3_EXIT_CAUSAL_LAB_001`.
3. Use MT5 only for final replication of pre-registered candidates.
