# LAB070 — HIGH-VOL FAILED-EARLY DEFENSIVE STOP CAP

Action: at +15m P80_100 + FAILED_EARLY -> cap max loss at -0.75R.

## Comparison

| period       | variant                             |    N |       WR |        EV |      PF |     SumR |   MaxDD_R |     R_DD |   MaxConsecutiveLosses |   positive_periods |   periods_total |   action_count |   total_saved_R |   total_given_up_R |   net_local_delta_R |   original_initial_stop_share |   original_right_tail_share |   immediate_close_share |
|:-------------|:------------------------------------|-----:|---------:|----------:|--------:|---------:|----------:|---------:|-----------------------:|-------------------:|----------------:|---------------:|----------------:|-------------------:|--------------------:|------------------------------:|----------------------------:|------------------------:|
| historical   | CONTROL                             | 5297 | 0.390221 | 0.13222   | 1.22566 | 700.37   |   31.9769 | 21.9024  |                     14 |                  5 |               5 |              0 |         0       |            0       |             0       |                    nan        |                 nan         |             nan         |
| historical   | HIGHVOL_FAILED_EARLY_STOPCAP_-0.75R | 5302 | 0.384949 | 0.127094  | 1.21807 | 673.85   |   34.5083 | 19.5272  |                     14 |                  5 |               5 |            371 |        49.9779  |           56.6409  |            -6.66304 |                      0.541779 |                   0.107817  |               0.0134771 |
| forward_2026 | CONTROL                             |  544 | 0.369485 | 0.0652534 | 1.10549 |  35.4978 |   27.633  |  1.28462 |                     16 |                  4 |               6 |              0 |         0       |            0       |             0       |                    nan        |                 nan         |             nan         |
| forward_2026 | HIGHVOL_FAILED_EARLY_STOPCAP_-0.75R |  544 | 0.371324 | 0.0845004 | 1.13911 |  45.9682 |   27.1639 |  1.69225 |                     16 |                  4 |               6 |             33 |         5.21903 |            1.49235 |             3.72668 |                      0.636364 |                   0.0606061 |               0.030303  |

## Checks

{
  "historical": {
    "R_DD_not_worse": false,
    "SumR_ge_98pct_control": false,
    "PF_ge_control_or_DD_better": false,
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

PASS both periods: **False**