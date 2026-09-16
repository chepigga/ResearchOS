# GC→XAU ORDER-FLOW RESEARCH — BACKLOG & FULL RECOVERY STATE 003

_Last updated: 2026-09-16 after LAB011._

This file is intentionally redundant. Its purpose is to let the research process be restored after a session crash, context loss, model reset, or handoff to another researcher without reconstructing the lineage from chat history.

---

## 0. 60-second restore summary

Current project is **NOT** the old M5 AEIF reconstruction and **NOT** a crypto/CrowdFade branch.

Current working lineage:

`ATAS/dxFeed GC M1 AEIF discovery → longer raw-feed falsification → bounded GC M1 order-flow search → BUYER_BREAKOUT_LONG historical candidate → GC→FTMO XAU transfer → XAU limit-entry geometry → operational/Monte-Carlo robustness → signal-decay map.`

Current practical hypothesis:

> A completed GC M1 bar showing extreme buyer aggression plus local upside breakout identifies a short-lived bullish state. Do **not** buy XAU at market immediately. Use the GC event as sensor, then place a short-lived XAU buy-limit roughly one XAU M1 ATR below the contemporaneous XAU Ask.

Current historical execution candidate:

- GC signal: `BUYER_BREAKOUT_LONG_001`
- GC timeframe: M1
- XAU instrument: FTMO-Demo XAUUSD raw Bid/Ask ticks
- XAU volatility scale currently used: ATR14(M1)
- limit depth: `1.00 × XAU ATR14(M1)` below market-reference Ask
- historical operational candidate expiry: 3 minutes (`D1.00_E3M`)
- post-discovery decay challenger: 1 minute (`D1.00_E1M`), **not promoted**, forward-only challenger
- SL: `1.50 × XAU ATR14(M1)` from fill
- TP: `3R` = `4.50 × ATR14(M1)` from fill
- nominal R:R = 1:3
- one active setup at a time
- historical robustness cost stress: +0.05R adverse cost per filled trade, on top of real FTMO quoted spread already embedded through Ask-entry/Bid-exit
- recommended research risk if converted to shadow/equity simulation: 0.25%/trade, not 0.5%

Current evidence status:

- Original AEIF reversal: **interesting historical effect but not robustly replicated on longer causal history**.
- GC buyer-breakout LONG state: **strong historical candidate**, not independent OOS.
- GC→FTMO XAU information transfer: **historically present but weak with market-entry/fixed-time exit**.
- XAU short-lived limit retrace execution: **historically positive**, strongest fills occur very early.
- Production/live edge: **NOT yet certified**. Next requirement is untouched forward shadow/OOS.

Never resume by retuning the Aug–Sep historical sample.

---

## 1. Repository / branch / canonical files

Repository:

`chepigga/ResearchOS`

Working branch:

`gc-amp-feed-audit-001`

Important canonical status file preceding this recovery snapshot:

`research/gc/GC_ORDERFLOW_CANONICAL_LINEAGE_AND_EDGE_STATUS_002.md`

This file extends that status through LAB011 and should be read first after any context loss.

Important scripts/reports already committed:

- `research/gc/GC_M1_AEIF_HISTORICAL_EDGE_REPLICATION_001.md`
- `research/gc/GC_M1_AEIF_CAUSAL_EDGE_AUDIT_002.md`
- `research/gc/GC_M1_ORDERFLOW_EDGE_DISCOVERY_003.md`
- `research/gc/gc_m1_orderflow_edge_discovery_003.py`
- `research/gc/GC_M1_BUYER_BREAKOUT_LONG_AUDIT_004.md`
- `research/gc/gc_m1_buyer_breakout_long_audit_004.py`
- `research/gc/GC_M1_BUYER_BREAKOUT_INCREMENTAL_ORDERFLOW_AUDIT_005.md`
- `research/gc/GC_BUYER_BREAKOUT_LONG_TO_FTMO_XAU_TRANSFER_LAB_006.md`
- `research/gc/gc_buyer_breakout_long_to_ftmo_xau_transfer_lab_006.py`
- `research/gc/GC_BUYER_BREAKOUT_LONG_TO_FTMO_XAU_TRANSFER_LAB_006_EVENTS.csv`
- `research/gc/GC_XAU_POST_SIGNAL_PATH_GEOMETRY_LAB_007.md`
- `research/gc/gc_xau_post_signal_path_geometry_lab_007.py`
- `research/gc/GC_XAU_POST_SIGNAL_PATH_GEOMETRY_LAB_007_CONFIGS.csv`
- `research/gc/GC_XAU_LIMIT_ORDER_DEPTH_EXPIRY_STABILITY_LAB_008.md`
- `research/gc/GC_XAU_LIMIT_ORDER_OPERATIONAL_ROBUSTNESS_LAB_009.md`
- `research/gc/GC_XAU_LIMIT_D1_E3_DEPENDENCY_MONTE_CARLO_LAB_010.md`
- `research/gc/GC_XAU_LIMIT_D1_E3_DEPENDENCY_MONTE_CARLO_LAB_010.json`
- `research/gc/GC_XAU_LIMIT_SIGNAL_DECAY_CURVE_LAB_011.md`
- `research/gc/GC_XAU_LIMIT_SIGNAL_DECAY_CURVE_LAB_011.json`

Relevant GitHub Actions runs:

