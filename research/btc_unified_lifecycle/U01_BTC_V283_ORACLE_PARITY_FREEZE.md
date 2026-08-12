# U01 — BTC v283 ORACLE Exact Entry Pipeline Parity Freeze

Source SHA256: `88b8acff6ae26f020fa3f0b08474364233ab9d38eacdf3f1c600f9d0d9ba40e7`

## Security
The uploaded source contains credentials. The source itself must **not** be committed to ResearchOS. Only this redacted manifest/spec and replay code may be committed.

## Canonical defaults that change reachable logic

| Input | Default |
|---|---:|
| `InpMockMode` | `true` |
| `InpMockUseSmartAI` | `true` |
| `InpMinConf` | `68` |
| `InpUsePriorityE` | `false` |
| `InpUsePriorityF` | `false` |
| `InpUseLiquidityFilter` | `false` |
| `InpUseEarlyRangeBuy` | `false` |
| `InpUseEarlyRangeSell` | `false` |
| `InpUseFVGOBFilter` | `false` |
| `InpUseLevelEntry` | `true` |
| `InpUseRegimeFilter` | `false` |
| `InpUseBOSOnlyBlock` | `true` |
| `InpUseSlopeKill` | `false` |
| `InpUseCascadeBOS` | `false` |
| `InpUseDistEMAGuard` | `false` |
| `InpUseCounterHTFGate` | `false` |
| `InpUseH4FlipOverride` | `false` |
| `InpUseCascadeEntry` | `false` |
| `InpUseLiqRevBypass` | `true` |
| `InpUseM15PanicDetector` | `true` |
| `InpLimitEntry` | `false` |
| `InpStopMultATR` | `1.5` |
| `InpMinRR` | `1.5` |
| `InpLateEntryATR` | `1.5` |
| `InpMaxSpreadPrice` | `32.0` |
| `InpTimerSec` | `10` |
| `InpAIPollFlatSec` | `180` |
| `InpAIPollInPosSec` | `120` |
| `InpUseSessionMomentum` | `false` |
| `InpUseRealBosFilter` | `false` |
| `InpExhaustVeto2` | `true` |
| `InpBuyBearD1` | `true` |
| `InpBuyLateRecov` | `true` |

## Canonical reachable SmartMock branches

- Priority A Raid/Reclaim: coded, but effectively unreachable with `InpUseLiquidityFilter=false` because `DetectLiquidityRaid/DetectRaidReclaim` return NONE.
- Priority B CHoCH+BOS: reachable.
- Priority C OB/FVG + M1 microbreak: reachable because FVG/OB state is still computed even when the hard FVG/OB filter is disabled.
- Priority D EQH/EQL: effectively unreachable with `InpUseLiquidityFilter=false`.
- Priority E/F: disabled by default.

## Exact state-update clock

1. `UpdateD1Context()` is called every timer cycle (10 s default), despite its comment saying H4. `e_index` therefore uses live bid against last closed D1 EMA/ATR.
2. H1/M15 BOS refresh only on a new H1 bar.
3. Range compression refresh only on a new H1 bar.
4. M1 fractals, extended liquidity, sweep levels and PRE score refresh only on a new M5 bar.
5. `BuildAIContext()` runs every timer and refreshes live `distATR`, EMA slope, impulse, panic and FVG/OB globals.
6. Flat SmartMock polling default = 180 s when `need_ai` is true.
7. Entry gates are evaluated against live bid/ask after SmartMock.

## Required parity row markers already present in v283

`D1_PARITY`, `EMA_PARITY`, `PRE_SCORE_BTC`, `SMART_MOCK`, `ORACLE_GATE_BLOCK`, `BOS_ONLY_BLOCK`, `KNIFE_BTC`, `LATE_ENTRY_BLOCK`, `EXEC_EVENT`.

## U01 acceptance rule

Offline bar replay may be used to validate indicator/state formulas, but **profitability is not accepted** until one exact v283 Strategy Tester run is compared, because the EA evaluates live bid/ask every 10 seconds while the frozen ResearchOS release provides M1/M5 bars rather than broker ticks.
