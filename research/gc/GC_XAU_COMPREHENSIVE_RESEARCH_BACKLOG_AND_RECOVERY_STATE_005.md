# GC_XAU_COMPREHENSIVE_RESEARCH_BACKLOG_AND_RECOVERY_STATE_005

**Date:** 2026-09-17  
**Repository:** `chepigga/ResearchOS`  
**Branch:** `gc-amp-feed-audit-001`  
**Purpose:** canonical recovery/backlog for the complete current GC futures / COMEX order-flow -> XAUUSD research program.  
**Supersedes as primary recovery checkpoint:** `GC_XAU_LONG_RESEARCH_BACKLOG_AND_RECOVERY_STATE_004.md` for combined LONG+SHORT continuation.  
**Production/funded authorization:** NO.  

---

## 0. READ THIS FIRST — STRICT THREAD SEPARATION

This recovery file belongs only to:

- GC futures / COMEX order flow;
- Rithmic raw GC;
- AMP Futures MT5 / CQG GC;
- GC -> FTMO XAUUSD transfer/execution;
- the dedicated LONG `BUYER_BREAKOUT_LONG_001` lineage;
- the dedicated SHORT `Chris/AEIF POST10` lineage;
- the older frozen AEIF candidate only as a separate preserved reference lineage.

Do **not** mix this work with:

- Crypto Bot / CrowdFade;
- BTC AEIF;
- BTC flow labs;
- old XAU SELL / inverse-breakdown programs;
- unrelated EAs;
- other research branches.

The current objective is **not** to rediscover a universal signal. The current program has:

1. a frozen LONG candidate ready for FTMO Demo shadow;
2. a promising dedicated SHORT Chris/AEIF candidate that has passed historical causal path, walk-forward gate, and GC->XAU transfer on a small ~40-day sample, but now needs a much larger historical replication sample before execution optimization or Demo promotion.

---

# 1. CURRENT PROGRAM STATUS

## LONG lineage

**Canonical status:** `READY_FOR_FTMO_DEMO_SHADOW`

Frozen candidate:

`BUYER_BREAKOUT_LONG_001 + D1.00_E3M_BARE_CORRECTED + SL 1.5 ATR + TP 3R + hard timeout 30m + one active setup + 0.25% risk`

Interpretation:

> Extreme aggressive GC buying successfully breaks recent resistance and closes strongly; do not market-buy XAU. Wait for XAU pullback and use a 1 ATR-deep BUY LIMIT for up to 3 minutes.

This candidate passed exact historical replay, corrected execution semantics, dependency/bootstrap robustness, cost stress, late-period checks, and Demo-readiness gates.

It is **not** yet independent forward/OOS proven and is **not** funded/live authorized.

---

## Dedicated SHORT Chris/AEIF lineage

**Current status:** strong historical candidate, but sample still too small for long-history confidence.

Current mechanism:

`EXTREME BUY EFFORT -> UPPER LOCATION -> WEAK UPWARD RESULT -> BEARISH CONFIRMATION <=2 M1 -> WAIT 10m -> POST10 DISTANCE FROM SEED HIGH >= EXPANDING PRIOR Q50 -> SHORT CONTINUATION`

The critical result is that the POST10 gate does not merely describe the already-finished first 10 minutes. It showed positive **future residual edge after +10m**, survived causal walk-forward gating, and transferred to executable FTMO XAU Bid->Ask semantics.

However current selected sample is only approximately:

- Rithmic OOF: 14 events -> 7 selected;
- AMP OOF: 15 events -> 8 selected;
- exact-common selected XAU transfer events: 6.

Therefore the current next research task is **long-history replication**, not SL/TP optimization.

---

## Older frozen AEIF lineage — preserve separately

Do not confuse this with the dedicated Chris POST10 lineage.

Frozen AEIF:

- LONG = extreme negative delta + aggressive sells near M5 low + failed downside impact;
- SHORT = mirror concept;
- confirmation maximum next 2 M5 bars;
- entry only after confirmation;
- TP3;
- max hold 240m;
- single position.

Historical candidate approximately:

- ~46 trades;
- EV ~+0.666R;
- Sum ~+30.63R;
- PF ~2.33;
- MaxDD ~3.32R;
- max consecutive losses 4.

This remains a **candidate**, not production-proven. Do not retune it unless a separate LAB explicitly reopens that lineage.

---

# 2. CANONICAL REPO / RECOVERY REFERENCES

Repository:

`chepigga/ResearchOS`

Working branch:

`gc-amp-feed-audit-001`

Previous combined LONG recovery checkpoint:

`research/gc/GC_XAU_LONG_RESEARCH_BACKLOG_AND_RECOVERY_STATE_004.md`

Known recovery commit associated with state 004 lineage:

`b618500a640e1b62bdc378f626dff88107337019`

Previous branch HEAD before recovery work:

`291403fdd5f44121b9315f450d59c4c2ad04573d`

This file (`STATE_005`) is now the preferred recovery point for the complete GC/XAU program.

Known unrelated noisy workflow:

`.github/workflows/xau_ifvg_vwap_lab001.yml`

It often fails on ordinary pushes and is unrelated to this GC program. Ignore it when assessing GC LAB status.

---

# 3. DATA / PROVENANCE

## 3.1 Rithmic raw GC

