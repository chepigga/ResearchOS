# GC_XAU_LONG_RESEARCH_BACKLOG_AND_RECOVERY_STATE_004

**Date:** 2026-09-17  
**Branch:** `gc-amp-feed-audit-001`  
**Scope:** GC futures / COMEX order flow / AMP Futures MT5/CQG -> FTMO XAUUSD LONG execution only.  
**Current status:** `READY_FOR_FTMO_DEMO_SHADOW`  
**Live/funded authorization:** NO.

---

## 1. Purpose of this recovery file

This is the canonical recovery/backlog checkpoint for the current GC->XAU LONG lineage. It is intended to let a future session continue directly from the current state without restarting discovery.

Do **not** mix this branch with:
- crypto / CrowdFade / BTC AEIF;
- old XAU SELL research;
- unrelated EAs;
- the separate frozen GC AEIF lineage unless explicitly requested.

The current objective is no longer discovery. The current LONG candidate has passed the historical/demo-readiness gates and the next phase is exact FTMO Demo shadow execution.

---

## 2. Frozen data / provenance

### AMP GC raw archive

File:
`AMP_GC_HISTORY_EXPORTER_001_GCEZ26_20260806_182355__20260915_182355_TICKS.csv.zip`

SHA256:
`81d675597368a9f6c78eee726ed547737366ffd8d8e54aa976bce50111db752b`

Symbol: `GCEZ26`

Coverage:
- 2026-08-06 18:24 UTC -> 2026-09-15 18:23 UTC
- raw rows: 3,737,579
- dual BUY+SELL flags excluded: 5,609
- exclusive-direction rows: 3,731,970
- reconstructed GC M1 bars: 38,464

Frozen aggressor semantics:
- BUY = `is_buy=1 && is_sell=0`
- SELL = `is_sell=1 && is_buy=0`
- simultaneous BUY+SELL excluded

### FTMO XAU raw ticks

FTMO-Demo, raw Bid/Ask quote ticks.

Coverage:
- 2026-08-03 through 2026-09-15
- 32 non-empty daily files
- 8,236,717 valid quote ticks
- first `time_msc`: 1785719100005
- last `time_msc`: 1789516199707
- crossed quotes: 0

Execution semantics:
- LONG entry path: Ask
- SL/TP/timeout path: Bid
- quoted spread embedded
- extra cost stress handled separately

Clock mapping:
- GC UTC -> FTMO broker clock offset = **+180 minutes**
- best clock-alignment correlation = **0.9869174815478382**

---

## 3. Frozen GC LONG signal

Signal name:
`BUYER_BREAKOUT_LONG_001`

Evaluate only on a fully completed GC M1 bar.

Frozen feature definitions:
- ATR14 = SMA true range
- `body_atr = (close-open)/ATR14`
- `range_atr = (high-low)/ATR14`
- `close_pos = (close-low)/(high-low)`; fallback 0.5 on zero range
- all prior rolling quantiles are shifted one completed bar
- prior 240 M1 bars for quantiles
- `prior20_high` = max high of previous 20 completed M1 bars

Signal conditions:
1. completed GC M1 bar;
2. `delta_frac >= prior240 Q90`;
3. `buy_vol >= prior240 Q75`;
4. `high >= prior20_high`;
5. bullish body / positive buyer impact;
6. `close_pos >= 0.75`;
7. XAU execution starts only after GC signal information is fully available.

Interpretation:
aggressive GC buyers successfully push through the recent high and close the auction strongly near the bar high.

Do **not** retune this signal before Demo shadow unless a new, separately preregistered research branch is opened.

---

## 4. Frozen XAU execution candidate

Chosen candidate:
`D1.00_E3M_BARE_CORRECTED`

LONG only.

Frozen execution:
- order becomes actionable on the next XAU M1 after the completed GC signal;
- BUY LIMIT depth = contemporaneous executable XAU Ask minus `1.00 * ATR14(XAU M1)`;
- expiry = 3 minutes from order-start;
- for an unfilled setup, busy state therefore ends at `order_start + 3m`, not at signal-left-edge + 3m;
- SL = `1.5 * ATR`;
- TP = `3R = 4.5 * ATR`;
- hard timeout = original signal clock + 30 minutes;
- one active setup/position at a time;
- cost stress reference = +0.05R/fill historical baseline.

