# GC→XAU PRODUCTION RECOVERY STATE — LAB040 / v042

**Checkpoint date:** 2026-09-29  
**Purpose:** single self-contained recovery/backlog document. A future session should be able to continue the project from this file alone without reconstructing prior chats or searching for research files.

---

# 1. CURRENT PROJECT STATE

We are building a causal GC futures / COMEX → XAUUSD execution system.

The current historical candidate is **LAB040**.

The current executor lineage is **XAU_EXECUTOR_CAUSAL_BROAD_v042_LAB040_PRODUCTION**.

The current sensor lineage is **GC_SENSOR_CAUSAL_BROAD v020/v021 production-equivalent signal logic**.

Important terminology:
- "production bot" means the EA architecture is intended to become the real trading bot.
- It is currently being run on a **demo account only for forward validation**.
- Do NOT call the EA a demo bot.
- Do NOT silently retune the frozen LAB040 logic from early forward noise.

Current account observed at v042 startup:
- server: FTMO-Demo
- account: 1514715065
- account tradeMode: 0
- marginMode: 2
- leverage: 1:100
- symbol: XAUUSD
- tick size: 0.01
- tick value: 1.00
- contract size: 100
- min lot: 0.01
- volume step: 0.01
- current EA risk/trade: **0.25% equity**
- magic: 650032027

---

# 2. FROZEN LAB040 ARCHITECTURE

## Trading legs

TRADE:
- DOM2
- DOM_CONT
- MIX2

SHADOW / OBSERVATION ONLY:
- BASE1

DO NOT TRADE:
- REV1
- REV2
- REV3P
- MIXED
- other non-approved labels

BASE1 remains visible and is retained in the observation/confidence stream, but does not open positions.

The reason BASE1 is excluded from main execution is empirical, not conceptual: exact chronology/full-backfill LAB040 showed that adding BASE1 increased total historical R but degraded WR, PF, EV, drawdown and loss streak.

---

# 3. EXACT SENSOR → EXECUTOR CONTRACT

The GC sensor writes one causal signal record with this field order:

```
GCXAU_V2;
signal_id;
TRADE;
event_ms;
direction;
gc_atr;
label;
episode_index;
impact_deterioration;
attack2_volume;
write_epoch;
sensor_symbol
```

Meaning:
1. protocol = GCXAU_V2
2. signal_id = unique monotonic signal identifier
3. message type = TRADE
4. event_ms = GC event timestamp
5. direction = XAU trade direction already derived by sensor
6. gc_atr = GC ATR/context value
7. label = BASE1 / DOM2 / DOM_CONT / MIX2 / etc.
8. episode_index = causal episode index
9. impact_deterioration = causal signal feature
10. attack2_volume = causal second-attack volume
11. write_epoch = sensor write timestamp
12. sensor_symbol = source GC contract/symbol

The executor parser and sensor writer were audited: **field ordering matches**.

## Direction semantics

The sensor performs the inversion from failed aggressive crowd attack to intended XAU direction.

- failed aggressive SELL pressure / failed downside impact → `direction=+1` → XAU BUY
- failed aggressive BUY pressure / failed upside impact → `direction=-1` → XAU SELL

The executor must NOT invert direction a second time.

---

# 4. SENSOR CAUSAL LOGIC

Canonical Broad sensor lineage is LAB018 / GC_SENSOR_CAUSAL_BROAD_DEMO_v020. v021 production copy must preserve the same signal logic.

Core causal event:
- two contiguous 30-second buckets
- same crowd direction
- second attack impact <= first attack impact
- interpreted as repeated failed attack
- signal direction is opposite crowd direction
- 60-second cooldown
- 300-second episode anchor
- startup warm-up approximately 30 minutes per disconnected quality window
- no future episode class may be used

Episode labels:
- BASE1 = first episode signal
- DOM2 = second signal, same direction as first
- MIX2 = second signal, opposite first
- if first two mixed, later events can become MIXED
- if first two same, continuation in original direction becomes DOM_CONT
- reversals become REV1 / REV2 / REV3P

