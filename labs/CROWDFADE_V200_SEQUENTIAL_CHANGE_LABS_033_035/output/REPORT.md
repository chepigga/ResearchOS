# CrowdFade v200 sequential change LABs 033–035

Frozen: Z2.05 -> M15 confirm 0.25 ATR -> SL4.5 -> TP10 -> H24 -> flat risk.

## LAB033A — passive retrace only
- 0.60 ATR | hist N=1642 EV=+0.0745 PF=1.151 Sum=+122.40R DD=19.83 R/DD=6.174 fill=44.3% | 2026 N=176 EV=+0.0972 PF=1.198 Sum=+17.12R DD=8.34 R/DD=2.051 fill=48.6%
- 0.45 ATR | hist N=1780 EV=+0.0795 PF=1.167 Sum=+141.49R DD=27.96 R/DD=5.061 fill=57.0% | 2026 N=187 EV=+0.0496 PF=1.100 Sum=+9.28R DD=8.33 R/DD=1.114 fill=58.3%
- 0.40 ATR | hist N=1818 EV=+0.0746 PF=1.157 Sum=+135.69R DD=31.29 R/DD=4.336 fill=61.9% | 2026 N=190 EV=+0.0842 PF=1.176 Sum=+15.99R DD=8.12 R/DD=1.970 fill=64.0%
- 0.30 ATR | hist N=1880 EV=+0.0734 PF=1.155 Sum=+138.06R DD=36.84 R/DD=3.748 fill=70.7% | 2026 N=198 EV=+0.0089 PF=1.018 Sum=+1.76R DD=13.42 R/DD=0.131 fill=70.5%

Selected by preregistered guard: **0.60 ATR**

## LAB033B — TTL only
- 20m | hist N=1642 EV=+0.0745 PF=1.151 Sum=+122.40R DD=19.83 R/DD=6.174 fill=44.3% | 2026 N=176 EV=+0.0972 PF=1.198 Sum=+17.12R DD=8.34 R/DD=2.051 fill=48.6%
- 30m | hist N=1725 EV=+0.0745 PF=1.152 Sum=+128.58R DD=30.39 R/DD=4.230 fill=51.6% | 2026 N=182 EV=+0.0663 PF=1.136 Sum=+12.07R DD=9.65 R/DD=1.251 fill=56.9%
Selected: **20m**

