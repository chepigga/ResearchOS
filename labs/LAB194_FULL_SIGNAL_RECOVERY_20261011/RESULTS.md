# LAB194 FULL SIGNAL RECOVERY × SOFT CROWD SCORE

2026-10-11. Finished independent episode re-evaluation from LAB191 candidate table, removes inherited 48h price gate. Among 5001 episodes with >=1 row, 4411 first-entry events have a prior confirmed H1/H4 pivot target at RR>=1.5, vs 3009 old-gate events. 590 without that target; this is not proof no viable route exists.

Hypothetical net EV at **10 bps round trip**, first M5 open, original stop, known pivot TP, 24h timeout:

|Group|N|per month (68mo)|EV net|TP-first|Hindsight waves touched*|
|--|--:|--:|--:|--:|--:|
|Price only|4411|64.9|-0.198R|30.7%|1409|
|L/S AGAINST only|1091|16.0|-0.088R|33.7%|325|
|OI BUILD only|1022|15.0|-0.097R|33.5%|353|
|Soft >=1 point (OR)|1763|25.9|-0.115R|32.7%|556|
|Hard AND|350|5.1|+0.020R|38.0%|114|

10bps net EV TRAIN / VALID2024 / CHECK2025-26:
- Price only: -0.191 / -0.186 / -0.219R.
- LS only: -0.120 / -0.028 / -0.053R.
- OI only: -0.073 / -0.300 / -0.016R.
- Soft OR: -0.127 / -0.169 / -0.048R.
- Hard AND: +0.051 / -0.115 / +0.031R.

*Wave count: signal occurs in hindsight wave and direction matches, **not earned R or precise canonical route coverage**; use only for within-LAB194 comparison. Filtering from 1409 to 114 misses 1295 matched waves. Wave atlas future labels not used for trades.

**Do not deploy:** Inherited LAB191 events, price-volume profile proxy, unverified Binance flow +5m release lag, unvalidated execution/slippage assumptions; repeated research periods are not pristine OOS. No stable profit across eras. Score 1 cannot be promoted as a profitable execution filter. Production broker/prop specification required before EA. Confirm 5087 source breakout vs 5001 with candidates in event table.

Local full report and code /mnt/data/LAB194_REPORT.md; lab194_full_replay.py; lab194_score.py; LAB194_H1_H4_ALL_FIRST_TRADES.csv; LAB194_SOFT_SCORE_SUMMARY.csv; LAB194_WAVE_ATTRITION.csv.
