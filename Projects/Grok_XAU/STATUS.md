# Grok XAU Status

**Updated:** 2026-07-25  
**Project status:** ACTIVE  
**Validated laboratory:** BH_OOS_002 v2 — PASS / DEMO ONLY  
**Active laboratory:** FT_DEEP_001  
**FT_DEEP status:** STEP 0 PASS / TESTER REGIME / FORMAL RAW-BAR ORACLE BLOCKED

## BH_SWEEP deployment state

- `InpBH_Enable=true`: permitted on demo only.
- `InpBH_RiskPct=0.30`: frozen; do not increase.
- Live: prohibited pending one complete forward month and review.
- Preserve all integrated prop-firm portfolio and execution safety gates.

Primary BH records:

- [Specification](Specs/TZ-BH-OOS-002.md)
- [Report](Reports/BH_OOS_002_v002_Report.md)
- [Decision](Decisions/ADR-BH-OOS-002-PASS.md)
- [Results](Results/BH_OOS_002/v002/README.md)
- [Oracle](Code/Python/BH_OOS_Oracle_v002.py)

## FT_DEEP_001 frozen objective

Determine whether the FT core (`NYBUY + LONBUY`) has a persistent edge or is a regime bet concentrated in trend periods.

Frozen gates:

- GO: EV_net >= +0.10R, N >= 90, both chronological halves positive.
- REGIME: EV_net >= +0.10R but one half non-positive, or top three months exceed 70% of total R.
- NO-GO: EV_net < 0.
- INCONCLUSIVE: N < 90 or available raw-bar depth < 24 months.

## Engine and input provenance

- Source: `AK47_FT_EA_156.mq5`.
- Source SHA256: `838b3e180a139008c69792c0f122f3da66a590ef5e6ee98056056f0938311b65`.
- Specification SHA256: `8438dd2b8affeedb882cfd18e1ae9a0e17077337dbacd90c8de9df24afa5bd8c`.
- Dry-run signal fixture SHA256: `a62a93a471cff3ce000bb237556125a9f54101c0b0ee33c5b0bca4605b0db7f2`.
- Lifecycle fixture SHA256: `c9cfa9d8ee9e07c0f55706d0dfd8d581723646b0619a3d2366206e0ab9049a18`.
- Debug log SHA256: `f259dc513f4af46bdbff5d40b45101cd574e1587d2500e8beb50c736fe14a82e`.

## Step 0 parity

**PASS**

| Module | Oracle N | Tester executed N | Delta | Matches ±1 M5 | Overlap vs oracle | Overlap vs tester |
|---|---:|---:|---:|---:|---:|---:|
| NYBUY | 18 | 17 | +1 | 15 | 83.33% | 88.24% |
| LONBUY | 7 | 7 | 0 | 7 | 100.00% | 100.00% |

`AK47_ea_dryrun_signals.csv` contains candidate ACCEPT events. The canonical tester count is taken from `AK47_ea_trade_lifecycle.csv`, because duplicate-position protection and live execution gates can block an accepted candidate before a position is opened.

The supplied tester log ends on 2026-07-16. The oracle generated no additional FT entries during 2026-07-17..23, so the missing tail does not change Step 0 counts or overlap.

## 42-month direct tester evidence

Window evaluated: `2023-01-01..2026-07-23`; actual last FT entry: `2026-05-11`.

- FT core: N=135, WR=45.19%, EV execution-net `+1.123733R`, sum `+151.704R`, PF=2.761, trade-sequence MaxDD=15.451R.
- NYBUY: N=98, EV `+1.298765R`, sum `+127.279R`, PF=2.722.
- LONBUY: N=37, EV `+0.660135R`, sum `+24.425R`, PF=2.997.
- Early chronological half: N=54, EV `-0.007685R`, sum `-0.415R`.
- Late chronological half: N=81, EV `+1.878012R`, sum `+152.119R`.
- Top-three-month contribution: `46.51%`.
- January–February 2026 contribution to the full result: `32.35%`, not 88%.
- Zero-entry months: `9/43`.

Yearly:

- 2023: N=19, EV `-0.520158R`, sum `-9.883R`.
- 2024: N=42, EV `+0.698952R`, sum `+29.356R`.
- 2025: N=50, EV `+1.540160R`, sum `+77.008R`.
- 2026: N=24, EV `+2.300958R`, sum `+55.223R`.

### Tester classification: REGIME

The long direct tester run passes the N and EV gates but fails stationarity because the early half is non-positive and the late half produces essentially all profit. FT must not be scaled or treated as an always-on stationary edge.

This is execution-aware tester evidence, not the final raw-bar oracle decision, because the tester includes live/portfolio gates excluded by the frozen oracle convention.

## Reject and execution funnel

- NYBUY: 939 candidates, 121 accepts, 98 executed.
- LONBUY: 352 candidates, 40 accepts, 37 executed.
- Dominant rejects: `SL_TOO_TIGHT_USD`, `SCORE_BLOCK`, `FAR_FROM_SWING_HIGH`.
- HTF blocks: NYBUY 22,203; LONBUY 26,016.
- Accepted but not executed: 26, mainly duplicate-position protection and the live USD 3 SL floor.

## Raw M5 blocker

The file named `XAUUSD_M5_20220601_20260723_FULL.csv` is still incomplete:

- rows: `100,971`;
- first bar: `2025-02-13 14:15`;
- last bar: `2026-07-23 23:45`;
- SHA256: `1ba5f86a8d9f191e97e357875d6496e454630d95b5bf86e3052c2327b4a83f73`.

It cannot support the formal 2023–2026 raw-bar oracle. Terminal chart-history limits persisted even with chunked `CopyRates`.

## Next action

Run [Strategy Tester stream exporter v003](Code/Exporters/XAUUSD_M5_TesterStreamExporter_v003.mq5) inside Strategy Tester:

- XAUUSD M5;
- tester start no later than `2022-06-01`;
- tester end at least `2026-07-24` so the last requested closed bar is flushed;
- output: `XAUUSD_M5_20220601_20260723_TESTER_FULL.csv`.

Then execute the formal raw-bar oracle. No FT risk scaling or always-on deployment decision is permitted before that comparison.

Primary FT_DEEP records:

- [Specification](Specs/TZ-FT-DEEP-001.md)
- [Partial oracle report](Reports/FT_DEEP_001_PartialRun_2026-07-25.md)
- [42-month tester report](Reports/FT_DEEP_001_Tester42m_2026-07-25.md)
- [Tester results](Results/FT_DEEP_001/tester_2023_2026/)
- [Optimized oracle](Code/Python/FT_DEEP_Oracle_v002.py)
- [Tester stream exporter](Code/Exporters/XAUUSD_M5_TesterStreamExporter_v003.mq5)

## Security finding

The unrelated legacy `Grok_Core_XAU.mq5` contained a plaintext xAI API key. The key still must be revoked/rotated. `AK47_FT_EA_156.mq5` did not contain an embedded API credential in the source scan.
