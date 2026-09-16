# GC_XAU_D1_E3_CORRECTED_ONEACTIVE_DEPENDENCY_LAB_014H — PREREG

## Purpose

Quantify the risk/robustness impact of the execution-semantic defect isolated by LAB013H using only the already-collected historical sequence. No market data, signal threshold, depth, stop, target, cost, or exit parameter is changed.

LAB013H found that frozen LAB009 released an **unfilled** D1.00_E3M setup at `signal_time + 3m`, although the XAU limit becomes actionable at the next M1 open. Correct operational busy expiry is therefore `order_start + 3m = signal_time + 4m` for unfilled setups. Filled setups remain busy until their actual exit.

## Frozen candidate

- GC sensor: `BUYER_BREAKOUT_LONG_001`
- XAU depth: D1.00 ATR14(M1)
- expiry: E3M
- SL: 1.5 ATR
- TP: 3R
- hard timeout: frozen operational lineage
- cost stress: +0.05R per accepted filled trade
- cohorts: `COMMON_CLOCK`, `AMP_ALL`
- source: `GC_XAU_LIMIT_ORDER_OPERATIONAL_ROBUSTNESS_LAB_009_SEQUENCES.csv`
- no parameter search

The source sequence retains raw outcome/fill/exit information even for rows rejected by the historical one-active clock, allowing the corrected causal state machine to be replayed without raw-market re-download.

## Corrected one-active state machine

Process original signals in UTC order independently per cohort.

- If `signal_time < busy_until`, reject signal as overlap and assign 0R.
- Otherwise accept it.
- If accepted and filled: `busy_until = actual exit_time_msc - 180 minutes`.
- If accepted and unfilled: `busy_until = signal_time + 1 minute (order start) + 3 minutes expiry`.
- Accepted filled R = raw `r - 0.05R`; accepted unfilled = 0R; rejected = 0R.

## Dependency / Monte Carlo audit

Repeat LAB010 methodology exactly:

- chronological observed EV, SumR, MaxDD;
- UTC day/week concentration;
- leave-one-day-out and leave-one-week-out EV;
- 10,000 day-block bootstrap samples;
- bootstrap P(EV>0), EV 95% CI;
- bootstrap DD median/p95/p99;
- modeled p95 DD at 0.25% and 0.50% risk.

Use seed `20260916`, matching LAB010.

## Gates

Historical corrected robustness support requires:

- bootstrap P(EV>0) >=80% in both cohorts;
- leave-one-week-out minimum EV >0 in both cohorts;
- COMMON max positive-day contribution <50%;
- p95 DD at 0.25% risk <5% in both cohorts.

The old LAB010 0.50%-risk gate is reported for direct comparison but is not a promotion gate because LAB010 already showed 0.50% is too aggressive for prop use.

A PASS remains historical/internal evidence, not independent OOS certification.
