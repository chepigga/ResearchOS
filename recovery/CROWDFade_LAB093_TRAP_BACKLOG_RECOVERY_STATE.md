# CrowdFade LAB093 TRAP — Backlog / Recovery / Rebuild State

## Purpose

This document is the canonical recovery state for the standalone CrowdFade TRAP strategy derived through LAB088–LAB093.

Goal: be able to rebuild the standalone EA from zero even if the current MQ5 file is lost.

Current standalone EA:
`CrowdFade_LAB093_TRAP_ACTIVE_v001.mq5`

Do NOT mix this branch with GC-XAU research.

---

## Strategy idea in plain language

This is a crowd-trap / failed-participation strategy.

The bot does NOT trade simply because the crowd is heavily long or short.

It looks for:
1. extreme crowd positioning,
2. continued crowd participation,
3. growing open interest,
4. price moving against the crowded side.

Core interpretation:
- crowd keeps adding in one direction,
- new positions are entering,
- but price refuses to follow that crowd and starts moving against it,
- therefore the crowd may be trapped,
- trade in the opposite direction.

Example SELL:
- crowd extremely LONG,
- long/short ratio still rising,
- OI rising,
- price already rejecting upward pressure / moving down,
- SELL.

BUY is the mirror image.

---

## Research lineage

### LAB088 — LS × OI × Price Response Trap Edge
Purpose:
- decompose LS level, directional ΔLS, ΔOI and price response over 1/3/5/10m,
- measure MFE/MAE and TP hit rates.

Key result:
- broad `ΔLS↑ + OI↑ + non-response` was not enough,
- strongest specific cell was:
  `EXTREME LS + OI UP + PRICE AGAINST CROWD`,
- ~10m response was more useful than 1–5m.

Important caveat:
- LAB088 matrix cell did not yet explicitly require ΔLS rising in the final exact rule.

### LAB089 — Exact Trap Trigger
Frozen base trigger:
- `|Z| >= 2.5`
- directional `ΔLS > 0`
- `ΔOI > +0.02%`
- price response against crowd stronger than `0.10 ATR`

Candidate windows:
- BUY: 15m
- SELL: 10m

TRAIN Q50 thresholds frozen from historical sample:

BUY 15m:
- `dls_q50 = 0.02126813839258385`
- `doi_q50 = 0.00255557325829865`
- `reject_q50 = 0.49055696545663846 ATR`

SELL 10m:
- `dls_q50 = 0.0123825404840496`
- `doi_q50 = 0.0016377062940879`
- `reject_q50 = 0.3904050750016281 ATR`

LAB089 original admission:
- all 3 Q50 conditions required.

Result:
- strong historical and 2026 transfer,
- but frequency only ~10–11 trades/month.

### LAB090 — Taker confirmation
Question:
- does taker confirmation improve LAB089 trigger?

Result:
- hard taker confirmation did NOT improve robustness,
- often reduced precision or delayed entry,
- taker should remain diagnostic / confidence information only,
- NOT an entry gate.

Conclusion:
- price rejection is the main confirmation.

### LAB091 — Execution replay
Compared:
- MARKET after signal,
- RESP1,
- RESP3,
- 0.25 ATR retracement LIMIT with TTL 10m.

Frozen execution result:
- MARKET was best overall.
- Extra 1–3m confirmation threw away too many good signals.
- LIMIT reduced fills and degraded 2026 BUY transfer.

Frozen execution:
- BUY: MARKET, SL 1 ATR, TP 2.5R
- SELL: MARKET, SL 1 ATR, TP 2.0R
- max hold: 120 minutes
- same-bar TP/SL ambiguity in research counted conservatively as SL
- cost sensitivity tested at 0 / 0.5 / 2.0 bps round-trip proxy

### LAB092 — Frequency Frontier
Admissions tested:
- ALL_3_OF_3
- PRICE_LS
- PRICE_OI
- PRICE_PLUS_1OF2
- ANY_2_OF_3
- BASE

Key total results:

ALL_3_OF_3:
- historical ~10.65 trades/month
- hist EV +0.3619R
- hist PF 1.6957
- 2026 ~8.67 trades/month
- 2026 EV +0.5939R
- 2026 PF 2.3918

PRICE_PLUS_1OF2:
- historical ~21.05 trades/month
- hist EV +0.2922R
- hist PF 1.5470
- 2026 ~21.0 trades/month
- 2026 EV +0.2261R
- 2026 PF 1.4192

ANY_2_OF_3:
- historical ~28.33 trades/month
- hist EV +0.2579R
- hist PF 1.4777
- 2026 ~23.33 trades/month
- 2026 EV +0.2340R
- 2026 PF 1.4350

Conclusion:
- frequency can be increased,
- but aggressive universal loosening weakens PF,
- BUY and SELL should not use the same admission.

### LAB093 — Asymmetric BUY/SELL Frontier
All combinations of frozen LAB092 admissions were mixed independently by side.

