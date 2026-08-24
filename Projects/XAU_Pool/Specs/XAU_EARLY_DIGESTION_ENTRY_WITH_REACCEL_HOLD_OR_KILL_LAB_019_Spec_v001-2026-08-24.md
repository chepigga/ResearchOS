# XAU_EARLY_DIGESTION_ENTRY_WITH_REACCEL_HOLD_OR_KILL_LAB_019 — Spec v001

Date: 2026-08-24
Status: PREREGISTERED / PRE-OUTCOME

## Hypothesis
LAB012 showed that future MICRO_REACCEL strongly separates healthy from toxic digestion entries, but waiting to enter after confirmation destroys entry quality. LAB019 tests whether the same information is useful **after an early causal entry** as a position-management state: HOLD when reacceleration appears, KILL when it fails to appear soon or acceptance degrades.

## Frozen lineage
- Canonical M1: `XAUUSD_M1_20220601_20260723_TICK_NATIVE.csv`
- SHA-256: `db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b`
- Break census: LAB008 `break_census.csv`
- Bias Engine: LAB009 frozen ordered 3×5m state map, `p_accept >= 0.75`
- Digestion universe / entry / MICRO_REACCEL definition: exact LAB012 runner lineage.
- Discovery: break_time < 2024-01-01
- Confirmation: 2024-01-01 <= break_time < 2025-07-01
- Holdout >= 2025-07-01 remains sealed.

## Entry and risk geometry
- Universe: strong-bias events where LAB012 finds a frozen digestion block.
- Entry: exact LAB012 `BASELINE` next contiguous M1 open after digestion close.
- Risk: 0.50 × ATR_touch = 1R.
- Primary TP: 1.5R.
- Secondary TP: 2.0R.
- Commission proxy: identical to LAB012 (`0.05 price units` round-turn proxy).
- Max holding horizon: 60 minutes from early entry.
- No new entry filters.

## Frozen MICRO_REACCEL state
Use exact LAB012 trigger, observable only at completed M1 close:
1. accepted-side distance remains > +0.05 ATR;
2. close breaks the directional close-extreme of the digestion block by >= +0.05 ATR;
3. directional candle body >= +0.03 ATR;
4. close distance from old level >= +0.10 ATR.

## Primary management: HOLD_OR_KILL_5M
From the early entry:
- Original SL/TP are live immediately and always have intrabar priority.
- At each completed M1 close after entry, evaluate:
  - **HOLD**: if frozen MICRO_REACCEL has become true, permanently stop the kill timer and keep the original TP/SL/time-stop.
  - **DEGRADE_KILL**: if accepted-side close distance to the broken level is <= +0.05 ATR before HOLD, exit at the next contiguous M1 open.
  - **TIME_KILL**: if no HOLD has occurred by the close of the 5th completed M1 bar beginning with the entry bar, exit at the next contiguous M1 open.
- If TP or SL hits within the bar that later produces HOLD/KILL information, the barrier outcome wins; no close-based decision may override an earlier intrabar fill.
- If next-open kill execution is unavailable/non-contiguous, continue original trade rather than invent a fill.

## Secondary sensitivity (not eligible to rescue primary verdict)
- HOLD_OR_KILL_3M: same rules, 3 completed bars.
- HOLD_OR_KILL_10M: same rules, 10 completed bars.
- DEGRADE_ONLY: no timer; only early degradation kills, MICRO_REACCEL otherwise informational.

## Comparators
On the identical early-entry universe:
1. BASELINE: original LAB012 early digestion entry, no management.
2. HOLD_OR_KILL_5M primary.
3. Secondary 3M / 10M / DEGRADE_ONLY.

## Metrics
- independent and serial portfolio N / trades per week;
- net EV, gross EV, PF, TP rate;
- max DD, worst day, max consecutive losses;
- BUY/SELL EV;
- +0.10 price stress EV;
- weekly cluster bootstrap CI of strategy EV;
- paired same-trade management-minus-baseline R, weekly bootstrap CI;
- kill rate, hold rate, kill reason, median exit time, R saved/lost versus baseline;
- conditional diagnostics by future MICRO_REACCEL (diagnostic only; never usable at entry).

## Primary gates
G0 DATA_CAUSALITY: zero causality violations, holdout sealed.
G1 POWER: primary serial N >= 500 and >= 5 trades/week.
G2 CONFIRMATION_EV: primary EV > 0 and PF > 1.
G3 WEEK_CLUSTER_CI: weekly mean-R 95% CI lower bound > 0.
G4 MANAGEMENT_LIFT: paired primary-minus-baseline mean > 0 and weekly CI lower bound > 0.
G5 SPLIT_TRANSFER: Discovery and Confirmation primary independent EV both > 0.
G6 2R_SURVIVAL: Confirmation primary 2R EV >= 0.
G7 DIRECTION_BREADTH: BUY and SELL primary EV both > 0.
G8 PROP_DD_PROXY: max DD <= 20R and worst day > -16R.
G9 COST_STRESS: +0.10 price stress EV > 0.
G10 TOXIC_KILL_VALUE: among non-MICRO events, management-minus-baseline mean > +0.20R.
G11 HEALTHY_RETENTION: among future-MICRO events, management EV > 0 and management-minus-baseline mean > -0.15R.

## Verdict labels
- `EARLY_ENTRY_HOLD_KILL_EXECUTABLE_EDGE`
- `HOLD_KILL_POSITIVE_BUT_NOT_PROP_READY`
- `KILL_SAVES_TOXIC_TRADES_BUT_DAMAGES_HEALTHY_EDGE`
- `HOLD_KILL_IMPROVES_BUT_REMAINS_NEGATIVE`
- `NO_HOLD_KILL_MANAGEMENT_EDGE`
- `INVALID_DATA_CAUSALITY`

No threshold/time-window tuning after outcome. No holdout opening or live/EA authorization from this LAB alone.
