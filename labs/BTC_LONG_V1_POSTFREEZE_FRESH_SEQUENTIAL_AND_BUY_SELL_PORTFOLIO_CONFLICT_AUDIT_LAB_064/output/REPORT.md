# BTC_LONG_V1_POSTFREEZE_FRESH_SEQUENTIAL_AND_BUY_SELL_PORTFOLIO_CONFLICT_AUDIT_LAB_064

**Verdict:** `INVALID_PRICE_TRANSPORT_PARITY_DO_NOT_INTERPRET_FRESH_LONG`

## Methodological status

LONG v1 freeze: 2026-09-10 14:28:51 UTC. True fresh elapsed at run: 0.985 h.
August through 8 September is LOCKED_TRANSFER only and is not eligible for LONG promotion.

## Price transport parity

```json
{
  "m1": {
    "overlap_n": 3240,
    "min_required": 250,
    "exact_rows": 3240,
    "exact_share": 1.0,
    "max_abs_ohlc_diff": 0.0,
    "pass": true
  },
  "m5": {
    "overlap_n": 833,
    "min_required": 100,
    "exact_rows": 832,
    "exact_share": 0.9987995198079231,
    "max_abs_ohlc_diff": 18.0,
    "pass": false
  },
  "pass": false
}
```

## True fresh LONG

```json
{
  "window": "FRESH_POSTFREEZE_LONG",
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
  "additive_dd_pct": 0.0
}
```

## Locked transfer LONG

```json
{
  "window": "LOCKED_TRANSFER_CONFLICT",
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
  "additive_dd_pct": 0.0
}
```

## Canonical SHORT same-calendar

Canonical traded SHORT rows: 4

## Conflict audit

```json
{
  "long_trades": 0,
  "short_trades": 4,
  "direct_overlap_pairs": 0,
  "long_involved_direct": 0,
  "short_involved_direct": 0,
  "long_direct_conflict_rate": 0.0,
  "short_direct_conflict_rate": 0.0,
  "entry_against_open_rows": 0,
  "near_conflict_12h_pairs": 0,
  "total_overlap_h": 0.0,
  "max_single_overlap_h": 0.0
}
```

## Portfolio risk / additive realized accounting

```json
{
  "peak_long_positions": 0,
  "peak_short_positions": 1,
  "peak_total_positions": 1,
  "peak_gross_initial_risk_pct": 0.25,
  "peak_abs_directional_net_initial_risk_pct": 0.25,
  "additive_realized_return_pct_5bps": 0.879013393397122,
  "additive_realized_dd_pct_5bps": 0.09529135520392873
}
```

## Guardrail

No conflict policy was selected from outcomes. No LONG or SHORT rule changed. Fresh combined portfolio closure remains unavailable unless a canonical SHORT clock exists after the LONG freeze. Live allocation remains zero.