- LAB006 transfer: run `35133277498`
- LAB007 path geometry: run `35136596813`
- LAB008 depth/expiry stability: run `35137705894`
- LAB009 operational robustness: run `35138256119`
- LAB010 dependency/Monte Carlo: run `35138455480`
- LAB011 signal decay: run `35140472627`

Known noisy unrelated workflow:

`.github/workflows/xau_ifvg_vwap_lab001.yml`

It often fails on pushes to this branch. Its failure is unrelated to this GC→XAU research and must not be mistaken for a failure of the GC workflow being run.

---

## 2. Correct historical lineage — do not rewrite this

### 2.1 Original positive AEIF source

The first positive AEIF discovery was **GC M1 footprint exported from ATAS/dxFeed**.

It was **not** a Rithmic discovery and **not** an FTMO/XAU discovery.

Primary artifact:

`LAB001_GC_CAUSAL_EFFORT_RESULT_REPORT.md`

Original source window:

- 2026-09-06 22:00 → 2026-09-11 12:46
- 6,244 M1 bars
- 127,842 footprint price-level rows
- one anomalous bar at 2026-09-11 06:22 excluded

Original AEIF stages:

**A — extreme aggression**

- completed M1 bar
- causal prior rolling 240 M1 bars
- delta-fraction Q10/Q90
- aggressor-side total volume >= prior Q75

**B — effort/result failure**

- among prior same-side A events
- directional price result = body / ATR14
- current impact in weakest 20% causal Q20 of prior same-side A events
- this was **not** a fixed `0.15 ATR` rule
- this was **not** the later price-location concentration selector

**D — opposite response**

- within next <=2 M1 bars
- opposite delta plus reversal-direction price response
- exact original production D code should be rechecked if D lineage is ever revived

Original ATAS/dxFeed reference result:

- A: ~356 events; 5m +0.137 ATR; 15m +0.257 ATR
- B: N=77; 5m +0.407 ATR; 15m +0.561 ATR
- D: N=46; 5m +0.399 ATR; 15m +0.646 ATR; 15m WR ~63%

Canonical name:

`GC M1 AEIF / ATAS-dxFeed historical result`

### 2.2 M5 warning

Longer M5 bar-level replication was negative:

`LAB003_GC_BAR_LEVEL_EFFORT_RESULT_LONG_SHORT_REPLICATION_REPORT.md`

B result:

- 5m `-0.062 ATR`
- 15m `-0.064 ATR`

Therefore:

- M5 reconstruction is **not** proof of original AEIF.
- later M5 selector using location concentration + fixed impact <=0.15 ATR is only a reconstructed diagnostic control.
- do not call that selector “canonical AEIF”.

Correct lineage:

`Chris idea → ATAS/dxFeed GC M1 footprint → positive M1 AEIF discovery → later reconstructions → later GC→XAU transfer work → Rithmic/AMP raw feeds for replication/live sensor work.`

---

## 3. Raw data inventory and provenance

### 3.1 Rithmic GC raw archive

GitHub Release asset:

`GC_RITHMIC_40D_003_GCZ6.zip`

Release URL:

`https://github.com/chepigga/ResearchOS/releases/download/GC/GC_RITHMIC_40D_003_GCZ6.zip`

Integrity:

- asset id: `566393712`
- size: `35,287,562` bytes
- SHA256: `b12465a783f36aac41b82a9f2a5c4e74bd2dcf7024ffc3636e8c41a8fd01e803`

Contents / coverage:

- 40 gzip CSVs + manifest
- ~2026-08-03 → 2026-09-11
- 3,949,646 raw trades
- explicit aggressor BUY/SELL
- M1 replication coverage in LAB001 replication: 2026-08-03 00:00 UTC → 2026-09-11 20:59 UTC
- 41,102 reconstructed M1 bars

Use Rithmic as historical parity/robustness feed. Do **not** treat it as independent market OOS relative to AMP; both observe essentially the same GC market interval.

### 3.2 AMP/CQG GC raw archive

GitHub Release asset:

`AMP_GC_HISTORY_EXPORTER_001_GCEZ26_20260806_182355__20260915_182355_TICKS.csv.zip`

Release URL used in research code:

`https://github.com/chepigga/ResearchOS/releases/download/GC/AMP_GC_HISTORY_EXPORTER_001_GCEZ26_20260806_182355__20260915_182355_TICKS.csv.zip`

SHA256 frozen in `gc_m1_orderflow_edge_discovery_003.py`:

`81d675597368a9f6c78eee726ed547737366ffd8d8e54aa976bce50111db752b`

Contract / symbol:

`GCEZ26`

Feed characteristics:

- real Last
- volume / volume_real
- millisecond timestamps (`time_msc`)
- explicit `is_buy` / `is_sell` directional flags
- directional semantics in frozen loader:
  - `BUY` only if `is_buy=1 AND is_sell=0`
  - `SELL` only if `is_sell=1 AND is_buy=0`
  - simultaneous BUY+SELL is `EXCLUDE`
- CopyTicks + realtime audit passed historically

M1 replication coverage:

- 2026-08-06 18:24 UTC → 2026-09-15 18:23 UTC
- 38,464 reconstructed M1 bars

AMP is the intended practical realtime GC sensor feed for forward work.

### 3.3 FTMO XAUUSD raw tick archive for LAB006–011

