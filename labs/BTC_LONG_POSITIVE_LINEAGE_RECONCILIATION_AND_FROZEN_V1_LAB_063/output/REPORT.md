# BTC_LONG_POSITIVE_LINEAGE_RECONCILIATION_AND_FROZEN_V1_LAB_063

**Verdict:** `FROZEN_LONG_V1_CANDIDATE_READY_FOR_FRESH_OOS`

## Reconciliation

| family                           | status                     | reason                                                                                               |
|:---------------------------------|:---------------------------|:-----------------------------------------------------------------------------------------------------|
| RECENT_H4_TWO_BAR_BUY_LAB019_021 | REJECT_LONG_V1             | Strong 2025H2-2026 but negative historical transfer; LAB020 onset and LAB021 mechanism gates failed  |
| V283_TIMING_TIER_A               | REMOVE_AS_MANDATORY_TIMING | U02C4 same-state random null showed Tier-A state carries most edge; v283 timing increment not proven |
| B3_BUY_STATE                     | REJECT_LONG_V1             | U02C5 state-only periodic B3 weak, phase-sensitive and deteriorated in 2026                          |
| TIER_A_STATE_8H                  | SELECT_CORE                | U02C5 8h state-only: N163, EV~+0.689R, PF~2.18, positive 2024/2025/2026 and +4h phase positive       |

## Technical U02C5 baseline parity

```json
{
  "expected_n": 163,
  "actual_n": 163,
  "n_exact": true,
  "published_ev_legacy_approx": 0.689,
  "actual_ev_legacy": 0.6886486190547627,
  "ev_abs_diff": 0.00035138094523723407,
  "published_pf_legacy_approx": 2.18,
  "actual_pf_legacy": 2.1818259473303194,
  "pf_abs_diff": 0.0018259473303192664,
  "technical_parity_acceptable": true
}
```

## Frozen TP1.5 translation summary

| selector                       |   episodes |   trades |   trades_per_week |   ev_legacy |   pf_legacy |   ev_5bps |   pf_5bps |   ev_10bps |   pf_10bps |   cum_r_5bps |   win_rate_5bps |   maxdd_r_signal_order_5bps |   realized_additive_dd_pct_slot_risk |   peak_concurrent_positions |   peak_concurrent_initial_risk_pct |   slot_risk_pct |   tp_n |   sl_n |   time_n | start               | end                 |
|:-------------------------------|-----------:|---------:|------------------:|------------:|------------:|----------:|----------:|-----------:|-----------:|-------------:|----------------:|----------------------------:|-------------------------------------:|----------------------------:|-----------------------------------:|----------------:|-------:|-------:|---------:|:--------------------|:--------------------|
| BTC_LONG_V1_TIER_A_8H_TP15     |         16 |      163 |           1.23374 |    0.274779 |     1.57255 |  0.258982 |   1.53213 |   0.201272 |    1.39253 |      42.2141 |        0.533742 |                     14.3078 |                             1.19232  |                           6 |                           0.5      |       0.0833333 |     82 |     75 |        6 | 2024-01-22 16:00:00 | 2026-08-04 12:00:00 |
| PHASE_PLUS4_DIAGNOSTIC         |         16 |      155 |           1.17318 |    0.253149 |     1.50754 |  0.237016 |   1.46836 |   0.179039 |    1.33596 |      36.7375 |        0.516129 |                     10.1507 |                             0.845893 |                           5 |                           0.416667 |       0.0833333 |     80 |     74 |        1 | 2024-01-22 20:00:00 | 2026-08-04 16:00:00 |
| U02C5_NO_TP_TECHNICAL_BASELINE |         16 |      163 |           1.23374 |    0.688649 |     2.18183 |  0.672851 |   2.13428 |   0.615142 |    1.98    |     109.675  |        0.429448 |                     26.379  |                             2.19502  |                           6 |                           0.5      |       0.0833333 |      0 |     91 |       72 | 2024-01-22 16:00:00 | 2026-08-04 12:00:00 |

## Yearly

| selector                   |   year |   n |       ev5 |     pf5 |    cumR5 |      ev10 |    pf10 |
|:---------------------------|-------:|----:|----------:|--------:|---------:|----------:|--------:|
| BTC_LONG_V1_TIER_A_8H_TP15 |   2024 |  49 | 0.190578  | 1.38509 |  9.33832 | 0.13898   | 1.26794 |
| BTC_LONG_V1_TIER_A_8H_TP15 |   2025 |  69 | 0.371743  | 1.82864 | 25.6503  | 0.304646  | 1.63874 |
| BTC_LONG_V1_TIER_A_8H_TP15 |   2026 |  45 | 0.160566  | 1.29948 |  7.22549 | 0.110596  | 1.19708 |
| PHASE_PLUS4_DIAGNOSTIC     |   2024 |  46 | 0.376373  | 1.85396 | 17.3132  | 0.323965  | 1.70056 |
| PHASE_PLUS4_DIAGNOSTIC     |   2025 |  67 | 0.238946  | 1.46982 | 16.0094  | 0.171922  | 1.31863 |
| PHASE_PLUS4_DIAGNOSTIC     |   2026 |  42 | 0.0813088 | 1.14176 |  3.41497 | 0.0316652 | 1.05282 |

## Gates

```json
{
  "technical_u02c5_baseline_parity": true,
  "primary_n_ge100": true,
  "primary_ev5_gt0": true,
  "primary_pf5_ge1_30": true,
  "primary_ev10_gt0": true,
  "primary_pf10_ge1_10": true,
  "all_2024_2025_2026_positive_ev5_n5": true,
  "realized_additive_dd_slotrisk_le4pct": true,
  "peak_concurrent_le6": true,
  "phase4_ev5_gt0": true,
  "phase4_pf5_ge1_10": true,
  "no_tuning": true
}
```

## Interpretation guardrail

All 2024-2026 results in this LAB are reused historical/replication evidence, not fresh OOS. Passing them can freeze a candidate for future sequential OOS, but cannot authorize live trading. FTMO/broker-native parity is separately required.