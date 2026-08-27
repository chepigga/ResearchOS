# LAB024 — M15_VOLATILITY_REGIME_DISCOVERY

Date: 2026-08-27
Status: PREREGISTERED BEFORE RESULT CALCULATION

## Objective
Test whether the surviving M15 event families are conditioned by causal volatility regimes that can add independent positive populations without weakening the frozen old-protected-pivot core.

## Frozen event families
1. BREAK_RETEST — canonical frozen v002 trade/event lineage.
2. COMPRESSION_RELEASE SELL — canonical reproducible LAB023 pooled BUY+SELL compression queue, SELL trades only.

No entry, stop, TP, BE, or queue logic may be changed in LAB024.

## Causal volatility features
All features are computed from completed M15 bars available no later than the trade fill bar. No forward information.

1. ATR14 percentile over trailing 20 trading days (1920 M15 bars): bins `<20%`, `20–40%`, `40–60%`, `60–80%`, `>80%`.
2. Realized volatility of log returns over 4 bars (1h), 16 bars (4h), and 96 bars (24h), each expressed as percentile over trailing 1920 bars; same five percentile bins.
3. ATR14 / rolling median ATR14(96): bins `<0.75`, `0.75–1.0`, `1.0–1.25`, `1.25–1.5`, `>1.5`.
4. Volatility-of-volatility: rolling std of ATR14/price over 16 bars, percentile over trailing 1920 bars; five percentile bins.
5. Compression-to-expansion transition: prior 8-bar realized range <= 40th trailing percentile AND current 4-bar realized range >= 60th trailing percentile. Binary frozen state.

## Analysis
For each event family and each volatility feature/state report DEV (2019–2022), VAL (2023–2025), and 2026 shadow separately:
- N
- trades/year
- EV in R
- PF
- sumR
- MaxDD
- yearly VAL results
- 1.0x and 1.5x modeled cost stress
- overlap with the current old-protected-pivot core where applicable.

No continuous threshold optimization, ML, feature combinations, or post-result threshold movement are allowed.

## Discovery gate for a volatility regime seed
A regime is a replication seed only if:
- DEV EV > 0;
- VAL EV >= +0.08R;
- VAL PF >= 1.15;
- VAL N >= 25;
- at least 2/3 VAL years positive;
- VAL EV remains >0 at 1.5x costs;
- no single VAL year contributes >70% of net positive VAL sumR;
- overlap with existing old-pivot core <=50% for a candidate intended to add frequency.

Because multiple volatility states are screened, any passing state remains DISCOVERY/REPLICATION_SEED, not confirmed production edge.

## Output integrity
Persist trade-level feature table before interpretation, state/bin metrics, yearly metrics, cost stress, overlap table, and candidate-gate table.