Canonical archive:

`GC_RITHMIC_40D_003_GCZ6.zip`

Available through GitHub release tag:

`GC`

Approximate coverage:

2026-08-03 -> 2026-09-11

Known properties:

- ~3,949,646 trades;
- true Last / trade volume;
- millisecond timestamps;
- explicit aggressor BUY/SELL semantics;
- historical parity feed, not independent OOS against AMP.

AMP_GC_TICK_AUDIT_001 result:

**PASS**

Important conclusion:

Rithmic explicit BUY/SELL is the certified reference semantics for GC order flow.

---

## 3.2 AMP/CQG raw GC

Canonical archive:

`AMP_GC_HISTORY_EXPORTER_001_GCEZ26_20260806_182355__20260915_182355_TICKS.csv.zip`

SHA256:

`81d675597368a9f6c78eee726ed547737366ffd8d8e54aa976bce50111db752b`

Coverage:

2026-08-06 18:24 UTC -> 2026-09-15 18:23 UTC

Raw rows:

`3,737,579`

Dual BUY+SELL rows:

`5,609`

These are excluded from frozen directional aggregation.

Exclusive directional rows:

`3,731,970`

Reconstructed GC M1 bars:

`38,464`

Frozen aggressor semantics:

- BUY = `is_buy=1 && is_sell=0`;
- SELL = `is_sell=1 && is_buy=0`;
- dual BUY+SELL = exclude;
- no invented tick-rule replacement.

A second AMP export exists with timestamp suffix `182904`; use the canonical SHA above unless a LAB explicitly changes the source.

---

## 3.3 GitHub release `GC`

Release URL/tag:

`https://github.com/chepigga/ResearchOS/releases/tag/GC`

Important known assets include:

- `GC_RITHMIC_40D_003_GCZ6.zip`
- `AMP_GC_HISTORY_EXPORTER_001_GCEZ26_20260806_182355__20260915_182355_TICKS.csv.zip`
- related AMP CHUNKS/META files
- Rithmic realtime connectivity EA sources
- `GC_Footprint_AEIF_Research_Backlog.docx`
- `XAUUSD_M1_2026.csv`
- other GC/XAU support files.

Do not assume the release currently contains multi-year true-flow GC history. The known Rithmic/AMP explicit-aggressor archives are still approximately 40 days.

---

## 3.4 FTMO XAU raw ticks — short recent transfer inventory

Broker:

FTMO-Demo / FTMO Global Markets Ltd.

Observed MT5 build during research:

6182.

Frozen XAU recent tick inventory:

- 32 non-empty daily files;
- 2026-08-03 -> 2026-09-15;
- 8,236,717 valid quote ticks;
- first `time_msc = 1785719100005`;
- last `time_msc = 1789516199707`;
- crossed quotes = 0.

Execution semantics:

LONG:

- entry = Ask;
- exit/SL/TP/timeout = Bid.

SHORT:

- entry = Bid;
- exit/SL/TP/timeout = Ask.

Quoted spread is embedded in those mechanics.

---

## 3.5 Long XAU historical inventory

Existing long XAU dataset:

`XAUUSD_M1_20220601_20260723_TICK_NATIVE.csv`

Known audit summary:

- M1 rows: 1,454,538;
- first time: 2022-06-01 01:05:00;
- last time: 2026-07-23 23:49:00;
- selection period historically used elsewhere: 2022-06-01 -> 2024-12-31;
- frozen OOS period in that older XAU research: 2025-01-01 -> 2026-07-23.

Important:

Long XAU history is **not** the current bottleneck. Long GC true order-flow history is the bottleneck for LAB008H.

---

## 3.6 Clock alignment

GC feed is UTC.

Historical FTMO broker offset found:

`+180 minutes`

Best GC/XAU minute-return alignment correlation:

`0.9869174815478382`

Live/Demo implementations must not hard-trust this forever. Normalize/log UTC and disable new orders if time mapping is not verified.

---

# 4. FROZEN COMMON GC FEATURE ENGINEERING

Completed UTC M1 bars only.

Per-bar fields:

- OHLC;
- buy_vol;
- sell_vol;
- volume;
- delta;
- delta_frac.

ATR14:

SMA of true range.

Derived:

`body_atr = (close-open)/ATR14`

`range_atr = (high-low)/ATR14`

`close_pos = (close-low)/(high-low)`

Fallback `close_pos=0.5` if range is zero.

Rolling quantiles:

- prior 240 completed M1 bars;
- shifted by one completed bar;
- no current/future contamination.

Aggressor extremes:

`A_buy = delta_frac >= prior240 Q90 && buy_vol >= prior240 Q75`

`A_sell = delta_frac <= prior240 Q10 && sell_vol >= prior240 Q75`

Recent structure:

`prior20_high = max(high of previous 20 completed M1 bars)`

`prior20_low = min(low of previous 20 completed M1 bars)`

---

# 5. LONG LINEAGE — FROZEN SIGNAL

Signal:

`BUYER_BREAKOUT_LONG_001`

Conditions on completed GC M1:

1. `A_buy == true`;
2. `high >= prior20_high`;
3. bullish body / positive buyer impact;
4. `close_pos >= 0.75`;
5. all information must be completed before XAU execution begins.

Concept:

Aggressive GC buyers show both effort **and successful price acceptance** beyond recent high.

Do not retune the signal before Demo shadow unless a separate preregistered research branch is created.

---

# 6. LONG LINEAGE — FROZEN XAU EXECUTION

Chosen candidate:

`D1.00_E3M_BARE_CORRECTED`

Frozen mechanics:

- signal ledger `signal_time` = left edge of completed signal GC M1;
- information becomes actionable after the signal minute is completed;
- order start = first executable XAU quote / next XAU M1 after completed signal information;
- BUY LIMIT = contemporaneous executable XAU Ask - `1.00 * XAU ATR14(M1)`;
- expiry = 3 minutes from **order_start**;
- unfilled busy state ends at `order_start + 3m`;
- hard timeout = original signal clock + 30m;
- fill historical = Ask touches/crosses limit;
- SL = `1.5 ATR`;
- TP = `3R = 4.5 ATR`;
- exits on Bid;
- one active setup/position;
- historical reference extra cost = 0.05R/fill;
- Demo risk = **0.25% equity/trade**.

Do not use 0.50% for prop-style shadow.

---

# 7. LONG LINEAGE — CORE METRICS

Corrected AMP ALL historical baseline:

- original signals: 279;
- accepted: 237;
- fills: 103;
- EV/original signal: `+0.0863395506R`;
- SumR: `+24.0887346R`;
- observed MaxDD: `8.4R`;
- late EV/signal: `+0.06814492R`.

Dependency robustness:

- bootstrap `P(EV>0) = 96.31%`;
- bootstrap 95% CI slightly crosses zero;
- LOO-week minimum EV = `+0.07497318R`;
- max positive-day share ~16.9%;
- p95 DD @0.25% risk = `3.894%`;
- p95 DD @0.50% risk = `7.788%`.

Historical cost stress:

- 0.10R/fill total cost -> SumR ~+18.94; EV/signal +0.06788077R;
- 0.15R/fill -> SumR ~+13.79; EV/signal +0.04942199R;
- 0.20R/fill diagnostic -> SumR ~+8.64; EV/signal +0.03096321R;
- 0.25R/fill diagnostic -> SumR ~+3.49; EV/signal +0.01250443R;
- historical break-even total cost ~0.28387121R/fill.

---

# 8. LONG LAB HISTORY

## LAB002 — feature/feed parity

PASS.

Normalized AMP/Rithmic M1 feature parity approximately:

- common bars 13,616;
- delta_frac correlation ~0.9927.

---

## LAB003 — bounded LONG discovery

Found `BUYER_BREAKOUT_LONG_001`.

Representative discovery metrics:

- TRAIN N=1115, EV15 +0.0284 ATR;
- VALID N=254, EV +0.0816 ATR;
- LATE N=98, EV +0.0873 ATR.

---

## LAB004 — historical audit

PASS for LONG continuation.

Simple mirror SHORT was materially weaker and was **not** advanced. This does not mean all SHORT mechanisms fail; it only rejected the naive mirror.

---

## LAB005 — GC -> XAU transfer

Historical transfer PASS.

Common signal count around 277; XAU usable ~272.

Representative EV:

- Rithmic +0.10878 ATR;
- AMP exact +0.10260 ATR;
- AMP all +0.08589 ATR.

Not independent OOS.

---

## LAB006 — execution snapshot

D1.00 identified as robust candidate with SL1.5 / TP3R family.

---

## LAB007 — depth sensitivity

D0.93 looked somewhat stronger historically but was not adopted post hoc.

D1.00 remained incumbent.

---

## LAB008 — time split

D1.00 sufficiently stable to continue.

---

## LAB009 — operational historical execution

One-active historical simulation.

Later audit found a technical unfilled busy-state expiry error.

---

## LAB010 — dependency / risk

Conclusion:

0.25% risk candidate acceptable.

0.50% too aggressive for prop-style use.

---

## LAB011 — signal decay

0–1m fills strongest, 1–3m still positive, later fills weaker.

E1 challenger not promoted because late-period E1 EV became negative.

---

## LAB012 — E1 vs E3 forward-shadow prereg

Protocol valid but insufficient fresh sample.

No change to E3.

---

## LAB013 / 013H — realtime parity protocol + historical exact replay

Historical replay PASS.

Key:

- GC bars 38,464 exact;
- signal events 281 exact;
- numerical feature mismatches 0;
- XAU inventory exact;
- +180 min clock reproduced;
- LAB009 reproduced.

Busy-state defect corrected:

unfilled setup expiry must be `order_start + expiry`, not `signal_left_edge + expiry`.

Corrected D1/E3:

- accepted 237;
- fills 103;
- EV/signal +0.08633955R;
- EV/fill +0.2338712R;
- PF ~1.37995;
- MaxDD 8.4R.

Correction slightly improved performance. Edge was not created by bug.

---

## LAB014H — dependency / Monte Carlo

Historical robustness PASS, not OOS.

- N 279;
- accepted 237;
- fills 103;
- SumR +24.0887R;
- bootstrap P positive 96.31%;
- LOO-week min EV +0.074973;
- p95 DD @0.25 = 3.894%;
- p95 DD @0.50 = 7.788%.

---

## LAB015 — static failure discriminator

FAIL.

Primary deployable order-start features:

- OOF AUC ~0.4112;
- veto enrichment not useful;
- PnL degraded.

Do not add static classifier.

Fill-time diagnostics were more interesting (~0.56 AUC) but not causal pre-order information.

---

## LAB016 — D0.75 causal prefill warning

FAIL.

- warnings 94/103;
- median warning lead 5.325s;
- p10 lead 0.647s;
- OOF AUC 0.4895;
- veto enrichment ~1.057.

Economic overlay looked better but predictive gates failed.

Reject.

---

## LAB017 — approach-shape acceleration

FAIL by prereg statistical gates.

- OOF AUC 0.56754 < 0.60 required;
- veto share ~24.49%;
- veto SL rate 75%;
- enrichment 1.225 < 1.25 required.

Historical overlay improved SumR/DD but is **not adopted**.

Do not add LAB017 to Demo candidate.

---

## LAB018 — Demo readiness

PASS.

Status:

`READY_FOR_FTMO_DEMO_SHADOW`

Implementation:

`research/gc/gc_xau_long_demo_readiness_lab_018.py`

Workflow:

`.github/workflows/gc_xau_long_demo_readiness_lab_018.yml`

Run:

`35159704564` SUCCESS.

Result:

`research/gc/GC_XAU_LONG_DEMO_READINESS_LAB_018.json`

Freeze spec:

`research/gc/GC_XAU_LONG_DEMO_READINESS_FREEZE_001.md`

Execution JSON:

`research/gc/GC_XAU_LONG_DEMO_EXECUTION_SPEC_001.json`

All readiness gates passed.

---

# 9. LONG DEMO GOVERNANCE

Forbidden during Demo collection:

- signal retune;
- D1 change;
- E3 change;
- SL/TP change;
- post-hoc gate;
- adding LAB016/LAB017 overlay;
- selecting spread filters from Demo outcome data;
- risk >0.25% without separate approval.

Required logging:

- GC signal UTC;
- full frozen GC feature snapshot;
- XAU order-start timestamp;
- Bid/Ask/ATR/limit;
- submit/ack/cancel;
- fill timestamp/price;
- spread start/fill;
- exit timestamp/price;
- slippage versus research semantics;
- server UTC offset;
- symbol constraints;
- all rejects/errors.

Likely deployment architecture:

AMP MT5 Sensor EA -> `FILE_COMMON` atomic signal -> FTMO MT5 Execution EA polling on timer ~100–250ms, with UTC validation and monotonic signal IDs.

Before final production MQL5 code, reconfirm current broker/prop specifications.

---

# 10. DEDICATED SHORT RESEARCH — WHY IT EXISTS

Naive mirror SHORT from LONG LAB004 was weak.

That only rejected the mirror mechanism.

Dedicated SHORT work therefore explored distinct mechanisms where GC buying fails or seller pressure behaves differently.

The strongest current branch is the Chris/AEIF BUY-failure -> delayed bearish resolution mechanism.

---

# 11. SHORT LAB001 — FAILED RECLAIM

Hypothesis:

`SELLER BREAKDOWN -> RECOVERY ATTEMPT -> FAILED RECLAIM -> SHORT`

Status:

`HISTORICAL_SHORT_MECHANISM_REJECT_NOT_OOS`

Important metrics:

Rithmic:

- TRAIN N15 27, EV15 -0.91272 ATR;
- VALID N15 18, EV15 +0.34830;
- LATE N15 4, EV15 +2.18959;
- FULL N15 49, EV15 -0.19624;
- FULL N30 49, EV30 +0.05490.

AMP:

- VALID N15 16, EV15 +0.81779;
- LATE N15 6, EV15 +2.53193;
- FULL N15 42, EV15 -0.03797;
- FULL N30 41, EV30 +0.50549.

Interpretation:

Exact rule rejected. Strong regime hint: TRAIN poor, later windows much stronger.

No post-hoc threshold rescue.

---

# 12. SHORT LAB002 — SELL PRESSURE ACCEPTANCE CONTINUATION

Frozen mechanism:

`EXTREME SELL PRESSURE -> BREAK PRIOR20 LOW -> ACCEPT BELOW -> NEXT M1 ALSO ACCEPTS BELOW -> SHORT`

Status:

`HISTORICAL_SHORT_ACCEPTANCE_REJECT_NOT_OOS`

Representative metrics:

Rithmic FULL:

- N15 80, EV15 -0.05173;
- N30 79, EV30 +0.35453.

AMP FULL:

- N15 75, EV15 +0.09052;
- N30 75, EV30 +0.14865.

VALID/LATE were weak/negative despite positive AMP POST.

Conclusion:

Reject exact definition.

Order-flow meaning appears regime-dependent.

---

# 13. SHORT LAB003 — CHRIS/AEIF BUY FAILURE

This is the foundation of the current dedicated SHORT lineage.

Mechanism:

`EXTREME BUY EFFORT -> UPPER LOCATION -> WEAK UPWARD RESULT -> BEARISH CONFIRMATION <=2 M1 -> SHORT`

Frozen seed on completed GC M1:

- `A_buy == true`;
- `buy_loc >= prior240 Q75 buy_loc`;
- causal same-aggressor weak-result quantile exists;
- `impact <= prior BUY impact Q20`.

Confirmation, first qualifying t+1 or t+2:

