# GC_AEIF_CANONICAL_BACKLOG_001

## STATUS — CANONICAL / SEARCH CLOSED

This document is the canonical backlog for the **GC futures / COMEX order flow / AEIF / XAU execution** lineage.

**Do not repeat the forensic search for the old AEIF formula, 105/92 fingerprints, confirmation rule, or the two missing LONG transfers.** Those points are resolved/frozen below from recovered historical Rithmic and XAU artifacts.

Only reopen forensic reconstruction if a genuinely new primary artifact appears that directly contradicts this backlog, e.g. the original LAB022 51-row ledger or original frozen source code.

`AMP_GC_OOS_001` was not used to select or resolve any of the rules below.

---

## 1. Canonical historical source artifacts

### Rithmic GC raw archive

- file: `GC_RITHMIC_40D_003_GCZ6.zip`
- GitHub Release tag: `GC`
- symbol: `GCZ6`
- coverage: 2026-08-03 through 2026-09-11 UTC
- raw trade prints: **3,949,646**
- M5 bars with trades: **8,231**
- explicit aggressor: Rithmic `BUY` / `SELL`
- SHA256: `b12465a783f36aac41b82a9f2a5c4e74bd2dcf7024ffc3636e8c41a8fd01e803`

### Historical XAU mapping source

- file: `XAUUSD_M1_2026.csv`
- GitHub Release tag: `GC`
- rows: **36,489**
- file-clock coverage: `2026-08-03 01:05` through `2026-09-08 20:03`
- historical clock mapping: **file clock = UTC + 2h**
- SHA256: `0e0c75fab3516fb31d3db1f3d3a7a25a848c0340b1cbd894cca66e628f3ecb18`

### Historical research backlog

- file: `GC_Footprint_AEIF_Research_Backlog.docx`
- release tag: `GC`
- SHA256: `043a5bfe612f6cefc516e2aadf5f890cd7758a6f78d3c811481f2bdf52fc087c`

---

## 2. Frozen GC M5 footprint

Working timeframe: **M5, UTC clock bins**.

For each completed M5 bar:

```text
delta      = aggressive BUY volume - aggressive SELL volume
delta_frac = delta / (BUY volume + SELL volume)

lower20_cut = low + 0.20 * (high-low)
upper20_cut = high - 0.20 * (high-low)

sell_lower20 = SELL volume at trade_price <= lower20_cut
buy_upper20  = BUY volume at trade_price >= upper20_cut

sell_loc = sell_lower20 / total SELL volume, else 0
buy_loc  = buy_upper20 / total BUY volume, else 0
```

20% price boundaries are inclusive using native `<=` / `>=` comparisons.

ATR for the **AEIF GC core** is **Wilder ATR14 on M5 true range**.

---

## 3. Frozen causal reference windows

Every threshold uses only the **prior 240 completed M5 bars**.

The current bar is excluded from its own thresholds.

```text
LONG delta tail  = prior-240 Q10(delta_frac)
SHORT delta tail = prior-240 Q90(delta_frac)
LONG location    = prior-240 Q75(sell_loc)
SHORT location   = prior-240 Q75(buy_loc)
```

Do not replace 240 M5 with 48 M5. The 48-M5/ATR3 branch is retained only as an old negative-control lineage.

---

## 4. Frozen AEIF CORE

### LONG

```text
delta_frac <= prior Q10(delta_frac)
AND sell_loc >= prior Q75(sell_loc)
AND max(0, open-close) / ATR14_Wilder_M5 <= 0.15
```

Interpretation: extreme aggressive selling concentrated near the lower part of the bar, but sellers fail to produce proportional downside body impact.

### SHORT

```text
delta_frac >= prior Q90(delta_frac)
AND buy_loc >= prior Q75(buy_loc)
AND max(0, close-open) / ATR14_Wilder_M5 <= 0.15
```

Mirror interpretation for aggressive buying failing to generate proportional upside impact.

### Historical fingerprint

```text
CORE = 105
LONG = 48
SHORT = 57
```

This count is reproduced exactly on the recovered canonical Rithmic archive.

Frozen ledger:

