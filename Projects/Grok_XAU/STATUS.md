# Grok XAU Status

**Updated:** 2026-07-25  
**Project status:** ACTIVE  
**Validated laboratory:** BH_OOS_002 v2 — PASS / DEMO ONLY  
**Completed laboratory:** FT_REJECTED_001 — CONFIRMS-REGIME  
**FT_DEEP status:** STEP 0 PASS / TESTER REGIME / FULL M5 RECOVERED / FORMAL RAW-BAR ORACLE READY

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
- FT_DEEP specification SHA256: `8438dd2b8affeedb882cfd18e1ae9a0e17077337dbacd90c8de9df24afa5bd8c`.
- FT_REJECTED specification SHA256: `45e6bed26e0a0e5d795d45eeefa4d70cf7ff02c88755ed0f4425d1fe42b5d89d`.
- Dry-run signal fixture SHA256: `a62a93a471cff3ce000bb237556125a9f54101c0b0ee33c5b0bca4605b0db7f2`.
- Lifecycle fixture SHA256: `c9cfa9d8ee9e07c0f55706d0dfd8d581723646b0619a3d2366206e0ab9049a18`.
- Debug log SHA256: `f259dc513f4af46bdbff5d40b45101cd574e1587d2500e8beb50c736fe14a82e`.
- Tester-stream M5 SHA256: `40175d5d73fbbe01d26fd1813d1bc299854ef535c328fa1fdd1b883f90509ae4`.
- Tester-stream M5 rows: `290,893`.
- Tester-stream M5 coverage: `2022-06-01 01:05 .. 2026-07-23 23:40`.

## Step 0 parity

**PASS**

| Module | Oracle N | Tester executed N | Delta | Matches ±1 M5 | Overlap vs oracle | Overlap vs tester |
|---|---:|---:|---:|---:|---:|---:|
| NYBUY | 18 | 17 | +1 | 15 | 83.33% | 88.24% |
| LONBUY | 7 | 7 | 0 | 7 | 100.00% | 100.00% |

`AK47_ea_dryrun_signals.csv` contains candidate ACCEPT events. The canonical tester count is taken from `AK47_ea_trade_lifecycle.csv`, because duplicate-position protection and live execution gates can block an accepted candidate before a position is opened.

## 42-month direct tester evidence

Window evaluated: `2023-01-01..2026-07-23`; actual last FT entry: `2026-05-11`.

- FT core: N=135, WR=45.19%, EV execution-net `+1.123733R`, sum `+151.704R`, PF=2.761, trade-sequence MaxDD=15.451R.
- NYBUY: N=98, EV `+1.298765R`, sum `+127.279R`, PF=2.722.
- LONBUY: N=37, EV `+0.660135R`, sum `+24.425R`, PF=2.997.
- Early chronological half: N=54, EV `-0.007685R`, sum `-0.415R`.
- Late chronological half: N=81, EV `+1.878012R`, sum `+152.119R`.
- Top-three-month contribution: `46.51%`.
- January–February 2026 contribution: `32.35%`.
- Zero-entry months: `9/43`.

### Tester classification: REGIME

The long direct tester run passes the N and EV gates but fails stationarity because the early half is non-positive and the late half produces essentially all profit. FT must not be scaled or treated as an always-on stationary edge.

## FT_REJECTED_001 formal control

**Primary verdict: CONFIRMS-REGIME**

Formal independent replay after excluding `DAILY_STOP`:

- candidates: `1,288`;
- missing M5 timestamps: `0`;
- ACCEPT: N=161, EV `+1.324759R`, PF `3.481`;
- REJECT: N=1127, EV `+0.044172R`, PF `1.056`;
- ACCEPT 2023: N=22, EV `-0.439417R`;
- REJECT 2023: N=268, EV `-0.031983R`;
- REJECT EARLY: N=551, EV `-0.072206R`;
- REJECT LATE: N=576, EV `+0.155498R`.

The broad rejected population is also weak in 2023/early and improves later. The regime break is therefore not primarily a narrow-sample or gate-calibration artifact.

### Gate findings

Strong keep evidence:

- `SL_TOO_TIGHT_USD`: N=508, EV `-0.150530R`, PF `0.816`; negative in 2023, 2024 and 2025.

Research-only `GATE_LOOSEN_CANDIDATE`:

- ALL/FAR_FROM_SWING_HIGH: N=245, EV `+0.164429R`.
- ALL/SCORE_BLOCK: N=318, EV `+0.208001R`.
- LONBUY/FAR_FROM_SWING_HIGH: N=91, EV `+0.307528R`.
- NYBUY/SCORE_BLOCK: N=297, EV `+0.202525R`.

No gate change, threshold tuning or risk increase is authorized.

Primary FT_REJECTED records:

- [Specification](Specs/TZ-FT-REJECTED-001.md)
- [Formal report](Reports/FT_REJECTED_001_Formal_Report.md)
- [Decision](Decisions/ADR-FT-REJECTED-001-CONFIRMS-REGIME.md)
- [Results](Results/FT_REJECTED_001/formal_2026-07-25/README.md)

## Next action

The full tester-stream M5 input is now available. The next canonical action is the formal frozen raw-bar `FT_DEEP_001` run. Do not retune FT before that result.

If the formal FT_DEEP oracle confirms REGIME, open one separate preregistered OOS laboratory for either a regime classifier or one selected gate-loosening hypothesis. Do not run a multi-gate tournament and choose the best result on the same 2023–2026 data.

## Security finding

The unrelated legacy `Grok_Core_XAU.mq5` contained a plaintext xAI API key. The key still must be revoked/rotated. `AK47_FT_EA_156.mq5` did not contain an embedded API credential in the source scan.
