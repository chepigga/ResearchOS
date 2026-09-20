# LAB035B — SIGN_FLIP_STABILITY_AND_PAIRED_EVENT_AUDIT

Frozen geometry: Z2.05 -> M15 confirm .25 ATR -> retrace .60 ATR -> TTL20 -> SL4.5 -> TP10 -> H24.

## Headline
- historical PRESERVE: N=1642 EV=+0.0745 PF=1.151 Sum=+122.40R DD=19.83 R/DD=6.174
- historical CANCEL_SIGN_FLIP: N=1617 EV=+0.0845 PF=1.173 Sum=+136.62R DD=18.81 R/DD=7.261
- forward PRESERVE: N=176 EV=+0.0972 PF=1.198 Sum=+17.12R DD=8.34 R/DD=2.051
- forward CANCEL_SIGN_FLIP: N=172 EV=+0.1321 PF=1.276 Sum=+22.72R DD=8.01 R/DD=2.836

## Paired sequence decomposition
{
  "historical": {
    "baseline_only_removed": {
      "N": 68,
      "SumR": -10.909724787030084,
      "EV": -0.16043712922103065,
      "direct_sign_flip_N": 41,
      "direct_sign_flip_SumR": -15.527747553044877
    },
    "candidate_only_added": {
      "N": 43,
      "SumR": 3.3063279437044235,
      "EV": 0.07689134752800984
    },
    "common": {
      "N": 1574,
      "baseline_SumR": 133.30943536722947,
      "candidate_SumR": 133.30943536722947,
      "delta_R": 0.0,
      "identical_entry_N": 1574
    },
    "reconciliation": {
      "baseline_total_R": 122.39971058019937,
      "candidate_total_R": 136.6157633109339,
      "delta_R": 14.216052730734507,
      "decomp_delta_R": 14.216052730734507
    }
  },
  "forward": {
    "baseline_only_removed": {
      "N": 9,
      "SumR": 2.69738417285301,
      "EV": 0.2997093525392234,
      "direct_sign_flip_N": 5,
      "direct_sign_flip_SumR": -1.834711162879635
    },
    "candidate_only_added": {
      "N": 5,
      "SumR": 8.306145971855727,
      "EV": 1.6612291943711455
    },
    "common": {
      "N": 167,
      "baseline_SumR": 14.417852607425374,
      "candidate_SumR": 14.417852607425374,
      "delta_R": 0.0,
      "identical_entry_N": 167
    },
    "reconciliation": {
      "baseline_total_R": 17.11523678027838,
      "candidate_total_R": 22.723998579281098,
      "delta_R": 5.608761799002716,
      "decomp_delta_R": 5.608761799002718
    }
  }
}

