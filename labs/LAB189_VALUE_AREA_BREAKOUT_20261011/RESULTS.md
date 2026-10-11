# LAB189 — Value Area Breakout × Acceptance × Rejection × Candles

Diagnostic on frozen 5089 LAB185/186 H1 situations. Pre-entry 24h M5-OHLCV uniform volume-by-price estimate, 1h-frozen VAH/VAL. All confirmations observed only at entry, no retrospective fills. **No standalone breakout entry replay.**

|Period|Rejection n|Rejection TP-first|Acceptance n|Acceptance TP-first|
|--|--:|--:|--:|--:|
|TRAIN 2021–23|506|24.51%|36|13.89%|
|VALID 2024|199|23.62%|12|0%|
|CHECK 2025–Aug26|313|17.25%|24|4.17%|

Rejection+Engulfing: TRAIN 108/25.93%, VALID 38/26.32%, CHECK 55/16.36%. Rejection+3bar micro BOS TRAIN 364/26.10%, VALID 137/23.36%, CHECK 217/15.67%. Rejection+failed retest TRAIN 382/24.08%, VALID 153/24.84%, CHECK 231/15.15%. No consistent incremental benefit. Side interaction: CHECK SELL rejection 14.7% vs other 16.7%, BUY 20.3% vs 15.9%. Profile is approximation, not true per-price traded volume. Acceptance 72 cases only, selected by mandatory H1 sweep; do not infer continuation engine weak. Outcome is original M5 OHLC TP-first without trading costs, re-entry or post-confirmation fills. RR has near-zero SL outliers and requires stop QA. Historical CHECK previously researched; data-release latency assumption +5min is unverified.

**Next:** independent all-bar fresh VA breakout atlas with profile frozen before breakout and new post-confirmation next-open entries, fee-aware and no lookahead; compare Acceptance Continuation against Rejection Fade. No production EA change.

Local reproducible outputs in run container: LAB189_CAUSAL_PATTERN_ROWS.csv, LAB189_PATTERN_SUMMARY.csv, LAB189_REPORT.md, lab189_run.py.
