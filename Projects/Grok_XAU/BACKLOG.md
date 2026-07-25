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
- **Audit:** `Reports/FT_DEEP_001_EngineInputAudit.md`.

## XAU-FTD-003 — Export full same-feed M5 history
- **Priority:** P0
- **Status:** BLOCKED / USER RUN REQUIRED
- **Required coverage:** 2022-06-01 warmup through 2026-07-23.
- **Tool:** `Code/Exporters/XAUUSD_M5_DEEP_Exporter_v001.mq5`.
- **Current data:** 2025-01-01 23:00 through 2026-04-21 23:45, 95,466 rows, 15.61 months.
- **Done when:** full CSV is uploaded and passes hash/coverage/OHLC audit.

## XAU-FTD-004 — Recover tester 156-1 parity fixture
- **Priority:** P0
- **Status:** BLOCKED / INPUT MISSING
- **Required:** NYBUY and LONBUY entry times for 2026-01-01..2026-07-23.
- **Gate:** N +/-2 per module and >=80% entry-time overlap within one M5 bar.
- **Note:** historical v1.54b candidate outcomes are diagnostic only.

## XAU-FTD-005 — Step 0 parity run
- **Priority:** P0
- **Status:** BLOCKED BY XAU-FTD-003/004
- **Stop rule:** no deep run after parity failure.

## XAU-FTD-006 — 42-month frozen oracle run
- **Priority:** P0
- **Status:** BLOCKED BY XAU-FTD-005
- **Window:** 2023-01-01..2026-07-23 with >=200 D1 warmup.
- **Outputs:** trades, rejects, monthly/year/halves, zero-trade months, top-3 contribution and formal GO/REGIME/NO-GO/INCONCLUSIVE verdict.

## XAU-FTD-007 — FT deployment decision
- **Priority:** P1
- **Status:** BLOCKED
- **Rule:** current seven-month tester profitability is not sufficient evidence for scaling.
