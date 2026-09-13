# XAU_CONTEXT_HIGH_FREQUENCY_EXECUTION_LAYER_DISCOVERY_LAB_001 — PREREG

Status: **FROZEN BEFORE OUTCOMES**

## Question
Can the already-frozen XAU Context BULL edge be converted from a rare H4 sniper signal into a materially higher-frequency executable M15 system without destroying expectancy, R:R, drawdown, or holding-time quality?

This is an **execution-layer discovery LAB on reused 2022–2026 XAU history**, not fresh OOS proof. Any selected execution family must later receive a frozen temporal/OOS replication before production use.

## Frozen parent context
Do not modify XAU Context semantics from LAB013–018.

Canonical population construction:
- H4 closed-bar causal router.
- `regime == PULLBACK`.
- `G1_VOL_COMPRESSION == True` (`range24_ratio < 0.85 AND atr_ratio < 0.95`).
- D14 concordance = D1 HTF Bias and D2 Trend Pressure agree.
- LONG-only: `D14_CONCORDANCE == +1`.
- LAB016 confirmation score from four frozen M15 components: OB / Imbalance-FVG / Liquidity / Price Action, 25% each.

Two predeclared context gates are tested:
- `E75`: setup confirmation >=75% (current sniper lineage).
- `E50`: setup confirmation >=50% (broader context; does NOT itself trigger a trade).

Each qualifying H4 bar activates a causal execution window `[available_time, available_time + 24h)`, matching the established 24h context horizon. Overlapping windows for the same gate are merged into one active context episode. M15 signals must become known while the episode is active. Pending-limit fills must occur before both their own expiry and episode end.

## Data
- Canonical XAU native M1: release `ak47/XAUUSD_M1_20220601_20260723_TICK_NATIVE.csv`.
- SHA256 `db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b`.
- H4/M15 aggregated causally from canonical M1.
- Strategy evaluation window: **2023-01-01 through 2026-06-30 inclusive** (42 complete calendar months). Earlier data are warmup only; July 2026 is excluded as a partial month.

## Frozen M15 execution families
All signals are LONG-only and require active H4 context.

### A — SWEEP_RECLAIM
On a closed M15 bar:
- prior reference = minimum low of preceding 20 closed M15 bars;
- trigger if current low < reference and current close > reference;
- entry = next M15 open (market benchmark).

### B — OB_RETEST
On a closed M15 bullish displacement bar:
- real body >= ATR14(M15);
- close > maximum high of previous 4 closed M15 bars;
- order block = most recent bearish candle among previous 4 bars;
- pending BUY limit = OB midpoint `(high+low)/2`;
- valid for next 12 M15 bars (3h) and no later than context end.

### C — FVG_RETEST
On a closed M15 bar:
- bullish FVG if current low > high from two M15 bars earlier;
- pending BUY limit = midpoint of the gap `[high[i-2], low[i]]`;
- valid for next 12 M15 bars (3h) and no later than context end;
- cancel before fill if a closed M15 bar closes below the lower FVG boundary.

### D — BOS_RETEST
On a closed M15 bar:
- BOS if close > maximum high of previous 8 closed M15 bars;
- breakout level = that prior-8 high;
- pending BUY limit at breakout level;
- valid for next 12 M15 bars (3h) and no later than context end.

### E — OR_ROUTER
Union of A/B/C/D. When flat, take the earliest causally available fill. If simultaneous, priority is `SWEEP_RECLAIM > OB_RETEST > FVG_RETEST > BOS_RETEST` (frozen before outcomes). Re-arm after exit with 60-minute cooldown while context remains active.

Portfolio rules for every family:
- one position at a time;
- maximum 2 entries per UTC calendar day;
- 60-minute cooldown after exit;
- no pyramiding, averaging, martingale, or overlapping trades.

## Frozen entry risk / exit model
Same for every execution family so the LAB compares entry method, not exit tuning.

At fill time:
- M15 ATR14 is the last fully closed value known at entry.
- structural low = minimum low of previous 8 closed M15 bars.
- structural stop = structural low - 0.10 × M15 ATR14.
- minimum stop distance = 1.00 × M15 ATR14.
- final stop is the lower of structural stop and `entry - 1.00×ATR15` (therefore at least 1 ATR away).
- reject setup if stop distance > 2.50 × M15 ATR14 or non-positive.
- TP = **1.50R** exactly.
- hard time-stop = **8 hours** after entry; if neither TP nor SL occurs, exit at the first available M1 open at/after 8h.

