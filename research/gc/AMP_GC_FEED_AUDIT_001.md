# AMP_GC_FEED_AUDIT_001

Scope: **AMP/CQG GCEZ26 historical feed parity only. NO AEIF RETUNING. NO TRADING.**

## Verdict: PASS

Canonical run: **20260806_182904__20260915_182904**

| Run | Version | Chunk h | Status | Tick rows | BUY | SELL | NONE | Aggressor coverage | Chunk failures | Seq errors | Non-monotonic | Base |
|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `20260806_182355__20260915_182355` | 1.10 | 24 | COMPLETE | 3,737,579 | 1,862,531 | 1,880,657 | 0 | 100.0000% | 0 | 0 | 0 | PASS |
| `20260806_182904__20260915_182904` | 1.20 | 12 | COMPLETE | 3,737,719 | 1,862,617 | 1,880,711 | 0 | 100.0000% | 0 | 0 | 0 | PASS |

## Reproducibility on exact overlap

- Overlap: `1786040949058` → `1789496634164`
- Rows A/B: **3,737,471 / 3,737,471**
- SHA256 A: `ecf4dcebc5da59442fd989c3466d1e9eaf7f1dd45e1a62cbdd883e67b9861d8b`
- SHA256 B: `ecf4dcebc5da59442fd989c3466d1e9eaf7f1dd45e1a62cbdd883e67b9861d8b`
- Exact canonical tick-stream match: **YES**

## Per-run diagnostics

### `20260806_182355__20260915_182355`
- META status/version: `COMPLETE` / `1.10`
- Requested: `2026.08.06 18:23:55` → `2026.09.15 18:23:55`
- Exported tick time_msc: `1786040654857` → `1789496634164`
- Rows / CHUNKS sum / META total: **3,737,579 / 3,737,579 / 3,737,579**
- Volume BUY / SELL / delta: **2113090 / 2139947 / -26857**
- Last price min/max: **4288.0 / 4755.0**
- Exact adjacent duplicates preserved: **944,855**
- Same-ms adjacent prints: **1,619,955**
- Zero-volume / nonpositive-last / inverted-BBO: **0 / 0 / 211**
- Request gaps/overlaps: **0 / 0**
- Top time gaps ms (includes scheduled market closures): `[176404914, 176402731, 176402367, 176401671, 176400828, 176400697, 12600490, 3605700, 3604511, 3603751]`
- Top flag values: `[('344', 1869314), ('312', 1851575), ('88', 5734), ('376', 5604), ('56', 5347), ('120', 5)]`

### `20260806_182904__20260915_182904`
- META status/version: `COMPLETE` / `1.20`
- Requested: `2026.08.06 18:29:04` → `2026.09.15 18:29:04`
- Exported tick time_msc: `1786040949058` → `1789496942280`
- Rows / CHUNKS sum / META total: **3,737,719 / 3,737,719 / 3,737,719**
- Volume BUY / SELL / delta: **2113193 / 2140040 / -26847**
- Last price min/max: **4288.0 / 4755.0**
- Exact adjacent duplicates preserved: **944,877**
- Same-ms adjacent prints: **1,619,985**
- Zero-volume / nonpositive-last / inverted-BBO: **0 / 0 / 211**
- Request gaps/overlaps: **0 / 0**
- Top time gaps ms (includes scheduled market closures): `[176404914, 176402731, 176402367, 176401671, 176400828, 176400697, 12600490, 3605700, 3604511, 3603751]`
- Top flag values: `[('344', 1869254), ('312', 1851527), ('88', 5848), ('376', 5604), ('56', 5481), ('120', 5)]`

## Acceptance rule

PASS requires COMPLETE metadata, non-empty data, exact seq ordering, monotonic timestamps, contiguous chunk requests, no failed/error chunks, TICKS=CHUNKS=META row parity, >=99% aggressor classification, and exact SHA256 equality of the normalized tick stream on the common interval between two independent exports.

## Next if PASS

Freeze canonical AMP dataset as `AMP_GC_OOS_001`, aggregate M5 footprint from raw prints, apply the already-frozen AEIF logic unchanged, then test GC→FTMO XAU transfer with frozen SL1 / TP3 / max hold 240m / single-position.
