# XAU_IFVG_ANCHORED_VWAP_CAUSAL_REACTION_LAB_001 — Frozen Specification

**Version:** v001  
**Date:** 2026-08-22  
**Project:** XAU_Pool  
**Status:** PREREGISTERED_EVENT_STUDY / HOLDOUT_SEALED  
**Code:** `Code/Python/XAU_IFVG_ANCHORED_VWAP_CAUSAL_REACTION_LAB_001/run_lab.py`

## 1. Research question

Does a causally computed intraday anchored VWAP add conditional information to a confirmed inverse fair-value-gap (iFVG) event on XAUUSD, specifically when price has crossed the VWAP centre, held on the new side, attempted to recover the centre, failed, and then produced an iFVG in the accepted direction?

Primary mechanism:

`VWAP centre cross -> acceptance -> recovery attempt -> failed recovery -> aligned iFVG -> forward response`

The study tests **incremental information relative to ordinary iFVG events**. It is not a strategy, not an EA backtest, and does not authorize live allocation.

## 2. Source-derived hypothesis and what is NOT claimed

The podcast source states that:

- the indicator is anchored to the **18:00 new-day open**;
- it is used as **confluence**, not as a standalone trading system;
- the examples shown are explicitly described as partly **cherry-picked**;
- one shown gold setup uses a **5-minute inverse FVG**, a return, a **1-minute gap**, and a **close below** as the entry model;
- another example shows price testing the centre/"point of control", dropping below it, then repeatedly respecting it as resistance while holding the lower portion of the VWAP;
- the author uses the VWAP region for entry context, stop placement and targets.

The source does **not** provide a fully reproducible mathematical definition of the indicator's outer "volume high/volume low" lines, nor a deterministic iFVG algorithm. Therefore:

1. the **VWAP centre** is the primary tested level because it has an unambiguous standard volume-weighted definition;
2. outer bands are secondary diagnostics only and use an explicitly declared research proxy (`±1.618` causal weighted standard deviations); they are **not claimed to exactly reproduce VWAP AA**;
3. the iFVG definition below is a frozen research formalization of the described inverse-gap/retest logic, not a claim that it is the author's complete discretionary model.

## 3. Data lineage and embargo

Canonical input:

- member: `XAUUSD_M1_20220601_20260723_TICK_NATIVE.csv`;
- expected SHA-256: `db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b`;
- expected population: approximately 1,454,538 M1 rows;
- fields already used elsewhere in XAU_Pool: Bid OHLC, Ask-side OHLC/close fields where available, spread summaries, and volume/tick-volume fields when present.

Frozen temporal partitions:

- **Discovery:** `< 2024-01-01`;
- **Internal confirmation:** `2024-01-01 <= decision_time < 2025-07-01`;
- **Sealed historical holdout:** `decision_time >= 2025-07-01`.

The 2024–H1 2025 interval has already been inspected by prior XAU research and is **not independent OOS**. The holdout must not be used by the default analytical run. The code requires an explicit `--open-holdout` flag for a later one-time authorization.

## 4. Clock and anchor

The podcast anchor is 18:00 America/New_York. FTMO MetaTrader server time is GMT+2 with DST and shifts to GMT+3 in the US-DST season. This preserves a 7-hour offset from New York, so 18:00 New York maps to **01:00 next-day FTMO platform time**.

Primary ResearchOS implementation therefore uses:

`session anchor = 01:00 source/platform clock`

A timestamp from `00:00` through `00:59` belongs to the prior anchored session.

**Clock gate:** this mapping is authorized only if the canonical member is confirmed to use the same FTMO/platform clock lineage. If the input timestamp lineage differs, the run is invalid until the clock map is documented. No post-hoc anchor search is allowed.

## 5. Causal anchored VWAP

At each completed M1 bar within an anchored session:

- price source: `typical = (BidHigh + BidLow + BidClose) / 3`;
- primary weight: broker `tick_volume` (retail spot-volume proxy);
- cumulative VWAP is computed using only bars from the current anchor through the current completed bar;
- no end-of-session/future volume or future price may enter the level.

Primary centre:

`VWAP_t = sum(typical_i * tick_volume_i) / sum(tick_volume_i)` for `i <= t` inside the current anchored session.

