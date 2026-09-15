# AMP_NATIVE_AEIF_FORWARD_SHADOW_001 — preregistration

## Purpose
Forward-only validation of AMP/CQG-native GC AEIF signals against the **live target XAUUSD feed**. This is a shadow experiment only: neither EA is allowed to place, modify, or close a real order.

## Frozen signal engine
Source of truth: `AEIF_FROZEN_SPEC_001.json` and `amp_gc_oos_001_one_shot.py`.

- GC working bars: UTC M5 traded bars built from `COPY_TICKS_TRADE`.
- Aggressor bridge: **exclusive-side only**. Prints carrying both BUY and SELL flags are excluded from directional aggressive volume.
- Delta fraction: `(buy_only - sell_only)/(buy_only + sell_only)`.
- Location: LONG uses exclusive SELL volume in inclusive lower 20% of the bar range; SHORT uses exclusive BUY volume in inclusive upper 20%.
- References: current bar excluded; prior 240 completed traded M5 bars; Q10/Q90 delta-fraction and side-specific Q75 location.
- ATR for AEIF: ATR14 Wilder equivalent to `ewm(alpha=1/14, adjust=false, min_periods=14)`.
- LONG core: delta <= prior Q10; sell-location >= prior Q75; `max(0,open-close)/ATR14 <= 0.15`.
- SHORT core: mirror with prior Q90, buy-location Q75, `max(0,close-open)/ATR14 <= 0.15`.
- Confirmation: first of the next 2 **clock-contiguous** M5 bars with LONG `close>open && delta>0`, SHORT `close<open && delta<0`; missing M5 clock bar expires the setup.
- Entry schedule: next M5 clock after completed confirmation.
- Historical 30m cooldown is recorded as a diagnostic branch only and **does not suppress transfer confirmations** in this forward experiment, matching the frozen GC→XAU lineage.

## Frozen shadow execution
- Target symbol: broker's live XAUUSD symbol (input; default `XAUUSD`).
- Entry quote: LONG at live Ask, SHORT at live Bid.
- Risk distance: 1.0 × XAU ATR20(M5), calculated from the previous completed M5 bar.
- TP: 3R.
- Max hold: 240 minutes from scheduled entry clock.
- Single position: yes. Signals arriving while a shadow position is active are logged and rejected.
- BE/partials/trailing: none.
- Stop/target monitoring: live executable side (LONG Bid, SHORT Ask), consuming the full live XAU tick stream rather than timer snapshots.
- Session gap: if quote timestamps jump by >90s, exit is recorded at the last executable quote before the gap.
- Stale signal gate: >5000ms after scheduled entry clock is rejected and logged; no carry-forward.

## Transport
Version 001 uses `FILE_COMMON`, therefore both MT5 terminals must run under the **same Windows user on the same machine/VPS**. Signal bridge: `Terminal/Common/Files/AEIF_SHADOW_001/signals.csv`.

## Logged evidence
Every signal/decision stores sensor session+sequence, GC core/confirmation clocks, scheduled XAU entry clock, GC emission tick time, XAU quote time, transport lag, spread, ATR20, entry/SL/TP, MFE/MAE, exit reason and R.

## Governance
- No parameter changes during the forward sample.
- No retrospective deletion of rejected/stale/busy signals.
- No use of the prior `AMP_NATIVE_AEIF_XAU_EV_001` negative number as a certified benchmark because historical XAU parity failed.
- Evaluate the forward stream as a new independent evidence set. Any strategy change requires a separately named LAB/version.
