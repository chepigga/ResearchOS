# Grok XAU Backlog

## XAU-BH-001 — Register frozen BH_SWEEP OOS protocol

- **Priority:** P0
- **Status:** DONE
- **Record:** `Specs/TZ-BH-OOS-002.md`

## XAU-BH-002 — Revoke leaked xAI key

- **Priority:** P0 SECURITY
- **Status:** USER ACTION REQUIRED
- **Reason:** plaintext key found in unrelated legacy `Grok_Core_XAU.mq5`.
- **Done when:** old key is revoked and replacement is stored outside source code.

## XAU-BH-003 — Recover frozen oracle source

- **Priority:** P0
- **Status:** DONE
- **Source:** `AK47_FT_EA_156.mq5`, BH_SWEEP v1.55 inside EA v1.56.
- **Evidence:** exact Step 0 reproduction N=88, B52/S36, EV=+0.275780R.

## XAU-BH-004 — Export and audit same-feed XAUUSD M15

- **Priority:** P0
- **Status:** DONE
- **File:** `XAUUSD_M15_202412020100_202607232345.csv`
- **Coverage:** 2024-12-02 01:00 through 2026-07-23 23:45.
- **Rows:** 38,742; duplicates 0; invalid OHLC 0.
- **SHA256:** `7a03c7eca6d333981cc9f30c783f83c31ec15bed46d6b44ae2164a756574f1f3`.

## XAU-BH-005 — Build isolated BH oracle parity harness

- **Priority:** P0
- **Status:** DONE / FROZEN
- **Code:** `Code/Python/BH_OOS_Oracle_v002.py`
- **Excluded:** daily/portfolio/live broker gates.
- **Included:** exact signal ordering, next-open entry, SL/TP, 96-bar time stop, conservative collision and fixed -0.05R cost.

## XAU-BH-006 — Step 0 reproduction control

- **Priority:** P0
- **Status:** PASS
- **Result:** N=88, B52/S36, legacy EV=+0.275780R.
- **Diff:** 88/88 time+direction matches; exit mismatches 0; only reference rounding residuals.
- **Canonical parent:** wide basket + EMA20 reversal context.

## XAU-BH-007 — Step 1 frozen OOS run

- **Priority:** P0
- **Status:** PASS / VALIDATED
- **Window:** 2026-05-01..2026-07-23.
- **Result:** N=14, EV_net=+0.235714R, sum=+3.300R.
- **Monthly:** May, June and July all positive.
- **Decision:** demo-only enablement permitted; live prohibited.

## XAU-BH-008 — Demo forward month

- **Priority:** P0
- **Status:** READY / NEXT
- **Configuration:** unchanged v1.56 defaults; `InpBH_Enable=true`; `InpBH_RiskPct=0.30`.
- **Required logging:** signal, fill, spread, slippage, SL/TP, time-stop, rejects and portfolio gates.
- **Stop conditions:** material oracle drift, duplicated/missing signals, execution cost materially above convention, or unsafe drawdown behaviour.
- **Done when:** one complete forward month is reviewed and a live/no-live decision is recorded.

## XAU-BH-009 — Live decision

- **Priority:** P1
- **Status:** BLOCKED BY XAU-BH-008
- **Rule:** OOS PASS alone is insufficient for live deployment.
