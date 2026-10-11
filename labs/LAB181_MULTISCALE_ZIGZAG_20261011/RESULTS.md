# LAB181 — MULTISCALE ZIGZAG × TIMEFRAME SCALE (first pass)
Date 2026-10-11, BTCUSDT 589793 M5 bars 2021-01-01 to 2026-08-10. Price-only causal closed-candle ATR(14) ZigZag; signal only after confirmation (never pivot-time). A=M30/M15/M5, B=H1/M15/M5, C=H4/H1/M15 (context/signal/execution).

Signals confirmed at k=1.5 signal-TF ATR: A/B 24567 with median confirmation lag 0.5h; C 5994 with median lag 2h. After last-confirmed context ZigZag direction alignment, target preceding already confirmed opposite signal ZigZag pivot, SL extreme + 0.1 ATR, RR>=1.5: A 191 (~2.81/month), B 691 (~10.16/month), C 165 (~2.43/month). For k=0.5: A 1356, B 5602, C 1480; k=3: A75, B360, C84. These are geometric setups, NOT filled/profitable trades, and NOT independent episodes.

Critical limitations: signal ATR sizes differ by timeframe; no canonical 2680/2754 wave mapping, no fair equivalent-price-distance threshold matching, no full level lifecycle or cross-detector dedup, no SL-first backtest nor fees/slippage. Comparison cannot pick a winner by opportunity count alone. Provisional H1 context/M15 signal/M5 execution hypothesis; exclude M1 from signal discovery.

Local reproducible files: lab181_run.py, lab181_context.py, LAB181_SCALE_COMPARISON.csv, LAB181_ZIGZAG_CONFIRMED_EVENTS.csv, LAB181_CONTEXT_FILTER_COMPARISON.csv, LAB181_CONTEXT_ELIGIBLE_EVENTS.csv, LAB181_MULTISCALE_ZIGZAG_REPORT.md. Research only, no production EA.
