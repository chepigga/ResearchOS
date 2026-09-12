# XAU_CONTEXT_COMPRESSION_CONCORDANCE_FRESH_OOS_REPLICATION_LAB_015 — PREREG

## Objective
Perform a genuinely **post-freeze OOS replication** of the frozen human-facing XAU Context layer discovered in LAB013 and replicated on reused history in LAB014:

`PULLBACK + G1 compression` -> `BREAKOUT RISK HIGH`, and when frozen HTF bias and frozen trend pressure agree, display `DIRECTIONAL PRESSURE BULL/BEAR`; otherwise `UNRESOLVED`.

This lab does not optimize Context weights, compression thresholds, EMA periods, ATR barrier, horizons, direction logic, or any execution rule. It tests only whether the already-frozen concordance semantics survive data that occur after the historical freeze.

No entries, TP/SL, EV, PF, commission, sizing, or prop-risk changes are tested.

---

## Fresh data source frozen before outcomes

GitHub release asset:
- tag: `xau`
- asset: `CAUSAL_XAU_RAW_XAUUSD_20260825.zip`
- release asset id: `532183735`
- required archive SHA256: `31f9548204fa99c29ce7d09e5b64e01ff75f5e8e3efab6f747cbd410cf34fd2e`
- source manifest: symbol `XAUUSD`, server `FTMO-Demo`, company `FTMO Global Markets Ltd`, digits 2, point 0.01
- manifest export range: 2023-01-01 through 2026-08-27 23:59 server export
- raw schema confirmed in a schema-only inspection before prereg: `time_msc,time_server,bid,ask,spread_price,spread_points,last,volume,volume_real,flags`.

The schema inspection computed **no Context state and no OOS outcome**.

### Deterministic ingestion
Use only members named exactly `CAUSAL_XAU_RAW_XAUUSD_YYYYMMDD.csv`.

For computational warm-up, read members dated **2025-01-01 through 2026-08-27** inclusive. Older archive members are ignored.

For every row:
- timestamp = `time_msc`, interpreted as Unix milliseconds UTC;
- price = `bid` only;
- rows with invalid/non-finite timestamp or bid <= 0 are dropped;
- `ask`, spread, flags and last may be retained for QA but cannot affect Context or outcomes.

Aggregate valid ticks to causal M1 BID bars in UTC:
- open = first bid in the minute by `time_msc`;
- high = max bid;
- low = min bid;
- close = last bid;
- volume = number of valid bid ticks in that minute.

Aggregate M1 to H4 exactly as frozen LAB008:
- `resample('4h', origin='epoch', label='left', closed='left')`;
- open first, high max, low min, close last, volume sum;
- incomplete/no-trade H4 buckets are dropped by the same OHLC completeness behavior as the frozen helper.

No forward fill of price bars is allowed.

### Warm-up versus OOS
Ticks before the OOS boundary exist only to warm EMA/ATR/rolling Context features. They can never enter a LAB015 metric.

**Fresh OOS boundary:** an H4 Context observation is OOS only if its frozen `available_time` is >= `2026-07-24 00:00:00 UTC`.

The maximum OOS time is determined solely by the fixed release asset. For each metric, observations lacking the entire required future window are naturally ineligible; they are not imputed or shortened.

The previous canonical historical dataset ended 2026-07-23, so no H4 observation with `available_time` before 2026-07-24 is allowed in any primary or secondary OOS result.

---

## Frozen Context and overlay definitions

Apply the existing frozen Context router unchanged, including the documented technical runtime parity patches only:
1. `d.stack` pandas name-collision -> `d['stack']`;
2. warm-up readiness mask before 3-bar score smoothing;
3. LAB008 all-NaN raw-winner handling if that helper is imported.

Frozen main state: `PULLBACK`.

Frozen compression overlay G1 from LAB010–014:
- `range24_ratio < 0.85`
- AND `atr_ratio < 0.95`.

Frozen D1 HTF bias:
- `BULL -> +1`
- `BEAR -> -1`
- `NEUTRAL -> 0`.

Frozen D2 trend pressure:
- BULL if `close > EMA20 > EMA50` and `slope50_atr > 0`;
- BEAR if `close < EMA20 < EMA50` and `slope50_atr < 0`;
- otherwise 0.

Frozen LAB014 concordance D14:
- if D1 == D2 and both are nonzero, D14 = that sign;
- otherwise D14 = 0 / `UNRESOLVED`.

No confidence threshold or score-gap threshold is allowed.

---

## Exact fresh first-passage target

For each fresh `PULLBACK + G1` observation at frozen H4 `available_time`:
- reference price = closed H4 BID close;
- reference volatility = closed H4 ATR14;
- upper barrier = close + 1.0 ATR;
- lower barrier = close - 1.0 ATR.

Using the freshly reconstructed M1 BID bars strictly from `available_time` forward for the next **8 hours**:
- `BULL_FIRST`: +1 ATR first;
- `BEAR_FIRST`: -1 ATR first;
- `AMBIGUOUS`: both first touched inside the same M1 bar;
- `NO_BREAKOUT`: neither touched in 8h.

`AMBIGUOUS` and `NO_BREAKOUT` are not forced into a direction.

The target definition is identical in semantics to LAB013/014; the source is fresh FTMO raw ticks aggregated to M1.

