# LAB041B — CORE_FAST_OVERLAP_CONFLICT_AND_2025_FAILURE_AUDIT

G1 is frozen. No new alpha filter is selected in this audit.

## Entry/lifetime overlap — ALLOW_ALL
{
  "historical": {
    "entry_overlap": {
      "CORE_OPPOSITE": {
        "N": 126,
        "WR": 0.4126984126984127,
        "EV": 0.0545018370857013,
        "SumR": 6.867231472798363,
        "PF": 1.1044188797013808,
        "MaxDD_R": 12.694822961807368,
        "R_DD": 0.5409473998541428,
        "MaxConsecutiveLosses": 6
      },
      "CORE_SAME": {
        "N": 374,
        "WR": 0.4037433155080214,
        "EV": -0.00021704788795866403,
        "SumR": -0.08117591009654035,
        "PF": 0.9995470240996523,
        "MaxDD_R": 26.194562340923614,
        "R_DD": -0.0030989603506266523,
        "MaxConsecutiveLosses": 7
      },
      "NONE": {
        "N": 506,
        "WR": 0.4051383399209486,
        "EV": -0.009616454990365363,
        "SumR": -4.865926225124873,
        "PF": 0.980942885546844,
        "MaxDD_R": 35.338636407524206,
        "R_DD": -0.13769422704971246,
        "MaxConsecutiveLosses": 10
      }
    },
    "lifetime_any_overlap": {
      "False": {
        "N": 181,
        "WR": 0.24861878453038674,
        "EV": -0.33627499094632,
        "SumR": -60.86577336128393,
        "PF": 0.5314518665896854,
        "MaxDD_R": 60.86577336128393,
        "R_DD": -1.0,
        "MaxConsecutiveLosses": 9
      },
      "True": {
        "N": 825,
        "WR": 0.44,
        "EV": 0.07610412448346772,
        "SumR": 62.78590269886087,
        "PF": 1.169507047499396,
        "MaxDD_R": 27.76647751051673,
        "R_DD": 2.2612123801112443,
        "MaxConsecutiveLosses": 10
      }
    },
    "counts": {
      "fast_total": 1006,
      "entry_none": 506,
      "entry_same": 374,
      "entry_opposite": 126,
      "lifetime_any": 825,
      "later_core_same": 324,
      "later_core_opposite": 203
    }
  },
  "forward": {
    "entry_overlap": {
      "CORE_OPPOSITE": {
        "N": 6,
        "WR": 0.6666666666666666,
        "EV": 0.6746483237317845,
        "SumR": 4.047889942390707,
        "PF": 3.773740057291018,
        "MaxDD_R": 1.459361677295778,
        "R_DD": 2.773740057291018,
        "MaxConsecutiveLosses": 2
      },
      "CORE_SAME": {
        "N": 42,
        "WR": 0.40476190476190477,
        "EV": -0.05686972614765507,
        "SumR": -2.388528498201513,
        "PF": 0.8895195993253897,
        "MaxDD_R": 8.303208273881577,
        "R_DD": -0.2876633247554232,
        "MaxConsecutiveLosses": 5
      },
      "NONE": {
        "N": 49,
        "WR": 0.5510204081632653,
        "EV": 0.276031572532646,
        "SumR": 13.525547054099652,
        "PF": 1.7326689631143444,
        "MaxDD_R": 3.6479825837145876,
        "R_DD": 3.7076786261208396,
        "MaxConsecutiveLosses": 4
      }
    },
    "lifetime_any_overlap": {
      "False": {
        "N": 16,
        "WR": 0.5,
        "EV": 0.31427956900690135,
        "SumR": 5.028473104110422,
        "PF": 1.6894786881084265,
        "MaxDD_R": 2.8853556088780583,
        "R_DD": 1.7427567987246095,
        "MaxConsecutiveLosses": 3
      },
      "True": {
        "N": 81,
        "WR": 0.49382716049382713,
        "EV": 0.1253880912861534,
        "SumR": 10.156435394178427,
        "PF": 1.296569961087277,
        "MaxDD_R": 6.758208294081506,
        "R_DD": 1.5028295891786756,
        "MaxConsecutiveLosses": 5
      }
    },
    "counts": {
      "fast_total": 97,
      "entry_none": 49,
      "entry_same": 42,
      "entry_opposite": 6,
      "lifetime_any": 81,
      "later_core_same": 37,
      "later_core_opposite": 15
    }
  }
}

