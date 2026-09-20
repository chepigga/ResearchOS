# LAB041C — FAST_ENTRY_LATENESS_AND_FIRST_RESPONSE_AUDIT

## Baseline
- Hist: N=1006 EV=+0.0019 PF=1.004 Sum=+1.92R DD=43.98 R/DD=0.044
- 2026: N=97 EV=+0.1565 PF=1.366 Sum=+15.18R DD=7.26 R/DD=2.090

## Lateness diagnostics
- Hist: {"first_touch_0.10_min": {"N": 1006, "mean": 5.210735586481113, "median": 1.0, "p10": 1.0, "p25": 1.0, "p75": 3.0, "p90": 11.0}, "first_close_0.10_min": {"N": 1006, "mean": 7.333001988071571, "median": 1.0, "p10": 1.0, "p25": 1.0, "p75": 6.0, "p90": 19.0}, "confirmation_0.30_min": {"N": 1006, "mean": 17.065606361829026, "median": 5.0, "p10": 1.0, "p25": 2.0, "p75": 20.0, "p90": 53.5}, "entry_move_atr": {"N": 1006, "mean": 0.4561603855202174, "median": 0.3873795185542144, "p10": 0.31393904361831937, "p25": 0.3380882024743635, "p75": 0.48456032332392013, "p90": 0.660589980938306}, "pre_entry_mfe_atr": {"N": 1006, "mean": 0.5504516141079091, "median": 0.46082377223037385, "p10": 0.34312852515554393, "p25": 0.382713765888109, "p75": 0.5885960578652045, "p90": 0.8209185272474591}, "pre_entry_mae_atr": {"N": 1006, "mean": 0.2826480721846783, "median": 0.08785558208750024, "p10": 0.0, "p25": 0.0, "p75": 0.526704839392681, "p90": 0.7570815382828071}}
- 2026: {"first_touch_0.10_min": {"N": 97, "mean": 4.711340206185567, "median": 0.5833333333333334, "p10": 0.1, "p25": 0.2, "p75": 3.55, "p90": 12.680000000000023}, "first_close_0.10_min": {"N": 97, "mean": 4.718900343642612, "median": 0.6, "p10": 0.1, "p25": 0.2, "p75": 3.55, "p90": 12.680000000000023}, "confirmation_0.30_min": {"N": 97, "mean": 10.867869415807558, "median": 4.75, "p10": 0.6233333333333334, "p25": 1.5, "p75": 12.9, "p90": 28.873333333333346}, "entry_move_atr": {"N": 97, "mean": 0.3421032230267618, "median": 0.3198781416603208, "p10": 0.3027430485521053, "p25": 0.30717472390843364, "p75": 0.34097864151180557, "p90": 0.39445311082060397}, "pre_entry_mfe_atr": {"N": 97, "mean": 0.354003885208931, "median": 0.32702428215306906, "p10": 0.30377022718353075, "p25": 0.308682380023025, "p75": 0.3560473694427831, "p90": 0.42203110458385584}, "pre_entry_mae_atr": {"N": 97, "mean": 0.22789192807838762, "median": 0.0963898700832184, "p10": 0.0, "p25": 0.030166634744301944, "p75": 0.44036557501899504, "p90": 0.5793473650844669}}

## Causal early-response stateful replay
- 0.10 ATR: hist N=1011 EV=+0.0625 PF=1.133 Sum=+63.14R DD=25.83 R/DD=2.444 | 2026 N=105 EV=+0.1071 PF=1.241 Sum=+11.25R DD=8.61 R/DD=1.306
- 0.15 ATR: hist N=1010 EV=+0.0316 PF=1.064 Sum=+31.92R DD=34.80 R/DD=0.917 | 2026 N=100 EV=+0.0753 PF=1.166 Sum=+7.53R DD=7.42 R/DD=1.014
- 0.20 ATR: hist N=1007 EV=+0.0430 PF=1.089 Sum=+43.31R DD=34.61 R/DD=1.251 | 2026 N=102 EV=-0.0051 PF=0.990 Sum=-0.52R DD=9.16 R/DD=-0.056
- 0.25 ATR: hist N=1014 EV=+0.0230 PF=1.047 Sum=+23.31R DD=36.97 R/DD=0.631 | 2026 N=102 EV=+0.0618 PF=1.133 Sum=+6.30R DD=8.04 R/DD=0.784
- 0.30 ATR: hist N=1006 EV=+0.0019 PF=1.004 Sum=+1.92R DD=43.98 R/DD=0.044 | 2026 N=97 EV=+0.1565 PF=1.366 Sum=+15.18R DD=7.26 R/DD=2.090

