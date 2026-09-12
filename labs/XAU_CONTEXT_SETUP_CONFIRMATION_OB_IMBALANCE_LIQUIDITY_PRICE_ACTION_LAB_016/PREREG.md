# XAU_CONTEXT_SETUP_CONFIRMATION_OB_IMBALANCE_LIQUIDITY_PRICE_ACTION_LAB_016 — PREREGISTRATION

## Purpose
Test whether an independent, human-facing `SETUP_CONFIRMATION_%` derived from four causal M15 setup concepts adds semantic information on top of the already frozen XAU Context stack:

`PULLBACK + G1_VOL_COMPRESSION + D14_CONCORDANCE`.

This is **not** an automated-entry lab. The score is a decision-support value for a human trader. No SL/TP, position sizing, PnL, commission, or prop-risk claims are authorized.

## Frozen source / lineage
- Historical discovery source: release `ak47`, `XAUUSD_M1_20220601_20260723_TICK_NATIVE.csv`.
- SHA256: `db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b`.
- Frozen Context lineage: LAB008/009/010/013/014 with the already audited runtime-only hotfixes.
- Main population: H4 bars satisfying:
  - `regime == PULLBACK`
  - `G1_VOL_COMPRESSION == True`
  - `D14_CONCORDANCE != 0`
- `D14_CONCORDANCE` remains frozen: D1 HTF Bias and D2 Trend Pressure must agree; else 0.
- Primary target remains exact BID-M1 first passage to `close ± 1*ATR14(H4)` within 8h, as in LAB013/014.
- Persistence metric remains `D14_CONCORDANCE * close_ret_atr_24h`.

## Confirmation timeframe and causality
All confirmation concepts are computed from **closed M15 BID bars only**, strictly before or at the H4 `available_time`. No M15 bar that opens at or after `available_time` may contribute.

M15 bars are reconstructed from canonical M1 using epoch-aligned 15-minute OHLC.

For every Context observation with direction `dir ∈ {+1,-1}`, define four frozen binary confirmation components. Each component contributes exactly **25 percentage points**. No post-outcome weighting is allowed.

`SETUP_CONFIRMATION_% = 25 * (OB + IMBALANCE + LIQUIDITY + PRICE_ACTION)`

Possible values: `0,25,50,75,100`.

## Frozen component definitions

### C1 — ORDER_BLOCK_CONFIRMATION
A directional M15 order-block retest/rejection must be observable before `available_time`.

**Bullish (`dir=+1`)**
1. Candidate OB is a bearish M15 candle (`close < open`) occurring within the prior 12h.
2. Within the next 1–3 closed M15 bars, a bullish displacement bar must:
   - have real body `>= 1.0 * ATR14(M15)`, and
   - close above the candidate candle high, and
   - close above the highest high of the 4 M15 bars immediately preceding the candidate.
3. After displacement and before `available_time`, price must retest the candidate range (`low <= candidate high` and `high >= candidate low`) and subsequently close above the candidate midpoint.
4. The OB is invalid if any closed M15 bar after displacement closes below the candidate low.

**Bearish (`dir=-1`)** is the exact mirror.

If more than one valid candidate exists, use the most recent one. Component = 1 if a valid directional OB confirmation exists, otherwise 0.

### C2 — IMBALANCE_CONFIRMATION
A directional, still-open M15 fair-value gap (3-candle imbalance) must have formed within the prior 6h.

**Bullish** at M15 bar `i`: `low[i] > high[i-2]`.
- Gap = `[high[i-2], low[i]]`.
- It remains valid at `available_time` if no later closed M15 bar has `low <= high[i-2]` (full fill).

**Bearish**: `high[i] < low[i-2]`, mirrored validity using later `high >= low[i-2]` as full fill.

At least one valid directional FVG = 1, else 0. Most recent valid FVG is descriptive only; no size threshold optimization.

### C3 — LIQUIDITY_CONFIRMATION
A directional opposite-side liquidity sweep + reclaim must occur within the prior 4h.