## FAST conflict policies
- ALLOW_ALL: hist N=1006 (16.8/mo) EV=+0.0019 PF=1.004 Sum=+1.92R DD=43.98 R/DD=0.044 | 2026 N=97 (16.2/mo) EV=+0.1565 PF=1.366 Sum=+15.18R DD=7.26 R/DD=2.090
- BLOCK_ANY_CORE_OPEN: hist N=650 (10.8/mo) EV=-0.0130 PF=0.974 Sum=-8.45R DD=36.46 R/DD=-0.232 | 2026 N=64 (10.7/mo) EV=+0.0151 PF=1.030 Sum=+0.97R DD=7.97 R/DD=0.121
- BLOCK_OPPOSITE_CORE_OPEN: hist N=938 (15.6/mo) EV=-0.0126 PF=0.975 Sum=-11.83R DD=49.16 R/DD=-0.241 | 2026 N=94 (15.7/mo) EV=+0.1124 PF=1.251 Sum=+10.56R DD=6.35 R/DD=1.663
- BLOCK_SAME_SIDE_CORE_OPEN: hist N=786 (13.1/mo) EV=-0.0085 PF=0.984 Sum=-6.68R DD=44.99 R/DD=-0.148 | 2026 N=76 (12.7/mo) EV=-0.0004 PF=0.999 Sum=-0.03R DD=6.53 R/DD=-0.005

## Portfolio @ 0.25x FAST
- ALLOW_ALL: hist N=2623 (43.7/mo) EV=+0.0523 PF=1.150 Sum=+137.10R DD=20.96 R/DD=6.540 maxRisk=1.25u | 2026 N=269 (44.8/mo) EV=+0.0986 PF=1.286 Sum=+26.52R DD=7.95 R/DD=3.337 maxRisk=1.25u
- BLOCK_ANY_CORE_OPEN: hist N=2267 (37.8/mo) EV=+0.0593 PF=1.154 Sum=+134.50R DD=19.93 R/DD=6.749 maxRisk=1.25u | 2026 N=236 (39.3/mo) EV=+0.0973 PF=1.254 Sum=+22.97R DD=7.85 R/DD=2.927 maxRisk=1.25u
- BLOCK_OPPOSITE_CORE_OPEN: hist N=2555 (42.6/mo) EV=+0.0523 PF=1.147 Sum=+133.66R DD=20.34 R/DD=6.573 maxRisk=1.25u | 2026 N=266 (44.3/mo) EV=+0.0954 PF=1.273 Sum=+25.36R DD=7.95 R/DD=3.191 maxRisk=1.25u
- BLOCK_SAME_SIDE_CORE_OPEN: hist N=2403 (40.0/mo) EV=+0.0562 PF=1.151 Sum=+134.95R DD=21.46 R/DD=6.287 maxRisk=1.25u | 2026 N=248 (41.3/mo) EV=+0.0916 PF=1.247 Sum=+22.72R DD=8.35 R/DD=2.720 maxRisk=1.25u

