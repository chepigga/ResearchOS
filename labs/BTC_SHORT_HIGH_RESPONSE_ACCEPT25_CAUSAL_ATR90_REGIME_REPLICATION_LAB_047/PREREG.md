# BTC_SHORT_HIGH_RESPONSE_ACCEPT25_CAUSAL_ATR90_REGIME_REPLICATION_LAB_047

## Purpose
Replicate the LAB045 volatility-regime finding on the exact frozen LAB044 ACCEPT2.5 execution lineage without searching any new threshold, feature, stop, target, or time-exit.

## Frozen parent
- Signal lineage: exact LAB043 `SHORT HIGH_RESPONSE` universe.
- Execution: exact LAB044 `ACCEPT`, SL = 2.5 ATR14, TP = 1.5R, original horizon = `signal_time + 12h`, 5 bps round-turn friction.
- Formal pre-Aug ACCEPT trades expected N = 327.
- Regime feature is the already-causal LAB045 `atr_rank_90d`, evaluated at `entry_time - 15m` from strictly prior 90-day ATR history.
- August 2026 remains audit-only.

## Only tested regime split
No threshold search is allowed.
- `HIGH_ATR`: `atr_rank_90d >= 0.50`
- `LOW_ATR`: `atr_rank_90d < 0.50`

The 0.50 threshold is the preregistered natural median-rank split proposed before LAB047. No alternative percentile may be promoted from this LAB.

## Primary hypothesis
`HIGH_ATR` has higher frozen execution payoff than `LOW_ATR`.

Primary statistic:
- mean `net_r_5bps(HIGH_ATR) - net_r_5bps(LOW_ATR)`;
- 5000-draw 7-day cluster bootstrap, clustered by frozen signal time;
- PASS proof requires the 95% CI lower bound > 0.

## Economics
For HIGH_ATR, LOW_ATR, and parent ALL report:
- N, trade EV, PF, cumulative R, max DD R, DD at 0.25% risk/trade;
- win/TP/SL/time-exit shares;
- frequency per month;
- EV per original HIGH_RESPONSE signal, where vetoed/non-ACCEPT events count as zero.

Original-signal denominators are taken from the exact LAB043 HIGH_RESPONSE SHORT stream, not from the filtered accepted-trade subset.

## Fixed transfer windows
Report the exact split for:
- 2021
- 2022
- 2023
- 2024
- 2025H1
- 2025H2
- 2026 Jan-Jul
- pooled recent 2025H2 + 2026
- August 2026 audit only.

Bad-period repair is not required to be perfect, but is explicitly tested: 2022, 2023 and 2025H1 HIGH_ATR EV/original should each be >= the corresponding unfiltered parent EV/original from LAB044, while 2025H2 and 2026 must remain positive.

## Fixed gates
1. exact frozen ACCEPT2.5 pre-Aug N = 327;
2. ATR-rank coverage >=99%;
3. exact HIGH_RESPONSE original pre-Aug N = 475;
4. HIGH_ATR N >=120;
5. LOW_ATR N >=100;
6. HIGH_ATR trade EV > 0;
7. HIGH_ATR PF >=1.15;
8. HIGH_ATR trade EV > LOW_ATR trade EV;
9. HIGH-LOW gap >= +0.15R;
10. primary 7d bootstrap lower bound >0;
11. HIGH_ATR EV/original >= parent ACCEPT2.5 EV/original (+0.059R tolerance: >=0.055R);
12. HIGH_ATR DD at 0.25% <=4.0%;
13. HIGH_ATR 2022 EV/original >= parent 2022 (-0.025R);
14. HIGH_ATR 2023 EV/original >= parent 2023 (-0.004R);
15. HIGH_ATR 2025H1 EV/original >= parent 2025H1 (-0.080R);
16. HIGH_ATR 2025H2 EV/original >0;
17. HIGH_ATR 2026 EV/original >0;
18. HIGH_ATR pooled recent EV/original >0 with >=30 HIGH_ATR ACCEPT trades;
19. LOW_ATR trade EV <= HIGH_ATR trade EV;
20. August not used for selection.

## Verdict
- `PASS_CAUSAL_ATR90_REGIME_REPLICATION` only if >=16/20 and critical gates 1,2,3,6,7,8,10,16,17 pass.
- `WATCH_ATR90_REGIME_POSITIVE_PROOF_INCOMPLETE` if >=11/20 or the split is economically positive but bootstrap/transfer is incomplete.
- otherwise `FAIL_ATR90_REGIME_NO_REPLICATION`.

## Guardrail
This is reused historical regime replication, not fresh OOS. No live allocation and no EA promotion from this LAB alone.