For each closed M15 bar, define the prior swing reference from the **preceding 20 closed M15 bars**, excluding the event bar.

**Bullish:** event low < prior-20-bar low AND event close > prior-20-bar low.

**Bearish:** event high > prior-20-bar high AND event close < prior-20-bar high.

At least one directional sweep/reclaim within the last 16 M15 bars = 1, else 0.

### C4 — PRICE_ACTION_CONFIRMATION
Directional M15 price-action confirmation must occur within the prior 2h (last 8 closed M15 bars).

Component = 1 if at least one of the following directional patterns occurs:

**Bullish:**
- bullish engulfing: current close > current open, previous close < previous open, current open <= previous close, current close >= previous open; OR
- bullish rejection: lower wick >= 45% of candle range AND close is in the top 35% of candle range; OR
- directional structure close: close > highest high of the preceding 8 M15 bars.

**Bearish:** exact mirror (bearish engulfing, upper-wick rejection with close in bottom 35%, or close < prior-8 low).

No pattern gets extra weight; the whole module remains binary.

## Primary score tests

### H1 — Confirmation score adds first-passage direction information
Compare observations with `SETUP_CONFIRMATION_% >= 50` versus `< 50` among exact resolved ±1 ATR events.

Pass only if:
- each side has `N >= 100` resolved observations,
- observed accuracy premium (`accuracy_high - accuracy_low`) > 0,
- weekly-cluster bootstrap 95% CI lower bound > 0,
- premium sign positive in at least 3 of 4 years (2023–2026, eligible year requires >=20 observations in both groups).

### H2 — Confirmation score adds 24h directional persistence
Compare mean `D14_signed24` for `score >= 50` versus `<50`.

Pass only if:
- each group has `N >= 150`,
- observed difference > 0,
- weekly-cluster bootstrap 95% CI lower bound > 0,
- sign positive in at least 3 of 4 eligible years.

### H3 — High confirmation is independently useful
For `SETUP_CONFIRMATION_% >= 75`, among resolved events:
- require N >= 60,
- absolute first-passage accuracy > 55%,
- weekly-cluster bootstrap 95% CI lower bound > 50%.

### H4 — Score-response ordering
Report all five score buckets (`0/25/50/75/100`) without collapsing or deleting any bucket.
A descriptive monotonicity flag passes only if bucket accuracy is non-decreasing across all **eligible** buckets with N>=30. This is secondary and cannot by itself authorize promotion.

## Component diagnostics (predeclared, not selection gates)
For each of OB / Imbalance / Liquidity / Price Action, report:
- prevalence,
- first-passage accuracy when component present vs absent,
- 24h signed ATR when present vs absent,
- BULL and BEAR prevalence/accuracy,
- year breakdown.

No single component may be selected as a new rule from this LAB solely because it looks best.

## Side-symmetry diagnostic
For score >=50, report BULL and BEAR resolved accuracy separately. A side is considered adequately sampled at N>=50. No side may be dropped post-outcome.

## Verdict logic
- `SETUP_CONFIRMATION_SUPPORTED_DISCOVERY_ONLY`: H1 + H2 + H3 pass.
- `SETUP_CONFIRMATION_DIRECTION_ONLY`: H1 + H3 pass, H2 fails.
- `SETUP_CONFIRMATION_PARTIAL`: exactly one or two of H1/H2/H3 pass.
- `SETUP_CONFIRMATION_UNDERPOWERED`: no primary conclusion because H1 groups or H3 high-score group fail minimum N.
- `SETUP_CONFIRMATION_NOT_SUPPORTED`: adequately powered but none of H1/H2/H3 pass.

## Interpretation constraints
- This LAB uses reused historical data, therefore any positive result is `DISCOVERY_ONLY`.
- Confirmation % is not a probability of profit and must not be displayed as such. It is the percentage of the four frozen setup-confirmation modules currently present.
- No automated BUY/SELL arrow, entry, SL/TP, lot sizing, or prop-risk change is authorized by this LAB.
- Fresh OOS replication is required before production promotion.
