# AMP_GC_M5_FOOTPRINT_BUILD_001

## Verdict: PASS

Canonical raw dataset is frozen as **`AMP_GC_OOS_001`**. This LAB is data transformation only: **NO AEIF THRESHOLDS / NO RETUNING / NO TRADING**.

- Canonical run: `20260806_182904__20260915_182904`
- Raw ZIP SHA256 verified: `03dbec37caf947652a52f71a1f2d4f9f25b619401982dd97d56da0054c759fc8`
- Raw trade prints: **3,737,719**
- M5 footprint bars with >=1 trade: **7,699**
- First/last M5: **2026-08-06 18:25:00 UTC → 2026-09-15 18:25:00 UTC**
- BUY / SELL / BOTH / NONE ticks: **1,862,617 / 1,880,711 / 5,609 / 0**
- BOTH tick share: **0.1501%** (preserved; exclusive-side columns also exported)
- Raw total volume: **4247305**
- BUY / SELL volume: **2113193 / 2140040**
- Bars after >=240 completed-bar warm-up: **7,460**
- Non-contiguous M5 transitions (market closures/gaps included): **28**
- M5 footprint SHA256: `ff6e003bb58981439748051a530f7722c9edbf090b7b53740588e85611e873bd`

## Conservation checks

- raw rows == sum(M5 trades): **3,737,719 == 3,737,719**
- raw BUY ticks == sum(M5 BUY): **1,862,617 == 1,862,617**
- raw SELL ticks == sum(M5 SELL): **1,880,711 == 1,880,711**
- raw timestamp monotonic violations: **0**

## Exported causal-at-bar-close features

`OHLC`, `trades`, `volume`, inclusive and exclusive `BUY/SELL volume`, `delta`, `delta_frac`, lower/upper 20% price bands, side volume/concentration inside those bands, `true_range`, `ATR20 SMA`, `ATR20 Wilder`, 240-completed-bar warm-up marker, and clock-gap diagnostics.

Both ATR20 conventions and both inclusive/exclusive aggressor variants are diagnostics only. The frozen Rithmic AEIF implementation must choose its original convention during parity reconstruction; this LAB deliberately does not choose or tune one.

## Next

Reattach the exact frozen Rithmic AEIF selector to this footprint. Known frozen pieces are Q10/Q90 delta tail, Q75 location concentration, failed impact ~0.15 ATR, and max two M5 confirmation bars. The exact original rolling-window/ATR convention must be recovered rather than guessed before signal replication.
