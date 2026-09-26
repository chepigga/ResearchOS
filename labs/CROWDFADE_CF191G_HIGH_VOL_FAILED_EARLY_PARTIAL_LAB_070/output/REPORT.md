# LAB070 — HIGH-VOL FAILED-EARLY 50% REDUCTION + RUNNER

## Comparison

| period       | variant             |    N |       WR |        EV |      PF |     SumR |   MaxDD_R |     R_DD |   MaxConsecutiveLosses |   positive_periods |   periods_total |   actions |   total_saved_R |   total_given_up_R |   net_delta_R |   acted_control_right_tail_share |   acted_modified_mean_R_on_control_right_tail |
|:-------------|:--------------------|-----:|---------:|----------:|--------:|---------:|----------:|---------:|-----------------------:|-------------------:|----------------:|----------:|----------------:|-------------------:|--------------:|---------------------------------:|----------------------------------------------:|
| historical   | CONTROL             | 5297 | 0.390221 | 0.13222   | 1.22566 | 700.37   |   31.9769 | 21.9024  |                     14 |                  5 |               5 |         0 |         0       |            0       |       0       |                      nan         |                                     nan       |
| historical   | REDUCE_50_RUNNER_50 | 5297 | 0.387389 | 0.12982   | 1.22715 | 687.655  |   30.8498 | 22.2904  |                     14 |                  5 |               5 |       383 |        78.6142  |           91.33    |     -12.7158  |                        0.101828  |                                       1.13892 |
| forward_2026 | CONTROL             |  544 | 0.369485 | 0.0652534 | 1.10549 |  35.4978 |   27.633  |  1.28462 |                     16 |                  4 |               6 |         0 |         0       |            0       |       0       |                      nan         |                                     nan       |
| forward_2026 | REDUCE_50_RUNNER_50 |  544 | 0.369485 | 0.0674247 | 1.11122 |  36.679  |   27.3972 |  1.33879 |                     16 |                  4 |               6 |        33 |         7.15015 |            5.96897 |       1.18118 |                        0.0606061 |                                       1.23406 |

## Checks

{
  "historical": {
    "R_DD_not_worse": true,
    "SumR_ge_98pct_control": true,
    "PF_ge_control_or_DD_better": true,
    "max_consecutive_losses_not_worse": true,
    "positive_periods_not_worse": true,
    "event_count_meaningful": true
  },
  "forward_2026": {
    "R_DD_not_worse": true,
    "SumR_ge_98pct_control": true,
    "PF_ge_control_or_DD_better": true,
    "max_consecutive_losses_not_worse": true,
    "positive_periods_not_worse": true,
    "event_count_meaningful": true
  }
}

PASS both periods: **True**

## Limitations
- Partial reduction does not free occupancy; entry reachability remains identical to control.
- Uses frozen LAB068 event table and exact same 15m/P80/FAILED_EARLY state.
- 50% fraction is preregistered and not tuned.
- BTCUSDT only; 2026 Mar-Aug reused shadow/stress.