Labels are generated causally at signal time. No future label information is allowed.

---

# 5. PERSISTENT LIVE CONFIDENCE — v042 DECISION

The previously proposed external historical **seed file is REJECTED**.

There must be **no historical seed dependency** in production.

The EA must build confidence from the live sensor stream and persist it across MT5/VPS restarts.

## Confidence features

Use:
- attack2_volume
- episode_index

Keep BUY and SELL histories separately.

For current signal N:

```
history = signals 1 ... N-1
volume_percentile = percentile_rank(attack2_volume_N against prior same-side history)
episode_percentile = percentile_rank(episode_index_N against prior same-side history)

confidence_N = average(volume_percentile, episode_percentile)
```

CRITICAL causal ordering:

```
receive signal N
→ verify not duplicate
→ compute confidence using PRIOR history only
→ make warm-up/filter decision
→ append signal N to persistent history
→ persist state
```

The current signal must NEVER participate in its own percentile.

## Thresholds

Frozen thresholds:
- BUY confidence >= **0.60**
- SELL confidence >= **0.75**

Minimum history:
- at least **50 prior observations for the corresponding SIDE**

Before 50 prior observations for a side:
- signal is logged
- signal is appended to history
- NO TRADE for that side

Expected first-start warm-up estimate based on historical Broad frequency:
- roughly 2–5 days for both sides, market activity dependent
- this is an estimate, not a guaranteed duration

After the first warm-up, history must survive restarts so this delay is not repeated.

## Persistent state requirements

EA must persist:
- BUY observation history
- SELL observation history
- attack2_volume
- episode_index
- unique signal_id / deduplication state
- enough metadata to safely recover after restart

On restart:
- load persistent history
- continue from prior counts
- do not reset confidence distribution

Duplicate protection:
- the same signal_id must never be added twice
- the same signal must never produce a duplicate trade after restart

Corrupt/unreadable state:
- fail safe
- do not silently trade with a reset or partial distribution
- log the error clearly

BASE1:
- no trade
- **still contributes as a causal observation to confidence history**

This is intentional.

---

# 6. SIGNAL PROCESSING DECISION TREE

```
NEW GC SIGNAL
      |
      +-- duplicate signal_id? ------ YES → IGNORE
      |
      NO
      ↓
validate message / age / fields
      ↓
calculate CONFIDENCE
using PRIOR same-side live history only
      ↓
append observation to persistent history
      ↓
persist state
      |
      +-- prior side history < 50? -- YES → WARM-UP / NO TRADE
      |
      +-- BASE1? -------------------- YES → SHADOW / NO TRADE
      |
      +-- label not in
      |   DOM2/DOM_CONT/MIX2? ------- YES → NO TRADE
      |
      +-- BUY confidence < 0.60? ---- YES → NO TRADE
      |
      +-- SELL confidence < 0.75? --- YES → NO TRADE
      |
      ↓
ARM XAU SIGNAL
      ↓
wait max 10 minutes
for favorable XAU response +0.50 ATR
      |
      +-- no response ---------------→ EXPIRE
      ↓
RESPONSE CONFIRMED
      ↓
wait max next 10 minutes
for 0.50 ATR retracement
      |
      +-- no retracement ------------→ EXPIRE
      ↓
check ONE POSITION TOTAL
      |
      +-- position already open -----→ BLOCK / LOG
      ↓
ENTRY
```

GC signal is therefore **NOT an immediate market-entry command**.

GC identifies direction and context. XAU must independently confirm the direction, then retrace, before execution.

---

# 7. XAU RESPONSE / RETRACEMENT ENTRY

Frozen LAB040 entry logic:

## BUY
1. valid causal GC BUY signal
2. approved leg
3. confidence >= 0.60
4. XAU moves favorably **+0.50 ATR** within 10 minutes
5. after that response, XAU retraces **0.50 ATR** within the next 10 minutes
6. enter BUY only after retracement condition

