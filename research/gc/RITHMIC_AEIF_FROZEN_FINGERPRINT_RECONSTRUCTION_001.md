# RITHMIC_AEIF_FROZEN_FINGERPRINT_RECONSTRUCTION_001

## Verdict

**PARTIAL_RECONSTRUCTION / FINGERPRINT_GATE_BLOCKED_BY_MISSING_CANONICAL_RITHMIC_ARTIFACT**

This is a forensic reconstruction LAB. It deliberately does **not** read or score `AMP_GC_OOS_001` and it does **not** tune AEIF on the new AMP sample.

The frozen conceptual lineage is recoverable. The final positive Rithmic implementation is **not yet fingerprint-certified** because the canonical Rithmic raw/footprint/event artifact that generated the historical `105 -> 92` result is not present in the accessible ResearchOS repository, GitHub releases, or current File Library evidence.

Therefore the AMP OOS execution gate remains **CLOSED**.

---

## 1. Historical fingerprint that must be reproduced

A candidate implementation is not allowed to call itself `AEIF_FROZEN_SPEC_001` until it reproduces the historical lineage within the tolerances below.

| Stage | Historical fingerprint | Certification role |
|---|---:|---|
| Rithmic GC core | ~105 trades, EV ~+0.297R | primary implementation fingerprint |
| + 30m cooldown | ~92 trades, EV ~+0.244R, Sum ~+22.45R, MaxDD ~5R | clustering / re-arm fingerprint |
| GC -> XAU baseline transfer | ~51 trades, EV ~+0.250R, Sum ~+12.75R, MaxDD ~3.24R | cross-venue timestamp/side fingerprint |
| GC -> XAU TP3/240 | ~51 trades, EV ~+0.563R, Sum ~+28.69R, PF ~2.15, MaxDD ~3.42R | exit replay fingerprint; same-sample candidate |
| GC -> XAU TP3/240 single-position | ~46 trades, EV ~+0.666R, Sum ~+30.63R, PF ~2.33, MaxDD ~3.32R, max loss streak 4 | final historical candidate fingerprint |

These are fingerprints, not fresh claims. Exit TP3/240 was selected on the historical sample and remains a frozen candidate requiring independent OOS validation.

### Required parity tolerance

For implementation certification on the original Rithmic artifact:

- event timestamps / direction: **exact match required** if the original event ledger is available;
- otherwise core N: exact preferred, tolerance at most `+/-1` solely for documented boundary handling;
- cooldown N: exact preferred, tolerance at most `+/-1` solely for documented boundary handling;
- EV tolerance: `<= 0.01R` absolute;
- SumR tolerance: `<= 0.25R` absolute;
- no candidate may be selected using AMP OOS performance.

---

## 2. Recovered lineage — evidence classes

### A. VERIFIED from precursor GC causal reports

The authentic M1 precursor used:

- extreme aggression from a **prior 240-bar** rolling delta-fraction distribution;
- lower/upper tails at **Q10 / Q90**;
- aggressor-side volume at or above its **prior Q75**;
- ATR normalization with **ATR14 on M1**;
- effort/result failure based on weak directional price result;
- opposite response searched within **2 following bars**.

The precursor report explicitly describes A as prior-240-bar delta-fraction Q10/Q90 plus aggressor-side volume >= Q75. Its B stage is the weakest 20% of prior same-side A-event price result, and D is opposite response within two bars.

### B. VERIFIED negative-control M5 transfer

A later ATAS/dxFeed M5 transfer deliberately preserved clock-time semantics rather than exact numeric M1 bar counts:

- aggression window: **48 M5 bars = 4h**;
- warm-up: **24 M5 bars = 2h**;
- Q10/Q90 delta-fraction tails;
- Q75 aggressor-side volume;
- simple **ATR3 on M5** to approximate the ~15 minute M1 ATR14 horizon;
- B = weakest 20% of prior same-side A events, min 15 prior same-side A events.

That M5 transfer was negative and is explicitly retained as a **negative control**, not promoted as the final Rithmic AEIF implementation.

### C. RECOVERED FROM POSITIVE RITHMIC LINEAGE, BUT NOT RAW-ARTIFACT CERTIFIED

The positive Rithmic branch is consistently described in project lineage as:

- working bar: **M5 footprint**;
- LONG: extreme negative delta / seller aggression near bar low / failed downside price impact;
- SHORT: exact mirror;
- delta tail: **Q10/Q90 causal rolling reference**;
- location: aggressive SELL concentration in lower 20% for LONG, aggressive BUY concentration in upper 20% for SHORT;
- location threshold: **Q75 causal reference**;
- failed directional impact threshold around **0.15 ATR**;
- confirmation window: maximum **2 subsequent M5 bars**;
- recovered confirmation description: LONG = bullish body + positive delta; SHORT = bearish body + negative delta;
- entry only after confirmation, not on the unconfirmed core bar;
- baseline execution fingerprint: `SL=1 ATR / TP=1.5 ATR / max hold=30m`;
- separate signal clustering control: 30-minute cooldown.

These items may be used to constrain reconstruction candidates, but they cannot be stamped `EXACT_FROZEN` until the original Rithmic artifact reproduces the historical fingerprint.

---

## 3. What remains unresolved

The following implementation details materially affect exact event identity and therefore remain **UNRESOLVED**:

1. **Final Rithmic rolling-window length** for Q10/Q90/Q75.
   - `48 M5` is a lineage-supported clock-equivalent candidate.
   - `240 M5` appears in later sensor warm-up planning but is not proof of the positive Rithmic threshold window.
   - no value may be selected from AMP performance.

