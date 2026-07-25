# Grok XAU Status

**Updated:** 2026-07-25  
**Project status:** ACTIVE  
**Validated laboratory:** BH_OOS_002 v2 — PASS / DEMO ONLY  
**Active laboratory:** FT_DEEP_001  
**FT_DEEP status:** PREREGISTERED / BLOCKED_FULL_M5_AND_PARITY_FIXTURE

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

Determine whether the FT core (`NYBUY + LONBUY`) has a persistent edge or is a
regime bet concentrated in a few trend months.

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

## Current FT_DEEP data state

Available same-feed M5:

- coverage: `2025-01-01 23:00` through `2026-04-21 23:45`;
- rows: `95,466`;
- approximate depth: `15.61 months`;
- SHA256: `cd2e3285c0e4660786a019999fb3e746257c2cbd4d400fe48092cdbbc7760a80`.

This is below the frozen 24-month minimum and lacks the required 200-D1 warmup
before 2023-01-01. A formal deep verdict is not open.

## Step 0 blocker

The tester 156-1 target is NYBUY N=17 plus a small LONBUY sample, with N tolerance
+/-2 per module and at least 80% entry-time matching within one M5 bar.

A historical v1.54b candidate diagnostic is available, but the exact tester
156-1 entry fixture is not available. Trade-time parity is therefore not claimed.

## Next executable action

1. Run `Code/Exporters/XAUUSD_M5_DEEP_Exporter_v001.mq5` in the same broker terminal.
2. Upload `XAUUSD_M5_20220601_20260723.csv`.
3. Upload tester 156-1 deals/signals containing NYBUY and LONBUY entry times.
4. Run Step 0. Do not open the 42-month result unless the registered parity gate passes.

## Security finding

The unrelated legacy `Grok_Core_XAU.mq5` contained a plaintext xAI API key. The
key still must be revoked/rotated. `AK47_FT_EA_156.mq5` did not contain an
embedded API credential in the source scan.
