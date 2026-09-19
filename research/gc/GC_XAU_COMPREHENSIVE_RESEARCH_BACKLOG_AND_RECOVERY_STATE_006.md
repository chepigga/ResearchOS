# GC / XAU COMPREHENSIVE RESEARCH BACKLOG AND RECOVERY STATE 006

Date: 2026-09-19  
Branch: `gc-amp-feed-audit-001`  
Project: GC futures / COMEX order flow / AMP Futures MT5/CQG / GC→XAUUSD FTMO execution  
Status: FORWARD_SHADOW_CANDIDATE / NOT_PRODUCTION_PROVEN

---

## 0. THREAD SEPARATION

This branch is ONLY for:

- COMEX GC futures order flow
- AMP Futures MT5/CQG
- GC as information source / sensor
- FTMO XAUUSD as execution venue
- GC→XAU signal transfer
- forward/demo validation

Do NOT mix with:

- CrowdFade crypto
- BTC AEIF
- Bybit
- other crypto systems
- unrelated EAs

---

## 1. CORE CONCEPT

The project moved from direct XAU price-pattern logic toward using futures information that spot/CFD does not contain.

Primary hypothesis:

> Crowd Pressure ↑ + Price Efficiency ↓ = trapped crowd probability ↑

Useful GC information historically available:

- aggressive BUY/SELL volume
- delta / delta fraction
- CVD-type directional flow
- location of aggressive flow within bar/range
- effort vs result / price impact
- flow acceleration
- repeated failed attacks
- lead/lag impulse

Not historically available from current archive:

- true DOM replenishment
- resting liquidity changes
- cancel/replace behavior
- iceberg/replenishment signatures

DOM must be logged live if needed later.

---

## 2. AMP / CQG FEED STATE

### Canonical raw archive

`AMP_GC_HISTORY_EXPORTER_001_GCEZ26_20260806_182355__20260915_182355_TICKS.csv.zip`

SHA256:

`81d675597368a9f6c78eee726ed547737366ffd8d8e54aa976bce50111db752b`

Coverage:

- GCEZ26
- 2026-08-06 18:24 UTC → 2026-09-15 18:23 UTC
- raw rows: 3,737,579
- exclusive BUY/SELL rows: 3,731,970
- dual BUY+SELL excluded: 5,609
- reconstructed M1: 38,464

Feed supports:

- Last
- Volume
- millisecond timestamps
- explicit BUY/SELL tick flags
- CopyTicks history + realtime
- MarketBookAdd (live DOM auxiliary)

### Long-history compaction

Compactor:

`/mnt/data/amp_gce_lab008h_compactor.py`

Compact archive:

`/mnt/data/@GCE_LAB008H_COMPACT.zip`

Stats:

- 568 source files
- original ~17.3 GB
- total rows: 174,022,818
- directional rows: 27,025,331
- BUY: 13,456,208
- SELL: 13,569,123
- dual excluded: 148,947
- neither excluded: 146,848,540
- first kept: 2025-01-01 23:00 UTC
- last kept: 2026-09-15 23:55 UTC
- ~330,116 directional M1

Important caveat:

- `@GCE` vendor roll semantics remain unverified.
- single deferred contract `GCEZ26` is NOT a proper continuous front-month reconstruction.
- current long-history work is companion/audit evidence, not a fully certified causal contract stitch.

---

## 3. FROZEN AEIF LINEAGE — SEPARATE FROM CURRENT REV2 LINEAGE

Frozen AEIF:

LONG:
- extreme negative delta
- aggressive sells near M5 low
- failed downside impact

SHORT:
- mirror

Confirmation:
- max 2 following M5 bars
- entry only after confirmation

Frozen candidate:

- TP 3R
- max hold 240m
- single position
- ~46 trades
- EV ~ +0.666R
- Sum ~ +30.63R
- PF ~ 2.33
- MaxDD ~ 3.32R
- max consecutive losses 4

Status:
- candidate only
- do NOT retune AEIF without a separate LAB

---

## 4. CHRIS SHORT LINEAGE SUMMARY