2. **Final ATR convention / period** used by the positive Rithmic implementation.
   - precursor: ATR14 M1;
   - negative-control M5 transfer: simple ATR3 M5;
   - later AMP footprint currently exports ATR20 SMA and ATR20 Wilder as diagnostics only;
   - none of these is sufficient evidence to claim the final positive Rithmic convention.

3. **Exact failed-impact formula**.
   - recovered threshold is approximately `0.15 ATR`, but whether the numerator is directional body, close-vs-extreme progress, or another footprint price-impact definition is not raw-artifact certified.

4. **Exact Q75 location statistic**.
   - lower/upper 20% aggressor concentration is recovered;
   - exact reference population and whether Q75 is side-specific / pooled is unresolved.

5. **BOTH-side print handling**.
   - Rithmic feed handling for prints carrying both side flags is not recovered.
   - AMP M5 footprint preserves both inclusive and exclusive variants specifically to avoid silently deciding this after seeing OOS results.

6. **Confirmation edge cases**.
   - recovered semantic rule is bullish body + positive delta (LONG), bearish body + negative delta (SHORT), within max two M5 bars;
   - exact treatment of first-vs-second qualifying bar, zero-body/zero-delta, market gaps, and re-arm collisions needs the original artifact for exact parity.

7. **Entry price timestamp convention**.
   - semantic rule is entry only after completed confirmation;
   - exact `next M5 open` versus `first trade/tick after confirmation close` must be matched to the old ledger.

---

## 4. Reconstruction search is implementation parity, not strategy optimization

Allowed reconstruction axes are only fields that are already ambiguous in surviving lineage evidence. They are evaluated **only on the original Rithmic artifact** against the known historical fingerprints.

Forbidden during reconstruction:

- using `AMP_GC_OOS_001` trade count, EV, PF, drawdown, or signal dates to choose an implementation;
- adding sessions, trend filters, news filters, GVP/options context, DOM, or other new gates;
- changing Q10/Q90/Q75 because another percentile looks better;
- changing confirmation horizon beyond the recovered max-two-M5 rule;
- optimizing exit on the AMP sample.

---

## 5. Fingerprint certification gate

A candidate becomes `AEIF_FROZEN_SPEC_001` only when all are true:

- **F1 CORE COUNT:** historical Rithmic core reproduces ~105, with exact identity preferred;
- **F2 CORE ECONOMY:** EV within 0.01R of +0.297R;
- **F3 COOLDOWN COUNT:** 30m cooldown reproduces ~92;
- **F4 COOLDOWN ECONOMY:** EV within 0.01R of +0.244R and SumR within 0.25R of +22.45R;
- **F5 EVENT IDENTITY:** if old event ledger exists, timestamps + direction match exactly;
- **F6 TRANSFER:** if old GC/XAU transfer artifacts exist, baseline transfer reproduces ~51 trades and EV ~+0.250R;
- **F7 SINGLE POSITION:** if old exit-transfer artifact exists, single-position count reproduces ~46;
- **F8 ZERO AMP READ:** reconstruction code has not loaded `AMP_GC_OOS_001` for parameter selection.

Failure to meet the gate is `RECONSTRUCTION_NOT_CERTIFIED`, not an invitation to tune on AMP.

---

## 6. Data-search result in this LAB

Searched accessible ResearchOS GitHub code/history/releases and current File Library for:

- `AEIF`, `Rithmic`, `105 trades`, `0.297R`, `92 trades`, `0.244R`, `LAB022`, `51 trades`, `0.250R`, `46 trades`, `0.666R`, `lower20`, `upper20`, `0.15 ATR`, and related GC footprint terms.

Found:

- authentic precursor LAB001 report/event ledger;
- negative-control LAB003 M5 transfer report/events;
- new AMP dataset/audit artifacts.

Not found:

- canonical positive Rithmic raw trade file;
- canonical Rithmic M5 footprint used for the 105-trade result;
- 105-event core ledger;
- 92-event cooldown ledger;
- old GC->XAU transfer ledger / exact LAB022 artifact;
- original final code/config that can be hashed and replayed.

Therefore exact fingerprint replay cannot honestly be executed in the current evidence set.

---

## 7. Current frozen state

`AMP_GC_OOS_001` remains **SEALED_FOR_SIGNAL_PERFORMANCE**.

The AMP feed itself has already passed independent feed reproducibility and raw->M5 conservation. It may be opened for AEIF performance **only after** `AEIF_FROZEN_SPEC_001` reaches `FINGERPRINT_CERTIFIED`.

### Current status

```text
RITHMIC_AEIF_FROZEN_FINGERPRINT_RECONSTRUCTION_001
= PARTIAL_RECONSTRUCTION
= FINGERPRINT_GATE_BLOCKED_BY_MISSING_CANONICAL_RITHMIC_ARTIFACT

AMP_GC_OOS_001
= DO_NOT_USE_FOR_PARAMETER_SELECTION
```

---

## 8. Immediate next action

Recover any one of the following historical artifacts, in priority order:

1. original Rithmic AEIF Python/MQL code or config;
2. 105-event Rithmic core ledger with timestamps/directions/features;
3. 92-event cooldown ledger;
4. raw Rithmic GC tick/footprint file used by the positive LAB;
5. exact old LAB report containing the complete frozen config.

Once any of these is available, run the reconstruction harness against the historical fingerprint, freeze the exact implementation as `AEIF_FROZEN_SPEC_001`, and only then execute a **single untouched AMP OOS run**.
