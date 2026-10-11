# LAB191 — causal Value Area breakout replay

2026-10-11. 5,087 independent breakout events, 13,354 candidate variants (1/3/6 candle), 9,157 variants with a known historical H1 liquidity level at geometrical RR>=1.5. Frozen LAB169 hindsight atlas 2754 big waves; 1003 waves direction-matched to at least one eligible candidate and 692 previously not captured by LAB185 (union 1331/2754, 48.3% candidate coverage; NOT traded performance). These use profile computed from previous 24 completed **H1** candles, unlike LAB190 M5 baseline. See accompanying report in local environment for limitations.

Gross 2R/24h diagnostic, 12 M5 structural stop, SL-first on ambiguous bars:
|Model|N|TP-first|Mean R|
|--|--:|--:|--:|
|Acceptance 1 M5|4902|30.1%|-0.009|
|Acceptance 3 M5|2660|29.0%|-0.009|
|Acceptance 6 M5|1812|28.0%|-0.017|
|Rejection 3 M5|1834|31.4%|-0.028|
|Rejection 6 M5|2146|29.6%|-0.043|

L/S 6h against trade + OI 4h building on ACCEPT events, **post-hoc** subgroup:
2021-23 n470 +0.216 gross R, 2024 n148 +0.114R, 2025–Aug26 n203 +0.116R. These are non-independent variants, zero costs and no confirmation of true publication timestamps. Not ready for EA.

**Critical:** 2R target used for simulated outcome, known H1 liquidity only checked for geometry, not actual exit target. Costs, broker, slippage, equity DD, 1-entry-per-event constraint NOT modeled. Profile approximate volume distribution; 5m assumed Binance publication lag. Next run must replay one causal entry per independent event with actual known-liquidity TP, execution costs, paired side/year comparisons, and profile parity. Do not promote rule until completed.

Local full data: `/mnt/data/LAB191_REPORT.md`, `LAB191_CAUSAL_EVENTS.csv`, `LAB191_EXECUTION_SUMMARY.csv`, `LAB191_WAVE_COVERAGE.csv`, `LAB191_FACTOR_INTERACTIONS.csv`, `lab191_run.py`.