## SELL
Mirror:
1. valid GC SELL
2. approved leg
3. confidence >= 0.75
4. XAU moves **-0.50 ATR** favorably within 10 minutes
5. then retraces +0.50 ATR within next 10 minutes
6. enter SELL

Do not replace this with immediate market entry.

This entry architecture was selected because earlier research showed that GC often identified the destination/direction before the best XAU execution point. Immediate entry suffered adverse excursion; response + retracement improved precision.

---

# 8. POSITION MANAGEMENT — FROZEN LAB040

## BUY
- initial SL = **1.5 ATR**
- profit protection trigger = **+3R**
- after trigger move SL to **+1R**
- runner maximum hold = **120 minutes**

## SELL
- initial SL = **2.0 ATR**
- profit protection trigger = **+1.5R**
- after trigger move SL to **+0.5R**
- runner maximum hold = **120 minutes**

Portfolio:
- **ONE POSITION TOTAL**
- only one own XAU position may be active
- accepted later candidates while position is active are blocked/logged
- no automatic re-entry from a previously blocked signal

Current v042 startup print showed emergency TP:
- BUY TP = 45 ATR
- SELL TP = 60 ATR
- equivalent to 30R

This is intended only as a distant emergency hard TP so normal runner logic is not truncated. Do not tune it from the current historical sample.

Risk:
- current forward setting **0.25% equity per trade**
- user generally prefers 0.25–0.5% risk
- do not raise risk because of historical PF

---

# 9. LAB038 — RAW DIRECTION-ONLY TEST

Question tested:
Can structural labels/routing be removed and trade only raw GC direction + confidence + response/retracement?

Raw Broad after development-month exclusion:
- 89,387 signals
- threshold passed: 28,888
- response: 22,006
- response + retracement: 21,731
- executed after ONE POSITION TOTAL: 4,520

LAB035 routed:
- N499
- WR36.67%
- PF1.9302
- EV +0.6028R
- Sum +300.8024R
- MaxDD17.7346R

RAW direction + confidence:
- N4520
- WR33.89%
- PF1.2555
- EV +0.1726R
- Sum +780.3124R
- MaxDD88.8422R

Conclusion:
**REJECT raw direction-only architecture.**

Raw GC direction contains information, but structural selection concentrates the edge dramatically. The larger raw SumR is not evidence of superiority because trade count and DD explode while PF/EV collapse.

---

# 10. LAB039 — FULL LEG ATTRIBUTION

LAB035 executed-trade attribution:

## DOM2
- N261
- WR42.53%
- PF2.1055
- EV +0.6502R
- Sum +169.7061R
- MaxDD10.6334R
- active months14
- positive12 / negative2

Sides:
- BUY N180 PF2.1588 EV+0.7445R Sum+134.011R
- SELL N81 PF1.9427 EV+0.4407R Sum+35.695R

**Strongest and most stable core leg.**

## DOM_CONT
- N67
- WR31.34%
- PF2.0390
- EV +0.7300R
- Sum +48.9131R
- MaxDD17.5613R
- positive5 / negative5 months

Sides:
- BUY N55 PF2.3860 EV+0.9800R
- SELL N12 PF0.3908 EV-0.4157R

SELL sample is too small to make a hard independent exclusion from this attribution alone.

## MIX2
- N73
- WR34.25%
- PF1.7848
- EV +0.5281R
- Sum +38.5499R
- MaxDD9.4911R
- positive5 / negative5 months

## BASE1
- N98
- WR26.53%
- PF1.5922
- EV +0.4452R
- Sum +43.6333R
- MaxDD23.2556R
- positive5 / negative7 months
- median monthly R negative

BASE1 adds historical profit but has the weakest stability/equity quality.

---

# 11. LAB040 — EXACT CHRONOLOGY WITH FULL BACKFILL

