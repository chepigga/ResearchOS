# LAB190 — Price Wave × Crowd L/S × OI × Value Area Atlas

**Forensic diagnostic; not a completed executable signal/backtest.**

Frozen 2754 LAB169 hindsight waves; frozen LAB185 detection 639/2754 (23.2%) by any eligible signal variant; 2115 missed. Price profile frozen to prior 288 M5 candles at *hindsight wave start*, with 40 histogram bins, volume uniformly spread through M5 high-low and 70% value area. Flow as-of uses *assumed* 5m delayed Binance publication, unverified.

|At wave start|N waves|LAB185 covered|Coverage|
|--|--:|--:|--:|
|Inside Value Area|1442|261|18.1%|
|Above VAH|702|190|27.1%|
|Below VAL|610|188|30.8%|

Inside Value Area: **1181 missed waves**. Causal price model requires H1 sweep, so baseline undercounts waves originating in balance with no H1 sweep. This says nothing yet about real-time detectability.

L/S trailing 6h log change multiplied by **future-wave direction** (only for retrospective wave characterization): AGAINST 554 waves / 56 covered (10.1%); MIDDLE 1700/436 (25.6%); WITH 500/147 (29.4%). AGAINST + OI BUILD 201 waves / 10 covered (5%). Those are *missed-wave populations, not predictive win rates*. Trade direction must be selected causally from price/flow independently of future-wave label.

OI alone: BUILD 834/181 (21.7%), UNWIND 734/182 (24.8%), MIDDLE 1186/276 (23.3%). At wave-start profile above VAH and accepted for >75% of first 12 M5 closes after wave starts: 477 waves, covered 109; below VAL accepted: 417 waves, covered 118. These 1h responses are POST-WAVE descriptive labels, not available at wave start. Rejection taxonomy currently too narrow; do not interpret it as true false breakout census.

**Parity issue**: newly derived earliest ENTRY inside hindsight wave = 486 unique waves, versus prior LAB186 canonical first-entry coverage 491, due to different matching definitions; preserve 491 until matched-ID audit.

Need **causal LAB191**: standalone M5 first VA breakout + stable profile before breakout, confirm 1/3/6-bar close acceptance or rejection; next-open entry with known liquidity target and SL, min 1.5R, L/S×OI snapshot available only at decision; count ALL signals and false positives, retain canonical wave atlas as outcome coverage; assess costs and publication delay. No EA or final broker-tailored strategy until broker/prop specs reconfirmed.

Local artifacts: LAB190_REPORT.md, LAB190_WAVE_ATLAS.csv, LAB190_MISSED_WAVE_SUMMARY.csv, LAB190_CROWD_OI_VA_STATES.csv, LAB190_VA_RESPONSE_SUMMARY.csv, lab190_wave_atlas.py.
