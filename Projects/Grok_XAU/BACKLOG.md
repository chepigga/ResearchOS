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
- **Status:** DONE
- **File:** `XAUUSD_M5_20220601_20260723_TESTER_FULL.csv`.
- **Coverage:** 2022-06-01 01:05 through 2026-07-23 23:40.
- **Rows:** 290,893.
- **SHA256:** `40175d5d73fbbe01d26fd1813d1bc299854ef535c328fa1fdd1b883f90509ae4`.
- **Method:** Strategy Tester streaming exporter.
- **Audit:** zero duplicates, zero invalid OHLC rows.

## XAU-FTD-004 — Recover tester 156-1 parity fixture
- **Priority:** P0
- **Status:** DONE
- **Files received:** `AK47_ea_dryrun_signals.csv`, `AK47_ea_trade_lifecycle.csv`, `AK47_ea_debug_log.csv`.
- **Canonical execution fixture:** lifecycle CSV, not raw ACCEPT count.

## XAU-FTD-005 — Step 0 parity run
- **Priority:** P0
- **Status:** PASS
- **NYBUY:** oracle 18 vs tester executions 17; delta +1; 15 matches; overlap 83.33% vs oracle and 88.24% vs tester.
- **LONBUY:** oracle 7 vs tester executions 7; 7 matches; overlap 100%.

## XAU-FTD-006 — Partial raw-bar diagnostic
- **Priority:** P0
- **Status:** COMPLETED / SUPERSEDED BY FULL INPUT
- **Warmup-complete window:** 2025-12-03..2026-07-23, 7.62 months.
- **Result:** N=27, EV_net=+2.160244R, sum=+58.326586R.
- **Report:** `Reports/FT_DEEP_001_PartialRun_2026-07-25.md`.

## XAU-FTD-007 — 42-month direct tester analysis
- **Priority:** P0
- **Status:** DONE / TESTER CLASSIFICATION REGIME
- **FT core:** N=135, EV execution-net +1.123733R, sum +151.704R, PF 2.761.
- **Early half:** EV -0.007685R.
- **Late half:** EV +1.878012R.
- **Report:** `Reports/FT_DEEP_001_Tester42m_2026-07-25.md`.

## XAU-FTD-008 — 42-month frozen raw-bar oracle
- **Priority:** P0
- **Status:** READY / FULL M5 AVAILABLE
- **Window:** 2023-01-01..2026-07-23 with tester-stream warmup from 2022-06-01.
- **Inputs:** parity PASS, full tester-stream M5, frozen v1.56 source.
- **Outputs:** trades, rejects, monthly/year/halves, concentration and formal GO/REGIME/NO-GO/INCONCLUSIVE verdict.
- **Rule:** run once without retuning.

## XAU-FTD-009 — FT deployment decision
- **Priority:** P1
- **Status:** ALWAYS-ON SCALING REJECTED / FINAL MODE DECISION PENDING RAW-BAR ORACLE
- **Current decision:** do not scale FT as a stationary always-on edge.
- **Reason:** tester REGIME and FT_REJECTED CONFIRMS-REGIME.

## XAU-FTR-001 — Register frozen rejected-candidate control
- **Priority:** P0
- **Status:** DONE
- **Record:** `Specs/TZ-FT-REJECTED-001.md`.
- **SHA256:** `45e6bed26e0a0e5d795d45eeefa4d70cf7ff02c88755ed0f4425d1fe42b5d89d`.

## XAU-FTR-002 — Replay ACCEPT and REJECT population
- **Priority:** P0
- **Status:** DONE / FORMAL FROZEN
- **Candidates:** 1,288 after excluding 3 `DAILY_STOP` rows.
- **Missing M5 timestamps:** 0.
- **ACCEPT:** N=161, EV +1.324759R, PF 3.481.
- **REJECT:** N=1127, EV +0.044172R, PF 1.056.

## XAU-FTR-003 — Open frozen verdict
- **Priority:** P0
- **Status:** DONE / CONFIRMS-REGIME
- **ACCEPT 2023:** N=22, EV -0.439417R.
- **REJECT 2023:** N=268, EV -0.031983R.
- **REJECT EARLY:** N=551, EV -0.072206R.
- **REJECT LATE:** N=576, EV +0.155498R.
- **Decision:** `Decisions/ADR-FT-REJECTED-001-CONFIRMS-REGIME.md`.

## XAU-FTR-004 — Preserve strongly useful gates
- **Priority:** P0
- **Status:** DONE / KEEP
- **SL_TOO_TIGHT_USD:** N=508, EV -0.150530R, PF 0.816.
- **Rule:** do not weaken this filter.

## XAU-FTR-005 — Gate-loosening OOS follow-up
- **Priority:** P1
- **Status:** NOT STARTED / SEPARATE PREREGISTRATION REQUIRED
- **Candidates:** `FAR_FROM_SWING_HIGH` and `SCORE_BLOCK` only as frozen research leads.
- **Constraint:** choose one hypothesis before new OOS contact; no multi-gate tuning tournament on 2023–2026.