Best robust candidate:

BUY:
- `ANY_2_OF_3`

SELL:
- `PRICE_LS`

Historical combined:
- N = 1347
- trades/month = 22.45
- EV = +0.301472R
- PF = 1.565106
- SumR = +406.083R
- MaxDD = 21.119R
- Recovery = 19.228
- positive months = 50/60

Forward diagnostic 2026:
- N = 119
- trades/month = 19.83
- EV = +0.296862R
- PF = 1.579009
- SumR = +35.327R
- MaxDD = 11.348R
- positive months = 6/6

This is the currently preferred admission.

---

# Canonical LIVE / DEMO strategy specification

## Global base trigger — mandatory for BOTH sides

Before asymmetric LAB093 admission is evaluated, the signal must satisfy the original LAB089 base trigger:

- `abs(Z) >= 2.5`
- directional `ΔLS > 0`
- `ΔOI > +0.0002` (+0.02%)
- directional price response is AGAINST crowd by more than `0.10 ATR`

This base trigger is mandatory.

Do NOT rebuild LAB093 by applying ANY2/PRICE_LS directly to raw extreme-Z observations without these base conditions.

---

## BUY signal

Window:
- 15 minutes

Base trigger:
- crowd is extremely SHORT
- `abs(Z) >= 2.5`
- directional `ΔLS > 0`
- `ΔOI > +0.02%`
- price moves against crowd by >0.10 ATR

Then evaluate 3 Q50 strength components:

A. LS strong:
- `dLS >= 0.02126813839258385`

B. OI strong:
- `dOI >= 0.00255557325829865`

C. Price rejection strong:
- `rejection >= 0.49055696545663846 ATR`

LAB093 BUY admission:
- ANY 2 OF 3 = true

If at least 2 of A/B/C are true:
- BUY MARKET

Execution:
- SL = 1.0 ATR
- TP = 2.5R
- max hold = 120 min

---

## SELL signal

Window:
- 10 minutes

Base trigger:
- crowd is extremely LONG
- `abs(Z) >= 2.5`
- directional `ΔLS > 0`
- `ΔOI > +0.02%`
- price moves against crowd by >0.10 ATR

Q50 components:

A. LS strong:
- `dLS >= 0.0123825404840496`

B. OI strong:
- `dOI >= 0.0016377062940879`

C. Price rejection strong:
- `rejection >= 0.3904050750016281 ATR`

LAB093 SELL admission:
- PRICE_LS
- require A AND C
- Q50 OI is NOT required

Important:
- base trigger still requires `dOI > +0.02%`

If A and C are true:
- SELL MARKET

Execution:
- SL = 1.0 ATR
- TP = 2.0R
- max hold = 120 min

---

# Data requirements

## Long/Short ratio

Source:
- Binance Futures BTCUSDT Global Long/Short account ratio

Normalization:
- rolling Z-score
- window = 6 hours
- LAB lineage used the same crowd-ratio framework as CrowdFade.

Directional interpretation:
- crowd LONG extreme -> potential SELL setup
- crowd SHORT extreme -> potential BUY setup

Directional ΔLS:
- normalize change into crowd direction,
- positive value means the crowd is becoming more extreme in its current direction.

---

## Open Interest

Need historical OI change over the signal window, not only current OI.

Live implementation must be able to calculate:
- current OI
- prior OI at BUY: 15m ago
- prior OI at SELL: 10m ago

Use Binance Futures historical open-interest data where needed.

Directional threshold:
- base OI expansion > +0.02%

Q50 OI:
- BUY >= 0.255557325829865%
- SELL >= 0.16377062940879%

---

## Price / ATR

Broker execution symbol:
- usually BTCUSD on MT5 broker

Signal crowd/OI source:
- Binance BTCUSDT

ATR:
- use broker BTCUSD price series consistently for live execution calculations unless parity testing explicitly freezes another source.

Price rejection:
- compute crowd-direction price response over the window,
- convert to ATR units,
- rejection is the magnitude of movement AGAINST crowd.

BUY:
- crowd SHORT,
- price rising = against crowd

SELL:
- crowd LONG,
- price falling = against crowd

---

# Execution specification

Entry:
- MARKET immediately after full signal exists
- no extra 1m or 3m response confirmation
- no retracement limit
- no taker gate

Risk:
- default 0.25% equity risk per trade
- user preferred range 0.25–0.5%, but current recommendation is 0.25%

Stops:
- fixed SL = 1 ATR from actual fill

Targets:
- BUY TP = 2.5R
- SELL TP = 2.0R

Time stop:
- 120 minutes

Signal cooldown / dedup:
- 30 minutes

Do not use:
- martingale
- grid
- averaging down
- aggressive hedging
- latency arbitrage

---

# Standalone EA identity

Preferred file:
`CrowdFade_LAB093_TRAP_ACTIVE_v001.mq5`

