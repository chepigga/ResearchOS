# RITHMIC_AEIF_FROZEN_FINGERPRINT_RECONSTRUCTION_001

## Verdict

**CORE FINGERPRINT: CERTIFIED / CONFIRMATION-TRANSFER: HIGH CONFIDENCE, NOT YET BITWISE CERTIFIED**

The missing canonical raw artifact was recovered: `GC_RITHMIC_40D_003_GCZ6.zip`.

- SHA256: `b12465a783f36aac41b82a9f2a5c4e74bd2dcf7024ffc3636e8c41a8fd01e803`
- Symbol: `GCZ6`
- Coverage: `2026-08-03` through `2026-09-11` UTC
- Raw trade prints: **3,949,646**
- M5 bars with trades: **8,231**
- Aggressor field: explicit Rithmic `BUY` / `SELL`

`AMP_GC_OOS_001` was not read for parameter selection during this reconstruction.

---

## 1. Exact reconstructed GC footprint

For each UTC M5 bar:

- `delta = aggressive_buy_volume - aggressive_sell_volume`
- `delta_frac = delta / (buy_volume + sell_volume)`
- `lower20_cut = low + 0.20 * (high-low)`
- `upper20_cut = high - 0.20 * (high-low)`
- `sell_lower20 = SELL volume at price <= lower20_cut`
- `buy_upper20 = BUY volume at price >= upper20_cut`
- `sell_loc = sell_lower20 / sell_volume` (0 when no SELL volume)
- `buy_loc = buy_upper20 / buy_volume` (0 when no BUY volume)

The floating-point boundary comparison is the native `<=` / `>=` comparison. This detail matters at exact 20% price boundaries.

---

## 2. Exact reconstructed frozen CORE

All rolling thresholds use the **prior 240 completed M5 bars**; the current bar is excluded.

### LONG core

```text
delta_frac <= Q10_prior240(delta_frac)
AND sell_loc >= Q75_prior240(sell_loc)
AND max(0, open-close) / ATR14_Wilder_M5 <= 0.15
```

### SHORT core

```text
delta_frac >= Q90_prior240(delta_frac)
AND buy_loc >= Q75_prior240(buy_loc)
AND max(0, close-open) / ATR14_Wilder_M5 <= 0.15
```

ATR is **Wilder ATR14 on M5 true range**.

This formulation reproduces the historical raw-Rithmic core fingerprint exactly:

| Stage | Total | LONG | SHORT |
|---|---:|---:|---:|
| Reconstructed core | **105** | **48** | **57** |

The previously remembered historical core count was **105**. This is an exact count match on the recovered original raw Rithmic archive.

---

## 3. Exact 30-minute cooldown reconstruction

Cooldown is global across LONG and SHORT core events:

> Keep an event only if it occurs at least 30 minutes after the **last kept** core event.

This is not “30 minutes since the immediately preceding raw event”; rejected clustered events do not reset the timer.

Result:

| Stage | Total | LONG | SHORT |
|---|---:|---:|---:|
| Core | 105 | 48 | 57 |
| +30m cooldown | **92** | **43** | **49** |

This exactly reproduces the second major historical fingerprint: **105 → 92**.

Therefore the CORE and cooldown implementation are now classified as:

**`RAW_RITHMIC_FINGERPRINT_CERTIFIED`**.

---

## 4. Confirmation reconstruction

The surviving lineage says confirmation occurs within at most two following M5 bars and represents opposite dominance.

The strongest current causal reconstruction is:

### LONG

First clock-contiguous bar among the next two M5 bars with:

```text
close > open
AND delta > 0
```

### SHORT

First clock-contiguous bar among the next two M5 bars with:

```text
close < open
AND delta < 0
```

On the recovered Rithmic archive this gives:

- full 40-day archive: **61 confirmations = 30 LONG / 31 SHORT**;
- through `2026-09-08` UTC: **53 confirmations = 25 LONG / 28 SHORT**.

The historical XAU transfer backlog records:

- **51 executed transfer trades**;
- **23 BUY / 28 SELL**.

The SHORT side therefore matches exactly (**28 vs 28**), while the current reconstruction has **two additional LONG confirmations** before the XAU transfer eligibility layer.

At present we cannot honestly tell whether those two LONGs were removed by:

1. an additional exact detail of the historical confirmation rule; or
2. XAU history / timestamp / next-eligible-entry transfer eligibility.

No AMP OOS data may be used to decide between those explanations.

---

## 5. Historical XAU execution fingerprint (unchanged)

The recovered backlog freezes the historical execution candidate as:

- XAU entry: next eligible entry after confirmation;
- SL: `1.0 × ATR20(M5)`;
- TP: `3R`, full TP;
- max hold: 240 minutes / session close;
- one AEIF XAU position at a time;
- no BE, no partials, no trailing;
- historical/demo candidate risk: 0.5%.

Historical transfer results:

| Version | N | EV | SumR | PF | MaxDD |
|---|---:|---:|---:|---:|---:|
| LAB022 SL1 / TP1.5 / 30m | 51 | +0.250R | +12.75R | — | 3.24R |
| TP3 / 240m | 51 | +0.563R | +28.69R | 2.15 | 3.42R |
| TP3 / 240m / single-position | 46 | +0.666R | +30.63R | 2.33 | 3.32R |

The TP3/240/single-position exit was selected on the same historical transfer sample and remains a frozen candidate, not independent production proof.

---

## 6. Negative controls / why this is not threshold fitting

The reconstruction was constrained by surviving historical lineage before any AMP OOS performance read.

Important alternatives from prior reports remain negative controls:

- M1 precursor: prior 240 M1 bars, Q10/Q90, Q75 aggressor-side volume, ATR14 M1, prior-event Q20 price-result failure;
- time-equivalent M5 negative control: 48 M5 bars, ATR3, prior-event Q20 failure.

The positive Rithmic fingerprint is a different footprint implementation: **240 M5 + Q75 location concentration + Wilder ATR14 + fixed 0.15 directional impact failure**. It is selected because it reproduces the original 105/92 raw-Rithmic fingerprints, not because of AMP results.

---

## 7. Frozen reproducibility artifacts

The reconstruction is now stored as reproducible, hashed artifacts in ResearchOS:

- `RITHMIC_AEIF_FROZEN_RECONSTRUCTION_001_CORE_EVENTS.csv`
  - 105 rows
  - SHA256 `6f7bbed475cb8a627c51f5083852fb804d682d4a97b08313e51f6f918b4c011f`
- `RITHMIC_AEIF_FROZEN_RECONSTRUCTION_001_CONFIRMED_EVENTS.csv`
  - 61-row **confirmation candidate ledger**
  - SHA256 `05f343268d596a56dbce880e692ea9f055b51abcafbb98020a0608ab5da1bd69`
- `RITHMIC_AEIF_FROZEN_RECONSTRUCTION_001_MANIFEST.json`
- `freeze_rithmic_aeif_fingerprint_001.py`
- `.github/workflows/gc_rithmic_aeif_freeze_001.yml`

The rebuild script downloads the canonical GitHub Release asset, verifies its source SHA256, reconstructs the M5 footprint, regenerates both ledgers, and fails if the frozen event counts or ledger hashes change.

The 61-row confirmation ledger is deliberately labelled a **reproducible candidate ledger**, not historical bitwise proof, because of the two-LONG transfer ambiguity above.

---

## 8. Certification status

```text
RAW RITHMIC DATA               RECOVERED / HASHED
M5 FOOTPRINT                   RECONSTRUCTED
CORE 105                       EXACT MATCH
COOLDOWN 92                    EXACT MATCH
CORE FORMULA                   CERTIFIED BY HISTORICAL FINGERPRINT
CONFIRMATION MAX 2 M5          RECOVERED
CONFIRMATION BODY+DELTA        HIGH-CONFIDENCE CANDIDATE
XAU TRANSFER 51 / 23-28        TWO-LONG AMBIGUITY REMAINS
AMP_GC_OOS_001                 STILL SEALED FOR PERFORMANCE
```

### Current decision

`AEIF_FROZEN_SPEC_001` is frozen as:

**`CORE_FINGERPRINT_CERTIFIED_CONFIRMATION_PENDING`**.

The remaining ambiguity must be resolved from old XAU transfer evidence or explicitly preregistered before the one-shot AMP OOS replication. It must **not** be resolved by trying variants on AMP.
