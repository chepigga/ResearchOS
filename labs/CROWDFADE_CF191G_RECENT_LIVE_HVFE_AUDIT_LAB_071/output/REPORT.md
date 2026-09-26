# LAB071 — RECENT LIVE CF191g HVFE AUDIT

| broker       | decision_utc        | side   |   entry_price |   exit_price |   actual_R |   vol_percentile_7d |   expansion15_atr |     eff15 |   persist15 | HVFE   |   exit15_shadow_R |   stopcap075_shadow_R | stopcap_mode   |
|:-------------|:--------------------|:-------|--------------:|-------------:|-----------:|--------------------:|------------------:|----------:|------------:|:-------|------------------:|----------------------:|:---------------|
| ICTrader     | 2026-09-25 08:40:00 | SELL   |       84311.4 |      84642.1 |  -1.02175  |            0.47619  |         -0.159312 | -0.170297 |    0.466667 | False  |         -1.02175  |             -1.02175  | not_HVFE       |
| GetLeveraged | 2026-09-25 10:25:00 | BUY    |       84544.2 |      84799.2 |   0.734107 |            0.579861 |          0.713642 |  0.281787 |    0.6      | False  |          0.734107 |              0.734107 | not_HVFE       |
| GetLeveraged | 2026-09-25 11:10:00 | BUY    |       85086.6 |      84727.4 |  -1.01806  |            0.563988 |         -0.639327 | -0.212051 |    0.333333 | False  |         -1.01806  |             -1.01806  | not_HVFE       |
| GetLeveraged | 2026-09-25 12:25:00 | BUY    |       84285.4 |      83839.7 |  -1.04429  |            0.737103 |          0.735569 |  0.424696 |    0.466667 | False  |         -1.04429  |             -1.04429  | not_HVFE       |

## Summary

{
  "N": 4,
  "HVFE_N": 0,
  "actual_losers": 3,
  "HVFE_among_losers": 0,
  "actual_winners": 1,
  "HVFE_among_winners": 0,
  "actual_sum_R": -2.349987700724389,
  "exit15_shadow_sum_R": -2.349987700724389,
  "stopcap075_shadow_sum_R": -2.349987700724389,
  "actual_mean_R": -0.5874969251810972,
  "exit15_shadow_mean_R": -0.5874969251810972,
  "stopcap075_shadow_mean_R": -0.5874969251810972
}

N=4 is a recent forward case study, not statistical proof. BTC only.