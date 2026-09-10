# BTC_LONG_V1_CLOSED_BAR_TRANSPORT_PARITY_AND_FRESH_SEQUENTIAL_CONTINUATION_LAB_065

**Verdict:** `WATCH_POSTFREEZE_TOO_EARLY__CLOSED_BAR_TRANSPORT_CERTIFIED`

## Closed-bar transport

```json
{
  "m1": {
    "overlap_n": 3239,
    "min_required": 250,
    "exact_rows": 3239,
    "exact_share": 1.0,
    "max_abs_ohlc_diff": 0.0,
    "pass": true
  },
  "m5": {
    "overlap_n": 832,
    "min_required": 100,
    "exact_rows": 832,
    "exact_share": 1.0,
    "max_abs_ohlc_diff": 0.0,
    "pass": true
  },
  "pass": true
}
```

## Structural terminal exclusion

M1 frozen rows: 1371240 total; 1371239 provably closed; 1 unproven terminal.
M5 frozen rows: 728106 total; 728105 provably closed; 1 unproven terminal.

The same structural rule was applied to both intervals before parity outcomes. No mismatch-driven row filtering is allowed.

## True post-freeze LONG v1

Elapsed since freeze: 1.127 h.
```json
{
  "signals_with_entry": 0,
  "completed": 0,
  "open": 0,
  "ev5": null,
  "pf5": null,
  "ev10": null,
  "pf10": null,
  "cumR5": 0.0,
  "tp": 0,
  "sl": 0,
  "time": 0,
  "additive_realized_dd_pct": 0.0,
  "peak_concurrent_long": 0,
  "peak_open_initial_risk_pct": 0.0
}
```

## Current causal state

```json
{
  "clock_time": "2026-09-10 12:00:00",
  "state": "OTHER",
  "tier_a_active": false,
  "st_dir": -1.0,
  "st_age": 1.0,
  "episode_onset": null,
  "next_signal_conditional": null
}
```

## Gates

```json
{
  "closed_m1_overlap_ge250": true,
  "closed_m1_exact_100pct": true,
  "closed_m5_overlap_ge100": true,
  "closed_m5_exact_100pct": true,
  "fresh_n_ge5": false,
  "fresh_ev5_gt0_if_n5": true,
  "fresh_pf5_ge1_10_if_n5": true,
  "fresh_ev10_gt0_if_n5": true,
  "fresh_dd_le4pct_if_n5": true,
  "peak_open_long_risk_le0_50pct": true,
  "no_tuning": true
}
```

## Guardrail

LAB064 remains INVALID under its original all-row parity prereg. LAB065 uses only the separately pre-registered structural closed-bar transport rule. LONG v1 and SHORT v1 are unchanged. No live allocation is authorized; broker-native parity remains required.