## Portfolio @ 0.40x FAST
- ALLOW_ALL: hist N=2623 (43.7/mo) EV=+0.0524 PF=1.139 Sum=+137.38R DD=22.25 R/DD=6.174 maxRisk=1.40u | 2026 N=269 (44.8/mo) EV=+0.1071 PF=1.291 Sum=+28.80R DD=7.91 R/DD=3.642 maxRisk=1.40u
- BLOCK_ANY_CORE_OPEN: hist N=2267 (37.8/mo) EV=+0.0588 PF=1.144 Sum=+133.23R DD=21.23 R/DD=6.275 maxRisk=1.40u | 2026 N=236 (39.3/mo) EV=+0.0979 PF=1.243 Sum=+23.11R DD=7.75 R/DD=2.983 maxRisk=1.40u
- BLOCK_OPPOSITE_CORE_OPEN: hist N=2555 (42.6/mo) EV=+0.0516 PF=1.135 Sum=+131.88R DD=21.59 R/DD=6.109 maxRisk=1.40u | 2026 N=266 (44.3/mo) EV=+0.1013 PF=1.272 Sum=+26.95R DD=7.91 R/DD=3.408 maxRisk=1.40u
- BLOCK_SAME_SIDE_CORE_OPEN: hist N=2403 (40.0/mo) EV=+0.0557 PF=1.140 Sum=+133.94R DD=23.89 R/DD=5.607 maxRisk=1.40u | 2026 N=248 (41.3/mo) EV=+0.0916 PF=1.232 Sum=+22.71R DD=8.55 R/DD=2.656 maxRisk=1.40u

