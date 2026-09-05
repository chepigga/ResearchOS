# BTC_REVERSAL_P975_T25_CONFIRMATION_AND_SECOND_PARENT_FAMILY_DISCOVERY_LAB_015

## Role
Two strictly separated tests:

A) formalize/reconfirm the post-LAB014 candidate `P975_T25 + VF1_MATURE` without any retuning;
B) discovery-only screen for a second causal parent-event family that can add independent frequency without weakening the canonical extreme-return parent threshold.

Discovery results cannot rescue Part A and cannot be promoted directly to live trading.

## Data / execution frozen
- Binance Spot BTCUSDT M15 lineage from prior LABs through 2026-08 monthly/daily right-edge support already consumed in prior work.
- Canonical CORE router models are fit exactly as in LAB014 on P97.5 DEV 2021-2024 events.
- Router candidate for Part A and all discovery families: **T25**, the 75th percentile cutoff of canonical DEV max(CONT,REV) router confidence.
- Direction must be routed `REV`.
- Episode definition: global 7-day signal-gap episode, assigned before evaluation-window slicing.
- Maturity: **VF1_MATURE** only. A real trade is allowed only when at least one earlier virtual frozen limit in the same family episode has actually filled strictly before the current event time. Prior virtual outcome is not required.
- Entry: `LIMIT_R0.50_T60`; no market fallback.
- SL: 1.00 x current parent event M15 high-low range from filled limit.
- TP: 1.5R.
- Same-bar SL/TP ambiguity: SL-first.
- Cost: 5 bps round trip notional converted to R using stop fraction.
- No changes to entry, SL, TP, TTL, cost, direction, or maturity rule.

## Evaluation windows
Primary reused research windows:
- 2025_H2 = 2025-07-01 <= event < 2026-01-01
- 2026_JAN_JUL = 2026-01-01 <= event < 2026-08-01
- POOLED_RECENT = 2025-07-01 <= event < 2026-08-01

Historical descriptive yearly audit: 2021, 2022, 2023, 2024, 2025_H1.
August 2026 remains reused/consumed audit only.

# Part A — P975_T25 formal confirmation
Frozen candidate: canonical 60m absolute log-return parent event at prior-30d 97.5th percentile + frozen T25 REV router + VF1_MATURE.

This is a formal re-freeze/confirmation on reused windows, not a fresh holdout.

Part A gates:
1. 2025_H2 fills >= 10
2. 2026_JAN_JUL fills >= 10
3. 2025_H2 mean R/fill >= +0.40
4. 2026 mean R/fill >= +0.40
5. PF >= 2.0 in both recent windows
6. CumR > 0 in both recent windows
7. Max DD <= 2.5R in both recent windows
8. Pooled CumR >= +12R
9. Pooled frequency >= 1.5 fills/month
10. Pooled all leave-one-episode-out remaining R > 0

PASS_CONFIRM_P975_T25 requires >=9/10 and gates 3,4,5,6 all pass.
WATCH_CONFIRM_P975_T25 requires positive both windows, PF>1.5 both, and >=7/10.
Otherwise FAIL_CONFIRM_P975_T25.

# Part B — second parent-family discovery
All families are defined before execution and use the SAME frozen T25 router, VF1 maturity and execution geometry. They deliberately exclude the exact canonical P97.5 current-bar return event where specified.

Common trailing windows are causal and shifted by one completed bar.
Cooldown remains 16 M15 bars (4h), as in the canonical lineage.

## Family D1: RANGE60_EXTREME
At event time:
- rolling 60m price range = (max high over last 4 completed/current bars - min low over last 4) / close;
- range >= its trailing 30d 97.5th percentile;
- absolute 60m log return is BELOW the canonical trailing P97.5 return threshold;
- direction = sign of 60m log return; zero direction rejected.

Purpose: catch violent two-sided/range expansion that does not qualify as extreme net 60m return.

## Family D2: VOLUME60_SHOCK
At event time:
- rolling 60m quote volume sum >= trailing 30d 97.5th percentile;
- absolute 60m log return >= trailing 30d 90th percentile but BELOW canonical P97.5 threshold;
- direction = sign of 60m log return.

Purpose: forced-flow/liquidity shock with meaningful but sub-extreme net displacement.

## Family D3: PERSISTENT60_MOVE
At event time:
- absolute 60m log return >= trailing 30d 95th percentile but BELOW canonical P97.5 threshold;
- directional efficiency over the four M15 returns = abs(sum four M15 log returns) / sum(abs(four M15 log returns)) >= 0.75;
- at least 3 of the 4 M15 returns share the 60m direction;
- direction = sign of 60m log return.

Purpose: clean persistent impulse that misses the extreme-amplitude threshold.

## Discovery diagnostics
For each family report:
- parent events, selected REV, mature opportunities, real fills;
- fills/month in each recent window;
- mean R/fill, CumR, PF, max DD;
- episode count, positive/negative episodes, worst episode, leave-one-episode-out;
- overlap with canonical P975_T25 selected events within the same timestamp and within +/-24h (descriptive only);
- incremental combined frequency and PnL if simply unioned with confirmed P975_T25 with timestamp de-duplication (descriptive only; no combined promotion).

Discovery screen marks a family `PROMISING_DISCOVERY` only if:
- >= 6 real fills in 2025_H2 and >= 7 in 2026_JAN_JUL;
- mean R/fill > 0 in both recent windows;
- PF > 1.2 in both;
- CumR > 0 in both;
- pooled frequency >= 0.75 fills/month;
- pooled worst leave-one-episode-out remaining R > 0.

No Part B family can become canonical from this LAB. A promising family must receive its own preregistered replication LAB.

## Overall status
- Part A and Part B verdicts are reported separately.
- No EA/live allocation is authorized by LAB015 alone.
