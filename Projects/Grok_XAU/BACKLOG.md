# Grok XAU Backlog

## XAU-BH-001 — Register frozen BH_SWEEP OOS protocol

- **Priority:** P0
- **Status:** DONE
- **Done when:** TZ-BH-OOS-001v2 is committed without parameter changes.

## XAU-BH-002 — Revoke leaked xAI key

- **Priority:** P0 SECURITY
- **Status:** USER ACTION REQUIRED
- **Reason:** plaintext key found in unrelated supplied legacy `Grok_Core_XAU.mq5` and prior File Library copies.
- **Done when:** old key is revoked and replacement is stored outside source code.

## XAU-BH-003 — Recover frozen oracle source

- **Priority:** P0
- **Status:** PARTIALLY DONE / ENGINE IDENTIFIED
- **Recovered source:** `AK47_FT_EA_156.mq5`, BH_SWEEP v1.55 inside EA v1.56.
- **Evidence:** source records MorrisCandle V2 + EMA20 and control `N=88 (B52/S36), EV=+0.276R`.
- **Remaining:** isolate the BH oracle from integrated EA gates and verify exact execution conventions by Step 0.
- **Done when:** isolated harness reproduces the registered control within drift tolerance.

## XAU-BH-004 — Export same-feed XAUUSD M15

- **Priority:** P0
- **Status:** READY FOR USER RUN
- **Range:** 2024-12-01 00:00 through 2026-07-24 00:00 exclusive.
- **Tool:** `Code/Exporters/XAUUSD_M15_Exporter_v001.mq5`
- **Done when:** CSV is uploaded, SHA256 and row count are recorded, last closed bar is 2026-07-23.

## XAU-BH-005 — Build isolated BH oracle parity harness

- **Priority:** P0
- **Status:** BLOCKED BY DATA / ORIGINAL CONTROL BOUNDARY
- **Source:** BH logic recovered from `AK47_FT_EA_156.mq5`.
- **Exclude:** daily stop, max trades/day, loss-streak cooldown, one-open-position restriction, portfolio gates, USD 3 SL floor, spread/STOPLEVEL/FREEZELEVEL/margin gates.
- **Include:** frozen signal rules, market-entry convention, SL/TP, 96-bar time stop and external `-0.05R/trade` cost.
- **Done when:** deterministic trades CSV can be generated from M15 data.

## XAU-BH-006 — Step 0 reproduction control

- **Priority:** P0
- **Status:** BLOCKED BY XAU-BH-004/005
- **Gate:** N=88, B52/S36, EV=+0.276R; allowed drift N≤2 and EV≤0.02R.
- **Stop rule:** larger drift means CONTROL_FAIL and pipeline localisation before OOS.

## XAU-BH-007 — Step 1 frozen OOS run

- **Priority:** P0
- **Status:** BLOCKED BY XAU-BH-006
- **Window:** 2026-05-01..2026-07-23
- **Outputs:** trades CSV, May/June/July breakdown, report and formal verdict.

## XAU-BH-008 — Demo forward month

- **Priority:** P1
- **Status:** BLOCKED
- **Dependency:** only after OOS PASS.
- **Rule:** demo only; no live enablement.