## Preserve-sequence direct sign-flip event audit
{
  "historical": {
    "confirmed_flip_events": 126,
    "filled_flip_events": 61,
    "fill_rate": 0.48412698412698413,
    "filled_metrics": {
      "N": 61,
      "WR": 0.13114754098360656,
      "EV": -0.6938794152412749,
      "SumR": -42.32664432971777,
      "PF": 0.1566452813743963,
      "MaxDD_R": 42.32664432971778,
      "R_DD": -0.9999999999999998,
      "MaxConsecutiveLosses": 12
    },
    "confirmed_by_strength": {
      "<0.5": 49,
      "0.5-1.0": 17,
      "1.0-2.05": 37,
      ">=2.05": 23
    },
    "filled_by_strength": {
      "<0.5": {
        "N": 23,
        "SumR": -22.392273085703764,
        "EV": -0.9735770906827723,
        "WR": 0.0
      },
      "0.5-1.0": {
        "N": 11,
        "SumR": -11.051408235800636,
        "EV": -1.004673475981876,
        "WR": 0.0
      },
      "1.0-2.05": {
        "N": 14,
        "SumR": -6.091657471003293,
        "EV": -0.4351183907859495,
        "WR": 0.21428571428571427
      },
      ">=2.05": {
        "N": 13,
        "SumR": -2.791305537210065,
        "EV": -0.21471581055462036,
        "WR": 0.38461538461538464
      }
    },
    "filled_by_confirm_bar": {
      "1": {
        "N": 18,
        "SumR": -14.796866017467478,
        "EV": -0.8220481120815265,
        "WR": 0.05555555555555555
      },
      "2": {
        "N": 20,
        "SumR": -14.451700870362455,
        "EV": -0.7225850435181227,
        "WR": 0.15
      },
      "3": {
        "N": 8,
        "SumR": -6.637085921670631,
        "EV": -0.8296357402088289,
        "WR": 0.125
      },
      "4": {
        "N": 15,
        "SumR": -6.4409915202171995,
        "EV": -0.4293994346811466,
        "WR": 0.2
      }
    },
    "filled_by_direction": {
      "BUY": {
        "N": 42,
        "SumR": -23.255402720151487,
        "EV": -0.5537000647655116,
        "WR": 0.19047619047619047
      },
      "SELL": {
        "N": 19,
        "SumR": -19.07124160956628,
        "EV": -1.0037495583982252,
        "WR": 0.0
      }
    }
  },
  "forward": {
    "confirmed_flip_events": 9,
    "filled_flip_events": 4,
    "fill_rate": 0.4444444444444444,
    "filled_metrics": {
      "N": 4,
      "WR": 0.25,
      "EV": -0.20117956572160756,
      "SumR": -0.8047182628864302,
      "PF": 0.7330933052108726,
      "MaxDD_R": 3.01497968614915,
      "R_DD": -0.2669066947891274,
      "MaxConsecutiveLosses": 3
    },
    "confirmed_by_strength": {
      "<0.5": 4,
      "0.5-1.0": 1,
      "1.0-2.05": 2,
      ">=2.05": 2
    },
    "filled_by_strength": {
      "<0.5": {
        "N": 3,
        "SumR": 0.19944959760683068,
        "EV": 0.0664831992022769,
        "WR": 0.3333333333333333
      },
      ">=2.05": {
        "N": 1,
        "SumR": -1.0041678604932607,
        "EV": -1.0041678604932607,
        "WR": 0.0
      }
    },
    "filled_by_confirm_bar": {
      "1": {
        "N": 1,
        "SumR": -1.0055274403479089,
        "EV": -1.0055274403479089,
        "WR": 0.0
      },
      "3": {
        "N": 1,
        "SumR": -1.0041678604932607,
        "EV": -1.0041678604932607,
        "WR": 0.0
      },
      "4": {
        "N": 2,
        "SumR": 1.2049770379547393,
        "EV": 0.6024885189773697,
        "WR": 0.5
      }
    },
    "filled_by_direction": {
      "BUY": {
        "N": 4,
        "SumR": -0.8047182628864302,
        "EV": -0.20117956572160756,
        "WR": 0.25
      }
    }
  }
}

## Stability
### Historical year delta
- 2021: +2.969R (removed +2.761, added +0.208, common +0.000)
- 2022: -3.795R (removed +1.907, added -5.702, common +0.000)
- 2023: +8.908R (removed +5.335, added +3.573, common +0.000)
- 2024: +4.328R (removed +1.318, added +3.010, common +0.000)
- 2025: +1.806R (removed -0.412, added +2.218, common +0.000)

### 2026 forward month delta
- 2026-03: +1.735R
- 2026-04: +0.000R
- 2026-05: +1.200R
- 2026-06: +0.000R
- 2026-07: +1.644R
- 2026-08: +1.030R

### Leave-one-year-out historical
- exclude 2021: remaining delta +11.247R
- exclude 2022: remaining delta +18.011R
- exclude 2023: remaining delta +5.308R
- exclude 2024: remaining delta +9.888R
- exclude 2025: remaining delta +12.410R

### Concentration / bootstrap
- historical after removing top-3 positive weeks: +5.433R
- historical top-3 share of positive contribution: 28.2%
- historical bootstrap: {"reps": 20000, "block_weeks": 4, "observed_sumR": 14.21605273073451, "ci95_sumR": [-2.7167616308745255, 32.647364926078495], "p_bootstrap_sumR_gt_0": 0.94895, "median_sumR": 14.904786896578443}
- forward bootstrap: {"reps": 20000, "block_weeks": 4, "observed_sumR": 5.608761799002718, "ci95_sumR": [2.673602187275379, 9.916497779911559], "p_bootstrap_sumR_gt_0": 0.9993, "median_sumR": 6.314046330892616}

## Promotion gate
- PASS: **True**
{
  "historical_delta_positive": true,
  "historical_years_nonnegative_4of5": true,
  "leave_one_year_out_all_positive": true,
  "forward_delta_positive": true,
  "forward_months_nonnegative_4of6": true,
  "historical_bootstrap_ge_080": true,
  "forward_bootstrap_ge_070": true,
  "hist_after_top3_positive_weeks_positive": true
}

## Limitations
- 2021-2025 is discovery/in-sample; 2026 Mar-Aug is reused forward-shadow, not pristine OOS.
- This audit is BTC only; ETH/SOL transfer is not established.
- Bootstrap is a descriptive stability diagnostic, not an independent significance test.
- Stateful cancellation changes future reachability; paired decomposition is therefore required and direct removed-trade PnL alone is insufficient.