- `close < open`;
- `close < seed_close`;
- `close_pos <= 0.50`.

Entry:

next contiguous M1 open after confirmation.

No intrabar confirmation.

Status:

`HISTORICAL_CHRIS_AEIF_SHORT_REJECT_NOT_OOS`

Why exact LAB003 originally failed:

- Rithmic FULL event count 22 < required 25;
- Rithmic TRAIN 9 < required 10;
- Rithmic FULL 30m EV negative.

Key metrics:

Rithmic FULL:

- N15 22;
- EV15 +0.28854 ATR;
- N30 22;
- EV30 -0.13166 ATR.

AMP FULL:

- N15 23;
- EV15 +0.08749 ATR;
- N30 23;
- EV30 +0.23961 ATR.

Cross-feed VALID was notably consistent and positive.

Conclusion:

Mechanism interesting but sparse/rigid; exact LAB003 not promoted directly.

---

# 14. SHORT LAB003H — HORIZON DECAY

Purpose:

Pure horizon audit of exact frozen LAB003 events.

Frozen horizons:

1m, 3m, 5m, 10m, 15m, 30m.

No signal retune.

Status:

`HISTORICAL_HORIZON_DECAY_AUDIT_NOT_OOS`

Critical finding:

5m is **not** superior.

VALID:

Rithmic:

- 5m -0.117 ATR;
- 10m -0.457;
- 15m +0.299;
- 30m +0.598.

AMP:

- 5m -0.141;
- 10m -0.486;
- 15m +0.277;
- 30m +0.584.

Interpretation:

Chris SHORT is not an immediate 1–5m rejection edge. Resolution often develops over ~10–30m.

Do not select best horizon as a TP/timeout post hoc.

This motivated causal path analysis.

---

# 15. SHORT LAB004 — DELAYED RESOLUTION PATH

Lab name:

`GC_SHORT_CHRIS_AEIF_DELAYED_RESOLUTION_PATH_LAB_004`

Purpose:

Keep LAB003 seed/events frozen and inspect causal path shape at fixed checkpoints before future outcome.

Path features included:

- checkpoint returns;
- MFE/MAE;
- bearish-bar fraction;
- cumulative body;
- price location relative to seed high/close;
- path close-position structure.

Key finding:

By +10m, winners and losers separate strongly.

Several +10m features showed very high historical AUC, including 1.00 on VALID for some definitions.

Critical warning:

Because +10m path overlaps with original +15/+30 terminal labels, part of the apparent predictiveness could be mechanical.

Therefore LAB004 was **not** treated as sufficient edge proof.

Next step correctly became a residual target beginning **after** +10m.

---

# 16. SHORT LAB005 — POST10 RESIDUAL EDGE

Lab:

`GC_SHORT_CHRIS_AEIF_POST10_RESIDUAL_EDGE_LAB_005`

Goal:

Ask whether information known by +10m predicts additional bearish movement **after** +10m.

Targets:

- +10 -> +15;
- +10 -> +20;
- +10 -> +30.

Important surviving feature family:

`cp10_dist_seed_high`

Interpretation:

How far price has displaced downward from the original seed high by +10m.

Key results:

+10 -> +20:

- Rithmic VALID AUC ~0.708;
- AMP VALID AUC ~0.708;
- Rithmic FULL ~0.683;
- AMP FULL ~0.727.

+10 -> +30:

- VALID both feeds ~0.708;
- Rithmic FULL ~0.615;
- AMP FULL ~0.608.

Conclusion:

LAB004 was not pure target overlap illusion. A real residual relationship remained after checkpoint.

Only `cp10_dist_seed_high` was advanced.

---

# 17. SHORT LAB006 — POST10 DISTANCE WALK-FORWARD GATE

Lab:

`GC_SHORT_CHRIS_AEIF_POST10_DISTANCE_GATE_WALKFORWARD_LAB_006`

Frozen feature:

`cp10_dist_seed_high`

Threshold rule:

After minimum 8 eligible past events, threshold at each new event = expanding median Q50 of **prior feature values only**.

Selected iff current feature >= prior-history Q50.

No target-based threshold fit.

No quantile sweep.

Primary residual:

`+10 -> +20m`

Secondary:

`+10 -> +30m`

Status:

`HISTORICAL_POST10_DISTANCE_GATE_WALKFORWARD_PASS_NOT_OOS`

Rithmic primary:

- OOF N 14;
- selected 7;
- selection share 50%;
- baseline EV +0.80379 ATR;
- selected EV +2.02996 ATR;
- rejected EV -0.42238 ATR;
- uplift +1.22617 ATR;
- selected WR 85.7%.

AMP primary:

- OOF N 15;
- selected 8;
- selection share 53.3%;
- baseline EV +1.12337 ATR;
- selected EV +2.24587 ATR;
- rejected EV -0.15949 ATR;
- uplift +1.12250 ATR;
- selected WR 87.5%.

Secondary +10 -> +30:

Rithmic selected EV +2.70232 ATR, WR 85.7%.

AMP selected EV +2.39923 ATR, WR 75%.

Interpretation:

This is the first strong causal walk-forward separation in the dedicated SHORT branch.

But N is still tiny.

---

# 18. SHORT LAB007 — GC -> XAU POST10 TRANSFER

Lab:

`GC_XAU_SHORT_CHRIS_POST10_TRANSFER_LAB_007`

Frozen GC logic:

LAB003 Chris seed + bearish confirmation + LAB006 POST10 Q50 gate.

No GC retuning.

Execution timing:

Decision becomes known only after completion of +10m checkpoint.

XAU SHORT entry:

first executable XAU tick after checkpoint.

SELL enters at Bid.

Exit mark at Ask.

Spread therefore embedded honestly.

Clock calibration reproduced:

- +180m;
- correlation ~0.986917.

Primary 10m-after-checkpoint XAU result:

Rithmic selected:

- N 7;
- EV +10.021 bps;
- +2.052 ATR;
- WR 71.4%.

AMP selected:

- N 8;
- EV +11.449 bps;
- +2.205 ATR;
- WR 87.5%.

Exact-common selected:

- N 6;
- EV +11.740 bps;
- WR 83.3%.

Rejected primary:

Rithmic:

- -3.536 bps;
- -0.748 ATR;
- WR 28.6%.

AMP:

- -3.137 bps;
- -0.574 ATR;
- WR 42.9%.

20m-after-checkpoint:

Rithmic selected:

- +12.497 bps;
- +2.707 ATR;
- WR 85.7%.

AMP selected:

- +12.359 bps;
- +2.314 ATR;
- WR 75.0%.

30m diagnostic remained strong historically (~+18.9 to +20.1 bps selected).

All frozen LAB007 transfer gates passed.

Conclusion:

GC POST10 gate does not merely predict GC; it historically separates future XAU bearish continuation from rejected cases.

Critical limitation:

selected N only 7–8. This is not sufficient for Demo readiness.

Do **not** optimize XAU SL/TP yet.

---

# 19. LAB008H — LONG-HISTORY REPLICATION

Lab:

`GC_SHORT_CHRIS_LONG_HISTORY_REPLICATION_LAB_008H`

Prereg file:

`research/gc/GC_SHORT_CHRIS_LONG_HISTORY_REPLICATION_LAB_008H_PREREG.md`

Prereg commit:

`78957f62cf8be2b7e540dd145dbd84084477cf6a`

Important rule:

Frozen prereg must not be changed to rescue outcome.

Frozen Chris signal remains LAB003.

Frozen POST10 gate remains LAB006.

No threshold sweep.

No confirmation change.

No horizon change.

No feature-family change.

No quantile change.

---

## 19.1 Original intended long-history source

Long-history candidate was Massive Futures trades + quotes, but only after aggressor-inference parity versus explicit Rithmic.

Frozen Massive aggressor inference in prereg:

- latest quote at or before trade;
- BUY if trade >= prevailing ask;
- SELL if trade <= prevailing bid;
- inside-spread = exclude;
- stale/invalid/crossed quote = exclude;
- no tick-rule fallback.

Stage A parity gates:

1. common M1 >= 10,000;
2. delta_frac corr >= 0.85;
3. delta sign agreement >= 0.80;
4. A_buy Jaccard >= 0.40;
5. Chris seed timestamp Jaccard >= 0.35;
6. no quote lookahead.

Important development:

Massive plugin connected successfully, but the current plan returned `NOT_ENTITLED` for historical futures Trades and Quotes. Historical minute aggregates are accessible, but OHLCV alone cannot substitute true aggressor flow.

Therefore Massive is currently not usable for Stage A without higher data entitlement.

This is a data-access issue, not a strategy failure.

---

## 19.2 Stage B long-history target

Target window:

2022-06-01 -> 2026-07-23

Reason:

Long XAU history already exists over this window.

Contract stitching prereg:

For each session choose the GC contract with highest total volume in the **immediately preceding completed session** among eligible active single contracts.

No future-session volume.

At each contract switch:

- reset rolling state;
- require at least 240 new M1 bars before signal eligibility.

This prevents basis/roll jumps contaminating ATR and quantiles.

---

## 19.3 Frozen long-history PASS gates

All must pass:

1. usable stitched coverage >=24 months;
2. frozen Chris events >=75;
3. OOF POST10 events after warm-up >=50;
4. selected >=25;
5. selected primary EV +10->20 >0;
6. selected primary EV exceeds all-OOF baseline by >=+0.10 ATR;
7. selected primary EV > rejected primary EV;
8. selected primary WR >=55%;
9. selected secondary +10->30 EV >=0;
10. at least 3 calendar years with >=5 selected events each have positive primary EV;
11. no single year contributes >50% of selected events.

---

# 20. LAB008H — 40-DAY SUFFICIENCY AUDIT

The user requested that LAB008H first be evaluated on the available ~40-day certified explicit-aggressor data.

This does **not** become a new independent long-history sample. It is a sufficiency assessment using the already frozen Rithmic/AMP period.

Known current counts from frozen lineage:

Chris events:

- Rithmic 22;
- AMP 23.

OOF POST10 after warm-up:

- Rithmic 14;
- AMP 15.

Selected:

- Rithmic 7;
- AMP 8.

Primary selected EV:

- Rithmic +2.02996 ATR;
- AMP +2.24587 ATR.

Rejected EV:

- Rithmic -0.42238 ATR;
- AMP -0.15949 ATR.

Selected WR:

- Rithmic 85.7%;
- AMP 87.5%.

Conclusion:

**Effect size is strong, sample size is insufficient.**

The 40-day period cannot satisfy the prereg long-history gates of 75 Chris events / 50 OOF / 25 selected / multi-year consistency.

Therefore longer AMP true-flow history is needed.

40-day sufficiency audit commit recorded during recovery work:

`9a35fe3a5fd68c47bda1c6ff886c990eca2625ae`

---

# 21. NEXT DATA ACQUISITION — AMP MT5

The user can export more history directly from the AMP MT5 terminal.

Prepared script:

`AMP_GC_LONG_HISTORY_EXPORTER_002.mq5`

Purpose:

Export historical GC MqlTick records preserving the exact semantics needed for frozen delta.

Required fields:

- `time_msc`;
- time text;
- Bid;
- Ask;
- Last;
- `volume`;
- `volume_real`;
- raw `flags`;
- `is_buy` from `TICK_FLAG_BUY`;
- `is_sell` from `TICK_FLAG_SELL`;
- `has_last`;
- `has_volume`.

Recommended mode:

- `COPY_TICKS_ALL`;
- one-day chunks initially;
- do **not** discard raw non-trade ticks during collection;
- preserve dual BUY+SELL rows in raw export; frozen loader excludes them later.

Important:

Do not assume one symbol such as `GCEZ26` provides a valid continuous multi-year front-month series.

Expired GC contracts may need to be exported separately and then stitched causally using the prereg roll rule.

Likely future task after the first longer export:

build a multi-contract AMP exporter / contract-chain inventory for expired GC symbols and then stitch with preceding-session volume only.

Do not hand-pick contracts after seeing strategy outcomes.

---

# 22. WHAT TO DO WHEN NEW AMP FILES ARRIVE

Exact recovery procedure:

1. Do not change LAB008H prereg.
2. Audit each raw file:
   - exact symbol;
   - first/last time_msc;
   - row count;
   - BUY-only count;
   - SELL-only count;
   - dual count;
   - neither count;
   - Last/Volume validity;
   - timestamp monotonicity;
   - duplicate behavior.
3. Reconstruct M1 using the same frozen AMP semantics.
4. On overlap with existing AMP/Rithmic, run parity checks before using earlier history.
5. Build causal front-contract chain if multiple symbols are needed.
6. Reset rolling state at every contract switch and warm up 240 new M1 bars.
7. Run exact LAB003 Chris event builder unchanged.
8. Build +10m path state unchanged.
9. Run LAB006 expanding prior-event Q50 gate unchanged.
10. Evaluate LAB008H frozen long-history gates.
11. Report per-year and aggregate counts/EV/WR.
12. Do not inspect alternative thresholds if exact LAB008H fails.

If LAB008H passes:

advance to a separately preregistered long-history GC->XAU transfer replication, then only afterwards execution geometry.

If LAB008H fails:

reject this exact historical generalization. Do not rescue it by changing Q50, 10m checkpoint, seed thresholds, or excluding bad years.

---

# 23. WHAT NOT TO DO NEXT

Do NOT:

- optimize XAU SL/TP for Chris yet;
- pick a 15m/20m/30m timeout from the same 40-day sample;
- change the +10m checkpoint;
- sweep Q40/Q60/Q70 instead of Q50;
- change minimum history 8 because of results;
- retune buy effort Q90/Q75;
- change weak-impact Q20;
- alter bearish confirmation;
- use Massive OHLCV as a fake delta proxy;
- infer BUY/SELL from candle direction;
- combine LONG and SHORT feature searches into one optimizer;
- claim independent OOS from Rithmic vs AMP because they overlap historically;
- claim Demo/live readiness for Chris SHORT;
- increase prop risk while sample is this small.

---

# 24. NEXT RESEARCH ORDER

Current correct order of work:

### A. Acquire longer AMP GC true-flow history

Primary immediate task.

### B. Complete `GC_SHORT_CHRIS_LONG_HISTORY_REPLICATION_LAB_008H`

No retune.

### C. If LAB008H passes, long-history GC->XAU SHORT transfer replication

Use existing long XAU inventory where timestamps overlap.

### D. Only then execution geometry

Possible future lab:

`GC_XAU_SHORT_CHRIS_EXECUTION_GEOMETRY_LAB_009` or next free number.

Questions to evaluate only after long-history validation:

- market at checkpoint vs retracement limit;
- natural MAE/MFE;
- robust SL geometry;
- TP / timeout family;
- full spread/cost stress;
- one-position / cooldown rules.

### E. Dependency / bootstrap / Monte Carlo

Before Demo promotion.

### F. Demo readiness prereg + shadow

Only if the expanded evidence supports it.

---

# 25. PROP-RISK GOVERNANCE

Research account target context:

~100K.

Preferred risk:

0.25% per trade during early validation / shadow.

0.50% only after separate evidence and approval; do not default to it.

Hard principles:

- always hard SL;
- TP must be >=1.5x stop in any final trade design;
- prefer confirmed entries / limits when evidence supports them;
- no martingale;
- no aggressive grid;
- no unbounded averaging;
- protect daily DD <=4–5%;
- protect overall DD <=8–12% depending on prop rules.

---

# 26. FINAL EA / BROKER-SPEC REQUIREMENT

Before any final Demo/production EA code, reconfirm current broker/prop specs. Known historical assumptions are not enough.

