# LAB197 — breakout quality × profile × H4/D1 regime

Frozen 4411 LAB194 events; prior 24h candle-volume profile (40 bins, uniform high/low spreading), 6h/24h compression, breakout relative volume; completed H4/D1 EMA20 slope. Quartiles frozen on 2021–2023. 10 bps all-in assumed round trip, not actual broker.

|Group|TRAIN 2021–23|VALID 2024|CHECK 2025–Aug26|
|--|--:|--:|--:|
|Most compressed Q1|-0.270R|-0.407R|-0.317R|
|Compression Q3|-0.123R|-0.031R|-0.193R|
|Highest breakout volume Q4|-0.120R|-0.095R|-0.137R|
|H4/D1 aligned with trade|-0.188R|-0.230R|-0.318R|
|H4/D1 mixed|-0.190R|-0.165R|-0.123R|
|Exploratory comp Q3/Q4 + volume Q4|-0.052R (n291)|-0.023R (n114)|-0.001R (n171)|

Overall base -0.198R (4411 trades), exploratory combined group -0.031R (576 trades). No tested grouping proven profitable; mixed H4/D1 better than rigid alignment in later eras. This combined group is post hoc, not OOS. Cannot promote to EA. The source LAB194 detector strongly favors Acceptance; 24h approximate candle histogram is NOT actual trade-at-price value area. Publication delay, broker costs and real stop limitations not verified. Additional wave coverage and time-block confidence checks pending.

Local artifacts: LAB197_REPORT.md, LAB197_FACTOR_ROWS.csv, LAB197_SEGMENTS.csv, lab197_run.py.
