# LAB198 Liquidity Potential × Crowd Positioning

Full reproducible replay locally in LAB198_REPORT.md, lab198_run.py, lab198_coverage.py. Frozen 4411 BTC first-entry events and original H1/H4 TP, SL and outcome; 10bps hypothetical total costs. Causal prior24h reconstructed candle volume-by-price route density, cost-aware target geometry and L/S AGAINST + OI BUILD ordinal score. No execution or EA changes.

HIGH score net EV (TRAIN 2021-23 / VALID2024 / CHECK2025-Aug26):

- geometry: -0.136R n126 / -0.462R n33 / -0.192R n22.
- geometry+LS: -0.025R n315 / -0.196R n68 / +0.011R n68.
- geometry+LS+OI: +0.021R n543 / **-0.318R n130** / +0.066R n138.
- full geometry+LS+OI+route density: -0.069R n663 / **-0.169R n182** / +0.003R n210.

Wave matching via entry timestamp inside retrospective wave plus side (not prior canonical rule): entire set 4411 trades touch 1373/2754 hindsight waves; geometry high 181 trades/75 waves; geo LS high 451/178; geo LS OI high 811/300; full high 1055/451. No robust profit across eras; density via OHLC uniform approximation is NOT true volume profile or orderbook liquidity. Other limits: no real brokerage fee model; projected pivot as liquidity proxy; assumed L/S publication +5m; old CHECK reused. Score does not infer directional outcome. No production EA.
