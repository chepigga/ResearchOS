# GC_XAU_EXISTING_DATA_FULL_REPLAY_AUDIT_LAB_013H

**Status: HISTORICAL_REPLAY_PASS**

Uses only the already-collected frozen AMP GC and FTMO-Demo XAU raw data. No new market data and no retuning.

## Gates

- PASS — `amp_sha_exact`
- PASS — `gc_bar_timestamp_parity`
- PASS — `gc_numeric_parity`
- PASS — `gc_a_buy_parity`
- PASS — `gc_signal_parity`
- PASS — `lab004_event_timestamp_parity`
- PASS — `lab004_return_parity`
- PASS — `xau_frozen_inventory_exact`
- PASS — `clock_offset_reproduced`
- PASS — `lab009_d1e3_metrics_reproduced`

## GC independent replay

- AMP raw rows: 3,737,579
- exclusive directional rows: 3,731,970
- reconstructed M1 bars: canonical 38,464 / independent 38,464
- a_buy mismatches: 0
- signal mismatches: 0
- LAB004 AMP events: frozen 281 / replay 281 / exact timestamp matches 281

## FTMO XAU raw inventory

- files: 32 (expected 32)
- quote-valid rows: 8,236,717 (expected 8,236,717)
- first/last `time_msc`: 1785719100005 / 1789516199707
- crossed quotes: 0
- best GC/XAU clock offset: +180 min
- executable AMP events: 279

## Frozen D1.00 E3 operational replay (+0.05R/fill, one-active)

- signals: 279; accepted 241; fills 105
- EV/original signal: +0.078813R
- EV/fill: +0.209417R
- PF: 1.335710
- MaxDD: 8.400000R
- early/late EV: +0.083408 / +0.068145 R/signal
- exact LAB009 core-metric reproduction: PASS

## D1.00 E1 historical diagnostic — NOT promoted

- signals: 279; accepted 268; fills 51
- EV/original signal: +0.060879R
- EV/fill: +0.333043R
- PF: 1.550586
- MaxDD: 4.200000R
- early/late EV: +0.093407 / -0.014633 R/signal

## Interpretation

A PASS proves internal historical reproducibility of the collected-data pipeline. It does not create untouched OOS evidence and does not retroactively validate E1 as production logic.

## One-active clock semantic audit

Frozen LAB009 released an **unfilled** setup at `signal_time + expiry`; the actionable XAU limit starts at the next M1, so the operational clock should be `order_start + expiry`. Filled setups are unchanged.

| Candidate | Clock | Accepted | Fills | EV/signal | EV/fill | PF | MaxDD R | Late EV |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| D1.00_E1M | Frozen | 268 | 51 | +0.060879 | +0.333043 | 1.5506 | 4.2000 | -0.014633 |
| D1.00_E1M | Corrected | 261 | 49 | +0.062011 | +0.353085 | 1.5806 | 4.5876 | -0.014633 |
| D1.00_E3M | Frozen | 241 | 105 | +0.078813 | +0.209417 | 1.3357 | 8.4000 | +0.068145 |
| D1.00_E3M | Corrected | 237 | 103 | +0.086340 | +0.233871 | 1.3800 | 8.4000 | +0.068145 |

This correction is reported separately and does not overwrite the frozen LAB009 baseline. If material, the corrected execution semantics must become the reference for subsequent robustness work.