Risk for Demo shadow:
**0.25% equity per trade.**

Do not use 0.50% risk for prop-style shadow testing. Historical bootstrap p95 DD at 0.50% is too aggressive.

---

## 5. Core historical results

Corrected AMP_ALL D1/E3:
- original signals: **279**
- accepted signals: **237**
- fills: **103**
- EV/original signal: **+0.0863395506R**
- SumR: **+24.0887346R**
- observed MaxDD: **8.40R**
- late-period EV/original signal: **+0.0681449200R**

Dependency robustness:
- bootstrap `P(EV>0)` = **96.31%**
- leave-one-week-out minimum EV = **+0.0749731814R/signal**
- max positive-day share = **16.9%**
- bootstrap p95 DD at 0.25% risk = **3.894%**
- bootstrap p95 DD at 0.50% risk = **7.788%**

Important statistical nuance:
- the historical bootstrap is supportive but not independent forward OOS;
- historical 95% EV bootstrap CI slightly crosses zero;
- therefore this is a **Demo-ready historical candidate**, not a live/funded-proven system.

---

## 6. LAB lineage and conclusions

### LAB002 — GC M1 feature build / feed parity
PASS.
AMP and Rithmic normalized M1 feature construction showed high parity.

### LAB003 — bounded discovery
Found `BUYER_BREAKOUT_LONG_001`.
Candidate only at that stage.

### LAB004 — post-discovery historical audit
PASS for LONG continuation.
Mirror SHORT was materially weaker and was not advanced.

### LAB005 — GC -> XAU transfer
PASS historically.
GC buyer-breakout events transferred positively to XAU.

### LAB006 — execution snapshot
Identified D1.00 / SL1.5 / TP3R candidate.

### LAB007 — depth sensitivity
D0.93 looked somewhat better but was **not adopted post hoc**.
D1.00 remained incumbent.

### LAB008 — time split
D1.00 robust enough to continue.

### LAB009 — operational execution
Historical D1/E3 one-active evaluation.
Later found one technical busy-clock defect for unfilled setups.

### LAB010 — dependency / bootstrap
0.25% risk acceptable for further validation.
0.50% too aggressive for prop-style use.

### LAB011 — signal decay
Very early fills strongest; later fills weaker.
E1 challenger did not replace E3 because late-period E1 EV turned negative.

### LAB012 — E1 vs E3 forward shadow preregistration
Protocol valid, but insufficient fresh forward sample.
No conclusion replacing E3.

### LAB013 — realtime AMP implementation parity protocol
Forward parity observer prepared.
Fresh realtime sample was insufficient at the time.

### LAB013H — existing-data full replay audit
Status: `HISTORICAL_REPLAY_PASS`.

Key exact replay results:
- GC reconstructed bars: 38,464 vs 38,464
- signal events: 281 vs 281
- numerical feature mismatches: 0
- XAU inventory exact
- +180 min clock mapping reproduced
- LAB009 metrics exactly reproduced

Defect found:
LAB009 had used signal-left-edge + expiry for unfilled busy-state termination.
Correct semantic is order-start + expiry.

Corrected D1/E3:
- accepted: 237
- fills: 103
- EV/signal: +0.0863395506R
- EV/fill: +0.2338712099R
- PF: ~1.380
- MaxDD unchanged at 8.4R

The correction slightly improved results; the historical edge was **not** created by the bug.

### LAB014H — corrected one-active dependency robustness
Status: `CORRECTED_HISTORICAL_ROBUSTNESS_PASS_NOT_OOS`.

AMP_ALL:
- N 279
- accepted 237
- fills 103
- SumR +24.09
- EV/signal +0.08634
- bootstrap P(EV>0) 96.31%
- p95 DD @0.25% = 3.894%

Conclusion:
0.25% risk remains the correct Demo risk. 0.50% is too aggressive.

### LAB015 — trade-by-trade failure discriminator
Status: `HISTORICAL_FAILURE_DISCRIMINATOR_FAIL_NOT_OOS`.

Primary order-start classifier failed:
- OOF AUC ~0.411
- applying it historically reduced performance

Conclusion:
Do **not** add a static pre-order classifier/filter.

