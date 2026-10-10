# LAB180 — PERSISTENT LIQUIDITY LEVELS × DETECTOR ABLATION (preliminary)
BTCUSDT M5 2021-01-01 to 2026-08-10, frozen LAB179 20,260 candidate events. No profit or broker claims.

Proxy causal level state: reject event if target extreme was exceeded by completed M5 close by more than 1bp in prior up-to-576 M5 bars (48h) or since origin if shorter; count wick touches too. Retain earliest eligible event for `(side, level_id)` over full dataset. THIS IS NOT TRUE PERSISTENT FULL-LIFE LEVEL TRACKING: breaches more than 48h ago may escape detection; level IDs may fragment a shared zone, and sweep/breakout-retest can require an already-broken level. Level IDs already present from LAB179. No wave future used in detector or filtering.

Raw 20,260; levels not broken in bounded lookback 16,481; first candidate per level 10,841 (~159.4/month). Posthoc waves matched 1,131/2,754 (41.1%), vs LAB179 1,298/2,754 before this filter. Detectors in selected set:

|Detector|Episodes|BUY|SELL|Distinct waves covered|Unique-to-detector waves|
|---|---:|---:|---:|---:|---:|
|LAB171 pullback|5925|2886|3039|576|444|
|LAB175 continuation|4132|2079|2053|413|339|
|LAB175 reversal|65|34|31|12|8|
|LAB179 impulse|719|357|362|274|197|

Unique means removing detector from selected union loses that many hindsight-aligned LAB169 waves, NOT that the detector is causally predictive. Still not canonical LAB161 2,680 waves; not truly unified raw event scanner. Candidate counts are not independent executable trades, and R:R geometric does not imply target-first. Reproduction local lab180_audit.py with LAB180_ACTIVE_LEVEL_EPISODES.csv LAB180_LEVEL_LIFECYCLE_EVENTS.csv LAB180_DETECTOR_ABLATION.csv LAB180_MONTHLY.csv LAB180_REPORT.md.