## Causal retrace after valid 0.30 confirmation
- retrace 0.10: hist N=996 EV=-0.0192 PF=0.963 Sum=-19.12R DD=61.63 R/DD=-0.310 noFill=88 | 2026 N=95 EV=+0.0910 PF=1.200 Sum=+8.65R DD=5.25 R/DD=1.645 noFill=11
- retrace 0.20: hist N=968 EV=+0.0236 PF=1.047 Sum=+22.82R DD=41.65 R/DD=0.548 noFill=191 | 2026 N=101 EV=+0.0484 PF=1.100 Sum=+4.89R DD=8.26 R/DD=0.592 noFill=20
- retrace 0.30: hist N=934 EV=+0.0064 PF=1.013 Sum=+5.97R DD=48.21 R/DD=0.124 noFill=320 | 2026 N=99 EV=+0.0342 PF=1.070 Sum=+3.39R DD=8.93 R/DD=0.379 noFill=30

## 2025 halves
{
  "H1": {
    "metrics": {
      "N": 105,
      "WR": 0.44761904761904764,
      "EV": 0.1186588196186631,
      "SumR": 12.459176059959626,
      "PF": 1.2920228337850155,
      "MaxDD_R": 8.824988516438427,
      "R_DD": 1.411806489804689,
      "MaxConsecutiveLosses": 6
    },
    "diagnostics": {
      "first_touch_0.10_min": {
        "N": 105,
        "mean": 6.314285714285714,
        "median": 1.0,
        "p10": 1.0,
        "p25": 1.0,
        "p75": 3.0,
        "p90": 17.0
      },
      "first_close_0.10_min": {
        "N": 105,
        "mean": 7.6,
        "median": 2.0,
        "p10": 1.0,
        "p25": 1.0,
        "p75": 8.0,
        "p90": 20.800000000000026
      },
      "confirmation_0.30_min": {
        "N": 105,
        "mean": 17.83809523809524,
        "median": 6.0,
        "p10": 1.0,
        "p25": 2.0,
        "p75": 22.0,
        "p90": 50.00000000000004
      },
      "entry_move_atr": {
        "N": 105,
        "mean": 0.44862146856504653,
        "median": 0.3844520567335743,
        "p10": 0.3089558058923313,
        "p25": 0.3341145636451112,
        "p75": 0.47241998032056004,
        "p90": 0.6560552374036388
      },
      "pre_entry_mfe_atr": {
        "N": 105,
        "mean": 0.5379947725412578,
        "median": 0.44118983889703767,
        "p10": 0.3312001489723916,
        "p25": 0.3688402190144633,
        "p75": 0.5707329502024195,
        "p90": 0.7491544655612087
      },
      "pre_entry_mae_atr": {
        "N": 105,
        "mean": 0.3058782873262931,
        "median": 0.12074666492921991,
        "p10": 0.0,
        "p25": 0.0,
        "p75": 0.5131282247276671,
        "p90": 0.82278449064542
      }
    }
  },
  "H2": {
    "metrics": {
      "N": 110,
      "WR": 0.2636363636363636,
      "EV": -0.371815645769636,
      "SumR": -40.89972103465996,
      "PF": 0.4297962156461937,
      "MaxDD_R": 43.984708452591256,
      "R_DD": -0.9298622742661479,
      "MaxConsecutiveLosses": 9
    },
    "diagnostics": {
      "first_touch_0.10_min": {
        "N": 110,
        "mean": 3.790909090909091,
        "median": 1.0,
        "p10": 1.0,
        "p25": 1.0,
        "p75": 3.0,
        "p90": 9.0
      },
      "first_close_0.10_min": {
        "N": 110,
        "mean": 5.909090909090909,
        "median": 2.0,
        "p10": 1.0,
        "p25": 1.0,
        "p75": 4.75,
        "p90": 15.100000000000009
      },
      "confirmation_0.30_min": {
        "N": 110,
        "mean": 13.554545454545455,
        "median": 4.0,
        "p10": 1.0,
        "p25": 1.0,
        "p75": 14.5,
        "p90": 41.50000000000004
      },
      "entry_move_atr": {
        "N": 110,
        "mean": 0.4477329058883695,
        "median": 0.39455545472824344,
        "p10": 0.3142461405211817,
        "p25": 0.3527463345200304,
        "p75": 0.49281074142015024,
        "p90": 0.6658554986812515
      },
      "pre_entry_mfe_atr": {
        "N": 110,
        "mean": 0.5159680478716001,
        "median": 0.46134646601309387,
        "p10": 0.353672415857713,
        "p25": 0.3818513902201468,
        "p75": 0.5684392109268508,
        "p90": 0.736495844533747
      },
      "pre_entry_mae_atr": {
        "N": 110,
        "mean": 0.2565488479844847,
        "median": 0.05533968111795088,
        "p10": 0.0,
        "p25": 0.0,
        "p75": 0.4888149259023118,
        "p90": 0.708815699313304
      }
    }
  }
}