## LAB034A — volatility expansion diagnostic
{
  "atr_expansion_confirm": {
    "<0.90": {
      "N": 3,
      "WR": 0.0,
      "EV": -0.8190100750523825,
      "SumR": -2.4570302251571476,
      "PF": 0.0,
      "MaxDD_R": 2.4570302251571476,
      "R_DD": -1.0,
      "MaxConsecutiveLosses": 3
    },
    "0.90-1.10": {
      "N": 133,
      "WR": 0.41353383458646614,
      "EV": 0.1013057975950447,
      "SumR": 13.473671080140944,
      "PF": 1.2039061830177318,
      "MaxDD_R": 9.87768711159737,
      "R_DD": 1.364051212385695,
      "MaxConsecutiveLosses": 9
    },
    "1.10-1.25": {
      "N": 28,
      "WR": 0.4642857142857143,
      "EV": 0.039088604448400684,
      "SumR": 1.0944809245552192,
      "PF": 1.0866912921293972,
      "MaxDD_R": 5.4516681812103345,
      "R_DD": 0.20076073747985,
      "MaxConsecutiveLosses": 4
    },
    "1.25-1.50": {
      "N": 10,
      "WR": 0.5,
      "EV": 0.4351551826786464,
      "SumR": 4.351551826786464,
      "PF": 2.0179593808223144,
      "MaxDD_R": 4.044068213437182,
      "R_DD": 1.0760332410634443,
      "MaxConsecutiveLosses": 4
    },
    ">=1.50": {
      "N": 2,
      "WR": 0.5,
      "EV": 0.3262815869764494,
      "SumR": 0.6525631739528988,
      "PF": 1.6490763661837913,
      "MaxDD_R": 1.005371953056322,
      "R_DD": 0.6490763661837913,
      "MaxConsecutiveLosses": 1
    }
  },
  "crowd_exc_atr": {
    "<0.50": {
      "N": 112,
      "WR": 0.4017857142857143,
      "EV": 0.04608617263411742,
      "SumR": 5.161651335021151,
      "PF": 1.090969407392993,
      "MaxDD_R": 9.622948080786307,
      "R_DD": 0.5363898143986853,
      "MaxConsecutiveLosses": 6
    },
    "0.50-1.00": {
      "N": 39,
      "WR": 0.4358974358974359,
      "EV": 0.17368214095268839,
      "SumR": 6.7736034971548476,
      "PF": 1.3531635093457428,
      "MaxDD_R": 4.192273716548642,
      "R_DD": 1.6157350295179027,
      "MaxConsecutiveLosses": 5
    },
    "1.00-1.50": {
      "N": 13,
      "WR": 0.38461538461538464,
      "EV": -0.19817631749852735,
      "SumR": -2.5762921274808557,
      "PF": 0.5314025819163429,
      "MaxDD_R": 4.263000394158299,
      "R_DD": -0.6043377643152968,
      "MaxConsecutiveLosses": 6
    },
    ">=1.50": {
      "N": 12,
      "WR": 0.5833333333333334,
      "EV": 0.6463561729652703,
      "SumR": 7.756274075583243,
      "PF": 2.544513418329236,
      "MaxDD_R": 2.0106877604590956,
      "R_DD": 3.857522897444938,
      "MaxConsecutiveLosses": 2
    }
  }
}

## LAB034B — dynamic execution ATR
- baseline hist N=1642 EV=+0.0745 PF=1.151 Sum=+122.40R DD=19.83 R/DD=6.174 fill=44.3% | 2026 N=176 EV=+0.0972 PF=1.198 Sum=+17.12R DD=8.34 R/DD=2.051 fill=48.6%
- dynamic hist N=1556 EV=+0.0794 PF=1.167 Sum=+123.48R DD=19.56 R/DD=6.313 fill=41.7% | 2026 N=164 EV=+0.1154 PF=1.249 Sum=+18.93R DD=10.19 R/DD=1.857 fill=46.2%
Selected: **frozen signal ATR**

## LAB035 — Z flip persistence
- PRESERVE | hist N=1642 EV=+0.0745 PF=1.151 Sum=+122.40R DD=19.83 R/DD=6.174 fill=44.3% | 2026 N=176 EV=+0.0972 PF=1.198 Sum=+17.12R DD=8.34 R/DD=2.051 fill=48.6% | z-cancel forward=0
- CANCEL_SIGN_FLIP | hist N=1617 EV=+0.0845 PF=1.173 Sum=+136.62R DD=18.81 R/DD=7.261 fill=44.2% | 2026 N=172 EV=+0.1321 PF=1.276 Sum=+22.72R DD=8.01 R/DD=2.836 fill=48.3% | z-cancel forward=8
- CANCEL_OPPOSITE_THRESHOLD | hist N=1638 EV=+0.0749 PF=1.152 Sum=+122.65R DD=19.83 R/DD=6.186 fill=44.2% | 2026 N=174 EV=+0.1143 PF=1.236 Sum=+19.88R DD=8.01 R/DD=2.481 fill=48.2% | z-cancel forward=3

LAB035 has **no automatic promotion**; interpretation must consider losses avoided and right-tail winners removed.

## Limitations
- 2021-2025 is discovery/in-sample.
- 2026 Mar-Aug is reused forward-shadow/stress, not pristine OOS.
- BTC only; ETH/SOL transfer is not proven.
- Historical path uses M1; 2026 forward uses second OHLC; same-bar stop-first.
- LAB036 broker execution requires fresh IC Markets/GetLeveraged logs and is not inferred from Binance replay.