- `RITHMIC_AEIF_FROZEN_RECONSTRUCTION_001_CORE_EVENTS.csv`
- 105 rows
- SHA256 `6f7bbed475cb8a627c51f5083852fb804d682d4a97b08313e51f6f918b4c011f`

Classification: **RAW_RITHMIC_FINGERPRINT_CERTIFIED**.

---

## 5. Frozen 30-minute cooldown

Cooldown is global across LONG and SHORT core events.

Rule:

> Keep an event only if it occurs at least 30 minutes after the **last kept** core event.

Rejected clustered events do **not** reset the cooldown clock.

Historical fingerprint:

```text
105 CORE
  ↓ global 30m cooldown
92 kept
LONG = 43
SHORT = 49
```

Historical baseline economics reproduced to essentially exact parity:

```text
N       92
EV      ~+0.244R
Sum     ~+22.45R
MaxDD   ~5R
```

Do not search or retune this again.

---

## 6. Frozen confirmation state machine

After a kept core event, search only the next **maximum 2 clock-contiguous M5 bars**.

Never jump across a missing M5/session clock gap. If continuity breaks, the confirmation opportunity expires.

### LONG confirmation

First qualifying contiguous M5 bar with:

```text
close > open
AND delta > 0
```

### SHORT confirmation

First qualifying contiguous M5 bar with:

```text
close < open
AND delta < 0
```

After confirmation, scheduled XAU eligibility is the **next M5 clock time**.

Reconstructed full-archive result:

```text
61 confirmations
LONG = 30
SHORT = 31
```

Through the historical XAU overlap ending 2026-09-08 UTC:

```text
53 confirmations
LONG = 25
SHORT = 28
```

Frozen reconstruction ledger:

- `RITHMIC_AEIF_FROZEN_RECONSTRUCTION_001_CONFIRMED_EVENTS.csv`
- 61 rows
- SHA256 `05f343268d596a56dbce880e692ea9f055b51abcafbb98020a0608ab5da1bd69`

---

## 7. Resolved GC→XAU transfer rule

Historical LAB022 fingerprint:

```text
51 XAU transfers
BUY  = 23
SELL = 28
```

The apparent discrepancy versus the reconstructed confirmation stream was:

```text
53 confirmations = 25 LONG + 28 SHORT
historical XAU   = 23 BUY  + 28 SELL
```

This is resolved by historical XAU timestamp eligibility.

### Frozen transfer eligibility

1. Convert scheduled `entry_eligible_utc` to the historical XAU file clock using **UTC + 2h**.
2. An XAU transfer is eligible only if an XAU M1 row exists at the **exact scheduled entry timestamp**.
3. **Do not carry the signal forward across a missing XAU bar, session gap, maintenance break, or weekend reopen.**

With this exact-timestamp rule:

```text
53 GC confirmations
- 2 LONG without exact XAU entry bar
= 51 transfers
= 23 BUY / 28 SELL
```

This exactly reproduces the historical LAB022 count and side split.

### The two excluded LONG events

#### LONG A — daily/session gap

```text
GC core UTC       2026-08-05 22:25
confirmation UTC  2026-08-05 22:30
entry eligible    2026-08-05 22:35 UTC
XAU file target   2026-08-06 00:35
previous XAU M1   2026-08-05 23:49
next XAU M1       2026-08-06 01:05
next delay        30 min
```

No exact XAU M1 entry bar exists.

#### LONG B — weekend reopen boundary

```text
GC core UTC       2026-08-30 22:50
confirmation UTC  2026-08-30 22:55
entry eligible    2026-08-30 23:00 UTC
XAU file target   2026-08-31 01:00
previous XAU M1   2026-08-28 23:49
next XAU M1       2026-08-31 01:05
next delay        5 min
```

No exact XAU M1 entry bar exists.

Therefore the former `+2 LONG` ambiguity is classified as **TRANSFER-LAYER RESOLVED**.

Forensic files:

- `GC_XAU_TRANSFER_MAPPING_FORENSIC_001.md`
- `GC_XAU_TRANSFER_MAPPING_FORENSIC_001_DISCREPANT_LONGS.csv`
- workflow `.github/workflows/gc_xau_transfer_mapping_forensic_001.yml`

