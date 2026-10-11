# LAB183 — Percentage ZigZag vs shared ATR(H1): causal timeframe replay
BTCUSDT M5 2021-01 to 2026-08-10. First-pass price-only replay; no PnL or EA deployment.

Closed 15m/H1/H4 OHLC, prior closed H1 14TR ATR, separate historical pivot_time and causal confirm_time. Confirm only once price closes beyond k% of candidate extreme or k×H1 ATR. Geometry at confirmation close, stop beyond pivot +0.1 H1ATR, target previous confirmed opposite pivot, RR>=1.5. These are **not executed fills**.

| TF/pct | Confirmations/mo | median lag hours | Geometric RR>=1.5 candidates | Distinct aligned LAB169 waves |
|---|---:|---:|---:|---:|
|M15 0.5%|412.8|0.25|6169|648|
|H1 1%|105.4|1|1827|300|
|H1 2%|40.7|3|663|170|
|H4 3%|16.4|8|270|69|
|H4 5%|7.5|16|113|39|
|H4 7%|4.25|32|67|26|

Equal **1 × prior H1 ATR threshold**: M15 3378 RR>=1.5 candidates, 539 aligned LAB169 waves, median first matched signal elapsed 14.9% wave duration; H1 2460, 368, 27.2%; H4 1499, 160, 45.2%.

Important: all wave matching hindsight audit, not selection; denominator 2754 LAB169 NOT canonical LAB161 2680. No unique episode dedup, no structural liquidity freshness, no intra-bar path fidelity, no next-open execution, no costs. Median elapsed time is NOT remaining amplitude. H4 5–7% poor as sole high-frequency trigger; potentially useful broad macro context. M15 early discovery + H1 trading structure remains research hypothesis, not proven edge.

Local reproducibility source lab183_run.py and outputs LAB183_SCALE_AND_THRESHOLD.csv (all thresholds including shared 0.5/1/2/3 H1 ATR), LAB183_CONFIRMED_EVENTS.csv, LAB183_REPORT.md. Next LAB184 combine *only causally confirmed* H4 regime, H1 structure, M15 early candidates, analyze added wave coverage and zone-level overlapping episodes.