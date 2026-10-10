# LAB175 — First price-only sequential replay
BTCUSDT 589793 M5 bars 2021-01 to 2026-08-10. Event sequence uses only known price history.

Continuation: aligned completed H1/H4 trend; 0.5 ATR pullback followed by 0.25 ATR recovery in <=48 M5 bars. Reversal: wick sweeps prior 48 M5 extrema and reclaims, then a later M5 close breaks pre-sweep 12-bar structure in <=36 bars. Enter hypothetical next M5 open, structural SL beyond pullback/sweep extremum +/-0.1 H1 ATR, nearest known 6h/12h/48h/prior-day extreme as TP, RR>=1.5, 12-bar same-engine-side cooldown.

|Mode|Routes|BUY|SELL|RR>=2|RR>=3|Median RR|matched routes|distinct LAB169 waves|monthly|
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|Continuation|7199|3621|3578|4446|1527|2.210|842|620|105.87|
|Reversal|112|50|62|46|14|1.904|24|24|1.65|

Union distinct LAB169 waves with same-side timestamp-inside-wave matched signal 641/2754 = 23.3%; NOT canonical LAB161 2680 ID parity. Only geometric opportunity census, NOT 7311 independent executed trades. Cooldown is not global route dedup. No tick fills, TP-before-SL or profitability evaluation; no Crowd/OI/Profile; historical liquidity level proxies, not order-book liquidity. Range deliberately outside LAB175 scope. Production unchanged.

Raw CSVs and executable research script were created as conversation files. Pending stricter route episode dedup, remaining-to-wave-end test, and canonical segmentation check before claims about ~40 large waves/month.