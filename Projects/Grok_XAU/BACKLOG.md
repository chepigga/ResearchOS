# Grok XAU Backlog

## XAU-BH-001 — Register frozen BH_SWEEP OOS protocol
- **Priority:** P0
- **Status:** DONE
- **Record:** `Specs/TZ-BH-OOS-002.md`

## XAU-BH-002 — Revoke leaked xAI key
- **Priority:** P0 SECURITY
- **Status:** USER ACTION REQUIRED
- **Reason:** plaintext key found in unrelated legacy `Grok_Core_XAU.mq5`.

## XAU-BH-003 — Recover and validate BH oracle
- **Priority:** P0
- **Status:** DONE / PASS
- **Result:** Step 0 N=88 B52/S36; OOS N=14, EV_net=+0.235714R.

## XAU-BH-004 — Demo forward month
- **Priority:** P0
- **Status:** READY / NEXT
- **Configuration:** unchanged v1.56 defaults; `InpBH_Enable=true`; risk 0.30%.
- **Live:** prohibited until forward review.

## XAU-FTD-001 — Register frozen FT_DEEP specification
- **Priority:** P0
- **Status:** DONE
- **Record:** `Specs/TZ-FT-DEEP-001.md`
- **Rule:** no post-data parameter changes.

## XAU-FTD-002 — Recover exact v1.56 parity contract
- **Priority:** P0
- **Status:** DONE / AUDITED
- **Source:** `AK47_FT_EA_156.mq5`.
- **SHA256:** `838b3e180a139008c69792c0f122f3da66a590ef5e6ee98056056f0938311b65`.
- **Modules:** NYBUY + LONBUY only.
- **Oracle:** `Code/Python/FT_DEEP_Oracle_v002.py`.

## XAU-FTD-003 — Export full same-feed M5 history
- **Priority:** P0
- **Status:** BLOCKED / TERMINAL HISTORY LIMIT PERSISTS
- **Latest received:** `XAUUSD_M5_20220601_20260723_FULL.csv`.
- **Actual coverage:** 2025-02-13 14:15 through 2026-07-23 23:45.
- **Rows:** 100,971.
- **SHA256:** `1ba5f86a8d9f191e97e357875d6496e454630d95b5bf86e3052c2327b4a83f73`.
- **Problem:** ordinary terminal `CopyRates` still exposes only the recent chart-history cache.
- **Replacement tool:** `Code/Exporters/XAUUSD_M5_TesterStreamExporter_v003.mq5`.
- **Done when:** tester-stream file begins no later than 2022-06-01 and ends at or after 2026-07-23 23:45.

## XAU-FTD-004 — Recover tester 156-1 parity fixture
- **Priority:** P0
- **Status:** DONE
- **Files received:** `AK47_ea_dryrun_signals.csv`, `AK47_ea_trade_lifecycle.csv`, `AK47_ea_debug_log.csv`.
- **Canonical execution fixture:** lifecycle CSV, not raw ACCEPT count.
- **Reason:** accepted candidates may be blocked before execution by duplicate protection or live execution gates.

## XAU-FTD-005 — Step 0 parity run
- **Priority:** P0
- **Status:** PASS
- **NYBUY:** oracle 18 vs tester executions 17; delta +1; 15 matches; overlap 83.33% vs oracle and 88.24% vs tester.
- **LONBUY:** oracle 7 vs tester executions 7; 7 matches; overlap 100%.
- **Gate:** N ±2 and >=80% time overlap passed for both modules.

## XAU-FTD-006 — Partial raw-bar diagnostic
- **Priority:** P0
- **Status:** COMPLETED / INCONCLUSIVE
- **Warmup-complete window:** 2025-12-03..2026-07-23, 7.62 months.
- **Result:** N=27, EV_net=+2.160244R, sum=+58.326586R.
- **Concentration:** top three months 93.31%; zero-entry months 4/8.
- **Interpretation:** strong regime-concentration signal, but insufficient raw-bar depth.
- **Report:** `Reports/FT_DEEP_001_PartialRun_2026-07-25.md`.

## XAU-FTD-007 — 42-month direct tester analysis
- **Priority:** P0
- **Status:** DONE / TESTER CLASSIFICATION REGIME
- **Window:** 2023-01-01..2026-07-23.
- **FT core:** N=135, EV execution-net +1.123733R, sum +151.704R, PF 2.761.
- **Early half:** EV -0.007685R, sum -0.415R.
- **Late half:** EV +1.878012R, sum +152.119R.
- **Year 2023:** negative; 2024–2026 positive.
- **Frozen-rule classification:** REGIME because one chronological half is non-positive.
- **Constraint:** this is tester evidence with live/portfolio gates, not the final raw-bar oracle.
- **Report:** `Reports/FT_DEEP_001_Tester42m_2026-07-25.md`.

## XAU-FTD-008 — 42-month frozen raw-bar oracle
- **Priority:** P0
- **Status:** BLOCKED BY XAU-FTD-003 ONLY
- **Window:** 2023-01-01..2026-07-23 with >=200 D1 warmup.
- **Outputs:** trades, rejects, monthly/year/halves, zero-trade months, top-3 contribution and formal GO/REGIME/NO-GO/INCONCLUSIVE verdict.
- **Next action:** run `XAUUSD_M5_TesterStreamExporter_v003.mq5` inside Strategy Tester.

## XAU-FTD-009 — FT deployment decision
- **Priority:** P1
- **Status:** ALWAYS-ON SCALING REJECTED / FINAL MODE DECISION BLOCKED
- **Current decision:** do not scale FT as a stationary always-on edge.
- **Reason:** tester REGIME classification, 2023 negative, early half flat/negative, late-half concentration.
- **Final decision dependency:** formal raw-bar oracle and, if REGIME confirms, preregistered regime-classifier research rather than parameter retuning.
