# LAB196 — Entry Confirmation × Stop Transfer

4411 frozen LAB194 entries, BTC M5 replay, H1/H4 known pivot TP retained, R:R >=1.5 requalification, 10bps total roundtrip hypothetical costs, 24h stop-first OHLC replay.

|Immediate Stop|N|Net EV R|Matched delta R against baseline|
|---|---:|---:|---:|
|BASE|4411|-0.198|0|
|12 completed M5 extreme + 0.1ATR|4411|-0.236|-0.038|
|Min 2ATR M5|4202|-0.186|0.000|
|Min 4ATR M5|3143|-0.178|+0.015|
|Previous 24h range edge (NOT VA boundary)|261|-0.016|-0.061|

|Delay original stop|N|Net EV R|Same-event BASE EV R|Paired delta R|
|--|--:|--:|--:|--:|
|0 bars|4411|-0.198|-0.198|0|
|3 M5 closed bars|708|-0.218|-0.064|-0.154|
|6 M5 closed bars|584|-0.111|+0.068|-0.179|

Delayed confirmation is merely previous M5 candle close favorable versus original entry, not true BOS or retest. Next M5 open entry, cost model hypothetical. A 24h prior-price-range stop cannot be represented as stop beyond VAH/VAL: actual frozen value-area boundaries were NOT retained in LAB194. This alternative is a proxy only and highly selected. Rejection engine underrepresented in source population. No variant robustly profitable and no production EA change. Source data and scripts local as LAB196_REPORT.md, lab196_run.py, LAB196_VARIANT_TRADES.csv, LAB196_VARIANT_SUMMARY.csv, LAB196_PAIRED.csv. Broker specs needed for real execution. Next: actual VAH/VAL reconstruction and matched full-population trade simulation, paired per-year, BUY/SELL, Crowd/OI groups, latency and fees.
