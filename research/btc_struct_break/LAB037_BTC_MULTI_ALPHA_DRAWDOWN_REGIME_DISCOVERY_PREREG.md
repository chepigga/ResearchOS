# BTC_MULTI_ALPHA_DRAWDOWN_REGIME_DISCOVERY_LAB_037

Date: 2026-08-27

## Objective
Identify causal pre-trade portfolio-wide bad regimes for the frozen BASE3 + FAILED_RANGE_EXPANSION_DIST_GT_1 portfolio, without changing entry logic.

## Frozen feature families
All features are computed strictly from information available before each candidate trade starts.

1. ATR percentile / volatility regime
   - ATR14 percentile over trailing 20 trading days (1920 M15 bars), lagged by one bar.
   - States: LOW <20%, MID 20-80%, HIGH >80%.
2. Range efficiency
   - abs(close_t - close_t-16) / sum(abs(diff close)) over prior 16 completed M15 bars.
   - States: LOW <0.25, MID 0.25-0.55, HIGH >0.55.
3. Directional persistence
   - fraction of prior 12 completed M15 closes moving in same sign as net 12-bar return.
   - States: LOW <0.58, MID 0.58-0.75, HIGH >0.75.
4. Recent failed-break density
   - count during prior 24 completed M15 bars of closes beyond prior-8-bar high/low that return inside that prior range within 3 bars.
   - States: 0-1, 2-3, 4+.
5. Recent signal clustering
   - number of frozen portfolio candidate starts in previous 24 hours, excluding current trade.
   - States: LOW <=2, MID 3-5, HIGH >=6.
6. Recent realized portfolio hit-rate / drawdown
   - hit-rate among previous 10 completed accepted trades, before current start: LOW <40%, MID 40-60%, HIGH >60%.
   - realized drawdown state before current start: NORMAL <2R, ELEVATED 2-4R, HIGH >=4R.

## Discovery protocol
- Discovery universe: frozen one-position BASE3 + FAILED_RANGE_EXPANSION_DIST_GT_1 baseline from LAB036.
- DEV: <=2022.
- VAL: 2023-2025.
- 2026 shadow only.
- Single-state screening only. No conjunction search in this LAB.
- BUY/SELL and individual streams are diagnostics only, not selectable.
- For each state compute N, EV, PF, MaxDD, yearly transfer, 1.5x cost EV, and share of worst-drawdown trades.

## Bad-regime seed gate
A state is considered a portfolio-wide bad-regime seed only if:
- DEV EV <= baseline DEV EV - 0.08R OR DEV EV < 0,
- VAL EV <= baseline VAL EV - 0.08R OR VAL EV < 0,
- N >= 60 in VAL,
- at least 2/3 VAL years have EV below the VAL portfolio baseline,
- state captures >=25% of baseline worst-drawdown trades,
- state frequency <=60% of all VAL trades (must be selective),
- no post-hoc side or stream selection.

## Router diagnostics
For each qualifying bad regime, test exactly two non-promotional diagnostics:
- REDUCE: all portfolio trades in bad state use 0.5x risk.
- SKIP: all portfolio trades in bad state are skipped.

A router can be promoted only if VAL 2023-2025 has:
- trades/year >=115,
- EV >= +0.15R,
- PF >=1.35,
- MaxDD <=10R,
- profitable months >=60%,
- Recovery >=2,
- worst rolling 3M >= -3R,
- 1.5x cost EV >0.

2026 shadow cannot promote a router.