Secondary outer diagnostic proxy:

- causal weighted variance inside the same session;
- `upper = VWAP + 1.618 * weighted_sd`;
- `lower = VWAP - 1.618 * weighted_sd`.

### Volume-ablation placebo

Because XAUUSD spot has no centralized exchange volume, broker tick volume may merely proxy activity. The lab computes a second anchored object with **identical 01:00 reset but no volume weighting**:

- cumulative arithmetic mean of M1 typical price;
- cumulative unweighted standard deviation;
- same `±1.618 sd` diagnostic bands.

The primary claim is stronger only if the volume-weighted centre is not fully explained by this time-anchored placebo.

## 6. Completed M15 ATR clock

All distance thresholds are normalized by Wilder `ATR14(M15)`.

- M15 bars use `label=left, closed=left`;
- an M15 bar starting at `t` becomes available only at `t + 15 minutes`;
- the current still-forming M15 bar is forbidden.

## 7. Frozen iFVG formalization

### 7.1 Source FVG

At completed M1 bar `i`:

- bullish FVG when `Low[i] > High[i-2]`; zone is `[High[i-2], Low[i]]`;
- bearish FVG when `High[i] < Low[i-2]`; zone is `[High[i], Low[i-2]]`.

The source FVG remains eligible for inversion for at most **240 M1 bars** after formation.

### 7.2 Inversion

- bullish FVG becomes a bearish inverse FVG after the first completed M1 close **below the lower edge**;
- bearish FVG becomes a bullish inverse FVG after the first completed M1 close **above the upper edge**.

### 7.3 Confirming retest / decision clock

Within at most **30 M1 bars after inversion**:

- bearish iFVG: price revisits the zone/lower edge and the completed bar closes back below the lower edge -> SELL decision;
- bullish iFVG: mirrored -> BUY decision.

The first qualifying retest only is used. If overlapping source FVGs create the same minute and direction, retain the **narrowest gap**, then oldest source gap as tie-break.

The decision is known only at that confirming retest bar close.

## 8. VWAP reaction state machine

For each confirmed iFVG, identify the nearest causal level among `CENTER`, `UPPER`, `LOWER`. Primary inference uses `CENTER` only.

A level is `NEAR` when decision close is within `0.10 * completed M15 ATR`.

Define signed side distance:

`side_t = direction * (close_t - level_t) / ATR_t`

where positive values are on the iFVG's intended side.

### ACCEPTANCE

Before the final recovery attempt, at least **4 of 5 completed M1 closes** must lie on the intended side of the dynamic level. Only windows already completed before the final three-bar recovery segment can qualify.

### RECOVERY ATTEMPT

Within the final three completed M1 bars before/including the iFVG decision:

- BUY: M1 low reaches to within `0.05 ATR` of the dynamic level;
- SELL: M1 high reaches to within `0.05 ATR` of the dynamic level.

### FAILED RECOVERY

`ACCEPTANCE` is already known, a recovery attempt occurs, and the iFVG decision close finishes at least `0.03 ATR` back on the accepted/intended side.

State priority:

`FAILED_RECOVERY > ACCEPT_HOLD > REJECTION > NEAR > FAR`

**Primary subset:** `anchor_kind = VWAP_VOLUME`, `level = CENTER`, `state = FAILED_RECOVERY`.

## 9. Outcome probe

This is an event-response probe, not finalized trade economics.

Decision-entry convention mirrors existing XAU ResearchOS quote-side studies:

- BUY nominal entry: Ask close at the causal decision bar when available;
- SELL nominal entry: Bid close at the causal decision bar;
- BUY future barriers use Bid OHLC;
- SELL future barriers use Ask OHLC when available;
- if Ask-side fields are absent, the run is marked `bid-only / mechanism-only` and cannot support an execution claim.

Frozen risk unit:

`1R = 0.75 * completed ATR14(M15)`

Two simultaneous pre-registered probes:

- `TP1.5R before SL1R`;
- `TP2R before SL1R`.

