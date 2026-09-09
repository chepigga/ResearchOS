# BTC_SHORT_HIGH_RESPONSE_ACCEPT25_CAUSAL_ATR90_REGIME_REPLICATION_LAB_046

## Purpose
Replicate the single strongest trade-level regime clue from LAB045 without searching any new feature, threshold, entry, stop, target, or weighting rule.

## Frozen lineage
- Base execution: exact LAB044 `SHORT HIGH_RESPONSE -> ACCEPT -> SL 2.5 ATR -> TP 1.5R -> original +12h horizon`, 5 bps research friction.
- Formal sample: exact 327 pre-August 2026 ACCEPT2.5 trades from LAB045 `failure_state_stream.csv`.
- Regime clock remains `entry_time - 15m` from LAB045; no entry-bar information is added.
- `atr_rank_90d` is reused exactly as persisted by LAB045; it is not recomputed or redefined.
- August 2026 remains audit-only and is not used for selection.

## Single fixed causal router
- `HIGH_ATR90`: `atr_rank_90d >= 0.50`
- `LOW_ATR90`: `atr_rank_90d < 0.50`

The threshold 0.50 is fixed before results as the natural median-rank boundary. No alternate percentile is tested.

## Primary hypothesis
If ATR90 is a real missing execution-state, HIGH_ATR90 should preserve the SHORT ACCEPT2.5 edge while LOW_ATR90 should be materially weaker. The HIGH-vs-LOW net-R gap must survive 7-day cluster bootstrap.

## Metrics
For HIGH_ATR90, LOW_ATR90, and ALL:
- N, share of 327 trades;
- mean net R at 0/5/10 bps (10 bps joined from frozen LAB044 execution output);
- PF, win rate, cumulative R;
- max realized DD in R and equivalent DD at 0.25% risk/trade;
- contribution to the full 327-trade cumulative R;
- selected EV per original 475 HIGH_RESPONSE signals, with abstained/non-ACCEPT events contributing zero.

Transfer is fixed for 2021, 2022, 2023, 2024, 2025H1, 2025H2, 2026 Jan-Jul, pooled recent 2025H2+2026, plus BAD composite (2022+2023+2025H1). Report HIGH and LOW separately.

## Bootstrap
7-day clusters by frozen signal_time. 5,000 draws with fixed seed 20260909. Primary statistic = HIGH_ATR90 mean netR5 - LOW_ATR90 mean netR5.

## Gates
1. exact formal ACCEPT2.5 N = 327;
2. `atr_rank_90d` coverage = 100%;
3. frozen LAB044 0/5/10 bps payoff parity for joined rows = 100%;
4. HIGH_ATR90 N >= 130;
5. LOW_ATR90 N >= 130;
6. HIGH_ATR90 trade EV5 > 0;
7. HIGH_ATR90 PF5 >= 1.20;
8. LOW_ATR90 trade EV5 <= 0;
9. HIGH-minus-LOW EV5 gap >= +0.20R;
10. 7d bootstrap CI lower bound > 0;
11. HIGH_ATR90 EV10 > 0;
12. HIGH_ATR90 max DD @0.25% <= 4.0%;
13. HIGH_ATR90 selected EV per original 475 >= +0.05R;
14. HIGH_ATR90 captures >=75% of full ACCEPT2.5 cumulative R;
15. 2021 HIGH EV > 0;
16. 2022 HIGH EV > 0;
17. 2023 HIGH EV > 0;
18. 2024 HIGH EV > 0;
19. 2025H1 HIGH EV > 0;
20. 2025H2 HIGH EV > 0;
21. 2026 HIGH EV > 0;
22. pooled recent HIGH EV > 0 with N >=30;
23. BAD composite HIGH EV > LOW EV;
24. August not used for selection.

## Verdict
- PASS: >=20/24 gates and critical gates 1,2,3,6,7,9,10,11,12,13,20,21,22 pass.
- WATCH: >=14/24 or HIGH_ATR90 remains positive/robust but bootstrap or historical transfer is incomplete.
- FAIL otherwise.

## Guardrail
This is reused historical replication, not fresh OOS. A PASS would justify treating ATR90 as a candidate causal regime router for a subsequent fresh/forward validation, not live allocation. Live allocation = 0.
