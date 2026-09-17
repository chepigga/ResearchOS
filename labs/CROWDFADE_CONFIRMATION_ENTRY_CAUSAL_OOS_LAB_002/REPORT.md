# CROWDFADE_CONFIRMATION_ENTRY_CAUSAL_OOS_LAB_002

## Verdict

**Production gate: FAIL / research candidate survives.**

The causal confirmation-entry mechanism is real enough to continue researching, but the development winner does **not** survive the predeclared OOS gate strongly enough for promotion to live CrowdFade.

The important positive result is that the previously observed Jun-Aug effect was independently reproduced, and the same month-by-month behavior transports from Binance to FTMO after correcting broker-server time. The important negative result is that the strongest development setting is regime-sensitive and fails in May OOS.

No live CrowdFade code or frozen baseline was modified.

---

## Hypothesis

Replace passive `1.5 ATR` limit commitment with a causal state machine:

1. `z >= +1` arms SHORT; `z <= -1` arms LONG.
2. Freeze side, signal price and signal ATR.
3. Wait for price to move **against the crowd** by `ConfirmATR`.
4. Enter at market on the first observed confirmation.
5. Place stop from actual entry.

This directly avoids the non-causal scheduling defect found in the old limit-order research simulator.

---

## Frozen design before OOS read

- Signal source: Binance `count_long_short_ratio`
- z-score: 72 x 5-minute observations, population SD, strict causal lookup
- Decision clock: M5
- `ConfirmATR`: `{0.25, 0.35, 0.40, 0.50}`
- `StopATR`: `{1.25, 1.50}`
- Signal TTL: 3h
- Pause: 3h
- Max hold: 6h
- BE: arm `+0.50 ATR`, lock `+0.15 ATR`
- Trailing: arm `+2.50 ATR`, distance `0.50 ATR`
- Opposite-z exit: enabled
- Binance execution proxy: first 1-second close after confirmation threshold is touched
- Development: **2026-06-01 through 2026-08-31**
- Untouched Binance OOS: **2026-03-01 through 2026-05-31**

The exit stack was deliberately left unchanged so LAB002 isolates the entry state machine.

---

## 1. Reproduction of the claimed Jun-Aug effect

The previously cited candidate `ConfirmATR=0.25 / StopATR=1.50` was reproduced on Binance seconds:

- Jun-Aug gross R/DD: **8.74**
- Gross EV: **+0.03695R**
- N: **566**
- WR: **73.14%**
- PF: **1.144**

So the prior `R/DD ~= 8` observation was not lost in reconstruction.

However, Binance OOS Mar-May for the same setting was weaker:

- N: **586**
- Gross EV: **+0.03946R** in aggregate
- PF: **1.161**
- R/DD: **3.88**

Monthly decomposition exposed instability hidden by the aggregate:

| Month | Binance gross EV |
|---|---:|
| Mar | +0.084R |
| Apr | +0.045R |
| May | **-0.012R** |
| Jun | +0.066R |
| Jul | +0.053R |
| Aug | **-0.009R** |

Thus the original `0.25 / 1.50` candidate is not a clean six-month stable solution.

---

## 2. Cost-model audit

The initial Binance replay also displayed fixed ATR cost proxies. These proxies should **not** be treated as FTMO truth.

Broker-native FTMO BTCUSD ticks show entry spread approximately:

- median spread / ATR: ~**0.0064-0.0069 ATR**
- p95: ~**0.012-0.018 ATR**

The earlier `0.054 ATR` full-spread proxy is therefore far too punitive for these FTMO BTCUSD data.

For this reason the decisive broker transport test uses real FTMO Bid/Ask and lets spread enter PnL naturally. **Commission is not included** because no validated crypto commission model was frozen in this LAB.

---

## 3. Critical timestamp audit

The FTMO tick export timestamps are `MT5_SERVER_HISTORY_TIME_MSC`, not UTC.

Cross-correlation of FTMO and Binance one-minute returns found:

- mapping: `UTC = FTMO server time - 180 minutes`
- best offset: **+180 min server offset**
- N: **42,368** matched one-minute observations
- return correlation at correct offset: **0.997761**
- moving only a few minutes away collapses the correlation toward zero

Therefore FTMO server time was **UTC+3** for the audited May period.

An earlier uncorrected FTMO replay produced unrealistically large results and was rejected. All broker results below use the validated UTC mapping.

---