### Frozen mechanism

M1 directional trades reconstructed from Last / directional volume.

Key variables:

- `buy_loc`: BUY volume in upper 20% of current M1 range / buy_vol
- `delta_frac = (buy-sell)/(buy+sell)`
- ATR14
- prior 240 causal quantiles:
  - delta Q90
  - buy volume Q75
  - buy location Q75
- A_buy:
  - delta_frac >= prior Q90
  - buy_vol >= prior Q75
- impact = (close-open)/ATR14
- impact_q20 from prior A_buy impacts after minimum history
- seed:
  - A_buy
  - buy_loc >= prior Q75
  - impact <= impact_q20
- bearish confirmation:
  - first next max2 contiguous M1
  - close < open
  - close < seed close
  - close_pos <= 0.50
- entry = next contiguous M1 open

Mechanism interpretation:

> extreme aggressive BUY + upper auction + weak result → bearish confirmation → SHORT

Key historical labs:

- LAB001 reclaim: reject
- LAB002 sell-pressure acceptance: reject
- LAB003 Chris/AEIF BUY FAILURE: frozen
- LAB004 path study → cp10 distance
- LAB005 POST10 residual
- LAB006 prior-Q50 WF: historically positive small, not OOS
- LAB007 GC→XAU transfer: positive but tiny N
- LAB008H long-history Q50: failed stability
- LAB009 delayed raw resolution: supportive
- LAB010 GC native execution geometry: positive candidate
- LAB011 raw Chris→XAU SL1/TP2: failed
- LAB012 raw 30m XAU transfer: failed
- LAB013 GC native cost: positive native GC edge

Conclusion:

- Chris mechanism stronger natively on GC than universally transferred to XAU.
- not current production path.

---

## 5. PRIMARY XAU LONG LINEAGE — SEPARATE

`BUYER_BREAKOUT_LONG_001`

Execution:

- `D1.00_E3M_BARE_CORRECTED`
- signal completed
- order +1m
- BUY LIMIT XAU Ask -1 ATR14
- expiry 3m
- timeout signal+30m
- fill Ask touch
- exits Bid
- SL 1.5 ATR
- TP 3R = 4.5 ATR
- single active
- cost 0.05R/fill
- risk 0.25%

LAB018 readiness:

- N 279
- accepted 237
- fills 103
- EV/signal +0.08634R
- Sum +24.09R
- MaxDD 8.4R
- late EV +0.06814
- LOO min +0.07497
- bootstrap P(positive) +0.9631
- p95 DD @0.25% = 3.894%
- cost stress positive to 0.25R
- BE cost ~0.28387R/fill

Status:

`READY_FOR_FTMO_DEMO_SHADOW`

Still separate from current REV2 system.

---

## 6. CURRENT MAIN LINEAGE — TRAPPED CROWD / REV2

### LAB001–006 discovery

Repeated failed GC crowd attacks became the main causal state.

LAB005 causal repeated_failed_attack:

- two non-overlapping 30s GC crowd attacks same direction
- second signed crowd impact <= first
- predicted XAU opposite crowd
- cooldown 60s
- optional QUIET prior30 XAU abs <= 0.25 ATR

Counts:

- ALL ~15,206 signals (~475/day)
- QUIET ~8,261 (~258/day)

Problem:

- too many “signals”; many are really repeated observations of the same market episode.

### LAB006C episode clustering

5m time-only clustering:

- 15,206 raw signals → 1,140 clusters
- median ~9 signals per cluster
- revealed repeated_failed_attack as market state rather than independent trade signal

10m overmerged.

### LAB007 anchored episodes

Anchored 5-minute episodes:

- 5,341 episodes
- median 3 signals
- median span 240s
- max 300s

No simple dominance/run/flip rule survived.

### LAB007C structural classes

Classes:

- SPARSE
- ONE_SIDED_BUILDUP
- DOMINANCE_REVERSAL
- ALTERNATING_CONFLICT
- REASSERTION
- MIXED

Most interesting:

`DOMINANCE_REVERSAL`

Results:

- TRAIN N54
- VALID N74
- POST N45
- fixed5m EV approximately positive across splits
- small N, not formally passed

### LAB007D mechanism / timing

REV1:
- clearly bad

REV2:
- defined as second reversal-side event after initial dominance
- FULL N173
- +2ATR ~22.5%
- +3ATR ~11.6%
- fixed5m EV ~+0.0755 ATR
- median ~+0.045 ATR
- PF ~1.11
- median time to +0.5 ATR among +2 winners ~34.6s

Interpretation:

- sequence structure matters more than simple impact magnitude
- REV2 itself too weak for direct trading

---

## 7. LAB008 / 008B — EXECUTION GEOMETRY FAILURE ON RAW REV2

Wide XAU grid:

LAB008:
- SL 0.25→2 ATR
- TP 0.5→4 ATR
- R:R >= 1.5

LAB008B extended:
- SL 0.25→4 ATR
- TP 0.5→8 ATR

Result:

- ZERO cells positive in both TRAIN and VALID under formal criteria
- best area around SL ~2 ATR
- mostly timeout-driven outcomes
- raw REV2 cannot be rescued by geometry alone

Conclusion:

> need a quality discriminator before execution.

---

## 8. LAB009 — FLOW / IMPULSE / VOLUME QUALITY

Features around REV2:

Exact t0:
- attack1_volume
- attack2_volume
- volume ratio
- aligned delta frac
- impact deterioration
- aligned aggressor share

Post-confirmation windows:
- +5s
- +15s
- +30s

Features:
- total volume
- aligned volume
- opposite volume
- signed GC impulse / ATR
- impulse efficiency
- volume acceleration
- delta acceleration
- XAU signed confirm move
- GC-XAU lead gap

Important methodological issue:

Original LAB009 tail gate required N>=30 while TRAIN had only 54 events and Q20/Q80 tails yielded ~10–12. Gate was mathematically impossible.

Therefore:

- “no survivors” in LAB009 is not evidence that features failed.
- LAB009 became discovery only.

Strongest discovery feature:

### 5s `post_signed_impulse_atr`

Q5/high tail:

- TRAIN EV ~+0.564 ATR in original tail view
- VALID ~+0.490
- POST ~+0.993
- strongest cross-split feature

Other useful features:

- 30s volume_acceleration
- 30s post_volume
- 30s post_aligned_volume
- 30s post_opposite_volume
- 5s XAU confirm move

Pure delta-strength features were less stable.

---

## 9. LAB009B — MONOTONICITY AUDIT

Commit prereg:
`2e84a4ddea830f7daa6a530adcf133945ad4b581`

Code:
`b2d23ace9469e629db7691a8629359d20c7159d0`

Workflow:
`62cfefc7f36860cfb4a858112a4be98115ad402b`

Result report:
`research/gc/GC_XAU_REV2_FLOW_IMPULSE_VOLUME_MONOTONICITY_LAB009B.md`

Broad TRAIN-only terciles LOW/MID/HIGH.

Key observations:

### 5s impulse

TRAIN:
- LOW +2 = 7.1%
- EV = -0.432 ATR
- HIGH +2 = 37.5%
- EV = +1.384 ATR

VALID:
- LOW 16.7% / -0.352
- HIGH 35.0% / +0.567

POST:
- LOW 23.1% / +0.008
- HIGH 40.0% / +0.650

### 30s total volume

HIGH:
- TRAIN +2 38.9%, EV +1.615
- VALID +2 33.3%, EV +0.311
- POST +2 26.3%, EV +0.395

### 30s aligned volume

HIGH:
- TRAIN +2 38.9%, EV +1.620
- VALID +2 36.1%, EV +0.282
- POST +2 27.3%, EV +0.481

### attack2_volume at t0

Failed transfer / unstable.

Conclusion:

- post-REV2 impulse and post-REV2 executed volume are much more useful than raw REV2 volume.
- exact LOW→MID→HIGH monotonicity not clean due ties/small N.
- threshold effect more likely than smooth monotonicity.

---