## 2025 failure audit
{
  "overall": {
    "N": 215,
    "WR": 0.35348837209302325,
    "EV": -0.13228160453348994,
    "SumR": -28.440544974700337,
    "PF": 0.751379336290068,
    "MaxDD_R": 43.98470845259125,
    "R_DD": -0.6466007386488618,
    "MaxConsecutiveLosses": 9
  },
  "month": {
    "2025-01": {
      "N": 21,
      "WR": 0.47619047619047616,
      "EV": 0.10751584027124463,
      "SumR": 2.257832645696137,
      "PF": 1.2732624278558216,
      "MaxDD_R": 2.470161568093736,
      "R_DD": 0.9140424961912686,
      "MaxConsecutiveLosses": 3
    },
    "2025-02": {
      "N": 15,
      "WR": 0.4666666666666667,
      "EV": 0.1322223934279057,
      "SumR": 1.9833359014185854,
      "PF": 1.3415659606172374,
      "MaxDD_R": 2.898289259383293,
      "R_DD": 0.6843126147597172,
      "MaxConsecutiveLosses": 4
    },
    "2025-03": {
      "N": 20,
      "WR": 0.5,
      "EV": 0.3505699555485529,
      "SumR": 7.011399110971058,
      "PF": 2.018729081904736,
      "MaxDD_R": 2.3244919228981873,
      "R_DD": 3.016314680168565,
      "MaxConsecutiveLosses": 4
    },
    "2025-04": {
      "N": 17,
      "WR": 0.23529411764705882,
      "EV": -0.36790019376433114,
      "SumR": -6.25430329399363,
      "PF": 0.3851662543154153,
      "MaxDD_R": 8.824988516438426,
      "R_DD": -0.7087038450354529,
      "MaxConsecutiveLosses": 6
    },
    "2025-05": {
      "N": 18,
      "WR": 0.4444444444444444,
      "EV": 0.1307873684373812,
      "SumR": 2.3541726318728617,
      "PF": 1.4270636726311983,
      "MaxDD_R": 3.3286620048772733,
      "R_DD": 0.7072429187533744,
      "MaxConsecutiveLosses": 5
    },
    "2025-06": {
      "N": 14,
      "WR": 0.5714285714285714,
      "EV": 0.3647670759996153,
      "SumR": 5.106739063994614,
      "PF": 1.847076526558632,
      "MaxDD_R": 4.017755923642162,
      "R_DD": 1.2710426320186397,
      "MaxConsecutiveLosses": 4
    },
    "2025-07": {
      "N": 20,
      "WR": 0.15,
      "EV": -0.6602277360648491,
      "SumR": -13.204554721296981,
      "PF": 0.10620183815430877,
      "MaxDD_R": 13.204554721296981,
      "R_DD": -1.0,
      "MaxConsecutiveLosses": 8
    },
    "2025-08": {
      "N": 13,
      "WR": 0.3076923076923077,
      "EV": -0.21450410452835114,
      "SumR": -2.788553358868565,
      "PF": 0.662099729104238,
      "MaxDD_R": 4.4238265063275595,
      "R_DD": -0.630348716180437,
      "MaxConsecutiveLosses": 3
    },
    "2025-09": {
      "N": 19,
      "WR": 0.3157894736842105,
      "EV": -0.22595615240685613,
      "SumR": -4.293166895730266,
      "PF": 0.671990094161995,
      "MaxDD_R": 9.916338098383754,
      "R_DD": -0.4329387373782668,
      "MaxConsecutiveLosses": 7
    },
    "2025-10": {
      "N": 18,
      "WR": 0.3333333333333333,
      "EV": -0.2079526438179551,
      "SumR": -3.743147588723192,
      "PF": 0.6107772152291201,
      "MaxDD_R": 5.280423704643432,
      "R_DD": -0.7088725825981711,
      "MaxConsecutiveLosses": 4
    },
    "2025-11": {
      "N": 17,
      "WR": 0.29411764705882354,
      "EV": -0.43086806158414315,
      "SumR": -7.324757046930434,
      "PF": 0.3693723637721054,
      "MaxDD_R": 10.135795396771963,
      "R_DD": -0.722662283540492,
      "MaxConsecutiveLosses": 8
    },
    "2025-12": {
      "N": 23,
      "WR": 0.21739130434782608,
      "EV": -0.4150235401352401,
      "SumR": -9.545541423110523,
      "PF": 0.33626679809866783,
      "MaxDD_R": 12.630528841041823,
      "R_DD": -0.7557515242032544,
      "MaxConsecutiveLosses": 9
    }
  },
  "direction": {
    "BUY": {
      "N": 108,
      "WR": 0.37037037037037035,
      "EV": -0.12437347380245602,
      "SumR": -13.43233517066525,
      "PF": 0.7714365602244021,
      "MaxDD_R": 21.837747889367115,
      "R_DD": -0.6150970896227584,
      "MaxConsecutiveLosses": 6
    },
    "SELL": {
      "N": 107,
      "WR": 0.3364485981308411,
      "EV": -0.14026364302836528,
      "SumR": -15.008209804035085,
      "PF": 0.7301885504210645,
      "MaxDD_R": 24.25338509773367,
      "R_DD": -0.6188088690942161,
      "MaxConsecutiveLosses": 9
    }
  },
  "branch": {
    "MID_RESPONSE_0.50_1.00": {
      "N": 80,
      "WR": 0.325,
      "EV": -0.2162393584832288,
      "SumR": -17.299148678658305,
      "PF": 0.6007524605313475,
      "MaxDD_R": 18.55729317211916,
      "R_DD": -0.9322021546035003,
      "MaxConsecutiveLosses": 6
    },
    "STRONG_RESPONSE_GE_2.50": {
      "N": 135,
      "WR": 0.37037037037037035,
      "EV": -0.08252886145216319,
      "SumR": -11.14139629604203,
      "PF": 0.8432201300831802,
      "MaxDD_R": 28.945345250474993,
      "R_DD": -0.3849115013012049,
      "MaxConsecutiveLosses": 9
    }
  },
  "align_tf": {
    "H1_ALIGN": {
      "N": 167,
      "WR": 0.3772455089820359,
      "EV": -0.10949846437751129,
      "SumR": -18.286243551044386,
      "PF": 0.7866854940976207,
      "MaxDD_R": 32.07170183215973,
      "R_DD": -0.5701675466659506,
      "MaxConsecutiveLosses": 7
    },
    "H4_ALIGN": {
      "N": 48,
      "WR": 0.2708333333333333,
      "EV": -0.2115479463261656,
      "SumR": -10.15430142365595,
      "PF": 0.6458089536489239,
      "MaxDD_R": 13.685977281976271,
      "R_DD": -0.741949311652639,
      "MaxConsecutiveLosses": 7
    }
  },
  "entry_overlap": {
    "CORE_OPPOSITE": {
      "N": 30,
      "WR": 0.3,
      "EV": -0.06722446653128153,
      "SumR": -2.016733995938446,
      "PF": 0.8760085401339784,
      "MaxDD_R": 5.513453801203708,
      "R_DD": -0.3657841470437548,
      "MaxConsecutiveLosses": 6
    },
    "CORE_SAME": {
      "N": 87,
      "WR": 0.367816091954023,
      "EV": -0.09195093467125515,
      "SumR": -7.999731316399198,
      "PF": 0.8133752167467541,
      "MaxDD_R": 16.094060497117216,
      "R_DD": -0.49706109392543407,
      "MaxConsecutiveLosses": 6
    },
    "NONE": {
      "N": 98,
      "WR": 0.35714285714285715,
      "EV": -0.18800081288125187,
      "SumR": -18.424079662362683,
      "PF": 0.6666103475588744,
      "MaxDD_R": 28.650813336325243,
      "R_DD": -0.6430560782371757,
      "MaxConsecutiveLosses": 9
    }
  },
  "lifetime_overlap": {
    "False": {
      "N": 40,
      "WR": 0.175,
      "EV": -0.5314106986353966,
      "SumR": -21.256427945415865,
      "PF": 0.3053595896991458,
      "MaxDD_R": 21.555660367065542,
      "R_DD": -0.9861181510306746,
      "MaxConsecutiveLosses": 9
    },
    "True": {
      "N": 175,
      "WR": 0.3942857142857143,
      "EV": -0.04105209731019698,
      "SumR": -7.184117029284472,
      "PF": 0.9142632176140394,
      "MaxDD_R": 27.766477510516673,
      "R_DD": -0.2587334683185311,
      "MaxConsecutiveLosses": 8
    }
  },
  "z_band": {
    "1.00-1.25": {
      "N": 55,
      "WR": 0.4,
      "EV": 0.021657131858291972,
      "SumR": 1.1911422522060584,
      "PF": 1.0416702388279448,
      "MaxDD_R": 8.456572855459873,
      "R_DD": 0.14085401646330206,
      "MaxConsecutiveLosses": 6
    },
    "1.25-1.50": {
      "N": 37,
      "WR": 0.43243243243243246,
      "EV": 0.08418106382240083,
      "SumR": 3.1146993614288307,
      "PF": 1.1805073007718294,
      "MaxDD_R": 12.966293966716012,
      "R_DD": 0.240215081458445,
      "MaxConsecutiveLosses": 9
    },
    "1.50-1.75": {
      "N": 44,
      "WR": 0.29545454545454547,
      "EV": -0.24185101726578628,
      "SumR": -10.641444759694597,
      "PF": 0.58937543032869,
      "MaxDD_R": 12.860248437044826,
      "R_DD": -0.8274680548970724,
      "MaxConsecutiveLosses": 9
    },
    "1.75-2.05": {
      "N": 79,
      "WR": 0.31645569620253167,
      "EV": -0.2798093902359573,
      "SumR": -22.104941828640627,
      "PF": 0.48156520956070215,
      "MaxDD_R": 24.319190264549537,
      "R_DD": -0.9089505690024288,
      "MaxConsecutiveLosses": 7
    }
  },
  "confirm_speed": {
    "<=15": {
      "N": 154,
      "WR": 0.36363636363636365,
      "EV": -0.12863633729549132,
      "SumR": -19.809995943505662,
      "PF": 0.7682325497881891,
      "MaxDD_R": 37.67133701428802,
      "R_DD": -0.525863893176717,
      "MaxConsecutiveLosses": 11
    },
    "15-30": {
      "N": 25,
      "WR": 0.32,
      "EV": -0.07930204673669518,
      "SumR": -1.9825511684173793,
      "PF": 0.8165965796869317,
      "MaxDD_R": 4.0033090548309485,
      "R_DD": -0.4952281078636579,
      "MaxConsecutiveLosses": 6
    },
    "30-60": {
      "N": 21,
      "WR": 0.3333333333333333,
      "EV": -0.2349366342110869,
      "SumR": -4.933669318432825,
      "PF": 0.5829797098034972,
      "MaxDD_R": 6.323145196354745,
      "R_DD": -0.7802555793400182,
      "MaxConsecutiveLosses": 4
    },
    "60-120": {
      "N": 13,
      "WR": 0.38461538461538464,
      "EV": -0.02018976705490015,
      "SumR": -0.262466971713702,
      "PF": 0.9456289279300848,
      "MaxDD_R": 3.4242958404915047,
      "R_DD": -0.07664845093408428,
      "MaxConsecutiveLosses": 4
    },
    "120-180": {
      "N": 2,
      "WR": 0.0,
      "EV": -0.7259307863153805,
      "SumR": -1.451861572630761,
      "PF": 0.0,
      "MaxDD_R": 1.451861572630761,
      "R_DD": -1.0,
      "MaxConsecutiveLosses": 2
    }
  }
}

