# Grok XAU Backlog

## XAU-BH-001 — Register frozen BH_SWEEP OOS protocol

- **Priority:** P0
- **Status:** DONE
- **Done when:** TZ-BH-OOS-001v2 is committed without parameter changes.

## XAU-BH-002 — Revoke leaked xAI key

- **Priority:** P0 SECURITY
- **Status:** USER ACTION REQUIRED
- **Reason:** plaintext key found in supplied legacy EA and prior File Library copies.
- **Done when:** old key is revoked and replacement is stored outside source code.

## XAU-BH-003 — Recover frozen oracle package

- **Priority:** P0
- **Status:** BLOCKED
- **Required:** exact MorrisCandle V2 code, config, dependency versions, original in-sample window and any tie-breaking/execution conventions.
- **Done when:** package hash is recorded and control can be run without reimplementation guesswork.

## XAU-BH-004 — Export same-feed XAUUSD M15

- **Priority:** P0
- **Status:** READY FOR USER RUN
- **Range:** 2024-12-01 00:00 through 2026-07-24 00:00 exclusive.
- **Tool:** `Code/Exporters/XAUUSD_M15_Exporter_v001.mq5`
- **Done when:** CSV is uploaded, SHA256 and row count are recorded, last closed bar is 2026-07-23.

## XAU-BH-005 — Step 0 reproduction control

- **Priority:** P0
- **Status:** BLOCKED BY XAU-BH-003/004
- **Gate:** N=88, B52/S36, EV=+0.276R; allowed drift N≤2 and EV≤0.02R.
- **Stop rule:** larger drift means CONTROL_FAIL and pipeline localisation before OOS.

## XAU-BH-006 — Step 1 frozen OOS run

- **Priority:** P0
- **Status:** BLOCKED BY XAU-BH-005
- **Window:** 2026-05-01..2026-07-23
- **Outputs:** trades CSV, May/June/July breakdown, report and formal verdict.

## XAU-BH-007 — Demo forward month

- **Priority:** P1
- **Status:** BLOCKED
- **Dependency:** only after OOS PASS.
- **Rule:** demo only; no live enablement.