## 10. LAB009C — THRESHOLD STABILITY + INTERSECTION

Prereg:
`48c8191e7abe9e065d98c46c9a4515bcba0a73f3`

Code:
`80d40b78aa0d205169df2b321c3ebe6e91fa4780`

Workflow:
`4d95f38dc135c1fab840a6e7974f8201421248e1`

Result commit:
`51833415d9869376f1ae9805f02f3ce775eec51e`

Report:
`research/gc/GC_XAU_REV2_IMPULSE_VOLUME_THRESHOLD_STABILITY_AND_INTERSECTION_LAB009C.md`

TRAIN-frozen threshold grid:

- Q60
- Q65
- Q70
- Q75
- Q80

Frozen features:

- 5s post_signed_impulse_atr
- 30s post_volume
- 30s post_aligned_volume

Thresholds:

Q60:
- impulse 0.0000
- volume 43.60
- aligned volume 17.20

Q65:
- impulse 0.0521
- volume 56.00
- aligned volume 20.60

Q70:
- impulse 0.0979
- volume 63.00
- aligned volume 22.80

Q75:
- impulse 0.1306
- volume 73.00
- aligned volume 29.00

Q80:
- impulse 0.1707
- volume 80.80
- aligned volume 36.00

### Plateau result

Robust positive plateau:

- IMPULSE: Q60–Q80
- VOLUME: Q65–Q80
- ALIGNED_VOLUME: Q60–Q80
- IMPULSE+VOLUME: Q60–Q80
- IMPULSE+ALIGNED_VOLUME: Q60–Q80

Most promising intersection:

`IMPULSE + ALIGNED_VOLUME`

Q60:
- TRAIN N12, +2 33.3%, EV +2.078 ATR, PF 11.34
- VALID N22, +2 36.4%, EV +0.539, PF 2.08
- POST N12, +2 25.0%, EV +0.337, PF 1.59

Q65:
- TRAIN N8, +2 50%, EV +3.385
- VALID N15, +2 40%, EV +0.721, PF 2.99
- POST N8, +2 37.5%, EV +0.745

Conclusion:

- Q60/Q65 became frozen execution candidates
- Q65 higher quality but smaller sample
- Q60 broader sample but weaker post robustness

---

## 11. LAB010 — FROZEN Q60/Q65 EXECUTION GEOMETRY + EQUITY/DD + COST STRESS

Prereg:
`e655aed409a371a978bde0b78f57ff66440cf192`

Code:
`a6573d20533d2765209d68bd9e343481a4d40520`

Workflow:
`3764119e0dc374867d0d27d8c026db55ab211a19`

Result commit:
`e72b4e9e2c7cd6408710ad148ac93d7d3ddd8fcc`

Report:
`research/gc/GC_XAU_REV2_Q60_Q65_FROZEN_EXECUTION_GEOMETRY_EQUITY_COST_LAB010.md`

Execution:

- entry = REV2 + 30s
- first executable XAU quote
- spread embedded via Bid/Ask
- timeout 300s
- SL grid 0.50→4.00 ATR step 0.25
- TP grid 0.75→8.00 ATR step 0.25
- R:R >=1.5
- cost stress: 0 / 0.02R / 0.05R / 0.10R / 0.15R

### Q60

Signals:
- FULL 46
- TRAIN 12
- VALID 22
- POST 12

Robust cells:
- positive TRAIN+VALID: 176
- PF>=1.10 TRAIN+VALID: 155
- positive at 0.05R cost: 155
- neighbor-supported robust cells: 154

Representative geometry:

SL 2.25 ATR / TP 4.50 ATR

- TRAIN EV +0.181R, PF 2.05
- VALID EV +0.276R, PF 2.37
- POST EV -0.019R, PF 0.95
- FULL EV +0.174R, PF 1.73
- CumR +8.02R
- MaxDD 3.124R
- DD @0.25% risk = 0.781%
- max losing streak 3

### Q65

Signals:
- FULL 31
- TRAIN 8
- VALID 15
- POST 8