Horizon ends at the next 01:00 anchored-session reset. Events with less than **60 minutes** remaining in the session are excluded. Same-M1 TP/SL collisions are `AMBIGUOUS` and excluded from binary win-rate calculations. If neither barrier is hit, the event is `NO_HIT`; its session-reset signed return is retained and clipped to `[-1R, targetR]` for the continuous session-R statistic.

No commission, swap, or assumed slippage is used to promote this event study into a live trading claim. If mechanism gates pass, a separate economics lab must use the exact prop/broker specification.

## 10. Baseline and incremental-edge test

The baseline is **ordinary confirmed iFVG** on the same data without a VWAP failed-recovery requirement.

For the primary lift estimate:

- selected = volume-VWAP `CENTER + FAILED_RECOVERY` iFVG;
- control = `FAR` volume-VWAP iFVG;
- compare within the same **broker week and direction**;
- compute one mean selected-minus-control R difference per `week × direction` cell;
- bootstrap those week-direction cells with replacement (`2,000` resamples, seed `20260822`).

This prevents a pooled bull/bear regime difference from being mistaken for VWAP information.

## 11. Frozen gates

The primary mechanism is `GO_TO_ECONOMICS` only if **all** gates pass on Discovery + Internal Confirmation without using the holdout:

- **G0 CLOCK/DATA:** canonical clock mapping valid; tick-volume proxy present; causal fields pass integrity checks.
- **G1 POWER:** internal-confirmation primary subset `N >= 150`, with at least `40 BUY` and `40 SELL` events.
- **G2 1.5R ECONOMY PROXY:** internal-confirmation mean session-R for primary subset `> 0` at the 1.5R probe.
- **G3 INCREMENTAL LIFT:** lower bound of the 95% week-cluster bootstrap CI for 1.5R selected-minus-FAR lift `> 0`.
- **G4 SPLIT SIGN:** Discovery and Internal Confirmation primary 1.5R session-R are both positive.
- **G5 2R SURVIVAL:** Internal Confirmation primary 2R session-R is `>= 0`.
- **G6 VOLUME ABLATION:** volume-weighted primary 1.5R session-R is at least as high as the unweighted-anchor `CENTER + FAILED_RECOVERY` placebo, with at least 50 observations in each comparison arm.

Verdicts:

- `GO_TO_ECONOMICS`: all gates pass;
- `WATCH_POWER`: directionally positive but G1 insufficient;
- `NO_INCREMENTAL_VWAP_EDGE`: iFVG may work, but VWAP failed recovery does not add robust lift;
- `NO_SIGNAL`: primary conditional effect is non-positive/unstable;
- `INVALID_DATA_CLOCK`: data/clock/volume gate fails.

The sealed holdout may be opened exactly once only after an internal `GO_TO_ECONOMICS` verdict is frozen.

## 12. Required outputs

`Results/XAU_IFVG_ANCHORED_VWAP_CAUSAL_REACTION_LAB_001/v001/`:

- `events.parquet` — causal event registry and outcomes;
- `summary.csv` — split × anchor × state statistics;
- `audit.json` — input period, counts, quote/volume availability and holdout status;
- `verdict.json` — frozen gates and week-cluster lift;
- `README.md` — final interpretation and next step.

## 13. Explicit exclusions

Not allowed in LAB_001:

- trend filters, D1/H4 bias, RSI, ADX, news filter, liquidity labels, SMT, fib, COT, AI/Grok score;
- optimizing VWAP proximity, acceptance window, FVG lifetime, retest window, ATR risk, targets, session anchor or band coefficient against outcomes;
- selecting only London/NY after seeing results;
- opening the historical holdout before all internal gates pass;
- claiming that outer bands exactly reproduce the protected VWAP AA script;
- building an EA from this lab before a separate prop/broker economics specification is frozen.

## 14. Source checkpoints from the podcast

For traceability, the source transcript contains the relevant statements approximately at:

- `00:57–01:03`: 18:00 new-day anchor;
- `01:17–01:20`: examples admitted to be cherry-picked;
- `07:59–08:07`: 5-minute inverse, 1-minute gap, close-below entry model;
- `15:37–15:42`: inversion, wick into gap, close-below entry;
- `16:04–16:33`: centre test, break below, then centre respected as resistance / lower VWAP portion held.

These source statements motivate the lab; they do not predetermine the result.
