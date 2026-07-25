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
- **Status:** PARTIAL FAIL / TRUNCATED AT 100,000 ROWS
- **Received:** `XAUUSD_M5_20220601_20260723.csv`.
- **Actual coverage:** 2025-02-19 06:30 through 2026-07-23 23:45.
- **Rows:** exactly 100,000.
- **SHA256:** `43a00406241ccad5136c111e9f58f06494abd2883507bbbf350eaa172d8be4c4`.
- **Problem:** single large `CopyRates` request did not return 2022-2025 history.
- **Replacement tool:** `Code/Exporters/XAUUSD_M5_DEEP_Exporter_v002.mq5` using 30-day chunks and retries.
- **Done when:** first bar <=2022-06-01, last bar >=2026-07-23 23:45, no failed chunks.

## XAU-FTD-004 — Recover tester 156-1 parity fixture
- **Priority:** P0
- **Status:** BLOCKED / INPUT MISSING
- **Required:** `AK47_ea_dryrun_signals.csv` or equivalent NYBUY/LONBUY entry times for 2026-01-01..2026-07-23.
- **Gate:** N +/-2 per module and >=80% entry-time overlap within one M5 bar.
- **Current count evidence:** NYBUY oracle 18 vs target 17; LONBUY oracle 7 vs diagnostic tester reference 7.
- **Remaining:** exact entry-time overlap.

## XAU-FTD-005 — Step 0 parity run
- **Priority:** P0
- **Status:** COUNT_PASS / TIME_OVERLAP_BLOCKED
- **NYBUY:** 18 vs 17, delta +1.
- **LONBUY:** 7 vs 7, delta 0.
- **Stop rule:** do not claim parity PASS until >=80% entry-time match is calculated.

## XAU-FTD-006 — Partial-depth frozen diagnostic
- **Priority:** P0
- **Status:** COMPLETED / INCONCLUSIVE
- **Warmup-complete window:** 2025-12-03..2026-07-23, 7.62 months.
- **Result:** N=27, EV_net=+2.160244R, sum=+58.326586R.
- **Concentration:** top three months 93.31%; zero-entry months 4/8.
- **Interpretation:** strong regime-concentration signal, but no formal REGIME verdict because depth<24 months and N<90.
- **Report:** `Reports/FT_DEEP_001_PartialRun_2026-07-25.md`.

## XAU-FTD-007 — 42-month frozen oracle run
- **Priority:** P0
- **Status:** BLOCKED BY XAU-FTD-003/004/005
- **Window:** 2023-01-01..2026-07-23 with >=200 D1 warmup.
- **Outputs:** trades, rejects, monthly/year/halves, zero-trade months, top-3 contribution and formal GO/REGIME/NO-GO/INCONCLUSIVE verdict.

## XAU-FTD-008 — FT deployment decision
- **Priority:** P1
- **Status:** BLOCKED
- **Rule:** partial seven-month profitability and concentrated January-February gains are not evidence for scaling.