Preferred magic:
`715193`

Trade comments:
- `LAB093_BUY_ANY2`
- `LAB093_SELL_PRICE_LS`

Terminal global prefix:
- `CF093_`

CSV:
- `CrowdFade_LAB093_TRAP_ACTIVE_v001.csv`

The standalone bot must NOT depend on LAB118 or LAB087 code paths.

It may reuse infrastructure patterns:
- WebRequest
- Binance JSON parsing
- ATR
- lot sizing
- margin checks
- position persistence
- max hold
- logging

But strategy state must remain independent.

---

# Safety / account layer

Current recommended defaults:
- RiskPercent = 0.25
- MaxConcurrentPositions = conservative / configurable
- cooldown = 30m
- max hold = 120m
- margin cap enabled
- broker STOPLEVEL and FREEZELEVEL validation
- spread/ATR safety filter may exist, but must not silently alter frozen LAB logic during research comparison

On netting accounts:
- do not mix unrelated strategy positions into one symbol position.

On hedging accounts:
- separate magic allows clean attribution.

---

# Research limitations

1. 2021–2025 is discovery / historical research, not pristine untouched OOS.
2. 2026 Mar–Aug was reused across multiple LABs and is diagnostic forward data, NOT pristine OOS.
3. Binance futures is a proxy for broker-native BTCUSD execution.
4. LAB091 execution replay uses 1m bars and a cost proxy; broker spread/slippage/fills can differ.
5. Sequential DD does not model all concurrency / portfolio margin interactions.
6. Limit-touch assumptions were avoided in final execution because MARKET won.
7. LAB093 should be validated on demo before increasing risk.

---

# Recovery procedure — rebuild from zero

If all MQ5 files are lost:

1. Recreate Binance Long/Short ratio reader for BTCUSDT.
2. Maintain 6h rolling Z-score.
3. Recreate historical/current OI reader.
4. Read broker BTCUSD ATR.
5. Build BUY 15m and SELL 10m feature windows.
6. Calculate:
   - abs(Z)
   - directional ΔLS
   - ΔOI
   - price rejection in ATR
7. Apply mandatory LAB089 base trigger.
8. BUY:
   - score Q50 LS/OI/rejection,
   - require any 2 of 3.
9. SELL:
   - require Q50 price rejection AND Q50 LS.
10. On accepted signal:
   - MARKET entry,
   - risk 0.25% equity,
   - SL 1 ATR,
   - BUY TP2.5R / SELL TP2R.
11. Add 120m time stop.
12. Add 30m dedup/cooldown.
13. Use magic 715193 and LAB093-specific comments.
14. Log every signal evaluation and every rejection reason.
15. Compile in current MT5 MetaEditor.
16. Demo forward-test before production.
17. Compare live signal counts to expected ~20–22 trades/month, allowing regime variance.
18. Audit LIVE vs LAB parity before changing thresholds.

---

# Do-not-change list without a new LAB

Do NOT silently retune:
- |Z| >= 2.5
- BUY window 15m
- SELL window 10m
- base ΔOI > +0.02%
- base rejection >0.10 ATR
- BUY Q50 thresholds
- SELL Q50 thresholds
- BUY ANY2 admission
- SELL PRICE_LS admission
- MARKET execution
- BUY TP2.5R
- SELL TP2.0R
- SL1R
- hold120m
- cooldown30m

Any change to these requires a new LAB and separate version.

---

# Next research backlog

Priority 1 — LIVE/LAB parity audit
- compare every demo signal feature against offline calculation,
- especially OI timestamp alignment and price-window alignment.

Priority 2 — broker execution transfer
- measure IC Markets / chosen broker:
  - spread
  - slippage
  - fill delay
  - contract size
  - margin
- replay with measured costs.

Priority 3 — monthly / regime robustness
- inspect negative historical months,
- especially whether large losing months cluster by volatility or trend regime,
- do NOT add filters until tested causally.

Priority 4 — position overlap / prop DD
- simulate actual overlapping positions,
- daily DD,
- overall DD,
- 0.25% vs 0.33% vs 0.5% risk.

Priority 5 — pristine OOS
- freeze LAB093 now,
- collect future unseen data without retuning.

---

# Current recommendation

Preferred strategy:
- LAB093 asymmetric standalone

Admission:
- BUY ANY2
- SELL PRICE_LS

Execution:
- MARKET

Risk:
- 0.25%

Expected research frequency:
- historical ~22.45 trades/month
- reused 2026 diagnostic ~19.83 trades/month

Historical:
- EV ~+0.301R
- PF ~1.565
- MaxDD ~21.12R
- 50/60 positive months

2026 diagnostic:
- EV ~+0.297R
- PF ~1.579
- MaxDD ~11.35R
- 6/6 positive months

Status:
- DEMO CANDIDATE
- NOT production-proven
- thresholds and execution should now be frozen until forward evidence justifies a new LAB.