Source was exported from FTMO MT5 using raw-tick exporter. Metadata checked in Drive before use.

Environment:

- account server: `FTMO-Demo`
- company: `FTMO Global Markets Ltd`
- terminal build observed: `6182`
- tick scope: `COPY_TICKS_ALL`

Coverage used:

- daily raw CSVs from 2026-08-03 through 2026-09-15
- 32 non-empty trading-day files
- quote-valid ticks: `8,236,717`
- first `time_msc`: `1785719100005`
- last `time_msc`: `1789516199707`

Fields required / used:

- `time_msc`
- `bid`
- `ask`
- quote-valid flag if present
- source exports also contain spread / mid fields, but simulation uses actual Bid/Ask directly

Execution convention:

- LONG entry uses actual FTMO `Ask`
- LONG path / TP / SL / timeout uses actual FTMO `Bid`
- therefore quoted spread is naturally embedded
- commission and discretionary slippage are not naturally embedded; later LABs stress-tested extra cost in R units

Data exporter retained in File Library / project lineage:

`XAU_RawTickExporter_v001.mq5`

If data must be recollected, preserve `time_msc`; do not align feeds by formatted time strings.

### 3.4 Older XAU datasets — do not confuse with current certified transfer sample

Older file:

`XAUUSD_M1_2026.csv`

It was useful historically for old GC→XAU transfer fingerprinting, but provenance was not reliably established as FTMO and coverage ended around 2026-09-08. Do not use it as certified FTMO evidence for the current buyer-breakout branch.

There is also an older audited FTMO-Demo M1 Bid/Ask dataset:

`XAUUSD_M1_20220601_20260723_TICK_NATIVE.csv`

SHA256:

`db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b`

Coverage:

- 2022-06-01 → 2026-07-23
- 1,454,538 M1 Bid/Ask rows
- tick-native aggregated M1, not raw every tick

Useful for generic FTMO execution conventions, but it does **not** overlap the current Aug–Sep GC signals.

---

## 4. Exact GC M1 feature engineering used by the current branch

Canonical implementation is in:

`research/gc/gc_m1_orderflow_edge_discovery_003.py`

### 4.1 Tick filtering

Keep rows where:

- valid timestamp
- `price > 0`
- `volume > 0`
- aggressor in `{BUY, SELL}`

Sort by timestamp.

Aggregate to UTC M1 bar:

`bar_ms = floor(time_ms / 60000) * 60000`

### 4.2 M1 OHLC / volume / delta

Per M1:

- `open` = first trade price
- `high` = max trade price
- `low` = min trade price
- `close` = last trade price
- `buy_vol` = aggressive BUY volume
- `sell_vol` = aggressive SELL volume
- `volume = buy_vol + sell_vol`
- `delta = buy_vol - sell_vol`
- `delta_frac = delta / volume`

### 4.3 ATR and bar-shape features

True range:

`TR = max(high-low, abs(high-prev_close), abs(low-prev_close))`

ATR:

`ATR14 = SMA(TR, 14)`

Other features:

- `body_atr = (close-open)/ATR14`
- `range_atr = (high-low)/ATR14`
- `close_pos = (close-low)/(high-low)`, fallback 0.5 if zero-range

### 4.4 Causal rolling references

All quantile references are shifted by one bar before rolling. Current bar is never included in its own threshold.

Over prior 240 completed M1 bars:

- delta Q10
- delta Q90
- buy-volume Q75
- sell-volume Q75
- additional location/range quantiles exist in discovery code but are not part of current BUYER_BREAKOUT_LONG rule

Local breakout reference:

- `prior20_high = max(high of prior 20 completed M1 bars)`
- `prior20_low = min(low of prior 20 completed M1 bars)`

### 4.5 Extreme aggression state A

BUY state:

`a_buy = delta_frac >= prior240_Q90(delta_frac) AND buy_vol >= prior240_Q75(buy_vol)`

SELL state mirror:

`a_sell = delta_frac <= prior240_Q10(delta_frac) AND sell_vol >= prior240_Q75(sell_vol)`

Aggressor label:

- BUY if `a_buy`
- SELL if `a_sell`

Directional impact:

- BUY: `impact = body_atr`
- SELL: `impact = -body_atr`

Historical impact Q20/Q80 among prior same-side A events require at least 15 prior same-side A events before quantile availability.

---

## 5. Current frozen GC signal: BUYER_BREAKOUT_LONG_001

This is the branch that survived historical investigation best.

On a **completed GC M1 bar** require all of:

1. extreme buyer aggression A:
   - `delta_frac >= causal prior240 Q90`
   - `buy_vol >= causal prior240 Q75`
2. bullish bar: `close > open`
3. positive buyer impact (`impact > 0`)
4. upside local breakout: `high >= prior20_high`
5. strong close location: `close_pos >= 0.75`

Historical GC-only causal entry used for characterization:

- exact next clock-contiguous M1 open
- LONG

For GC→XAU transfer, GC next-open price itself is not traded; the completed GC signal timestamp is the information event that launches the XAU execution logic.

Mirror seller-breakout SHORT was not promoted because the directional asymmetry was poor, especially on Rithmic.

Do not invent a symmetric SHORT version in live code without a separate research lineage.

---

## 6. Research chronology and what each LAB established

### LAB001 — M1 AEIF raw-feed replication

Report:

`GC_M1_AEIF_HISTORICAL_EDGE_REPLICATION_001.md`

Rithmic full:

- A N~2494: 5m +0.017 ATR, 15m +0.060
- B N438: 5m +0.054, 15m +0.152
- D N238: 5m +0.534, 15m +0.795

AMP full:

- A N~2373: 5m +0.018, 15m +0.080
- B N441: 5m +0.022, 15m +0.094
- D N243: 5m +0.529, 15m +0.682

But raw D initially measured from the B event clock and included confirmation movement. That inflation was corrected in causal audit.

### LAB002 — causal next-open audit

Report:

`GC_M1_AEIF_CAUSAL_EDGE_AUDIT_002.md`

Key conclusion:

Original AEIF reversal is not robustly established on longer history.

Pre-discovery B:

- Rithmic N383: 5m +0.042, 15m +0.139; CI crosses zero
- AMP N341: 5m -0.024, 15m +0.115; CI crosses zero

D after confirmation:

- Rithmic PRE N207: 5m +0.066, 15m +0.122; CI crosses zero
- AMP PRE N186: 5m +0.023, 15m +0.110; CI crosses zero

AMP post-discovery D was negative.

Status:

`AEIF reversal = preserve lineage, do not call stable production edge.`

### LAB003 — bounded M1 order-flow discovery

Report:

`GC_M1_ORDERFLOW_EDGE_DISCOVERY_003.md`

Candidates tested:

- A_REV
- FAIL_Q20_REV
- OPPOSITE_BODY_REV
- REJECTION_REV
- SWEEP_REJECT_REV
- LOC_OPPOSITE_BODY_REV
- LOC_FAIL_Q20_REV
- A_CONT
- IMPACT_Q80_CONT
- BREAKOUT_CONT
- RANGE_IMPACT_CONT

Strict symmetric gates: **no candidate passed**.

Important post-result observation:

`BREAKOUT_CONT` had strong LONG/SHORT asymmetry. Buyer-breakout LONG remained positive; seller mirror weak/negative.

That directional asymmetry was observed after the bounded search, so buyer-breakout LONG became a post-discovery historical candidate requiring a separate freeze/audit.

### LAB004 — frozen buyer-breakout LONG audit

Report:

`GC_M1_BUYER_BREAKOUT_LONG_AUDIT_004.md`

15m EV:

Rithmic:

- TRAIN N146 +0.339 ATR
- VALID N115 +0.278
- LATE N40 +0.561
- PRE_DISCOVERY N261 +0.312
- FULL N302 +0.346

AMP:

- TRAIN N108 +0.532
- VALID N120 +0.320
- LATE N37 +0.319
- POST N14 +0.303
- PRE_DISCOVERY N228 +0.420
- FULL N279 +0.401

Feed event parity:

- common-clock Jaccard `0.858`
- 247 exact matches
- Rithmic 269 vs AMP 266 in common interval

Mirror SHORT weak, especially Rithmic.

### LAB005 — incremental order-flow audit

Report:

`GC_M1_BUYER_BREAKOUT_INCREMENTAL_ORDERFLOW_AUDIT_005.md`

Controls:

1. same bullish price breakout without the buyer-A state
2. deterministic time-shift placebos for buyer-A state

Key 15m results:

Rithmic FULL:

- candidate +0.346 ATR
- price-no-OF +0.115
- incremental +0.231
- CI crosses zero

AMP FULL:

- candidate +0.401
- price-no-OF -0.045
- incremental +0.446
- day CI `[+0.083,+0.825]`

AMP PRE_DISCOVERY:

- candidate +0.420
- price-no-OF -0.089
- incremental +0.509
- day CI `[+0.089,+0.944]`

But shifted-flow placebos frequently produced incremental effects similar to or larger than synchronous flow. Therefore:

- signal is a strong historical **market-state** candidate
- exact synchronous order-flow feature is not proven to be the unique causal alpha source
- could represent broader bullish initiative regime that buyer flow marks

Do not overclaim “footprint itself causes the edge”.

### LAB006 — GC buyer-breakout → FTMO XAU transfer

Report:

`GC_BUYER_BREAKOUT_LONG_TO_FTMO_XAU_TRANSFER_LAB_006.md`

Clock calibration:

- best FTMO clock offset = `UTC + 3h`
- GC/XAU M1 return correlation `0.9869`
- N=38,000 common M1 returns

Primary horizon preregistered at 15m.

XAU execution:

- first executable Ask after signal availability
- exit response Bid
- real spread included

Results at 15m:

Rithmic ledger:

- N301
- +0.162 bps
- +0.086 XAU ATR
- WR 49.5%
- price-no-OF -0.467 bps
- incremental +0.629 bps

AMP ledger:

- N280
- +0.299 bps
- +0.139 ATR
- WR 48.2%
- price-no-OF -1.122 bps
- incremental +1.422 bps

Exact common-clock subset:

- N246
- +0.660 bps at 15m
- WR 48.8%

Strict prereg verdict = `TRANSFER_FAIL` because AMP positive days were 16/33, narrowly below >=50% gate. Ten other gates passed.

Do **not** rewrite this as PASS.

Interpretation:

- some information transfers from GC to XAU
- market entry has tiny margin after FTMO spread
- execution geometry likely dominates practical profitability

### LAB007 — post-signal XAU path geometry

