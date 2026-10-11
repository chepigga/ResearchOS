# LAB187A — FIRST BINANCE FLOW REPLAY, 2026-10-11

User provided BTCUSDT_flow_2021-01-2026-08.csv(1).zip, inner BTCUSDT_flow.csv. 635420 raw records / 595268 unique timestamps / 40152 exact timestamp duplicates / no conflicting duplicates. UTC 2021-01-01–2026-08-31; 5m sampling. 5797 raw missing Global account L/S. Fields count_long_short_ratio, sum_open_interest, sum_open_interest_value, count_toptrader_long_short_ratio, sum_toptrader_long_short_ratio, sum_taker_long_short_vol_ratio.

Price baseline 5089 LAB186 first-available H1 entry variants, 942 TP-first, 3800 SL-first, 347 timeout, 24h OHLC. Joined 5041/5089 entry checkpoints to past flow samples. **Critical:** available_time=create_time+5m is a CONSERVATIVE ASSUMPTION, NOT VERIFIED TRUE PUBLICATION TIMESTAMP. No data from future timestamps joined. Need verify release latency with exchange or feeder logs. No live execution claims.

Directional 6h L/S change = side × (log(global account L/S now) - log(global account L/S 6h ago)). TRAIN 2021-2023 20/80 percentiles frozen at -0.0211088 and +0.0913730. LOW means crowd shifted opposite to trade, HIGH means shifted with trade.

|Period|LOW crowd against TP-first|HIGH crowd with TP-first|
|---|---|---|
|TRAIN 2021–23|22.43% n535|13.83% n535|
|VALID 2024|22.40% n125|15.48% n155|
|CHECK 2025–Aug26 previously seen|16.57% n169|10.67% n253|

Observed association repeated directionally, but **not validated independent alpha** due to side, year, time, risk geometry, regime confounding, potential sample selection, historical data release assumptions, multiple prior research iterations. z-score magnitude alone did NOT validate persistently across periods. L/S-only feed replay not done; OI/Profile held back. No EA promotion and no claim of profitability.

Local reproducible artifacts: LAB187A_CAUSAL_LS_JOIN.csv, LAB187A_Z6_GROUPS.csv, LAB187A_DIRECTION_TRAJECTORY_GROUPS.csv, LAB187A_LS_FIRST_PASS_REPORT.md, lab187a_flow_analysis.py. Next: check 5/10/15min publication delays; stratify direction/era/regime; time-block bootstrap; match same price structure/RR bins; hold full multi-factor work until incremental evidence.