Evidence status: **TRANSFER_TIMESTAMP_RULE_HIGH_CONFIDENCE_FINGERPRINT_MATCH**.

The original LAB022 51-row ledger has not been recovered, so this is not labelled historical bitwise proof. That absence is **not a reason to keep searching**; only reopen if the original ledger/source appears independently.

---

## 8. Historical XAU execution candidate

Frozen historical candidate:

```text
Entry       exact eligible XAU timestamp after confirmed GC signal
SL          1.0 × ATR20(M5) on XAU
TP          3R full take profit
Max hold    240 minutes / session close
Positions   one AEIF XAU position at a time
BE          none
Partials    none
Trailing    none
Risk used historically/demo candidate 0.5%
```

Historical results:

| Version | N | EV | SumR | PF | MaxDD |
|---|---:|---:|---:|---:|---:|
| LAB022 baseline SL1 / TP1.5 / 30m | 51 | +0.250R | +12.75R | — | 3.24R |
| TP3 / 240m | 51 | +0.563R | +28.69R | 2.15 | 3.42R |
| TP3 / 240m / single-position | 46 | +0.666R | +30.63R | 2.33 | 3.32R |

Max consecutive losses for the 46-trade candidate: **4**.

Important: TP3/240/single-position was selected on the same historical sample. It is a **frozen historical candidate**, not independent production proof.

---

## 9. AMP OOS status

AMP feed and M5 construction were independently audited before opening signal performance:

```text
AMP feed reproducibility    PASS
AMP raw → M5 conservation  PASS
AMP dataset                AMP_GC_OOS_001
```

No AMP performance was used to reconstruct or resolve the rules in this backlog.

After this backlog freeze, the next allowed research step is:

> **ONE-SHOT untouched AMP OOS replication of the frozen GC AEIF + transfer rules.**

No parameter sweep. No threshold changes. No session/filter additions. No exit optimization after seeing the AMP result.

If the AMP replication fails, record the failure. Do not retune on the same OOS sample and call it replication.

---

## 10. Research rules from this point forward

### Frozen — do not search/tune again

- prior-240 M5 window;
- Q10/Q90 delta tails;
- Q75 side-location threshold;
- lower/upper 20% aggressive concentration definition;
- Wilder ATR14 M5 for GC failed-impact;
- impact threshold `<= 0.15 ATR`;
- global 30-minute cooldown from last **kept** event;
- max 2 clock-contiguous M5 confirmation bars;
- LONG confirm `close>open AND delta>0`;
- SHORT confirm `close<open AND delta<0`;
- confirmation expires across a missing M5 clock bar;
- historical XAU clock mapping UTC+2;
- exact XAU timestamp eligibility;
- no carry across missing XAU bar/session/weekend gap.

### May be studied later only in separate LABs

- new context overlays (GVP/options/DOM/etc.);
- alternate exits;
- different risk sizing;
- new regimes/filters;
- AMP-vs-Rithmic feed differences;
- execution slippage/latency on live AMP → XAU bridge.

None of those may silently modify `AEIF_FROZEN_SPEC_001`.

---

## 11. Canonical status

```text
RAW RITHMIC DATA             RECOVERED + HASHED
M5 FOOTPRINT                 RECONSTRUCTED
CORE 105                     EXACT
COOLDOWN 92                  EXACT
CONFIRMATION                 FROZEN HIGH-CONFIDENCE
XAU TRANSFER 51 / 23-28      EXACT COUNT+SIDE FINGERPRINT
TWO EXTRA LONGS              RESOLVED BY XAU TIMESTAMP ELIGIBILITY
FORENSIC SEARCH              CLOSED
AMP OOS                      READY FOR ONE-SHOT REPLICATION
```

Canonical decision:

**`AEIF_FROZEN_SPEC_001 = SIGNAL_AND_TRANSFER_FINGERPRINT_FROZEN`**

Do not spend more research time trying to rediscover the same historical rules unless a new primary artifact directly contradicts this canonical backlog.