This is the key leg-selection experiment.

Frozen LAB035 candidate stream:
- total candidates = **768**
- original LAB035 executed = 499
- original blocked = 269

For every tested leg set, ONE POSITION TOTAL chronology was replayed from scratch.

If removing a leg freed a position slot, the next eligible candidate was allowed to execute. Therefore these are not simple attribution deletions; they include **full backfill within the frozen 768-candidate stream**.

## DOM2 ONLY
- eligible375
- blocked80
- executed295
- WR41.36%
- PF2.0423
- EV +0.6256R
- Sum +184.5408R
- MaxDD11.3040R
- max loss streak7

BUY:
- N209
- PF2.0899
- EV+0.7151R
- Sum+149.4626R

SELL:
- N86
- PF1.8789
- EV+0.4079R
- Sum+35.0781R

## DOM2 + DOM_CONT
- eligible477
- blocked122
- N355
- WR39.72%
- PF1.9785
- EV+0.6037R
- Sum+214.2973R
- MaxDD13.3976R

## DOM2 + MIX2
- eligible515
- blocked155
- N360
- WR40.00%
- **PF2.0661**
- **EV+0.6546R**
- Sum+235.6613R
- **MaxDD12.7572R**

This is the strongest tested lower-DD / risk-adjusted multi-leg alternative.

BUY:
- N274
- PF2.1073
- EV+0.7321R
- Sum+200.5831R

SELL:
- N86
- PF1.8789
- EV+0.4079R
- Sum+35.0781R

## DOM2 + DOM_CONT + MIX2 — CURRENT MAIN CANDIDATE
- eligible617
- blocked202
- **N415**
- **WR39.28%**
- **PF2.0490**
- **EV+0.6519R**
- **Sum+270.5347R**
- **MaxDD14.5952R**
- max loss streak11

BUY:
- N317
- PF2.1461
- EV+0.7585R
- Sum+240.4446R

SELL:
- N98
- PF1.6256
- EV+0.3070R
- Sum+30.0902R

## ALL FOUR INCLUDING BASE1 — OLD LAB035
- eligible768
- blocked269
- N499
- WR36.67%
- PF1.9302
- EV+0.6028R
- Sum+300.8024R
- MaxDD17.7346R
- max loss streak13

Adding BASE1 to the 3-leg core:
- +84 executed trades
- about +30.27R
but:
- WR 39.28% → 36.67%
- PF 2.049 → 1.930
- EV +0.652R → +0.603R
- DD 14.60R → 17.73R
- loss streak 11 → 13

**Current decision: trade DOM2 + DOM_CONT + MIX2; BASE1 shadow only.**

---

# 12. CURRENT v042 STARTUP OBSERVATION

Observed Journal at first launch:

```
V042 CONF: no prior live history. Warm-up starts from zero; BUY=0 SELL=0
BROAD_DEMO: restored last signal=GCX_1790703540000_1354
XAU_EXECUTOR_CAUSAL_BROAD_v042_LAB040_PRODUCTION started.
COMMON PATH: C:\Users\Administrator\AppData\Roaming\MetaQuotes\Terminal\Common
Account login=1514715065 server=FTMO-Demo tradeMode=0 marginMode=2 leverage=1:100
Symbol=XAUUSD tickSize=0.01000000 tickValue=1.00000000 contract=100.00 minLot=0.0100 step=0.0100
LAB040 v042 ONE_POSITION_TOTAL: risk/trade=0.250% BUY SL=1.50ATR TP=45.00ATR timeout=7200s | SELL SL=2.00ATR TP=60.00ATR RR=30.00 timeout=7200s | shadow=15m maxConcurrent=6 magic=650032027
```

Interpretation:
- first v042 run correctly has no live confidence history yet
- last sensor signal was restored, preventing accidental replay of old signal
- account/symbol specification read successfully
- risk and stop parameters match current forward design