Report:

`GC_XAU_POST_SIGNAL_PATH_GEOMETRY_LAB_007.md`

Primary common-clock executable cohort:

- 245 events after executable/ATR gate
- raw common signal times = 247

Secondary AMP cohort:

- N279

Key retrace geometry from market-reference Ask:

COMMON:

- 5m median retrace `-1.044 ATR`
- 10m median retrace `-1.360 ATR`

Market entry path:

- median MFE30 `+2.421 ATR`
- median MAE30 `-2.463 ATR`

So signal tends to be followed by large two-sided movement; immediate market BUY is structurally poor.

First passage market entry, 30m:

- SL1 ATR / TP1.5R: TP first 32.2%, SL first 67.8%
- SL1.5 ATR / TP2R: TP first 31.0%, SL first 66.5%
- SL1.5 ATR / TP3R: TP first 20.0%, SL first 70.2%, 24 neither

Observed historical leader in that bounded geometry map:

- limit -1.0 ATR
- expiry 10m
- SL1.5 ATR
- TP3R
- COMMON EV +0.054R/signal
- +0.084R/filled
- PF 1.13

Not validated; led to finer bounded limit study.

### LAB008 — limit depth / expiry stability map

Report:

`GC_XAU_LIMIT_ORDER_DEPTH_EXPIRY_STABILITY_LAB_008.md`

Frozen exit:

- SL1.5 ATR
- TP3R
- timeout 30m from original signal in this LAB

Varied only:

- depth: 0.50 / 0.75 / 1.00 / 1.25 / 1.50 ATR
- expiry: 3 / 5 / 10 / 15m

Important result: positive **plateau**, not one isolated point.

Stable positive candidates:

- D1.00_E5M: COMMON +0.082R/signal, AMP +0.080, PF 1.26, fill 51.4%, EARLY +0.104, LATE +0.025
- D1.00_E3M: COMMON +0.072, AMP +0.080, PF 1.28, fill 41.2%, EARLY +0.061, LATE +0.101
- D0.75_E5M: COMMON +0.062, AMP +0.066
- D0.75_E3M: COMMON +0.050, AMP +0.062

Depth 0.50 ATR was clearly poor. Waiting too long degraded late-period behavior.

### LAB009 — operational robustness

Report:

`GC_XAU_LIMIT_ORDER_OPERATIONAL_ROBUSTNESS_LAB_009.md`

Primary operational mode:

`ONE_ACTIVE_SETUP`

Primary adverse-cost stress:

`+0.05R / filled trade`

D1.00_E3M:

COMMON:

- accepted setups 86.5%
- 90 fills
- EV +0.075R/original signal
- EV +0.205R/fill
- PF 1.33
- MaxDD 8.40R
- positive weeks 4/6
- late EV +0.053R
- modeled DD at 0.5% risk = 4.20% observed sequence
- worst closed day at 0.5% = -2.10%

AMP:

- 105 fills
- EV +0.079R/signal
- +0.209R/fill
- PF 1.34
- MaxDD 8.40R
- positive weeks 5/7
- late EV +0.068R

Cost stress COMMON D1.00_E3M:

- +0R extra cost: +0.094R/signal
- +0.025R: +0.084
- +0.05R: +0.075
- +0.10R: +0.057

Operational descriptive leader = `D1.00_E3M`.

### LAB010 — dependency / Monte Carlo robustness

Report:

`GC_XAU_LIMIT_D1_E3_DEPENDENCY_MONTE_CARLO_LAB_010.md`

Frozen:

- D1.00_E3M
- one active setup
- SL1.5 ATR
- TP3R
- +0.05R cost/fill

COMMON:

- N245 signals
- observed EV +0.07519R/signal
- Sum +18.42R
- observed MaxDD 8.40R
- 30 days / 6 weeks
- positive days 13
- positive weeks 4
- max positive-day share 21.5%
- leave-one-day-out min EV +0.0482
- leave-one-week-out min EV +0.06146
- bootstrap P(EV>0) 94.15%
- bootstrap EV CI95 `[-0.0186,+0.1767]`
- bootstrap DD p95 14.74R
- p95 DD at 0.25% risk = 3.685%
- p95 DD at 0.50% risk = 7.370%

AMP:

- N279
- EV +0.07881R/signal
- Sum +21.99R
- observed MaxDD 8.40R
- max positive-day share 17.6%
- LOO-week min EV +0.06705
- bootstrap P(EV>0) 94.78%
- bootstrap EV CI95 `[-0.0159,+0.1779]`
- p95 DD at 0.25% risk = 4.075%
- p95 DD at 0.50% risk = 8.150%

Formal LAB010 verdict:

`HISTORICAL_ROBUSTNESS_FAIL_NOT_OOS`

Only failed gate:

`common_boot_p95_dd_050risk_lt5pct`

This is why research risk should be 0.25%, not 0.5%, if a forward shadow includes equity simulation.

### LAB011 — signal-decay curve

Report:

`GC_XAU_LIMIT_SIGNAL_DECAY_CURVE_LAB_011.md`

Frozen:

- depth 1.00 XAU ATR14(M1)
- SL 1.50 ATR
- TP 3R
- +0.05R/fill cost stress
- each filled order gets fixed 30m post-fill evaluation window
- tested expiry 1 / 3 / 5 / 10 / 15 / 30 / 60m