M1 path is used for fill and TP/SL resolution. If both SL and TP are touched within the same M1 bar, use conservative **SL-first**. For pending limit fills, execution begins only from the first M1 bar at/after activation; no pre-signal fill is allowed.

## Costs / R accounting
Primary performance is reported as:
- gross price-path R;
- commission-adjusted R using the currently supplied FTMO XAU commission assumption `0.0007% of notional per deal`, round turn;
- stress R with additional assumed round-trip price spread of **$0.20** and **$0.40 per ounce**. These spread values are robustness scenarios, not claims about the broker's average spread.

Selection/pass gates use the conservative **$0.40 spread-stress R**.

Risk/drawdown translation uses **0.25% account risk per 1R** on a 100K reference account. No leverage increase is used to manufacture returns.

## Variants
Exactly 10 primary variants:
- E75 × {SWEEP_RECLAIM, OB_RETEST, FVG_RETEST, BOS_RETEST, OR_ROUTER}
- E50 × {SWEEP_RECLAIM, OB_RETEST, FVG_RETEST, BOS_RETEST, OR_ROUTER}

No thresholds or definitions may change after preregistration.

## Primary metrics per variant
- total trades;
- mean and median trades/month across all 42 calendar months, including zero-trade months;
- percentage of months with >=10 trades;
- gross / commission / spread20 / spread40 expectancy in R/trade;
- PF on spread40 R;
- cumulative spread40 R and mean spread40 R/month;
- max drawdown in R and at 0.25% risk;
- maximum consecutive losing trades;
- win rate;
- median and 90th percentile holding hours;
- annual/half-year stability (2023, 2024, 2025, 2026H1).

## Quality gates
A variant is `EXECUTION_VIABLE` only if all are true on spread40 stress:
1. total trades >=420 (>=10/month mean over 42 months);
2. mean trades/month >=10;
3. expectancy >= +0.15R/trade;
4. PF >=1.35;
5. max DD at 0.25% risk <=4.0%;
6. max consecutive losses <=8;
7. median holding <=8h;
8. at least 3 of the 4 calendar blocks (2023, 2024, 2025, 2026H1) have positive expectancy, and none has cumulative result below -5R.

A variant is `TARGET_FREQUENCY` if it is `EXECUTION_VIABLE` and mean trades/month is 20–40 inclusive.

A variant with quality gates passing but 10–<20 trades/month is `VIABLE_LOW_FREQUENCY`.

A variant with >40 trades/month can remain viable, but is flagged `OVERACTIVE` and is not preferred automatically.

## Frozen discovery selection rule
This LAB may identify a **discovery winner**, not a validated strategy.

Selection order:
1. candidates that are `TARGET_FREQUENCY`;
2. otherwise `VIABLE_LOW_FREQUENCY` / viable overactive candidates;
3. among same class, highest mean spread40 R/month;
4. tie: higher spread40 PF;
5. tie: lower max DD.

If no candidate passes `EXECUTION_VIABLE`, verdict is `NO_HIGH_FREQUENCY_EXECUTION_METHOD_SUPPORTED` and no EA v0.2 should be claimed as validated from this LAB.

If one or more pass but none reach 20–40/month: `EXECUTION_EDGE_FOUND_FREQUENCY_BELOW_TARGET`.

If at least one reaches target: `HIGH_FREQUENCY_EXECUTION_CANDIDATE_FOUND`.

## Diagnostics — cannot rescue failed primary gates
- raw trigger counts vs actual fills;
- fill rate by pending family;
- duplicate/overlap rate across entry families;
- E50 incremental trades relative to E75;
- outcome by evidence 50/75/100;
- month-by-month trades and R;
- timeout fraction;
- gap/favorable excursion concentration;
- OR-router source composition.

## Anti-curve-fit boundary
After this prereg commit, no entry definition, H4 context rule, evidence gate, priority, pending expiry, stop formula, TP, timeout, daily cap, cooldown, cost stress, evaluation window, quality gate, or selection rule may be modified based on outcomes. Only technical/parser/runtime fixes that leave all frozen formulas unchanged are permitted and must be disclosed.