Important check on next restart:
After new observations have been received, startup should report restored BUY/SELL confidence history counts rather than `no prior live history`.

If it repeatedly says no history after signals were processed, persistence is broken and trading must be stopped until fixed.

---

# 13. REQUIRED FORWARD LOGGING / AUDIT

For every incoming sensor signal, log enough information to reconstruct the decision:

- signal_id
- event timestamp
- receive timestamp
- sensor symbol
- side/direction
- leg
- attack2_volume
- episode_index
- impact_deterioration
- number of prior BUY observations
- number of prior SELL observations
- volume percentile
- episode percentile
- resulting confidence
- warm-up PASS/FAIL
- leg PASS/SHADOW/REJECT
- confidence PASS/FAIL
- XAU reference price
- XAU ATR used
- response target
- response hit timestamp/price
- retracement target
- retracement hit timestamp/price
- signal expiry reason
- ONE_POSITION block
- entry timestamp/price
- requested lot
- actual fill / slippage
- spread at entry
- SL
- emergency TP
- lock trigger activation
- SL modification result/retcode
- exit timestamp/price
- exit reason
- realized R
- MFE/MAE if practical

Desired Journal chain for a valid trade:

```
SENSOR SIGNAL
→ RECEIVED
→ CONF / WARMUP
→ LEG PASS
→ ENTRY_ARMED
→ RESPONSE_HIT
→ RETRACEMENT_HIT
→ ORDER
→ FILL
→ LOCK (if triggered)
→ EXIT
```

---

# 14. KNOWN METHODOLOGICAL LIMITATIONS

Do not forget these when interpreting forward vs historical results:

1. LAB040 is not a fresh independent temporal OOS after all research decisions; later labs reuse the same historical universe.
2. XAU historical execution is based on M1 bid/ask OHLC proxy, not full tick-sequence reconstruction.
3. Exact intrabar sequence is unknown.
4. Historical cost is a calibrated proxy, not guaranteed FTMO/live execution cost.
5. ONE POSITION TOTAL materially changes chronology and candidate availability.
6. LAB040 full backfill is exact only within the frozen 768-candidate stream.
7. Confidence thresholds were developed in the prior causal research lineage. Do not re-normalize them onto arbitrary raw signal universes.
8. LAB038 proved raw-signal distribution shift can materially dilute the edge.
9. Right-tail winners matter significantly. Do not add tight TP/trailing merely to increase WR.
10. Do not add global ATR filter from LAB036/037; weakness was not universally explained by high ATR.
11. Do not add universal loss breaker; LAB023 rejected it.
12. Do not fine-tune 0.50 ATR response/retracement or confidence decimals on the same history.
13. Realized historical DD is not the same as floating-equity prop DD.
14. Forward execution must validate sensor → state → entry parity before risk is increased.

---

# 15. HISTORICAL RESEARCH LINEAGE — COMPACT RECOVERY

Key milestones before LAB038:

- LAB012: causal confidence layer identified HIGH-quality signals using prior-only percentiles of attack2_volume + episode_index.
- LAB013–016: immediate response / execution studies.
- LAB017–019: target/runner/profit-lock studies; runner value established.
- LAB020: side-specific portfolio.
- LAB021: failure regime analysis.
- LAB022/023: breaker studied; universal breaker rejected.
- LAB024/025: asymmetric confidence; BUY >=0.60, SELL >=0.75 selected.
- LAB026: response +0.50 ATR then retracement0.50 ATR materially improved entry precision.
- LAB027–031: SELL exit and protected runner studies.
- LAB032: BUY +3→lock1 and SELL +1.5→lock0.5 portfolio.
- LAB033: winner concentration stress; strategy is right-tail dependent but not dependent on one jackpot.
- LAB034: coarse SL test.
- LAB035: asymmetric SL BUY1.5 / SELL2 became historical leader.
- LAB036/037: regime/ATR audit; do not introduce global ATR filter.
- LAB038: raw direction-only architecture rejected.
- LAB039: full leg attribution.
- LAB040: exact chronology/full backfill; 3-leg core frozen.