Secondary fill-time diagnostics were economically interesting but not directly causal/deployable because the information was known at or near fill.

### LAB016 — causal D0.75 prefill warning gate
Status: `HISTORICAL_CAUSAL_PREFILL_GATE_FAIL_NOT_OOS`.

Results:
- corrected fills: 103
- executable D0.75 warnings: 94 / 103 = 91.3%
- median warning lead to D1 fill: 5.325s
- p10 warning lead: 0.647s
- OOF AUC: 0.489
- veto SL enrichment: 1.06x

Economic overlay improved historical PnL/DD, but predictive gates failed.

Conclusion:
Do **not** add LAB016 gate to Demo candidate.

### LAB017 — causal prefill approach-shape acceleration gate
Status: `HISTORICAL_CAUSAL_ACCELERATION_GATE_FAIL_NOT_OOS`.

Results:
- OOF AUC: 0.5675
- veto share: 24.5%
- veto SL rate: 75%
- SL enrichment: 1.225x
- historical OOF overlay SumR: +6.24R -> +10.85R
- MaxDD: 8.4R -> 6.3R

Frozen statistical gates required AUC >=0.60 and enrichment >=1.25x, so LAB017 failed.

Conclusion:
Despite attractive PnL, **reject LAB017 overlay**. Do not add it to Demo.

### LAB018 — Demo readiness audit
Status: **`READY_FOR_FTMO_DEMO_SHADOW`**.

Chosen candidate:
`D1.00_E3M_BARE_CORRECTED`

All frozen readiness gates passed:
- exact historical replay;
- positive historical EV;
- positive leave-one-week-out EV;
- bootstrap P(EV>0) >=95%;
- p95 DD at 0.25% <=4%;
- positive 0.10R/fill stress;
- nonnegative 0.15R/fill stress;
- positive late-half EV;
- no lookahead in frozen execution;
- implementation spec frozen.

Cost-stress:
- total 0.10R/fill -> EV +0.06788077R/signal; SumR +18.94
- total 0.15R/fill -> EV +0.04942199R/signal; SumR +13.79
- total 0.20R/fill diagnostic -> EV +0.03096321R/signal
- total 0.25R/fill diagnostic -> EV +0.01250443R/signal
- historical break-even total cost ~0.28387R/fill

Governance conclusion:
**Research phase for this LONG baseline is frozen. The next valid phase is FTMO Demo forward/OOS shadow execution.**

---

## 7. What is known

We know with high confidence within the existing historical dataset that:
- the GC signal can be reconstructed exactly;
- AMP aggressor semantics are usable;
- the GC->XAU time alignment is stable in the frozen archive;
- the LONG transfer exists historically;
- D1/E3 is the current robust execution incumbent;
- corrected one-active semantics do not remove the edge;
- 0.25% risk is materially safer than 0.50%;
- the system stays historically positive under much heavier cost than the baseline 0.05R/fill assumption;
- static and prefill ML-style filters tested so far should **not** be added.

---

## 8. What is NOT known yet

The following remains unproven:
- true independent forward/OOS expectancy;
- actual FTMO Demo fill quality versus historical Ask-touch assumptions;
- real cancellation / modification latency;
- realized slippage and spread behavior around signal/fill time;
- real VPS/network timing;
- behavior across future GC contract rollover;
- whether +180 min clock mapping remains correct under timezone/DST/server changes unless runtime timestamps are normalized safely;
- long-term regime durability across much larger historical periods;
- whether the system is ready for funded/live capital.

No live/funded claim is authorized by the current evidence.

---

## 9. NEXT PHASE — FTMO Demo shadow

### Immediate backlog

1. Reconfirm current FTMO Demo XAUUSD broker specifications before final EA code:
   - exact symbol name;
   - digits / point / tick size / tick value;
   - min lot / max lot / volume step;
   - `SYMBOL_TRADE_STOPS_LEVEL`;
   - `SYMBOL_TRADE_FREEZE_LEVEL`;
   - contract size;
   - current spread behavior;
   - commission / round-turn cost;
   - permitted pending-order behavior;
   - server timezone / timestamp normalization;
   - account leverage;
   - current FTMO challenge/demo rules relevant to EA/news execution;
   - VPS and expected latency.