Robust cells:
- positive TRAIN+VALID: 205
- PF>=1.10 TRAIN+VALID: 180
- positive at 0.05R cost: 180
- neighbor-supported robust cells: 177

Representative frozen geometry:

SL 2.25 ATR / TP 4.50 ATR = 2R

- TRAIN EV +0.390R, PF 4.12
- VALID EV +0.378R, PF 4.05
- POST EV +0.083R, PF 1.21
- FULL EV +0.305R, PF 2.56
- CumR +9.45R
- MaxDD 2.00R
- DD @0.25% = 0.50%
- max losing streak 3

Conclusion:

- Q65 clearly stronger than Q60
- geometry has broad stable plateau
- useful zone roughly SL 2.25–2.50 ATR, TP 4.0–5.0 ATR
- not a single-cell optimization artifact

---

## 12. LAB011 — FROZEN Q65 VALIDATION / COST / BOOTSTRAP / MONTE CARLO / LOPO

Prereg:
`745287064de5ab4a080156ac85327f822ea2d190`

Code:
`8edbf171b834759adc351f9a12f3b3ecd7faa7fe`

Workflow:
`c688baa43804ebbf0f01806b4b00d373c8ffc733`

Result commit:
`0815b5930e315584dbcb99d455622eee25a040a9`

Report:
`research/gc/GC_XAU_REV2_Q65_FROZEN_OOS_BOOTSTRAP_MONTECARLO_LOPO_COST_LAB011.md`

Frozen candidate:

- signal: Q65 impulse AND Q65 aligned volume
- entry: REV2 + 30s
- SL: 2.25 ATR
- TP: 4.50 ATR
- nominal RR: 2.0
- timeout: 300s
- no further retuning

### Exact FTMO metals commission conversion

Commission model:

- 0.0007% per side of notional
- XAUUSD contract size 100
- USD account
- round-turn commission_R =
  0.000014 * entry_price / (2.25 * ATR)

Observed:

- median commission = 0.0112R/trade
- mean = 0.0121R
- range = 0.0034–0.0286R

Spread already embedded in raw Bid/Ask.

### Exact-cost split results

TRAIN:
- N8
- EV +0.379R
- PF 4.000
- CumR +3.035R
- WR 75%
- MaxDD 1.010R
- DD @0.25% = 0.253%
- max losing streak 1

VALID:
- N15
- EV +0.366R
- PF 3.912
- CumR +5.488R
- WR 80%
- MaxDD 1.885R
- DD @0.25% = 0.471%
- max losing streak 3

POST_CHECK:
- N8
- EV +0.070R
- PF 1.170
- CumR +0.556R
- WR 50%
- MaxDD 2.025R
- DD @0.25% = 0.506%
- max losing streak 2

FULL:
- N31
- EV +0.293R
- PF 2.474
- CumR +9.080R
- WR 71%
- MaxDD 2.025R
- DD @0.25% = 0.506%
- max losing streak 3

### Bootstrap

IID:
- P(EV>0) = 0.979
- 95% CI = +0.009 … +0.585R

Block-3:
- P(EV>0) = 0.983
- 95% CI = +0.027 … +0.617R

### Monte Carlo path risk

- median MaxDD 2.045R
- p95 MaxDD 3.590R
- p99 MaxDD 4.260R
- p95 DD @0.25% risk = 0.898%
- losing streak median 2
- p95 4
- p99 5

### Leave-one-period-out

7 ISO weeks tested.

- minimum remaining EV after removing any week = +0.207R
- minimum remaining PF = 1.876
- remaining EV positive after removing every individual week = TRUE

Leave TRAIN:
- N23
- EV +0.263R
- PF 2.174
- CumR +6.045R

Leave VALID:
- N16
- EV +0.224R
- PF 1.840
- CumR +3.592R

Leave POST:
- N23
- EV +0.371R
- PF 3.943
- CumR +8.524R

Critical caveat:

POST_CHECK is NOT pristine OOS because it was inspected in earlier discovery labs.

### Current status

`Q65 candidate = READY_FOR_FORWARD_SHADOW / NOT_PRODUCTION_PROVEN`

