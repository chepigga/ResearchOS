# Grok XAU Status

**Updated:** 2026-07-25  
**Project status:** ACTIVE  
**Validated laboratory:** BH_OOS_002 v2 — PASS / DEMO ONLY  
**Active laboratory:** FT_DEEP_001  
**FT_DEEP status:** INCONCLUSIVE / PARTIAL REGIME SIGNAL / FULL DATA AND TIME-PARITY REQUIRED

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

Determine whether the FT core (`NYBUY + LONBUY`) has a persistent edge or is a regime bet concentrated in a few trend months.

Frozen gates:

- GO: EV_net >= +0.10R, N >= 90, both OOS halves positive.
- REGIME: EV_net >= +0.10R but one half non-positive, or top three months exceed 70% of total R.
- NO-GO: EV_net < 0.
- INCONCLUSIVE: N < 90 or available depth < 24 months.

## FT_DEEP engine provenance

- Source: `AK47_FT_EA_156.mq5`.
- Source SHA256: `838b3e180a139008c69792c0f122f3da66a590ef5e6ee98056056f0938311b65`.
- Specification SHA256: `8438dd2b8affeedb882cfd18e1ae9a0e17077337dbacd90c8de9df24afa5bd8c`.
- Modules: NYBUY and LONBUY only.
- v1.56 defaults frozen; tuning forbidden.
- Portfolio gates excluded from the oracle.
- Fixed cost: `-0.05R/trade`.

## Uploaded FT_DEEP data audit

Received `XAUUSD_M5_20220601_20260723.csv`:

- rows: `100,000`;
- first bar: `2025-02-19 06:30`;
- last bar: `2026-07-23 23:45`;
- calendar depth: `17.05 months`;
- SHA256: `43a00406241ccad5136c111e9f58f06494abd2883507bbbf350eaa172d8be4c4`;
- duplicates: `0`;
- invalid OHLC rows: `0`.

The filename requests history from 2022-06-01, but the content begins in February 2025 and contains exactly 100,000 rows. The single-request exporter was truncated by terminal/history limits. D1 EMA50 parity becomes warmup-complete only from `2025-12-03 01:05`, leaving `7.62 months` of reliable diagnostic depth.

## Step 0 status

- NYBUY: tester target `17`; oracle `18`; delta `+1` — count PASS.
- LONBUY: diagnostic tester reference `7`; oracle `7`; delta `0` — count PASS.
- Required `>=80%` entry-time overlap: BLOCKED because tester 156-1 entry-time fixture is missing.

Step 0 is `COUNT_PASS / TIME_OVERLAP_BLOCKED`, not a formal parity PASS.

## Warmup-complete partial diagnostic

Window: `2025-12-03 01:05..2026-07-23 23:45`.

- N: `27`;
- EV_net: `+2.160244R`;
- Sum: `+58.326586R`;
- WR: `59.26%`;
- PF: `6.050`;
- NYBUY: N=20, EV `+2.850000R`, Sum `+57.000000R`;
- LONBUY: N=7, EV `+0.189512R`, Sum `+1.326586R`.

Regime diagnostics:

- zero-entry months: `4/8`;
- top-three months contribution: `93.31%` of total net R;
- March, May, June and July 2026 had zero entries;
- HTF rejects: NYBUY `5,087`; LONBUY `5,927`.

The concentration exceeds the frozen REGIME trigger, but the formal verdict remains **INCONCLUSIVE** because depth is below 24 months, N is below 90, and Step 0 time parity is incomplete. This partial run is evidence, not permission to scale risk.

## Required next action

1. Run [chunked exporter v002](Code/Exporters/XAUUSD_M5_DEEP_Exporter_v002.mq5) in the same broker terminal.
2. Verify the first bar is no later than `2022-06-01` and the last bar is `2026-07-23 23:45` or later.
3. Upload tester 156-1 `AK47_ea_dryrun_signals.csv` or equivalent NYBUY/LONBUY entry-time fixture.
4. Re-run Step 0; only after parity PASS open the 42-month verdict.

Primary FT_DEEP records:

- [Specification](Specs/TZ-FT-DEEP-001.md)
- [Partial report](Reports/FT_DEEP_001_PartialRun_2026-07-25.md)
- [Partial results](Results/FT_DEEP_001/partial_2026-07-25/README.md)
- [Optimized oracle](Code/Python/FT_DEEP_Oracle_v002.py)
- [Chunked exporter](Code/Exporters/XAUUSD_M5_DEEP_Exporter_v002.mq5)

## Security finding

The unrelated legacy `Grok_Core_XAU.mq5` contained a plaintext xAI API key. The key still must be revoked/rotated. `AK47_FT_EA_156.mq5` did not contain an embedded API credential in the source scan.
