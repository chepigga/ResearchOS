# LAB188 — First Pass L/S × OI (2026-10-11)

Frozen 5089 price H1 entries; 5084 usable OI observations, conservative unverified L/S publication assumption +5m.

|Era|LS crowd against TP-first|LS crowd with TP-first|OI build TP-first|OI unwind TP-first|
|---|---|---|---|---|
|2021–23|22.43% n535|13.83% n535|19.32% n818|17.73% n818|
|2024|22.40% n125|15.48% n155|18.53% n232|19.67% n239|
|2025–Aug26|16.57% n169|10.67% n253|12.80% n250|17.47% n332|

Exploratory interaction LS moving with trade plus OI build: 2021–23 14.14% (198), 2024 9.09% (44), 2025–26 4.88% (82). Small samples, multiple comparisons, not a proven causal filter; no profile shape results yet. Train 2021-23 directional log-LS 6h percentile 20/80, OI 4h log-return percentile 30/70 fixed forward. Need independent validation, risk/side controls, TP-before-SL and net EV, publication latency audit. This lab stage does not claim trading profitability or change EA.

Local files `LAB188_CAUSAL_FACTOR_ROWS.csv`, `LAB188_LS_OI_INTERACTIONS.csv`, `LAB188_LS_GROUPS.csv`, `LAB188_OI_GROUPS.csv`, `lab188_run.py`, `LAB188_FIRST_PASS_REPORT.md`. Next phase Profile acceptance incremental contribution to the exact same price situations.