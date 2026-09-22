# LAB046 — V191_PREREGISTERED_TOXIC_STATE_GATES

Status: PRE-REGISTERED BEFORE EXECUTION

## Frozen base
Exact LAB045 base:
- v191d signal/confirm/management shell
- |Z| >= 1.00
- confirmation +0.30 ATR against crowd
- confirmation freshness <=45m
- cancel if max pre-confirm adverse excursion >0.75 ATR
- ExitZ retained at 0.75
- SL 1.5 ATR
- BE arm 0.5 ATR / lock 0.15 ATR
- trail arm 2.5 ATR / gap 0.5 ATR
- max hold 6h
- pause 1.0 ATR
- max 3 trades/day
- flat 0.5 bps cost proxy

No exit, stop, BE, trail, hold, confirmation, pause, day-cap, or cost changes are allowed in LAB046.

## Causal state definitions
All gates are evaluated at the completed M5 signal decision timestamp, before confirm/entry.

### RAPID_REPEAT_30
Current crowd extreme is vetoed when the previous completed M5 crowd extreme of the same sign (same crowd side) with |Z|>=1.00 occurred <=30 minutes earlier.

The prior-extreme clock is built from the full completed M5 crowd-state stream, independent of whether earlier trades were taken or skipped.

### HIGH_VOL
ATR% = completed M15 ATR14 / completed M5 close at the signal clock.

HIGH_VOL is defined exactly as in LAB045:
- rolling 30-day M5 ATR% distribution = 8640 M5 observations
- threshold = lagged q67
- current observation is excluded by shift(1)
- minimum history = 2880 observations
- HIGH_VOL when current ATR% >= lagged q67
- UNKNOWN is not treated as HIGH_VOL

No volatility threshold search is allowed.

### Z100_125
Signal is eligible only when 1.00 <= |Z| < 1.25.

No Z threshold search is allowed.

## Pre-registered variants
1. BASE_LAB045
2. SKIP_RAPID_REPEAT_30
3. SKIP_HIGH_VOL
4. SKIP_RAPID_REPEAT_30_AND_HIGH_VOL
5. Z100_125_ONLY
6. Z100_125_SKIP_RAPID_REPEAT_30_AND_HIGH_VOL

Reference controls:
- FULL_V191F_CONTROL from LAB044
- immutable V192_CANONICAL_CONTROL

## Stateful replay requirement
Variants MUST be replayed from raw chronological data. Post-hoc filtering of LAB045 trade rows is prohibited.

A skipped signal must remain skipped before confirm/entry so that subsequent:
- position occupancy,
- next reachable signal,
- ATR pause,
- max-trades/day state,
- trade sequence,
- equity curve,
- drawdown
are recomputed causally.

## Samples
- Historical: BTCUSDT, 2021-01-01 through 2025-12-31, 1m OHLC execution frame.
- 2026 shadow/stress: BTCUSDT, 2026-03-01 through 2026-08-31, second OHLC execution frame.

2026 is reused shadow/stress and is not pristine OOS.

## Required outputs
For every variant and control:
- N, WR, EV, PF, SumR, MaxDD_R, R/DD, max consecutive losses
- full chronological trade ledger
- historical yearly metrics
- 2026 monthly metrics
- side split
- exit-reason counts
- matched/reachability delta vs BASE_LAB045

## Decision rule
No threshold tuning is permitted after seeing results.

A v191 gate population is:
- SUPPORTED only if aggregate EV > 0 and PF > 1.0 in BOTH historical and 2026 shadow, with >=4/5 positive historical years and >=4/6 positive 2026 months.
- MIXED if aggregate EV/PF are positive in both samples but the period-consistency rule is not met.
- FAILED if EV <= 0 or PF <= 1.0 in either aggregate sample.

MaxDD/R-DD and frequency are reported as secondary consequences, not used to change thresholds inside LAB046.

Only a SUPPORTED or clearly MIXED-but-robust population may justify a separate LAB047 scalp-geometry test. No production promotion occurs directly from LAB046.
