# GC_SHORT_CHRIS_LONG_HISTORY_REPLICATION_LAB_008H — PREREG

## Purpose
Replicate the frozen Chris/AEIF SHORT lineage on substantially longer GC futures history without retuning the signal or the POST10 walk-forward gate.

## Frozen Chris lineage
Signal logic is inherited unchanged from LAB003:
- completed GC M1;
- `a_buy = delta_frac >= causal prior240 Q90 AND buy_vol >= causal prior240 Q75`;
- upper location: `buy_loc >= causal prior240 Q75 buy_loc`;
- weak result: `impact <= causal prior same-side BUY impact Q20`;
- bearish confirmation within next <=2 completed M1 bars: `close < open`, `close < seed_close`, `close_pos <= 0.50`;
- entry = next contiguous M1 open after confirmation.

POST10 decision logic is inherited unchanged from LAB006:
- checkpoint = entry + 10m;
- feature = `cp10_dist_seed_high`;
- after >=8 prior eligible events, threshold = expanding median (Q50) of prior feature values only;
- selected iff current feature >= prior-history Q50;
- primary residual target = +10m→+20m SHORT return / seed ATR14;
- secondary residual target = +10m→+30m SHORT return / seed ATR14.

No threshold sweep, no change of confirmation, horizon, feature family, or quantile is permitted.

## Long-history source and critical parity stage
The certified current feeds (Rithmic/AMP) have explicit aggressor BUY/SELL but only ~40 days. Long-history candidate is Massive Futures trade + quote history.

Massive trade records do not provide the already-certified explicit aggressor flag used by Rithmic/AMP. Therefore LAB008H MUST NOT directly treat Massive prints as equivalent order flow.

Causal Massive aggressor inference is frozen as:
- align each trade to the latest quote known at or before the trade timestamp;
- BUY if trade_price >= prevailing ask;
- SELL if trade_price <= prevailing bid;
- otherwise EXCLUDE;
- crossed/invalid/stale quote rows are EXCLUDE;
- no tick-rule fallback for inside-spread trades.

### Stage A — overlap parity gate
Use overlapping 2026 GC history and compare Massive-inferred M1 against explicit Rithmic M1 before any long-history conclusion.

PASS requires all:
1. common M1 bars >= 10,000;
2. `delta_frac` Pearson correlation >= 0.85;
3. delta sign agreement >= 0.80 on bars where both are non-zero;
4. `a_buy` Jaccard >= 0.40;
5. LAB003 Chris seed-event timestamp Jaccard >= 0.35;
6. no timestamp lookahead in quote assignment.

If Stage A fails, status is `BLOCKED_LONG_HISTORY_AGGRESSOR_PARITY_FAIL`; Stage B is prohibited.

## Stage B — long-history replication
Target historical window: 2022-06-01 through 2026-07-23 where long FTMO XAU M1 Bid/Ask inventory is also available for a later transfer lab. LAB008H itself is GC-only.

### Contract stitching
Use a causal GC front-contract chain. For each session choose the contract with the highest total volume in the immediately preceding completed session among eligible active single GC contracts. Do not use future-session volume. At every contract switch reset rolling state and require at least 240 new M1 bars before signals are eligible. This prevents basis jumps from contaminating ATR/quantiles.

### Frozen long-history PASS gates
All must pass:
1. usable stitched coverage >= 24 months;
2. frozen Chris events >= 75;
3. OOF POST10 events after 8-event warm-up >= 50;
4. selected events >= 25;
5. selected primary EV (+10→20) > 0;
6. selected primary EV exceeds all-OOF baseline by >= +0.10 ATR;
7. selected primary EV > rejected primary EV;
8. selected primary WR >= 55%;
9. selected secondary EV (+10→30) >= 0;
10. at least 3 calendar years with >=5 selected events have positive primary EV;
11. no single calendar year contributes >50% of selected events.

## Governance
This is historical replication, not independent forward OOS. Massive parity must be established before long-history use. Do not rescue a failed result by changing aggressor inference, Q50, POST10 horizon, signal thresholds, contract-roll rule, or excluding losing periods after seeing outcomes.