True independent OOS requires fresh future events after freeze.

---

## 13. CURRENT FROZEN FORWARD CANDIDATE

Do NOT retune during forward validation.

Signal:

1. detect repeated_failed_attack / anchored dominance-reversal structure
2. detect REV2
3. wait 5s and measure `post_signed_impulse_atr`
4. wait 30s and measure `post_aligned_volume`
5. ACCEPT only if both pass frozen Q65 thresholds

Frozen thresholds:

- 5s impulse >= 0.0521
- 30s aligned volume >= 20.60

Execution on FTMO XAUUSD:

- entry after completion of 30s confirmation
- first executable quote
- direction = REV2 direction
- SL = 2.25 ATR
- TP = 4.50 ATR
- RR = 1:2
- timeout = 300s
- risk = 0.25% per trade
- one XAU position max
- no duplicate signal_id
- stale signal reject
- heartbeat required

Forward protocol:

- collect minimum 30–50 fresh trades before any logic retune
- log every signal stage
- compare fresh EV/PF/DD/streak to LAB011
- if edge degrades, diagnose execution vs signal quality before changing thresholds

---

## 14. CURRENT BROKER / SYMBOL SPECS

### AMP / GC sensor

Observed from MT5 Specification:

- Symbol: `GCEZ26`
- Description: Gold (Globex): December 2026
- Digits: 1
- Tick size: 0.1
- Tick value: 10 USD
- Contract size: 1
- Stops level: 0
- Execution: Exchange
- Filling: FOK / IOC
- Min volume: 1
- Volume step: 1
- Commission: 2.17 USD per lot, in/out deals
- Initial / maintenance margin: ~6062 USD
- Chart mode: Last price

Sessions shown:
- Sunday 22:00–24:00
- Mon–Thu 00:00–21:00 and 22:00–24:00
- Friday 00:00–21:00

Usage:
- sensor only
- no GC trade execution planned in current forward protocol

### FTMO / XAUUSD executor

Observed from MT5 Specification:

- Symbol: `XAUUSD`
- Description: Gold vs US Dollar, Spot CFD
- Digits: 2
- Contract size: 100
- Stops level: 0
- Execution: Market
- Filling: FOK / IOC
- Min lot: 0.01
- Max lot: 100
- Lot step: 0.01
- Commission: 0.0007% in USD per lot / side model used in LAB011
- Swap long: -83
- Swap short: -8.3
- Margin mode: CFD Leverage
- approximate margin shown ~8756 USD / lot
- Mon–Fri trading sessions: 01:05–23:50

Note:
- visual Specification showed tick size/value oddly as 0.00 / 0.
- production EA must query:
  - SYMBOL_TRADE_TICK_SIZE
  - SYMBOL_TRADE_TICK_VALUE
  - SYMBOL_POINT
  - SYMBOL_VOLUME_STEP
  at runtime instead of trusting UI text.

---

## 15. VPS / INFRASTRUCTURE STATE

### VPS

Provider:

- InterServer
- Windows Hyper-V VPS
- New Jersey
- 3 slices
- 6 GB RAM
- 120 GB storage
- ~$15/month

Do NOT store password in repo.

Mac access:

- FreeRDP 3.31.1
- XQuartz required
- working RDP connection established
- X11 needed via DISPLAY
- current command pattern:

`xfreerdp /v:<VPS_IP> /u:Administrator /dynamic-resolution +clipboard /cert:ignore`

For Mac file sharing use:

`/drive:MacDownloads,$HOME/Downloads`

RDP can be closed safely; VPS keeps running as long as Windows is not shut down.

### MT5 deployment

One MT5 installation was copied into two portable instances:

- `C:\Trading\MT5_AMP\`
- `C:\Trading\MT5_FTMO\`

Each runs independently via:

`terminal64.exe /portable`

Current state:

- AMP account logged in and working
- FTMO account logged in and working
- both terminals can run simultaneously
- account independence verified

This is the target architecture:

Windows VPS
├── MT5_AMP
│   └── GC_SENSOR_Q65
└── MT5_FTMO
    └── XAU_EXECUTOR_Q65

Communication target:

`FILE_COMMON`

No Google Drive / external relay needed.

---

## 16. CURRENT BRIDGE TEST STATE

Two non-trading test EAs were generated locally:

- `GC_BRIDGE_WRITER.mq5`
- `XAU_BRIDGE_READER.mq5`

Purpose:

AMP writer:
- writes PING every ~1s into FILE_COMMON
- logs:
  - version
  - type
  - counter
  - local time
  - server time
  - terminal
  - account
  - symbol

FTMO reader:
- polls FILE_COMMON every ~200ms
- reads new PING
- writes ACK
- logs source and receive info

No trading logic.
No OrderSend.
Pure bridge validation.

Expected log:

AMP:
- `BRIDGE_WRITER: PING #N written`
- `BRIDGE_WRITER: ACK received for PING #N`

FTMO:
- `BRIDGE_READER: PING #N received`
- `BRIDGE_READER: ACK sent for PING #N`

Current operational blocker:

- files were generated on the Mac / ChatGPT side
- RDP session initially did not expose Mac filesystem
- solution chosen:
  reconnect FreeRDP with:
  `/drive:MacDownloads,$HOME/Downloads`
- then copy both .mq5 files into each terminal's:
  `MQL5\Experts`

NEXT STEP IS EXACTLY THIS BRIDGE TEST.

---

## 17. FORWARD SYSTEM ARCHITECTURE AFTER BRIDGE PASS

### EA #1 — GC_SENSOR_Q65

Runs in AMP MT5 on GCEZ26.

Responsibilities:

- maintain directional GC trade stream
- reconstruct required episode state
- repeated_failed_attack logic
- anchored dominance-reversal logic
- REV1 / REV2
- 5s post-REV2 signed impulse
- 30s aligned volume
- compare to frozen Q65:
  - impulse >= 0.0521
  - aligned volume >= 20.60
- emit ACCEPT / REJECT
- heartbeat
- write signal_id
- never trade AMP in current version

Recommended signal packet:

- protocol version
- signal_id
- GC event UTC
- REV2 UTC
- side
- GC symbol
- GC price
- impulse
- aligned volume
- thresholds
- status
- writer timestamp
- heartbeat sequence

### EA #2 — XAU_EXECUTOR_Q65

Runs in FTMO MT5 on XAUUSD.

Responsibilities:

- read ACCEPT
- reject duplicate signal_id
- reject stale signal
- require fresh GC heartbeat
- require fresh XAU quote
- MaxSpread filter
- one position maximum
- risk size from 0.25% equity
- calculate SL/TP from current completed XAU M1 ATR14
- SL 2.25 ATR
- TP 4.50 ATR
- timeout 300s
- log intended vs actual execution
- log spread/slippage/commission
- ACK signal
- persistent processed-signal state across restart

Safety:

- hard SL immediately
- no martingale
- no grid
- no pyramiding in first forward build
- no duplicate signal
- optional daily kill-switch ~1.5–2% for demo validation
- reject if feed stale / communication broken

---

## 18. FORWARD LOGGING REQUIREMENTS

Must log full causal chain:

`REV1 → REV2 → 5s impulse → 30s aligned volume → ACCEPT/REJECT → signal write → FTMO receive → order send → fill → SL/TP/TIMEOUT`

Timestamp chain:

- GC signal UTC
- REV2 UTC
- AMP local write time
- FTMO receive time
- order send time
- fill time
- exit time

This lets us separate:

- signal edge failure
- bridge latency
- FTMO execution divergence
- spread/slippage effects
- stale feed problems

---

## 19. RISK / PROP GUIDELINES FOR FORWARD

Current demo risk:

- 0.25% per trade

Historical LAB011:

- Full MaxDD ~0.51% at 0.25% risk
- MC p95 DD ~0.90%
- MC p99 ~1.07% approximate from 4.26R * 0.25%

Still keep prop-safe guardrails:

- daily loss hard stop well below 5%
- overall DD well below 10%
- first forward build target daily kill-switch 1.5–2%
- no simultaneous multiple XAU positions
- no averaging
- no martingale
- no execution during broken heartbeat / stale data

---

## 20. WHAT WE KNOW

High confidence / relatively strong evidence:

1. Raw REV2 alone is too weak.
2. Post-REV2 GC impulse is a real quality separator in current historical sample.
3. Post-REV2 aligned executed volume is also a strong separator.
4. Q60–Q80 threshold plateau exists.
5. Q65 intersection gives better historical quality than Q60.
6. Q65 execution geometry has a broad stable plateau.
7. SL around 2.25 ATR / TP around 4.5 ATR is not a single-point optimization.
8. Exact FTMO commission is small relative to observed edge.
9. LAB011 bootstrap and LOPO are supportive.
10. Historical path risk is low at 0.25% risk.

---

## 21. WHAT WE DO NOT KNOW

1. True independent forward/OOS performance.
2. Whether current AMP feed/live contract behavior exactly matches historical archive.
3. Whether `GCEZ26` remains the correct active sensor contract through roll.
4. Actual live bridge latency after FILE_COMMON deployment.
5. Actual FTMO slippage under forward conditions.
6. Whether fresh Q65 signal frequency matches historical density.
7. Whether edge survives future macro/volatility regimes.
8. Whether DOM adds additional useful filtering.
9. Whether Q65 performance will remain stable after 30–50 fresh trades.

---

## 22. DO NOT DO YET

- do not retune Q65 thresholds
- do not retune SL/TP
- do not add trailing stop
- do not add BE logic
- do not add DOM filter yet
- do not add session filter yet
- do not add news filter unless execution/rules require it
- do not combine with other XAU strategies during first forward sample
- do not move to live funded execution before fresh sample

---

## 23. IMMEDIATE NEXT STEPS

### Step 1 — Bridge

Reconnect RDP with Mac Downloads shared:

`xfreerdp ... /drive:MacDownloads,$HOME/Downloads`

Copy:

- `GC_BRIDGE_WRITER.mq5` → AMP `MQL5\Experts`
- `XAU_BRIDGE_READER.mq5` → FTMO `MQL5\Experts`

Compile and run.

Verify:

- common path is identical
- PING received
- ACK returned
- no file locking problems
- latency stable

### Step 2 — Dry-run production architecture

Build:

- `GC_SENSOR_Q65_DRYRUN`
- `XAU_EXECUTOR_Q65_DRYRUN`

No trading.

Verify live:

- REV2 events
- impulse
- aligned volume
- Q65 gate
- signal transport
- FTMO receive
- freshness

### Step 3 — Demo execution

Enable FTMO demo trading:

- 0.25% risk
- frozen Q65
- SL 2.25 ATR
- TP 4.50 ATR
- timeout 300s

### Step 4 — Fresh forward freeze

Collect:

- minimum 30–50 fresh trades

Do not retune.

Compare:

- EV
- PF
- CumR
- MaxDD
- losing streak
- signal frequency
- cost/slippage
- bridge latency

### Step 5 — Decision

Only after fresh sample:

- continue
- adjust infrastructure only
- or open a new LAB for signal changes

---

## 24. CANONICAL CURRENT STATUS

Research status:

`Q65 REV2 + 5s impulse + 30s aligned volume = READY_FOR_FORWARD_SHADOW`

Execution status:

`NOT_PRODUCTION_PROVEN`

Infrastructure status:

`VPS READY / TWO MT5 READY / BRIDGE TEST NEXT`

Frozen trade geometry:

- Entry: REV2 +30s
- SL: 2.25 ATR
- TP: 4.50 ATR
- RR: 1:2
- timeout: 300s
- risk: 0.25%

Frozen thresholds:

- impulse Q65 = 0.0521
- aligned volume Q65 = 20.60

Latest validation commit:

`0815b5930e315584dbcb99d455622eee25a040a9`

Current recovery file:

`research/gc/GC_XAU_COMPREHENSIVE_RESEARCH_BACKLOG_AND_RECOVERY_STATE_006.md`