2. Build frozen Demo EA/bridge with **no strategy retuning**.

3. Sensor side:
   - consume AMP GC data;
   - reconstruct completed M1 exactly as research semantics;
   - calculate frozen rolling features;
   - emit only `BUYER_BREAKOUT_LONG_001` events;
   - log the complete feature state for every signal.

4. Execution side on FTMO XAUUSD:
   - next-M1 actionable order-start;
   - D1.00 BUY LIMIT;
   - E3 expiry;
   - SL1.5 ATR;
   - TP4.5 ATR / 3R;
   - signal+30m hard timeout;
   - corrected one-active state machine;
   - 0.25% risk;
   - normalize lots to broker volume step;
   - full order/result/error handling;
   - no LAB016/LAB017 overlay.

5. Shadow logging must capture at minimum:
   - GC signal timestamp UTC;
   - GC feature snapshot;
   - XAU order-start timestamp;
   - start Bid/Ask;
   - ATR used;
   - calculated D1 limit;
   - broker accepted pending-order price;
   - submit latency;
   - order reject/modify codes;
   - fill timestamp / fill price;
   - theoretical historical-semantics fill price;
   - fill slippage in points and R;
   - spread at start and fill;
   - SL/TP prices;
   - exit reason/time/price;
   - realized R;
   - theoretical expected R under frozen simulator;
   - state/busy transitions.

6. Demo is the independent forward/OOS phase. Do not retune during collection.

### Suggested Demo promotion gates to production-candidate review

Freeze before Demo launch; do not modify after results are visible.
Suggested minimums:
- enough calendar coverage to observe multiple market states;
- minimum 30 real fills, preferably 50+;
- exact GC signal parity versus an independent offline reconstruction;
- no unexplained order/state mismatches;
- positive realized Demo EV after all broker costs;
- realized execution degradation materially below the historical break-even cost budget;
- MaxDD consistent with the 0.25% risk envelope;
- no single week/day carrying an excessive share of total PnL;
- no strategy parameter changes during the forward sample.

Production/funded promotion must be a separate decision after Demo evidence.

---

## 10. Do not do next

Do NOT:
- restart LONG discovery from scratch;
- optimize D1 around 0.93/1.00/1.07 again on the same data;
- add LAB016 or LAB017 filters because their PnL looked attractive;
- change E3 to E1 based on historical diagnostics;
- increase risk to 0.50%;
- mix SHORT logic into this LONG forward candidate;
- use future information or fill-time features as a pre-order veto;
- call the system production-ready before forward Demo evidence.

---

## 11. Separate SHORT backlog

Mirror SHORT was weaker and is not part of the current Demo candidate.
If SHORT research resumes later, open a separate lineage. The more promising hypothesis is not a simple mirror but something like:

`SELLER_BREAKDOWN -> RECOVERY_ATTEMPT -> RECOVERY_FAILURE / ACCEPTANCE BELOW -> XAU RETRACE SHORT`

Do not contaminate the frozen LONG forward test with this research.

---

## 12. Canonical status sentence

> **GC->XAU LONG `BUYER_BREAKOUT_LONG_001 + D1.00/E3 corrected + SL1.5ATR + TP3R + 0.25% risk` has passed the frozen historical Demo-readiness audit and is ready for FTMO Demo shadow execution. It is not yet validated for live/funded trading.**

---

## 13. Key repository artifacts

Primary artifacts to consult before continuing:
- `GC_XAU_EXISTING_DATA_FULL_REPLAY_AUDIT_LAB_013H.json/.md`
- `GC_XAU_D1_E3_CORRECTED_ONEACTIVE_DEPENDENCY_LAB_014H.json`
- `GC_XAU_D1_E3_TRADE_FAILURE_DISCRIMINATOR_LAB_015.*`
- `GC_XAU_D075_PREFILL_WARNING_GATE_LAB_016.*`
- `GC_XAU_PREFILL_APPROACH_SHAPE_ACCELERATION_LAB_017.*`
- `GC_XAU_LONG_DEMO_READINESS_LAB_018.json`
- the frozen Demo execution specification created immediately before LAB018

Branch HEAD immediately before this recovery update was:
`291403fdd5f44121b9315f450d59c4c2ad04573d`

END OF RECOVERY STATE.