This LAB changed timeout convention only to make late fills comparable: 30m **from fill** rather than original GC signal. It was a decay study, not the canonical operational rule selection.

COMMON cumulative expiry:

- 1m: fill 18.0%; EV +0.078R/signal; +0.437R/fill; PF 1.76; MaxDD 4.20R; CI95 `[+0.007,+0.162]`
- 3m: fill 41.2%; EV +0.058; +0.140/fill; PF 1.22; DD 8.40R
- 5m: fill 51.4%; EV +0.052; +0.101/fill; PF 1.15
- 10m: +0.015; PF 1.03
- 15m: -0.002; PF ~1.00
- 30m: -0.021; PF 0.96
- 60m: -0.054; PF 0.91

AMP cumulative expiry:

- 1m: +0.059R/signal; +0.321/fill; PF 1.53
- 3m: +0.065; +0.156/fill; PF 1.24
- 5m: +0.049; +0.093/fill; PF 1.14
- 10m: +0.013
- 15m: +0.001
- 30m: -0.028
- 60m: -0.058

First-fill delay buckets are crucial:

COMMON:

- 0–1m: N44; +0.437R/fill; PF1.76; CI95 `[+0.041,+0.851]`
- 1–3m: N57; -0.089R/fill; PF0.87
- 3–5m: N25; -0.054R/fill
- 5–10m: N31; -0.291R/fill
- 10–15m: N13; -0.328R/fill
- 15–30m: N24; -0.190R/fill
- 30–60m: N12; -0.677R/fill; PF0.27; CI95 below zero at upper bound -0.018

AMP:

- 0–1m: N51; +0.321R/fill; PF1.53
- 1–3m: N66; +0.028R/fill; PF1.04
- 3–5m and later mostly negative

Interpretation:

**The GC→XAU execution edge appears very short-lived.** Most useful fills occur in the first ~1–3 minutes; after 5–10m the same 1ATR limit is generally stale/adversely selected. Fifteen minutes is effectively flat; 30–60m negative.

Governance:

- 1m expiry looks strongest on already-exposed history.
- Do **not** retroactively replace 3m with 1m as “validated production rule”.
- Promote 1m only as a forward-shadow challenger because LAB011 discovered its apparent superiority post hoc.

---

## 7. Current strategy semantics — exact version to remember

### 7.1 Sensor side: GC

Instrument:

`GC futures, current contract used in archive GCEZ26`

Timeframe:

`M1`

Signal:

`BUYER_BREAKOUT_LONG_001`

Signal exists only after GC M1 bar closes.

Do not trade GC itself in the current transfer strategy. GC is the **sensor**.

### 7.2 Execution side: XAUUSD FTMO

Instrument:

`XAUUSD on FTMO-Demo / target FTMO execution environment`

Raw price source:

FTMO Bid/Ask ticks.

Current historical reference geometry:

At completed GC signal time:

1. obtain current executable XAU market-reference Ask
2. obtain XAU `ATR14(M1)` from completed XAU M1 data before/at signal clock, causal only
3. place BUY LIMIT:

`limit = market_reference_ask - 1.00 × ATR14(M1)`

Operational historical candidate:

`expiry = 3 minutes`

Forward challenger discovered in LAB011:

`expiry = 1 minute`

If filled:

`SL = fill_price - 1.50 × ATR14(M1)`

`TP = fill_price + 4.50 × ATR14(M1)`

Therefore:

`R:R = 1 : 3`

One active setup at a time.

Unfilled limit contributes 0R to per-signal EV.

### 7.3 Timeout ambiguity that must be explicit in future code

Two historical conventions exist:

LAB008/009 operational lineage:

- hard timeout 30m from **original signal**

LAB011 decay study:

- fixed 30m from **fill**, intentionally changed so late fills could be compared fairly

For forward production candidate, do **not** silently mix them.

Recommended freeze for operational continuity:

- D1.00_E3M keeps the LAB009 convention unless a new preregistered LAB explicitly changes it.
- D1.00_E1M forward challenger should have timeout convention declared before first new signal. Best clean choice is 30m from fill because fill is necessarily within 1m, so difference is practically small while semantics are simpler.

---

## 8. What “M1” means here

There are two separate M1 uses.

### GC M1

This is part of the **signal discovery itself**. The original AEIF lineage and the current buyer-breakout candidate are M1 order-flow phenomena. M5 replication of the old AEIF reversal failed.

Do not convert GC signal to M5 without treating it as a new strategy.

### XAU M1 ATR

This is currently only the **execution volatility normalization**:

- limit depth = XAU ATR14(M1)
- stop = 1.5 × XAU ATR14(M1)

This scale is **not sacred** and is not proven uniquely optimal. It is a post-discovery execution choice.

A future volatility-scale audit may compare ATR14 M1 vs ATR20 M1 vs ATR14 M5 vs short realized range, but that should not be used to select live parameters on the same Aug–Sep sample. Prefer forward descriptive comparison or a separately frozen test.

---

## 9. Statistical / governance state

### What has evidence