Need:

- broker / prop exact name;
- account type;
- exact XAU symbol;
- digits / point;
- tick size / tick value;
- contract size;
- min/max lot / volume step;
- stop level;
- freeze level;
- spread distribution;
- commission;
- leverage;
- swaps;
- pending-order constraints;
- EA allowed;
- hedging rules;
- news trading rules;
- max orders / other challenge restrictions;
- VPS / latency / slippage conditions;
- current challenge/rules URL.

Do not generate final production EA without reconfirming these current values.

---

# 27. CURRENT RESEARCH CLAIMS — SAFE WORDING

## LONG

Use:

> GC->XAU LONG `BUYER_BREAKOUT_LONG_001 + D1.00/E3 corrected + SL1.5ATR + TP3R + 0.25% risk` has passed the frozen historical Demo-readiness audit and is ready for FTMO Demo shadow execution. It is not yet validated for live/funded trading.

## SHORT Chris

Use:

> GC Chris/AEIF POST10 SHORT has shown a strong historical causal walk-forward separation and positive FTMO XAU transfer on the available ~40-day explicit-aggressor sample, but selected N is only 7–8 per feed. The correct next step is frozen long-history replication on more AMP/Rithmic-quality GC true-flow data; it is not Demo/live ready.

Do not call SHORT production-proven.

---

# 28. CURRENT OPEN QUESTIONS

LONG:

- true forward Demo EV;
- real FTMO pending-order fill/slippage;
- live cancel/modify latency;
- DST/time mapping robustness;
- future GC roll behavior;
- forward DD distribution.

SHORT:

- does Chris POST10 survive 6–24+ months / multiple years?
- how many selected trades/year is realistic?
- does selected > rejected separation survive different GC contracts/regimes?
- does long-history XAU transfer remain positive?
- what is robust execution geometry only after signal validation?
- how correlated will LONG and SHORT PnL be?

Portfolio:

- eventual combined daily/overall DD;
- overlapping exposure handling;
- whether LONG/SHORT modules should share one-active state or independent risk caps.

Do not solve portfolio questions before both lineages have sufficient validation.

---

# 29. IMPORTANT COMMITS / ARTIFACTS

Known key references:

LONG LAB017 prereg commit:

`676b952b644031f0ac45a1ebf5b09c108af40bec`

LONG LAB017 implementation:

`e05013a0f99e01859ffd331c23557b4982d678d6`

LONG LAB017 workflow:

`b25f0ee851272f029d8ffa999d5e3621ce339b5c`

LONG LAB017 workflow run:

`35159592333` SUCCESS.

LONG Demo readiness freeze commit:

`aca675f32e5387086089112c640422b0beb484a8`

LONG Demo execution spec commit:

`689881f11791b379a1e46c667c6ef21052f34708`

LONG LAB018 implementation commit:

`bfe3a1526d0481ae161bfd5e9efbe8aaab4ab580`

LONG LAB018 workflow commit:

`ac5d1e965330b8e0db0a94285f9738ceb4eb3634`

LONG LAB018 run:

`35159704564` SUCCESS.

SHORT LAB003 prereg:

`90b50478bfa14845f2deb2dd68c80ef2b42013ee`

SHORT LAB003 implementation:

`51b6296231a705bc9f8dceed456f7d78efe51846`

SHORT LAB003H prereg:

`86ada8b1103a68e8263007c67b346cc5464e493d`

SHORT LAB003H implementation:

`8f931fb31894d0c327dda1e44632e8f9015eed43`

SHORT LAB003H workflow:

`0b5ce23cb431a4ed712ecc1099dad3df971d70c7`

SHORT LAB003H run:

`35207729831` SUCCESS.

LAB008H prereg commit:

`78957f62cf8be2b7e540dd145dbd84084477cf6a`

Initial LAB008H data-access status commit:

`9f2673a3088b342479f1e9d9ff2ac44c8e133b1e`

40-day sufficiency audit commit:

`9a35fe3a5fd68c47bda1c6ff886c990eca2625ae`

---

# 30. RECOVERY CHECKLIST FOR A NEW CHAT / SESSION

If this research is resumed in a fresh conversation:

1. Read this file first.
2. Stay only in GC/COMEX/AMP/Rithmic/GC->XAU scope.
3. Do not mix crypto/BTC/CrowdFade.
4. Treat LONG as frozen Demo-ready baseline.
5. Treat Chris SHORT as promising but sample-limited.
6. Do not retune LAB003/LAB006 rules.
7. Check whether new AMP GC history has been exported.
8. If new raw files exist, audit them before strategy evaluation.
9. Continue LAB008H exactly from prereg.
10. Do not optimize XAU SHORT exits before long-history signal replication.
11. Preserve 0.25% prop-style risk assumption unless a later risk LAB explicitly changes it.
12. Any new rule must be preregistered before looking at its outcome.

---

# 31. ONE-LINE RECOVERY STATE

**LONG:** frozen and ready for FTMO Demo shadow at 0.25% risk.  
**SHORT:** Chris/AEIF POST10 Q50 gate historically strong and XAU-transfer positive, but only 7–8 selected events on ~40 days; obtain longer AMP explicit-aggressor GC history and complete frozen LAB008H before any execution optimization or Demo claim.
