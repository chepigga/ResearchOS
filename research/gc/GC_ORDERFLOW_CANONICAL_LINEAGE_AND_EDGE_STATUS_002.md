# GC ORDER FLOW — CANONICAL LINEAGE AND HISTORICAL EDGE STATUS 002

## Purpose

This document supersedes any shorthand that described the original positive historical AEIF result as a “Rithmic result” or an “FTMO result”. It records the corrected research lineage and the current historical edge evidence after M1 replication on the raw GC feeds already available in the GC release.

## 1. Correct canonical lineage

The correct lineage is:

`Chris idea → ATAS/dxFeed GC M1 footprint → positive M1 AEIF historical result → later frozen/reconstructed selectors → historical GC→XAU transfer claim → Rithmic/AMP considered as realtime/raw-feed reproduction paths.`

### Original positive source

The primary positive discovery was **LAB001_GC_CAUSAL_EFFORT_RESULT_ABSORPTION_AND_SECOND_FAILURE** on historical **GC M1 footprint exported from ATAS/dxFeed**.

Original source window:
- 2026-09-06 22:00 → 2026-09-11 12:46
- 6,244 M1 bars
- 127,842 footprint price-level rows

Original LAB001 mechanism:
- A: prior-240 M1 delta-fraction Q10/Q90 extreme plus aggressor-side volume >= prior Q75.
- B: among prior same-side A events, current directional price result body/ATR14 falls in the weakest 20%.
- D: opposite delta plus reversal-direction price response within the following <=2 M1 bars.

Original reported results:
- A: 5m +0.137 ATR; 15m +0.257 ATR.
- B: N=77; 5m +0.407 ATR; 15m +0.561 ATR.
- D: N=46; 5m +0.399 ATR; 15m +0.646 ATR; 15m WR 63.0%.

These are **ATAS/dxFeed M1 historical results**, not Rithmic-live and not FTMO results.

## 2. M5 replication warning remains canonical

LAB003 on the longer ATAS/dxFeed M5 bar-total history did not replicate the B reversal edge:
- B 5m -0.062 ATR
- B 15m -0.064 ATR

The exact M1 selector on the available authentic M1 subset remained positive. Therefore M5 reconstruction must not be treated as proof of the original M1 edge.

## 3. Raw historical feeds now available

The GC release contains two useful raw trade-flow histories:

### Rithmic raw archive
- `GC_RITHMIC_40D_003_GCZ6.zip`
- used only as a later raw historical replication source
- not the source of original LAB001 discovery

### AMP/CQG raw archive
- `AMP_GC_HISTORY_EXPORTER_001_GCEZ26_20260806_182355__20260915_182355_TICKS.csv.zip`
- directional semantics use exclusive BUY or SELL prints; simultaneous BUY+SELL flags are excluded from directional aggressor volume in the preregistered bridge

Rithmic and AMP are largely two representations of the same GC market interval. Agreement between them is feed robustness/parity evidence, not independent market OOS.

## 4. Historical M1 replication — LAB001

### GC_M1_AEIF_HISTORICAL_EDGE_REPLICATION_001

The exact LAB001-style M1 mechanism was rebuilt on both raw feeds without XAU and without an execution model.

Full-history descriptive result:

Rithmic:
- B 5m ≈ +0.054 ATR
- B 15m ≈ +0.152 ATR

AMP/CQG:
- B 5m ≈ +0.022 ATR
- B 15m ≈ +0.094 ATR

The original discovery clock remained more positive, but the full-history edge was much smaller.

## 5. Causal timing audit

### GC_M1_AEIF_CAUSAL_EDGE_AUDIT_002

To remove close-fill / confirmation lookahead:
- B enters only at the exact next M1 open after completed B bar.
- D enters only at the exact next M1 open after the completed confirmation bar.

Pre-original-discovery results:

Rithmic B next-open:
- N=383
- 5m +0.042 ATR
- 15m +0.139 ATR
- day-cluster confidence intervals cross zero

AMP B next-open:
- N=341
- 5m -0.024 ATR
- 15m +0.115 ATR
- confidence intervals cross zero

D residual after waiting for confirmation was also weak/noisy pre-discovery.

**Conclusion:** original AEIF reversal is a historical phenomenon worth preserving, but it is not established as a robust transportable edge on the longer raw history currently available.

## 6. Bounded historical mechanism discovery

### GC_M1_ORDERFLOW_EDGE_DISCOVERY_003

A bounded, preregistered mechanism set was tested with exact next-M1-open causal entry. No candidate passed the strict symmetric gate.

The two most interesting continuation families were:

### IMPACT_Q80_CONT

Strong aggression whose directional price impact is in the strongest causal Q80, followed in the aggression direction.

15m EV:
- Rithmic TRAIN +0.232 ATR
- Rithmic VALID +0.145 ATR
- Rithmic LATE +0.113 ATR
- AMP TRAIN +0.246 ATR
- AMP VALID +0.115 ATR
- AMP LATE +0.032 ATR
- AMP POST +1.022 ATR

