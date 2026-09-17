# GC SHORT CHRIS LONG HISTORY REPLICATION LAB008H — AMP EXTENDED AUDIT 001

**Date:** 2026-09-17

**Status:** `EXTENDED_SAMPLE_SUPPORTIVE_BUT_LONG_HISTORY_GATES_NOT_MET`

## Source

User-provided archive: `AMP_GC_LONG.zip`

Exporter lineage: `AMP_GC_LONG_HISTORY_EXPORTER_002`

Symbol: `GCEZ26`

The exporter log reported 623 chunks, 0 failures, 17,886,225 raw rows. Inspection of the uploaded ZIP showed 49 CSV files: two empty files (`20250101`, `20250102`) and non-empty tick files beginning at `20260731` through `20260915`. Therefore available explicit-aggressor tick history in this archive is approximately 2026-07-31 -> 2026-09-15, despite chart/bar history being visible earlier in MT5.

Important distinction: MT5 chart/bar history is not proof that `CopyTicksRange()` exposes historical trade ticks with `TICK_FLAG_BUY/TICK_FLAG_SELL` for the same period.

## Raw audit

- raw rows: 17,886,225
- BUY-only: 2,128,728
- SELL-only: 2,156,540
- DUAL BUY+SELL: 6,249
- NEITHER: 13,594,708
- directional BUY+SELL rows: 4,285,268
- time_msc non-monotonic transitions within files: 0
- reconstructed explicit-aggressor M1 bars: 45,302
- first reconstructed M1: 2026-07-31 00:00 UTC
- last reconstructed M1: 2026-09-15 23:59 UTC

DUAL rows remain excluded from frozen directional aggregation exactly as in the canonical AMP lineage.

## Frozen Chris / POST10 result

No signal, checkpoint, feature, Q50, horizon, or threshold was changed.

Frozen LAB003 Chris events:
- 27 total events

Frozen LAB006-style expanding prior-event Q50 after 8 prior events:
- OOF POST10 events: 19
- selected: 9
- selection share: 47.37%

Primary residual +10m -> +20m:
- all OOF EV: +0.75936 ATR
- selected EV: **+2.03792 ATR**
- rejected EV: **-0.39135 ATR**
- uplift vs all OOF: **+1.27856 ATR**
- selected WR: **88.89%**

Secondary residual +10m -> +30m:
- all OOF EV: +0.63450 ATR
- selected EV: **+2.39884 ATR**
- rejected EV: **-0.95341 ATR**
- uplift vs all OOF: **+1.76434 ATR**
- selected WR: **77.78%**

## Interpretation

The added late-July history does not weaken the frozen Chris POST10 separation. Selected states remain strongly positive while rejected states remain negative. This is supportive replication on a slightly expanded sample.

However this archive is still far short of the frozen LAB008H long-history gates:
- coverage <24 months;
- Chris events 27 <75;
- OOF 19 <50;
- selected 9 <25;
- no multi-year consistency test possible.

Therefore this is **not** a long-history PASS and does not authorize SHORT execution optimization or Demo promotion.

## Next data step

To extend LAB008H, obtain explicit-aggressor tick history from earlier GC contracts available in AMP (e.g. preceding 2026 expiries) rather than relying on chart bars alone. Each candidate contract must be exported with `CopyTicksRange` and `TICK_FLAG_BUY/TICK_FLAG_SELL`, audited, then stitched causally under the frozen prereg rule.

Do not substitute OHLCV bars, candle-direction delta proxies, or post-hoc threshold changes.
