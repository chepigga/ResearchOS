# BTC_REVERSAL_LIMIT_RETEST_RR15_FIRST_HIT_AND_PROP_ECONOMICS_LAB_006 — PREREG

Frozen before reading LAB006 outputs.

## Lineage
- Selector: exact LAB005/LAB003 BTC-only CORE top-20 router, REV side only.
- Entry: exact LAB005 primary `LIMIT_R0.50_T60`: preset reversal limit at event close + impulse_dir × 0.50 × event M15 range, TTL 60m, no market fallback.
- Parent impulse: completed BTC 60m |return| >= prior 30d 97.5th percentile; 4h cooldown.
- No selector, threshold, limit distance or TTL tuning is allowed on 2026.

## Primary execution geometry
- Risk distance `1R` = exactly 1.00 × parent event M15 high-low range from filled limit price.
- For reversal after bullish impulse: short; SL = entry + 1R; TP = entry - RR×1R.
- For reversal after bearish impulse: long; SL = entry - 1R; TP = entry + RR×1R.
- Primary RR = 1.5. Secondary audit RR = 2.0.
- First-hit scan starts on the fill bar and ends at parent impulse +24h.
- If SL and TP are both touched in the same M15 bar, score SL first (conservative).
- If neither is hit by parent+24h, close at that bar close and mark TIME_EXIT.

## Cost stress
Exact FTMO BTC CFD spread/commission is not assumed here. Apply frozen round-trip execution-cost scenarios to every filled trade: 0, 2, 5, 10 bps of entry notional. Convert cost to R by dividing cost fraction by the trade stop fraction.
- `5 bps` is the primary prop-economic stress scenario for promotion.
- 0/2/10 bps are sensitivity only.

## Metrics
By DEV 2021–2024 / Bridge 2025 / OOS 2026:
- fill count
- TP / SL / TIME rates
- gross and net expectancy R
- profit factor
- cumulative R
- max consecutive losses
- max closed-equity drawdown in R
- MFE / MAE in R
- median time-to-exit
- max overlapping open positions
- compounded equity/DD at fixed 0.25% and 0.50% risk per trade under 5 bps cost.

Closed-equity DD is not a substitute for FTMO floating intraday drawdown; overlap/risk-load is reported separately.

## Promotion gates — primary RR1.5 / 5bps
1. Bridge filled >= 15.
2. OOS filled >= 10.
3. Bridge net expectancy R > 0.
4. OOS net expectancy R > 0.
5. Bridge PF > 1.0.
6. OOS PF > 1.0.
7. OOS max consecutive losses <= 8.
8. At 0.50% risk, OOS closed-equity max DD < 5%.
9. Max overlapping initial risk at 0.50% < 4% in OOS.

Verdict:
- 9/9: `PASS_PROP_ECONOMICS_SCREEN`
- 7–8/9 with positive Bridge/OOS net EV: `WATCH_PROP_ECONOMICS`
- otherwise: `FAIL_RR15_PROP_ECONOMICS`

No EA/live allocation is authorized by this LAB alone.