This remains a **historical candidate**, not promoted, because the original strict gate also required short-horizon and side robustness.

### BREAKOUT_CONT

Extreme aggressor state plus local price breakout/acceptance, followed in the aggression direction.

A strong directional asymmetry was discovered:
- buyer-breakout LONG was persistently positive;
- mirror seller-breakout SHORT was weak/negative on Rithmic.

This directional branch was observed after the bounded search output and therefore is explicitly post-hoc discovery.

## 7. Frozen historical candidate — buyer breakout LONG

### GC_M1_BUYER_BREAKOUT_LONG_AUDIT_004

Frozen rule after discovery 003:

1. completed M1 bar;
2. buyer aggression state:
   - `delta_frac >= prior240 Q90`
   - `buy aggressive volume >= prior240 Q75`;
3. current high reaches/exceeds prior 20 completed-bar high;
4. bullish body;
5. close in top 25% of current bar;
6. exact next clock-contiguous M1 open entry;
7. direction LONG;
8. information horizon currently characterized at 5m and 15m only; no SL/TP has been selected.

15m candidate EV:

Rithmic:
- TRAIN N=146, +0.339 ATR
- VALID N=115, +0.278 ATR
- LATE N=40, +0.561 ATR
- PRE_DISCOVERY N=261, +0.312 ATR
- FULL N=302, +0.346 ATR

AMP/CQG:
- TRAIN N=108, +0.532 ATR
- VALID N=120, +0.320 ATR
- LATE N=37, +0.319 ATR
- POST N≈14–16 depending exact report eligibility, about +0.303 ATR
- PRE_DISCOVERY N=228, +0.420 ATR
- FULL N≈279–281, about +0.401 ATR

Common-clock candidate event parity between Rithmic and AMP was high: Jaccard ≈0.858.

Mirror SHORT was materially weaker, especially on Rithmic.

## 8. Incremental order-flow audit

### GC_M1_BUYER_BREAKOUT_INCREMENTAL_ORDERFLOW_AUDIT_005

The buyer-breakout LONG candidate was compared with the same bullish price-breakout pattern when the frozen buyer-flow gate was absent, and with deterministic shifted-flow placebos.

Key 15m observations:

Rithmic:
- PRE_DISCOVERY candidate +0.312 ATR vs price-only complement +0.100; incremental +0.212 ATR; day-cluster CI crosses zero.
- FULL candidate +0.346 vs complement +0.115; incremental +0.231; CI crosses zero.

AMP/CQG:
- PRE_DISCOVERY candidate +0.420 vs complement -0.089; incremental +0.509; day-cluster CI [+0.089,+0.944].
- FULL candidate +0.401 vs complement -0.045; incremental +0.446; day-cluster CI [+0.083,+0.825].

However, deterministic shifted buyer-flow placebos often produced incremental effects of comparable or larger magnitude. Therefore the available history does **not** establish that the exact synchronous order-flow gate itself is the unique causal source of the return.

Interpretation:
- the BUYER_BREAKOUT_LONG signal is a strong **historical market-state candidate**;
- it may represent a bullish breakout/continuation regime for which buyer flow is a useful marker;
- current evidence is insufficient to call it a pure footprint/order-flow alpha.

## 9. Current research status

### Rejected as robust historical claim

`Original AEIF reversal is already proven as a stable general edge.`

This claim is NOT supported by the longer causal M1 history.

### Best historical candidates currently retained

1. `BUYER_BREAKOUT_LONG_001`
   - strongest directional consistency across historical partitions and both raw feeds;
   - not yet OOS;
   - not yet converted to SL/TP trading economics.

2. `IMPACT_Q80_CONT_001`
   - positive 15m continuation across many historical partitions;
   - weaker side/5m robustness;
   - retained as secondary candidate.

### No XAU / FTMO promotion yet

Do not use the old XAU transfer results to validate these newly discovered candidates. They have not been tested on XAU and no FTMO claim is attached to them.

## 10. Governance / next step

- Do not retune `BUYER_BREAKOUT_LONG_001` on the already-inspected Aug–Sep history.
- Freeze the exact signal rule before using new market data.
- Existing history may still be used for **descriptive execution geometry** (MFE/MAE, plausible stop scale, latency sensitivity), but any selected SL/TP becomes a same-sample historical candidate.
- Real validation requires a new untouched GC interval after the freeze.
- Only after GC edge validation should GC→XAU transfer and prop execution be promoted.

## Canonical one-line status

**Original ATAS/dxFeed M1 AEIF reversal = interesting but not robustly replicated; best current historical candidate = causal M1 buyer-aggression breakout LONG continuation, positive across all inspected historical partitions but not yet independent OOS and not proven to be uniquely order-flow-driven.**