---

# H1 — fresh first-passage direction replication

Population: fresh OOS `PULLBACK + G1` bars with D14 = BULL or BEAR and exact target BULL_FIRST or BEAR_FIRST.

Metric: `accuracy = D14 == target_dir`.

Report all counts even if underpowered:
- fresh Pullback+G1 population;
- D14 directional coverage;
- resolved ±1 ATR count;
- resolved D14 prediction N;
- accuracy;
- BULL and BEAR accuracy separately;
- NO_BREAKOUT and AMBIGUOUS counts;
- calendar-week breakdown.

### H1 eligibility
Full H1 inference requires:
- >=20 resolved D14 predictions;
- D14 directional coverage >=30% of fresh `PULLBACK + G1` bars;
- observations in >=3 distinct calendar weeks;
- at least 2 calendar weeks with >=3 resolved D14 predictions.

### H1 pass
Weekly-cluster bootstrap, 5,000 draws, seed `2026091215`:
- observed accuracy > 50%;
- 95% bootstrap CI lower bound > 50%.

Week-sign diagnostic: among weeks with >=3 resolved D14 predictions, report the share with accuracy >50%. It is diagnostic and cannot rescue a failed CI.

---

# H2 — fresh 24h directional persistence

For each fresh D14 directional observation with a contiguous future 24h H4 close:

`D14_signed_close_atr_24h = D14 * (close_24h - reference_close) / ATR14`.

This does not condition on first-passage outcome.

### H2 eligibility
- >=20 valid D14 directional observations with full 24h future;
- observations in >=3 calendar weeks.

### H2 pass
Weekly-cluster bootstrap, 5,000 draws:
- mean signed 24h ATR > 0;
- 95% CI lower bound > 0.

---

# H3 — side symmetry sanity gate

Using exact resolved D14 predictions:
- report BULL N, accuracy and mean signed24 ATR;
- report BEAR N, accuracy and mean signed24 ATR.

H3 is eligible only if both sides have >=5 resolved predictions.

H3 passes if:
- BULL accuracy >= 50%;
- BEAR accuracy >= 50%;
- absolute BULL/BEAR accuracy gap <= 20 percentage points.

If H1 and H2 pass but H3 is underpowered, the verdict must explicitly retain side uncertainty.

---

# H4 — compression breakout-risk continuity on fresh data

Because LAB012 independently established the non-directional breakout-risk overlay, LAB015 also checks whether that parent semantic directionally survives fresh data without changing G1.

Inside fresh `PULLBACK` only, compare G1 compression versus non-G1 Pullback for:
1. 8h exact-M1 `breakout_any_1atr` (either barrier touched within 8h);
2. 24h H4 future range / ATR.

This is a secondary continuity gate, not required to rescue D14.

H4 is eligible if fresh G1 has >=20 valid 8h observations and >=20 valid 24h observations.
H4 passes if both observed premiums are >0. Bootstrap CIs are reported; because the fresh window is short, H4 does not require CI lower >0 for the LAB015 D14 replication verdict.

---

## Freshness and leakage audits

The runner must fail if:
- any primary H1/H2/H3 row has `available_time < 2026-07-24 00:00 UTC`;
- any first-passage scan uses M1 timestamps earlier than `available_time`;
- any 24h close is not exactly 24h later on contiguous H4 bars;
- archive SHA differs;
- source server in manifest is not `FTMO-Demo` or symbol is not `XAUUSD`.

The report must include the actual first/last fresh OOS `available_time`, source archive hash, processed raw member range, and M1/H4 counts.

---

## Verdict ladder

1. `FRESH_OOS_CONCORDANCE_REPLICATED`
   - H1 pass + H2 pass + H3 pass.

2. `FRESH_OOS_DIRECTION_AND_PERSISTENCE_SUPPORTED_SIDE_UNDERPOWERED`
   - H1 pass + H2 pass + H3 not eligible.

3. `FRESH_OOS_DIRECTIONALLY_CONSISTENT_UNDERPOWERED`
   - H1 and/or H2 fail only minimum-N/coverage/week eligibility,
   - observed H1 accuracy >50% when at least 5 resolved predictions exist,
   - observed H2 mean signed24 ATR >0 when at least 5 valid follow-through observations exist,
   - and no eligible side with N>=5 has accuracy <45%.

4. `FRESH_OOS_NOT_REPLICATED`
   - an eligible H1 has accuracy <=50% or CI lower <=50%, or
   - an eligible H2 has mean <=0 or CI lower <=0, or
   - eligible H3 fails symmetry.

5. `FRESH_OOS_NO_TESTABLE_EVENTS`
   - fewer than 5 resolved D14 predictions or fewer than 5 24h D14 follow-through observations.

A positive LAB015 result can validate **human-facing Context semantics only**. It cannot authorize automated BUY/SELL entries, trading risk, or prop-firm deployment by itself.

---

## Anti-overfit restrictions
- No changes to router weights, smoothing, hysteresis, state age, G1 thresholds, D1/D2 definitions, concordance logic, ATR barrier or horizons.
- No post-result threshold search.
- No BUY-only or SELL-only promotion.
- No inclusion of pre-2026-07-24 observations in OOS metrics.
- No switching from BID to mid/ask after outcomes.
- No extending the OOS window with another source after seeing LAB015 results.