- GC buyer-breakout LONG is positive over inspected historical partitions in both raw feeds.
- exact GC event timestamps have high cross-feed parity.
- XAU transfer at 15m was positive in both feed-ledgers and positive on common-clock events.
- XAU market entry is poor because signal is followed by large retrace/noise.
- limit depth around 0.75–1.00 ATR produced a broad historical positive surface.
- operational one-active-setups favor 1.0 ATR depth and short expiry.
- D1.00_E3M remained positive under +0.10R/fill extra-cost stress historically.
- D1.00_E3M profit is not concentrated in one day/week; LOO-week remains positive.
- decay curve strongly suggests late fills are stale/adversely selected.

### What is NOT proven

- independent OOS profitability
- live AMP→FTMO operational parity
- that synchronous order flow is the unique causal driver vs broader bullish initiative regime
- that 1m expiry is truly superior out of sample
- that ATR14(M1) is the unique best volatility scale
- exact production commission/slippage economics under target challenge account
- performance under news spikes / abnormal spread unless separately filtered/tested

### Important interpretation

Rithmic and AMP are **not two independent markets**. Their agreement is feed robustness, not independent OOS.

The Aug–Sep FTMO XAU sample has now been inspected extensively. Further threshold micro-tuning on it is curve-fitting.

---

## 10. Current risk conclusion for prop context

User target context:

- nominal account: 100K
- preference: many small trades, roughly 0.25–0.5% risk, always stop, full TP, TP > stop at least 1:1.5

For current candidate:

- R:R = 1:3 satisfies user rule
- 0.5% risk is too aggressive under LAB010 bootstrap:
  - COMMON p95 DD ~7.37%
  - AMP p95 DD ~8.15%
- 0.25% risk gives approximately:
  - COMMON p95 DD ~3.69%
  - AMP p95 DD ~4.08%

Therefore current research risk ceiling for forward equity simulation:

`0.25% per filled trade`

Do not convert this directly into live lot sizing until current FTMO/broker specs are reconfirmed.

---

## 11. Broker/prop assumptions known from project — RECONFIRM BEFORE LIVE CODE

Historical project assumptions, not automatically current truth:

- FTMO MT5 / FTMO Standard style target
- 100K account target
- leverage historically noted around 1:10
- max daily DD target around 5%
- overall DD target around 10%
- EA historically allowed
- news/hedging historically discussed as allowed, but must be rechecked against current challenge rules
- historical commission assumption around $5 round-turn/lot in prior project work
- XAU spread must be observed from actual account/ticks rather than assumed
- VPS planned/expected latency roughly ~40 ms in prior project discussions

Before any real-order EA is finalized, explicitly obtain/reconfirm:

1. prop/broker and server exact name
2. account type: Demo / Challenge / Verification / Funded
3. current XAU average and stress spread
4. commission per lot / side / round-turn
5. STOPLEVEL
6. FREEZELEVEL
7. EA permission
8. news-trading rule
9. hedging rule
10. max orders / exposure rules
11. leverage
12. min lot / max lot / volume step
13. swap long/short if positions can survive rollover
14. VPS location/latency and realistic slippage
15. current FTMO rules link

Do not generate production execution code before these are supplied/reconfirmed.

---

## 12. Exact next research backlog

### PRIORITY 1 — LAB012: forward shadow, no historical retuning

Suggested name:

`GC_XAU_D1_E1_VS_E3_FORWARD_SHADOW_LAB_012`

Purpose:

Collect untouched signals **after the freeze date** and compare two already-declared candidates without modifying GC signal or execution geometry.

Candidate A — historical operational incumbent:

`D1.00_E3M`

Candidate B — LAB011 forward challenger:

`D1.00_E1M`

Frozen common parameters:

- GC BUYER_BREAKOUT_LONG_001 unchanged
- XAU depth = 1.00 ATR14(M1)
- SL = 1.50 ATR
- TP = 3R
- one active setup
- cost bookkeeping must include real quoted spread; log commission/slippage separately
- shadow only: no real orders until explicit live approval and broker specs

Required forward ledger fields:

GC sensor:

- GC signal timestamp UTC ms
- contract/symbol
- raw buy_vol
- raw sell_vol
- delta
- delta_frac
- prior240 q90 delta
- prior240 q75 buy volume
- prior20 high
- open/high/low/close
- close_pos
- ATR14 GC M1
- signal boolean and reason code

XAU mapping:

- FTMO server time
- canonical UTC time
- current Bid/Ask
- spread points / spread price / bps
- XAU ATR14 M1
- market-reference Ask
- limit price for E1/E3
- exact order start timestamp
- expiry timestamp
- first touch/fill timestamp
- fill delay ms
- shadow fill price

Path / outcome:

- SL price
- TP price
- MFE / MAE at 1m, 3m, 5m, 15m, 30m
- first passage order
- timeout result
- realized R before/after explicit costs
- missed/unfilled = 0R in per-signal statistics
- data-gap / stale-quote flag
- overlap rejection reason if one-active rule blocks setup

Forward metrics:

- signals
- fill rate
- EV/signal
- EV/fill
- PF
- MaxDD R
- day/week distribution
- E1 vs E3 paired difference on same signal set
- actual spread and actual fill-delay distribution

Do not look at forward data and then change thresholds. Any change creates a new candidate version.

### PRIORITY 2 — live feed parity audit

Before trusting shadow output, verify AMP realtime signal reconstruction equals historical semantics:

- exact exclusive BUY/SELL handling
- volume_real fallback logic
- UTC timestamp semantics
- M1 bar boundary semantics
- rolling 240 shifted thresholds
- prior20 high exclusion of current bar
- no signal until bar is fully closed