## Paired oracle diagnostics
{
  "historical": {
    "ORACLE_EARLY_0.10": {
      "metrics": {
        "N": 1006,
        "WR": 0.4194831013916501,
        "EV": 0.03745726287613782,
        "SumR": 37.68200645339465,
        "PF": 1.0778184109338869,
        "MaxDD_R": 40.55266948543833,
        "R_DD": 0.9292114904279118,
        "MaxConsecutiveLosses": 12
      },
      "fill_rate": 1.0,
      "paired_delta_vs_baseline_R": 35.76187711581769
    },
    "ORACLE_EARLY_0.15": {
      "metrics": {
        "N": 1006,
        "WR": 0.4165009940357853,
        "EV": 0.02957389730215267,
        "SumR": 29.751340685965584,
        "PF": 1.0609988159123753,
        "MaxDD_R": 40.66196241944008,
        "R_DD": 0.7316749835896205,
        "MaxConsecutiveLosses": 12
      },
      "fill_rate": 1.0,
      "paired_delta_vs_baseline_R": 27.83121134838864
    },
    "ORACLE_EARLY_0.20": {
      "metrics": {
        "N": 1006,
        "WR": 0.4125248508946322,
        "EV": 0.021841045870013967,
        "SumR": 21.97209214523405,
        "PF": 1.044801557200963,
        "MaxDD_R": 40.926341357523164,
        "R_DD": 0.5368692000413835,
        "MaxConsecutiveLosses": 12
      },
      "fill_rate": 1.0,
      "paired_delta_vs_baseline_R": 20.051962807657098
    },
    "ORACLE_EARLY_0.25": {
      "metrics": {
        "N": 1006,
        "WR": 0.40656063618290256,
        "EV": 0.012167594428430642,
        "SumR": 12.240599995001226,
        "PF": 1.0246996722879176,
        "MaxDD_R": 41.02281196304817,
        "R_DD": 0.2983852010444117,
        "MaxConsecutiveLosses": 12
      },
      "fill_rate": 1.0,
      "paired_delta_vs_baseline_R": 10.320470657424282
    },
    "ORACLE_EARLY_0.30": {
      "metrics": {
        "N": 1006,
        "WR": 0.40556660039761433,
        "EV": 0.0019086772739333416,
        "SumR": 1.9201293375769417,
        "PF": 1.0038379111781415,
        "MaxDD_R": 43.98470845259128,
        "R_DD": 0.04365447459192652,
        "MaxConsecutiveLosses": 12
      },
      "fill_rate": 1.0,
      "paired_delta_vs_baseline_R": 0.0
    },
    "RETRACE_0.10": {
      "metrics": {
        "N": 919,
        "WR": 0.41458106637649617,
        "EV": 0.019106155102855803,
        "SumR": 17.558556539524485,
        "PF": 1.0389753534646458,
        "MaxDD_R": 39.396370697171804,
        "R_DD": 0.4456896975229493,
        "MaxConsecutiveLosses": 9
      },
      "fill_rate": 0.9135188866799204,
      "paired_delta_vs_baseline_R": 16.750259726507597
    },
    "RETRACE_0.20": {
      "metrics": {
        "N": 825,
        "WR": 0.416969696969697,
        "EV": 0.01916380268158868,
        "SumR": 15.810137212310659,
        "PF": 1.0390017503453013,
        "MaxDD_R": 30.793797680841223,
        "R_DD": 0.5134195326011104,
        "MaxConsecutiveLosses": 9
      },
      "fill_rate": 0.820079522862823,
      "paired_delta_vs_baseline_R": 26.437091874704652
    },
    "RETRACE_0.30": {
      "metrics": {
        "N": 745,
        "WR": 0.4147651006711409,
        "EV": 0.009006569148269939,
        "SumR": 6.709894015461105,
        "PF": 1.0182375954030287,
        "MaxDD_R": 34.551630650344,
        "R_DD": 0.19419905483952318,
        "MaxConsecutiveLosses": 9
      },
      "fill_rate": 0.7405566600397614,
      "paired_delta_vs_baseline_R": 39.64629350068074
    }
  },
  "forward": {
    "ORACLE_EARLY_0.10": {
      "metrics": {
        "N": 97,
        "WR": 0.5051546391752577,
        "EV": 0.19379685961955406,
        "SumR": 18.798295383096743,
        "PF": 1.4595126985864197,
        "MaxDD_R": 6.926989410710803,
        "R_DD": 2.713775677790127,
        "MaxConsecutiveLosses": 5
      },
      "fill_rate": 1.0,
      "paired_delta_vs_baseline_R": 3.613386884807901
    },
    "ORACLE_EARLY_0.15": {
      "metrics": {
        "N": 97,
        "WR": 0.5051546391752577,
        "EV": 0.18689211040542858,
        "SumR": 18.128534709326573,
        "PF": 1.4423700952644525,
        "MaxDD_R": 6.929328299895451,
        "R_DD": 2.616203753775109,
        "MaxConsecutiveLosses": 5
      },
      "fill_rate": 1.0,
      "paired_delta_vs_baseline_R": 2.943626211037729
    },
    "ORACLE_EARLY_0.20": {
      "metrics": {
        "N": 97,
        "WR": 0.4948453608247423,
        "EV": 0.1819737629800477,
        "SumR": 17.651455009064627,
        "PF": 1.428284506511779,
        "MaxDD_R": 6.947522867885038,
        "R_DD": 2.540683254265858,
        "MaxConsecutiveLosses": 5
      },
      "fill_rate": 1.0,
      "paired_delta_vs_baseline_R": 2.466546510775788
    },
    "ORACLE_EARLY_0.25": {
      "metrics": {
        "N": 97,
        "WR": 0.5051546391752577,
        "EV": 0.16501171112145563,
        "SumR": 16.006135978781195,
        "PF": 1.388574587145389,
        "MaxDD_R": 6.989677296995239,
        "R_DD": 2.2899678051892325,
        "MaxConsecutiveLosses": 5
      },
      "fill_rate": 1.0,
      "paired_delta_vs_baseline_R": 0.8212274804923508
    },
    "ORACLE_EARLY_0.30": {
      "metrics": {
        "N": 97,
        "WR": 0.4948453608247423,
        "EV": 0.15654544843596743,
        "SumR": 15.184908498288841,
        "PF": 1.3655535503153073,
        "MaxDD_R": 7.264802130649438,
        "R_DD": 2.090202627023426,
        "MaxConsecutiveLosses": 5
      },
      "fill_rate": 1.0,
      "paired_delta_vs_baseline_R": 0.0
    },
    "RETRACE_0.10": {
      "metrics": {
        "N": 87,
        "WR": 0.4827586206896552,
        "EV": 0.09988732680804667,
        "SumR": 8.69019743230006,
        "PF": 1.2271730526052984,
        "MaxDD_R": 6.028181424303513,
        "R_DD": 1.4415952043620042,
        "MaxConsecutiveLosses": 4
      },
      "fill_rate": 0.8969072164948454,
      "paired_delta_vs_baseline_R": 1.6181260136845952
    },
    "RETRACE_0.20": {
      "metrics": {
        "N": 82,
        "WR": 0.4878048780487805,
        "EV": 0.08700572337025475,
        "SumR": 7.13446931636089,
        "PF": 1.200388260076868,
        "MaxDD_R": 7.470926309797587,
        "R_DD": 0.9549644877375569,
        "MaxConsecutiveLosses": 4
      },
      "fill_rate": 0.845360824742268,
      "paired_delta_vs_baseline_R": 2.931077226890805
    },
    "RETRACE_0.30": {
      "metrics": {
        "N": 73,
        "WR": 0.4794520547945205,
        "EV": 0.1051537238224558,
        "SumR": 7.676221839039274,
        "PF": 1.2324818864073919,
        "MaxDD_R": 8.109383739379831,
        "R_DD": 0.946585102609328,
        "MaxConsecutiveLosses": 3
      },
      "fill_rate": 0.7525773195876289,
      "paired_delta_vs_baseline_R": 3.29880715272548
    }
  }
}

## Limitations
- Historical path is 1-minute OHLC; 2026 forward-shadow path is second OHLC, so latency precision differs.
- 2026 Mar-Aug is reused forward-shadow, not pristine OOS.
- Paired early-entry counterfactuals are oracle diagnostics because baseline G1 membership is only known at the later 0.30 confirmation.
- Causal early-entry reruns avoid that lookahead but change G1 population and later sequence.
- Broker spread/slippage/freeze effects are represented only by flat research cost, not full MT5 execution.