## 4. Corrected FTMO broker-native replay

Data:

- FTMO-Demo BTCUSD
- ~31.1 million MT5 ticks
- May 1 through Aug 7, 2026
- real Bid/Ask
- execution aggregated to 1-second path
- M15 ATR remains on broker-server chart boundaries
- Binance z is queried using mapped UTC
- spread included naturally
- commission excluded

### Original development winner: 0.25 / 1.50

Jun-Aug-to-Aug7 development:

- N: **408**
- EV: **+0.04894R**
- PF: **1.211**
- R/DD: **9.54**

May OOS:

- N: **183**
- EV: **-0.02362R**
- PF: **0.916**
- R/DD: **-2.34**

This is the key failure. The large development R/DD survives broker transport, but **not May OOS**.

Matched-date direction is consistent between Binance and FTMO:

| Period | Binance gross EV | FTMO native EV |
|---|---:|---:|
| May | -0.012R | -0.024R |
| Jun | +0.066R | +0.037R |
| Jul | +0.053R | +0.100R |
| Aug 1-7 | -0.007R | -0.136R |

The two venues agree on the sign in every matched subperiod. This supports transport parity, but also confirms regime instability.

---

## 5. Post-hoc survivor: 0.35 / 1.25

This setting was **not** the preregistered winner and therefore cannot be promoted from LAB002. It is recorded only as a candidate for a new frozen test.

### Binance

Gross monthly EV:

| Month | EV |
|---|---:|
| Mar | +0.087R |
| Apr | +0.027R |
| May | +0.019R |
| Jun | +0.098R |
| Jul | +0.008R |
| Aug | +0.036R |

Aggregate:

- Mar-May OOS gross EV: **+0.04488R**
- Jun-Aug dev gross EV: **+0.04617R**

The two aggregate windows are nearly identical.

### FTMO transport

- May: **+0.02156R**
- Jun-Aug-to-Aug7: **+0.02389R**

Again the two aggregate windows are nearly identical, but statistical strength is weak (`t` only ~0.30 May and ~0.51 Jun-Aug partial).

May-July matched-date cumulative transport is unusually close:

- Binance: **+22.74R / 566 trades = +0.040R EV**
- FTMO: **+23.78R / 543 trades = +0.044R EV**

However Aug 1-7 is a real failure state on both venues:

- Binance: **-0.147R EV**, PF **0.565**, N=39
- FTMO: **-0.250R EV**, PF **0.365**, N=41

Binance later recovered during the remainder of August, which is why full-month August is positive. The early-Aug failure is therefore not a broker artifact.

---

## Interpretation

### What LAB002 proved

1. **Confirmation entry is causal.** It does not need future knowledge of whether a passive order will fill.
2. **The old Jun-Aug R/DD ~8 phenomenon is reproducible.**
3. **Broker transport is real after clock correction.** Binance and FTMO often agree closely on monthly direction and aggregate R.
4. **The edge is regime-sensitive.** May hurts the aggressive `0.25 / 1.50` candidate; early August hurts the whole confirmation family.
5. **The old ATR spread proxy was not appropriate for FTMO BTCUSD.** Native Bid/Ask transport is the better cost representation.

### What LAB002 did NOT prove

1. It did not validate `0.25 / 1.50` for production.
2. It did not establish `0.35 / 1.25` as OOS-valid because that setting became interesting only after observing the LAB002 surface.
3. It did not include a validated commission model.
4. It did not explain the early-Aug regime failure.

---

## Decision

**LAB002 = FAIL for live promotion, PASS as a research mechanism.**

Keep frozen live CrowdFade unchanged.

Freeze the post-hoc survivor only as a new research candidate:

```text
ConfirmATR = 0.35
StopATR    = 1.25
TTL        = 3h
Pause      = 3h
Hold       = 6h
BE         = 0.50 -> +0.15 ATR
Trail      = arm 2.50 / distance 0.50 ATR
Entry      = market after causal confirmation
```

The next valid test must use **fresh data not used anywhere in LAB002**. Do not tune the candidate further on Mar-Aug 2026.

Suggested next gate:

`CROWDFADE_CONFIRMATION_035_125_FROZEN_FRESH_OOS_LAB_003`

Primary question: does the frozen `0.35 / 1.25` candidate remain positive on genuinely unseen time and/or independent crypto symbols, including execution costs, without adding a regime filter after seeing early-Aug behavior?