---

# 16. CURRENT BACKLOG — ORDER OF OPERATIONS

## P0 — verify v042 live persistence
Wait for new GC Broad signals.

Confirm:
1. sensor writes signal
2. executor receives it
3. signal is not duplicated
4. prior history count is correct
5. confidence is calculated before append
6. observation is persisted
7. restart MT5
8. verify history count restores correctly
9. verify last signal ID restores correctly

Do NOT wait for an actual trade to test persistence; warm-up observations are enough.

## P0 — sensor/executor parity
For several live signals manually compare:
- sensor line
- executor parsed fields
- direction
- label
- attack2_volume
- episode_index
- confidence-history counts

Any mismatch is a stop condition.

## P1 — complete warm-up
Allow at least 50 prior BUY and 50 prior SELL observations to accumulate naturally.

No threshold reduction to accelerate trading.

## P1 — first executable signals
After warm-up inspect every:
- PASS
- confidence reject
- response expiry
- retracement expiry
- position block
- actual trade

Check timing against XAU chart.

## P1 — forward execution parity
Compare real fill to frozen historical assumptions:
- response/retracement geometry
- ATR
- spread
- slippage
- stop distance
- lot sizing
- lock modification
- timeout

## P2 — forward sample
Do not optimize from first few trades.
Collect an independent sample before changing frozen signal thresholds.

Track separately:
- DOM2
- DOM_CONT
- MIX2
- BASE1 shadow

This is important: BASE1 remains observable so forward evidence can later confirm or contradict its historical weakness.

## P2 — risk
Stay at 0.25% while forward parity is unproven.
Do not move to 0.5% merely because historical PF is >2.

---

# 17. WHAT MUST NOT BE DONE

- Do not restore the rejected seed-file architecture.
- Do not reset confidence history on every restart.
- Do not use the current signal in its own percentile.
- Do not invert sensor direction again in executor.
- Do not re-enable BASE1 main execution without a new explicit experiment.
- Do not replace response/retracement with immediate market entry.
- Do not trade raw direction-only.
- Do not introduce a global ATR filter.
- Do not introduce universal breaker.
- Do not fine-tune thresholds from this historical sample.
- Do not interpret demo-account status as meaning the EA is a throwaway demo EA.
- Do not increase risk before forward parity.

---

# 18. CURRENT FROZEN SPEC IN ONE BLOCK

```
SOURCE:
GC futures causal Broad sensor

TRADE LEGS:
DOM2
DOM_CONT
MIX2

SHADOW:
BASE1

CONFIDENCE:
prior-only live persistent percentile
features = attack2_volume + episode_index
BUY >= 0.60
SELL >= 0.75
minimum prior observations per side = 50

ENTRY:
favorable response = +0.50 ATR within 10m
then retracement = 0.50 ATR within next 10m

BUY:
SL = 1.5 ATR
at +3R → lock +1R
max hold = 120m

SELL:
SL = 2.0 ATR
at +1.5R → lock +0.5R
max hold = 120m

PORTFOLIO:
ONE POSITION TOTAL
risk = 0.25% equity during forward validation

LAB040 HISTORICAL 3-LEG:
N = 415
WR = 39.28%
PF = 2.0490
EV = +0.6519R
Sum = +270.5347R
MaxDD = 14.5952R
max loss streak = 11

STATUS:
production architecture
currently forward-validating on demo account
not yet proven by independent live/forward sample
```

---

# 19. RECOVERY INSTRUCTION FOR NEXT SESSION

If this project is resumed in another chat/session:

**Do not restart discovery. Do not ask for old LAB files merely to understand the current state. Use this document as the canonical recovery state.**

Immediate task is:
**continue v042 forward parity validation starting with persistent live confidence history and sensor→executor signal audit.**

Only request new runtime logs/files when they are needed to validate new observations or modify code.
