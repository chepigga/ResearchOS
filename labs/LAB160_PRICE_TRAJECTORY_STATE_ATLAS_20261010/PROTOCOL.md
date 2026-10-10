# LAB160 — preregistered before conditional outcome calculation
2026-10-10. Exploratory historical atlas, no strategy or live change.
Sources: GitHub btc release btc_5m.zip and BTCUSDT_flow_2021-01-2026-08.csv.zip; LAB159 branch source.
All closed M5 observations from 2021 onward, no engine selection. Timestamp = bar open + 5 minutes; reference = just-closed close. Future excludes reference bar.
H1 ATR14 simple moving mean of true range, on complete closed hours only, matching LAB158 lineage. This explicitly supersedes the initial audit's proposed Wilder ATR.
Profile exactly LAB158 24h/40 bins/70% contiguous value area, uniformly allocated M5 candle volume. Shapes D/P/b/DOUBLE. Gapped windows invalid.
Flow timestamp availability undocumented: primary assumes 5m publication delay; no forward interpolation; maximum matched age 5m after assumed availability. Compute Z on 72 consecutive original M5 ratios; OI4h on 48 intervals. OI value matches LAB158; OI quantity retained separately to expose price contamination.
Features: trailing6h price displacement and direction (>0.5 ATR, <-0.5 ATR, neutral); signed Z buckets abs <0.6, 0.6–1, 1–1.5, >=1.5; OI value change buckets negative, 0–0.35%, 0.35–0.867%, >=0.867%; location below/inside/above value, shape and POC migration6h.
Labels: 1/3/6/12/24/48h terminal return, up/down excursion, first touch of +/-0.5/1/2/3 ATR and timing; both-hit same-bar remains ambiguous. Incomplete/gapped future windows missing, not losses. All values in reference ATR, not trade R.
Primary descriptive diagnostic: 6h +2 ATR before -1 ATR, mirror for down. Not execution performance.
Historical split: discovery 2021–2023, validation2024, retrospective check2025–2026. Purge final48h before boundaries. All periods may have been used in earlier labs; none claimed pristine OOS.
Ablation on identical valid rows: price state; price+crowd+OI; +profile location+shape. Smoothed frequency estimators fit only on discovery (100 pseudo-observations at discovery unconditional frequency). Unknown groups use unconditional frequency. Brier score; paired calendar-week block bootstrap 1000 iterations seed160, descriptive 95% intervals.
Candidate screen: discovery N>=500, validation N>=100 and >=10 calendar weeks, discovery and validation uplift >=3 percentage points relative to unconditional same-direction frequency. Rank by smaller of the two uplifts. Freeze top10 before retrospective check; no deployment recommendation. No inferential significance claim for mined cells.
Report raw N, episode starts (contiguous state runs), conservative >=48h-separated observations. These are not trades/month.