## Stricter policy promotion checks
{
  "BLOCK_ANY_CORE_OPEN_RISK0.25": {
    "checks": {
      "historical_sum_not_below_allow025": false,
      "historical_rdd_not_below_allow025": true,
      "forward_sum_not_below_allow025": false,
      "forward_rdd_not_below_allow025": false,
      "fast_hist_ev_nonnegative": false,
      "fast_2026_ev_positive": true,
      "frequency_still_above_core_35pm": true,
      "max_risk_le_1_40": true
    },
    "pass": false
  },
  "BLOCK_ANY_CORE_OPEN_RISK0.40": {
    "checks": {
      "historical_sum_not_below_allow025": false,
      "historical_rdd_not_below_allow025": false,
      "forward_sum_not_below_allow025": false,
      "forward_rdd_not_below_allow025": false,
      "fast_hist_ev_nonnegative": false,
      "fast_2026_ev_positive": true,
      "frequency_still_above_core_35pm": true,
      "max_risk_le_1_40": true
    },
    "pass": false
  },
  "BLOCK_OPPOSITE_CORE_OPEN_RISK0.25": {
    "checks": {
      "historical_sum_not_below_allow025": false,
      "historical_rdd_not_below_allow025": true,
      "forward_sum_not_below_allow025": false,
      "forward_rdd_not_below_allow025": false,
      "fast_hist_ev_nonnegative": false,
      "fast_2026_ev_positive": true,
      "frequency_still_above_core_35pm": true,
      "max_risk_le_1_40": true
    },
    "pass": false
  },
  "BLOCK_OPPOSITE_CORE_OPEN_RISK0.40": {
    "checks": {
      "historical_sum_not_below_allow025": false,
      "historical_rdd_not_below_allow025": false,
      "forward_sum_not_below_allow025": true,
      "forward_rdd_not_below_allow025": true,
      "fast_hist_ev_nonnegative": false,
      "fast_2026_ev_positive": true,
      "frequency_still_above_core_35pm": true,
      "max_risk_le_1_40": true
    },
    "pass": false
  },
  "BLOCK_SAME_SIDE_CORE_OPEN_RISK0.25": {
    "checks": {
      "historical_sum_not_below_allow025": false,
      "historical_rdd_not_below_allow025": false,
      "forward_sum_not_below_allow025": false,
      "forward_rdd_not_below_allow025": false,
      "fast_hist_ev_nonnegative": false,
      "fast_2026_ev_positive": false,
      "frequency_still_above_core_35pm": true,
      "max_risk_le_1_40": true
    },
    "pass": false
  },
  "BLOCK_SAME_SIDE_CORE_OPEN_RISK0.40": {
    "checks": {
      "historical_sum_not_below_allow025": false,
      "historical_rdd_not_below_allow025": false,
      "forward_sum_not_below_allow025": false,
      "forward_rdd_not_below_allow025": false,
      "fast_hist_ev_nonnegative": false,
      "fast_2026_ev_positive": false,
      "frequency_still_above_core_35pm": true,
      "max_risk_le_1_40": true
    },
    "pass": false
  }
}

## Limitations
- BTC only.
- 2026 Mar-Aug is reused forward-shadow, not pristine OOS.
- Conflict policies act only when a FAST entry is about to occur; CORE is never blocked.
- Later CORE entries during an already-open FAST trade are audited but not force-closed in this LAB.
- 2025 decomposition is diagnostic only. No new failure-regime filter is promoted from this audit.
- FAST confirmation retains LAB039/LAB040 first-raw-close approximation to live timer/quote behavior.