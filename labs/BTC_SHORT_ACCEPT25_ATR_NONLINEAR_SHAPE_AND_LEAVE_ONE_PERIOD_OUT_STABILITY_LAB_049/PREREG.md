# BTC_SHORT_ACCEPT25_ATR_NONLINEAR_SHAPE_AND_LEAVE_ONE_PERIOD_OUT_STABILITY_LAB_049 — PREREG

## Objective
Audit whether the nonlinear ATR-rank payoff shape observed in LAB048 is stable to leaving out each frozen period, without searching any new cutoff or changing execution.

## Frozen parent lineage
- Exact 327 pre-Aug `SHORT HIGH_RESPONSE -> ACCEPT -> SL 2.5 ATR -> TP 1.5R -> original max 12h` trades.
- Exact causal `atr_rank_90d` measured before entry from LAB045/048.
- Frozen periods: 2021, 2022, 2023, 2024, 2025_H1, 2025_H2, 2026_JAN_JUL.
- Costs/payoff remain the frozen 5bps `net_r_5bps` from the execution lineage.
- August remains audit-only and cannot affect selection.

## Frozen nonlinear bands from LAB048
No alternative boundaries may be searched:
- `LOW_BAND`: ATR-rank [0.0, 0.4)
- `MID_SPIKE`: [0.4, 0.6)
- `DEAD_MID`: [0.6, 0.8)
- `TOP_BAND`: [0.8, 1.0]

The LAB048 observation being tested is: LOW_BAND weak/negative, TOP_BAND strong/positive, MID_SPIKE positive but potentially unstable, DEAD_MID near flat.

## Primary tests
For the full frozen sample and each of seven leave-one-period-out (LOPO) samples:
1. Compute N, EV, PF, CumR for the four frozen bands.
2. Primary contrast: `TOP_BAND EV - LOW_BAND EV`.
3. Secondary shape contrast: `MID_SPIKE EV - LOW_BAND EV`.
4. 7-day cluster bootstrap, 5000 draws, for the primary TOP-minus-LOW contrast in the full sample and each LOPO sample.
5. No rebinning, qcut, threshold optimization, stop/TP/time-exit search, or feature search.

## Stress tests
- 2022 alone: TOP minus LOW sign.
- 2025_H1 alone: TOP minus LOW sign.
- Combined bad periods 2022 + 2025_H1: TOP minus LOW sign plus 7-day cluster bootstrap.
- `MID_SPIKE` stability is evaluated separately: positive EV in LOPO samples and concentration of its CumR contribution by period.

## Frozen interpretation gates
Primary nonlinear-shape replication is considered strong only if:
- exact 327-trade parity and >=99% ATR coverage;
- full TOP-minus-LOW gap > +0.25R and full bootstrap lower bound >0;
- TOP_BAND EV >0 in all 7 LOPO samples;
- LOW_BAND EV <=0 in at least 6/7 LOPO samples;
- TOP-minus-LOW gap >0 in all 7 LOPO samples;
- at least 5/7 LOPO primary bootstrap lower bounds >0;
- combined 2022+2025_H1 TOP-minus-LOW gap >0;
- 2025_H2 and 2026 are not uniquely responsible for the full primary gap (leaving either out keeps gap >0).

MID_SPIKE is promoted only as a stable second nonlinear state if:
- MID_SPIKE EV >0 in all 7 LOPO samples;
- MID_SPIKE-minus-LOW gap >0 in all 7 LOPO samples;
- no single period contributes >50% of MID_SPIKE total CumR magnitude.

## Verdicts
- `PASS_ATR_NONLINEAR_SHAPE_LOPO_STABLE`: primary shape gates pass; this is still context evidence, not an executable ATR router.
- `WATCH_ATR_TOP_BAND_STABLE_MID_SPIKE_UNSTABLE`: TOP-vs-LOW shape is robust but MID_SPIKE is not.
- `FAIL_ATR_NONLINEAR_SHAPE_PERIOD_DEPENDENT`: primary TOP-vs-LOW shape fails LOPO stability.

## Guardrail
This LAB is an audit only. It cannot promote a new ATR cutoff, alter execution, or allocate live risk. Reused historical lineage; not fresh OOS. Live allocation = 0.