Store raw input snapshots for every forward signal so any discrepancy is replayable.

### PRIORITY 3 — FTMO XAU execution parity

Shadow system must verify:

- first executable quote after GC information time
- no use of stale quote > configured max lag
- limit touch based on actual Ask for long entries
- SL/TP outcome based on Bid
- all timestamps in ms
- actual spread at signal, fill, exit

### PRIORITY 4 — only after enough untouched forward sample

Possible forward acceptance gate should be preregistered before viewing outcomes. Example conservative gate, to be formalized before collection:

- >=100 forward GC signals ideally, or explicit time-based minimum if frequency makes this impractical
- primary candidate EV/signal >0 after real spread + commission + logged slippage
- PF >1.2 preferred
- no single day >50% of total positive R
- late-half EV not materially negative
- drawdown compatible with 0.25% risk and prop limits
- E1/E3 comparison reported but do not pick winner until sample minimum met

Do not retrofit gates after outcomes.

### PRIORITY 5 — volatility-scale audit, only under governance

Question left open after user asked “why M1?”:

Is XAU ATR14(M1) merely a convenient execution scale, or is the geometry robust to other volatility measures?

Potential comparison:

- ATR14 M1
- ATR20 M1
- ATR14 M5
- 5-minute realized high-low / true-range scale

Rules:

- GC signal remains frozen
- do not use Aug–Sep same-sample best performer as new production setting
- preferably run scale variants in forward shadow in parallel

### PRIORITY 6 — confirmation-after-retrace branch, future only

Possible later research branch:

`GC signal → XAU 0.75–1.00 ATR retrace → causal reclaim/failed acceptance → entry`

Candidate confirmation features that may be explored only in a separately preregistered LAB:

- reclaim above short micro-high after retrace
- failed acceptance below limit/retest level
- bid recovery velocity
- bullish M1 close after first touch
- spread normalization after touch
- short-term XAU impulse back toward signal direction

Do not mix these confirmation features into current frozen D1 E1/E3 forward candidates.

---

## 13. Things explicitly NOT to do

1. Do not call old M5 reconstructed AEIF the original edge.
2. Do not call original AEIF reversal proven stable.
3. Do not claim FTMO XAU was the original discovery source.
4. Do not treat Rithmic + AMP as two independent OOS samples.
5. Do not invent a seller/SHORT mirror for the current strategy.
6. Do not optimize GC thresholds further on Aug–Sep history.
7. Do not optimize 1.00 ATR into 0.93/1.07 ATR based on the exposed sample.
8. Do not choose expiry 1m as “validated winner” from LAB011; it is a forward challenger.
9. Do not mix LAB009 timeout-from-signal with LAB011 timeout-from-fill without declaring a new version.
10. Do not ignore unfilled limits in EV/signal; unfilled = 0R.
11. Do not model long fills on Bid. Long entry/touch uses Ask; exits/path use Bid.
12. Do not add old XAU TP3/240m rules from unrelated AEIF transfer lineage.
13. Do not begin real money / prop execution before broker specs are reconfirmed.
14. Do not confuse unrelated failing `xau_ifvg_vwap_lab001.yml` workflow with GC research failure.

---

## 14. Current canonical candidate labels

Use these names consistently:

### Sensor

`BUYER_BREAKOUT_LONG_001`

Definition = frozen GC M1 buyer aggression + local breakout rule in section 5.

### Historical operational execution candidate

`GCXAU_D1.00_E3M_SL1.5_TP3_ONEACTIVE_001`

Meaning:

- depth 1.00 XAU ATR14(M1)
- expiry 3m
- SL1.5 ATR
- TP3R
- one active setup

### Forward-only challenger

`GCXAU_D1.00_E1M_SL1.5_TP3_ONEACTIVE_CHALLENGER_001`

Meaning identical except expiry 1m.

This challenger exists because LAB011 exposed strong first-minute fills. It must not inherit the historical validation status of D1_E3.

---

## 15. One-line state for future assistant/model

**Do not restart discovery. Current best historical branch is GC M1 BUYER_BREAKOUT_LONG_001 used only as sensor, transferred to FTMO XAUUSD via a ~1 ATR short-lived buy-limit retrace. D1.00_E3M is the frozen historical operational candidate; D1.00_E1M is a post-discovery forward challenger. Both require untouched forward shadow before any production claim. Risk should be modeled at 0.25%, not 0.5%, because LAB010 p95 DD at 0.5% was ~7–8%.**

---

## 16. Immediate resume checklist after any crash

1. Checkout branch `gc-amp-feed-audit-001`.
2. Read this file.
3. Read `GC_ORDERFLOW_CANONICAL_LINEAGE_AND_EDGE_STATUS_002.md` for original lineage.
4. Read LAB009, LAB010, LAB011 reports for current execution state.
5. Do **not** rerun historical optimization to choose new parameters.
6. Continue with `GC_XAU_D1_E1_VS_E3_FORWARD_SHADOW_LAB_012`.
7. Use AMP/CQG as intended realtime GC sensor and FTMO XAU raw Bid/Ask as execution/shadow side.
8. Log every signal and quote to an append-only ledger.
9. Keep E1 and E3 rules frozen and parallel.
10. Reconfirm FTMO account specs before any real order placement.

End of recovery snapshot 003.
