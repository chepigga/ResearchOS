# LAB053 — THREE BOT FIXES HISTORICAL REPLAY

BTCUSDT causal stateful replay. Historical 2021–2025 + 2026 Mar–Aug forward shadow.

## Old vs new

| period       | bot    |   old_N |   new_N |   delta_N |       old_EV |      new_EV |     delta_EV |   old_PF |   new_PF |    delta_PF |   old_SumR |   new_SumR |   delta_SumR |   old_DD |   new_DD |   delta_DD |   old_R_DD |   new_R_DD |
|:-------------|:-------|--------:|--------:|----------:|-------------:|------------:|-------------:|---------:|---------:|------------:|-----------:|-----------:|-------------:|---------:|---------:|-----------:|-----------:|-----------:|
| historical   | CF191s |    5402 |    5404 |         2 |  0.000191258 |  0.00285259 |  0.00266133  | 1.00071  | 1.01059  |  0.00987148 |    1.03317 |    15.4154 |   14.3822    | 59.9693  | 53.8932  |  -6.07619  |  0.0172284 |   0.286036 |
| historical   | CF191g |    5297 |    5250 |       -47 |  0.13222     |  0.133953   |  0.00173263  | 1.22566  | 1.22873  |  0.0030747  |  700.37    |   703.252  |    2.88195   | 31.9769  | 34.4161  |   2.43917  | 21.9024    |  20.4338   |
| historical   | CF200  |    1642 |    1642 |         0 |  0.0745431   |  0.0745431  |  0           | 1.15099  | 1.15099  |  0          |  122.4     |   122.4    |    0         | 19.8257  | 19.8257  |   0        |  6.1738    |   6.1738   |
| forward_2026 | CF191s |     550 |     550 |         0 | -0.0329981   | -0.0328323  |  0.000165827 | 0.882335 | 0.884451 |  0.00211611 |  -18.149   |   -18.0578 |    0.0912051 | 42.6533  | 37.7187  |  -4.93462  | -0.4255    |  -0.478749 |
| forward_2026 | CF191g |     544 |     539 |        -5 |  0.0652534   |  0.064075   | -0.00117836  | 1.10549  | 1.10329  | -0.00220336 |   35.4978  |    34.5364 |   -0.961402  | 27.633   | 27.9629  |   0.329972 |  1.28462   |   1.23508  |
| forward_2026 | CF200  |     176 |     176 |         0 |  0.0972457   |  0.0972457  |  0           | 1.198    | 1.198    |  0          |   17.1152  |    17.1152 |    0         |  8.34399 |  8.34399 |   0        |  2.05121   |   2.05121  |

## Full metrics

| period       | bot    | variant                      |    N |       WR |           EV |       PF |      SumR |   MaxDD_R |       R_DD |   MaxConsecutiveLosses |   positive_periods |   periods_total | skip_counts                 |
|:-------------|:-------|:-----------------------------|-----:|---------:|-------------:|---------:|----------:|----------:|-----------:|-----------------------:|-------------------:|----------------:|:----------------------------|
| historical   | CF191s | OLD_STRICT                   | 5402 | 0.711773 |  0.000191258 | 1.00071  |   1.03317 |  59.9693  |  0.0172284 |                      6 |                  3 |               5 | 621|4232|0|0|0|18           |
| historical   | CF191s | NEW_v196_REGIME_GUARD        | 5404 | 0.713546 |  0.00285259  | 1.01059  |  15.4154  |  53.8932  |  0.286036  |                      6 |                  4 |               5 | 635|4367|39|130|38|0        |
| historical   | CF191g | OLD_v191g_POSITIVE_SKEW      | 5297 | 0.390221 |  0.13222     | 1.22566  | 700.37    |  31.9769  | 21.9024    |                     14 |                  5 |               5 | 0|0|1031|5062|165|424|8     |
| historical   | CF191g | NEW_v195_EPISODE_GUARD       | 5250 | 0.391619 |  0.133953    | 1.22873  | 703.252   |  34.4161  | 20.4338    |                     15 |                  5 |               5 | 16549|0|1005|4963|172|449|7 |
| forward_2026 | CF191s | OLD_STRICT                   |  550 | 0.710909 | -0.0329981   | 0.882335 | -18.149   |  42.6533  | -0.4255    |                      6 |                  2 |               6 | 40|321|0|0|0|0              |
| forward_2026 | CF191s | NEW_v196_REGIME_GUARD        |  550 | 0.707273 | -0.0328323   | 0.884451 | -18.0578  |  37.7187  | -0.478749  |                      5 |                  3 |               6 | 40|340|0|8|23|0             |
| forward_2026 | CF191g | OLD_v191g_POSITIVE_SKEW      |  544 | 0.369485 |  0.0652534   | 1.10549  |  35.4978  |  27.633   |  1.28462   |                     16 |                  4 |               6 | 0|0|104|533|11|54|1         |
| forward_2026 | CF191g | NEW_v195_EPISODE_GUARD       |  539 | 0.367347 |  0.064075    | 1.10329  |  34.5364  |  27.9629  |  1.23508   |                     11 |                  3 |               6 | 2343|0|112|541|10|55|1      |
| historical   | CF200  | OLD_V200_FROZEN_CORE         | 1642 | 0.433618 |  0.0745431   | 1.15099  | 122.4     |  19.8257  |  6.1738    |                     13 |                  5 |               5 | nan                         |
| historical   | CF200  | NEW_v204_WINNER_PRESERVATION | 1642 | 0.433618 |  0.0745431   | 1.15099  | 122.4     |  19.8257  |  6.1738    |                     13 |                  5 |               5 | nan                         |
| forward_2026 | CF200  | OLD_V200_FROZEN_CORE         |  176 | 0.420455 |  0.0972457   | 1.198    |  17.1152  |   8.34399 |  2.05121   |                      9 |                  4 |               6 | nan                         |
| forward_2026 | CF200  | NEW_v204_WINNER_PRESERVATION |  176 | 0.420455 |  0.0972457   | 1.198    |  17.1152  |   8.34399 |  2.05121   |                      9 |                  4 |               6 | nan                         |

## Notes
- CF191s v1.96 is a full stateful replay of old STRICT vs same-side + |confirm Z|>=0.75 + response>=0.50, with ExitZ0.75 retained.
- CF191g uses canonical completed M5 confirmation and positive-skew management (BE arm3.0/lock2.25 ATR, trail arm3.5/gap0.5 ATR); new variant adds max two entries per crowd episode, reset at |Z|<0.50 or sign flip.
- CF200 v2.04 does not alter the valid frozen Z2.05 core geometry. Historical result must be exactly identical; its purpose is config enforcement and exit-ownership audit.
- 2026 Mar-Aug is reused forward-shadow/stress, not pristine OOS.
- Broker CFD spread/slippage parity is not represented; flat 0.5bps research cost proxy is used.
- BTCUSDT only: ETH/SOL transfer is not established by this replay.