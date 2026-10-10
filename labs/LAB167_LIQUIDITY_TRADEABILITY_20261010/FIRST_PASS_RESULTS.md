# LAB167 FIRST PASS — PRICE ONLY / PROXY ROUTES
2026-10-10. Exploratory replay (NOT complete canonical 2680-wave matching).
Source: user-supplied btc_5m.zip, 589,793 M5 bars 2021-01-01 to 2026-08-10 21:20 UTC.
Causal rolling levels: prior closed 6h/12h/48h highs/lows and previous completed day highs/lows; range proxy uses prior 6h path efficiency <=0.35 and width 1-4 closed H1 ATR; sweep-reclaim or breakout triggers. Reversal targets midpoint; range targets opposing 6h edge; continuation targets nearest known 12h/48h/PDH/PDL obstacle. Structural stop +0.1 H1 ATR, next M5 open; only proposed RR>=1.5. Hold 24h; M5 high/low, SL wins ambiguous bar. Cost sensitivity here only 7.5bps proxy, not broker-native. Simplified portfolio max2, <=1 per mode+side+day. No crowd/OI or profile gating.

|Sample|Mode|N|Median RR|TP-first%|Gross EV R|Net EV 7.5bps R|
|---|---|---:|---:|---:|---:|---:|
|All candidates|CONTINUATION|5093|3.494|20.56|-0.057|-0.317|
|All candidates|RANGE|11708|5.176|16.48|+0.012|-0.310|
|All candidates|REVERSAL|2204|4.010|16.24|-0.205|-0.453|
|Portfolio|CONTINUATION|2326|3.310|20.85|-0.085|-0.350|
|Portfolio|RANGE|3451|4.704|17.85|+0.012|-0.332|
|Portfolio|REVERSAL|954|3.535|18.34|-0.218|-0.479|

Portfolio total 6731 trades / 68 calendar months ≈ 99/mo, TP first 18.96%, SL first 79.99%, timeout 1.05%, net EV -0.359R (7.5bps).
Year net EV R: 2021 -0.212 (n1186); 2022 -0.353 (n1157); 2023 -0.508 (n1160); 2024 -0.233 (n1254); 2025 -0.443 (n1254); 2026 -0.442 (n720).
Method caveats: this detector generates candidates independent of retrospective waves and therefore 99/mo cannot be interpreted as tradable fraction of 40 large waves. No wave-ID match yet, no unique wave opportunity coverage. The potential breakout stop is tight and vulnerable to microstructure costs; not an optimized executable strategy. Historical profile nodes/H1 swings not fully integrated; this is price-extrema proxy only. 24h timeout marked non-TP; P/L to time exit in EV. Intrabar SL-first but not tick exact. No true pristine OOS. No execution-cost or broker specs parity. Production unchanged.
Next: match each candidate to canonical 2680 wave IDs, deduplicate routes and compute eligible wave fraction; add closed-bar confirmed swings, target/sweep location, and price-only entry comparisons with no fitting on CHECK. User broker specs required prior to production adaptation.
