# GC_BUYER_BREAKOUT_LONG_TO_FTMO_XAU_TRANSFER_LAB_006 — PREREGISTRATION

Status: **FROZEN BEFORE XAU OUTCOME RUN**

## Purpose

Test whether the frozen historical GC M1 `BUYER_BREAKOUT_LONG_001` information edge transfers to executable FTMO-Demo XAUUSD prices. This LAB does **not** optimize signal thresholds, stop loss, take profit, time stop, session filters, or broker execution parameters.

## Frozen GC candidate

Source ledger: `research/gc/GC_M1_BUYER_BREAKOUT_LONG_AUDIT_004_EVENTS.csv`.

Candidate rule (`BUYER_BREAKOUT_LONG`):
- completed GC M1 bar;
- buyer aggression state: `delta_frac >= prior240 Q90` and aggressive BUY volume `>= prior240 Q75`;
- current high reaches/exceeds prior 20 completed-M1 high;
- bullish body;
- close in top 25% of current bar;
- LONG direction only;
- GC causal entry timestamp = exact next clock-contiguous M1 open after the completed signal bar.

The candidate is not re-derived or retuned in LAB006. The frozen event ledger is consumed as-is.

## Fixed controls

Primary control: `PRICE_BREAKOUT_NO_OF` from the same frozen LAB004 event ledger: same bullish local-high price structure but excluding the buyer-order-flow candidate.

Secondary control: `PRICE_BREAKOUT_ALL` from the same ledger.

Rithmic and AMP are treated as two feed representations of the same GC market, not independent market OOS samples. Results are reported separately, plus an exact common-clock candidate subset.

## FTMO XAU source

Google Drive raw tick export supplied by the user:
- folder lineage: `RawTicks/XAUUSD/2026`;
- schema: `RAW_TICK_V1`;
- symbol: `XAUUSD`;
- account server: `FTMO-Demo`;
- broker company: `FTMO Global Markets Ltd`;
- terminal build: `6182`;
- scope: `COPY_TICKS_ALL`;
- requested coverage: 2026-08-03 through 2026-09-15;
- tick fields include `time_msc`, Bid, Ask, quote-valid flag and spread.

Weekend/header-only files are not required. Trading-day raw CSVs are downloaded by immutable Drive file IDs in the workflow.

## Clock calibration — fixed before outcomes

Do **not** assume FTMO `time_msc` is UTC. Determine a constant clock offset using market-price synchronization only:

1. Reconstruct AMP GC M1 close returns from the canonical AMP raw GC history used by the historical discovery lineage.
2. Reconstruct FTMO XAU M1 mid-price close returns from the raw tick files.
3. Scan fixed candidate offsets from `-4h` to `+4h` in 30-minute increments, interpreting `FTMO_clock = UTC + offset`.
4. For each offset, align all common M1 bars and calculate Pearson correlation of 1-minute returns.
5. Select the offset with the highest correlation. No candidate/control trade outcomes may enter this selection.
6. Record the complete offset/correlation table.

This is a data-clock calibration, not a strategy parameter.

## Transfer execution convention

For each GC event:
- translate the frozen UTC `entry_time` into FTMO broker-clock using the selected clock offset;
- XAU entry = first quote-valid XAU tick **at or after** that broker-clock timestamp;
- entry must arrive within **5 seconds** or the event is rejected as non-executable/stale;
- LONG entry price = **Ask**;
- fixed-horizon exit = first quote-valid XAU tick at or after the horizon timestamp, within **5 seconds**;
- exit price = **Bid**;
- therefore quoted spread is included naturally;
- no commission, slippage surcharge, stop, target, BE, partial, trailing, or position-overlap restriction is imposed in LAB006.

## Frozen diagnostic horizons

Report executable XAU response at:
`1, 3, 5, 10, 15, 30, 60 minutes`.

**Primary horizon = 15 minutes**, chosen before the XAU run because the GC historical candidate was strongest/stable around 15 minutes.

## XAU normalization and path diagnostics

- Reconstruct XAU M1 mid OHLC.
- Compute causal XAU ATR14 using a 14-bar simple rolling mean of true range, consistent with the M1 historical discovery implementation style.
- Normalize executable returns by the latest completed XAU M1 ATR14 available at entry.
- Report entry spread in price and points/bps where possible.
- Report 15m and 60m MFE/MAE using executable LONG liquidation price (Bid) relative to entry Ask.

## Primary transfer gate

LAB006 is `TRANSFER_PASS` only if all are true:
1. Rithmic candidate has at least 100 executable XAU events at 15m.
2. AMP candidate has at least 100 executable XAU events at 15m.
3. Rithmic candidate executable 15m EV in XAU bps is > 0.
4. AMP candidate executable 15m EV in XAU bps is > 0.
5. Rithmic candidate-minus-`PRICE_BREAKOUT_NO_OF` 15m EV is > 0.
6. AMP candidate-minus-`PRICE_BREAKOUT_NO_OF` 15m EV is > 0.
7. Exact common-clock candidate subset has positive executable 15m EV.
8. At least 50% of candidate event-days have positive mean 15m executable return in both feeds.

Day-cluster bootstrap 95% CIs are reported but are not silently added to or removed from the frozen gate after seeing results.

## Governance

- No threshold sweep.
- No time-window selection after outcome observation.
- No filtering by session/news/spread after outcome observation.
- No stop/target optimization in LAB006.
- A failed transfer is recorded as failure; the same sample cannot be retuned and then called replication.
- If transfer passes, execution geometry (SL/TP/limit-retest) is a **separate LAB007**.
