# LAB041 — FAST_LANE_COMPOSITE_GATE_AND_PORTFOLIO_REPLAY

## CORE baseline
- Hist: N=1617 (26.9/mo) EV=+0.0845 PF=1.173 Sum=+136.62R DD=18.81 R/DD=7.261
- 2026: N=172 (28.7/mo) EV=+0.1321 PF=1.276 Sum=+22.72R DD=8.01 R/DD=2.836

## Standalone gated FAST
- G1_RESPONSE: hist N=1006 (16.8/mo) EV=+0.0019 PF=1.004 Sum=+1.92R DD=43.98 R/DD=0.044 | 2026 N=97 (16.2/mo) EV=+0.1565 PF=1.366 Sum=+15.18R DD=7.26 R/DD=2.090
- G2_RESPONSE_RECLAIM: hist N=1993 (33.2/mo) EV=+0.0042 PF=1.008 Sum=+8.39R DD=36.84 R/DD=0.228 | 2026 N=174 (29.0/mo) EV=-0.0426 PF=0.917 Sum=-7.42R DD=25.09 R/DD=-0.296
- G3_FULL_COMPOSITE: hist N=2065 (34.4/mo) EV=+0.0047 PF=1.010 Sum=+9.71R DD=37.38 R/DD=0.260 | 2026 N=187 (31.2/mo) EV=-0.0289 PF=0.944 Sum=-5.41R DD=21.45 R/DD=-0.252

## Combined portfolio
- G1_RESPONSE_RISK0.25: hist N=2623 (43.7/mo) EV=+0.0523 PF=1.150 Sum=+137.10R DD=20.96 R/DD=6.540 maxRisk=1.25u | 2026 N=269 (44.8/mo) EV=+0.0986 PF=1.286 Sum=+26.52R DD=7.95 R/DD=3.337 maxRisk=1.25u | PASS=True
- G1_RESPONSE_RISK0.40: hist N=2623 (43.7/mo) EV=+0.0524 PF=1.139 Sum=+137.38R DD=22.25 R/DD=6.174 maxRisk=1.40u | 2026 N=269 (44.8/mo) EV=+0.1071 PF=1.291 Sum=+28.80R DD=7.91 R/DD=3.642 maxRisk=1.40u | PASS=True
- G2_RESPONSE_RECLAIM_RISK0.25: hist N=3610 (60.2/mo) EV=+0.0384 PF=1.133 Sum=+138.71R DD=23.37 R/DD=5.936 maxRisk=1.25u | 2026 N=346 (57.7/mo) EV=+0.0603 PF=1.199 Sum=+20.87R DD=11.09 R/DD=1.882 maxRisk=1.25u | PASS=False
- G2_RESPONSE_RECLAIM_RISK0.40: hist N=3610 (60.2/mo) EV=+0.0388 PF=1.118 Sum=+139.97R DD=26.93 R/DD=5.197 maxRisk=1.40u | 2026 N=346 (57.7/mo) EV=+0.0571 PF=1.167 Sum=+19.76R DD=13.48 R/DD=1.466 maxRisk=1.40u | PASS=False
- G3_FULL_COMPOSITE_RISK0.25: hist N=3682 (61.4/mo) EV=+0.0378 PF=1.133 Sum=+139.04R DD=24.75 R/DD=5.618 maxRisk=1.25u | 2026 N=359 (59.8/mo) EV=+0.0595 PF=1.200 Sum=+21.37R DD=10.60 R/DD=2.016 maxRisk=1.25u | PASS=False
- G3_FULL_COMPOSITE_RISK0.40: hist N=3682 (61.4/mo) EV=+0.0382 PF=1.117 Sum=+140.50R DD=29.14 R/DD=4.821 maxRisk=1.40u | 2026 N=359 (59.8/mo) EV=+0.0573 PF=1.170 Sum=+20.56R DD=12.71 R/DD=1.618 maxRisk=1.40u | PASS=False

## Promotion checks
{
  "G1_RESPONSE_RISK0.25": {
    "adds_trades": true,
    "forward_sum_not_worse": true,
    "forward_rdd_not_worse": true,
    "hist_portfolio_ev_positive": true,
    "fast_lane_hist_positive": true,
    "max_risk_ok": true,
    "pass": true
  },
  "G1_RESPONSE_RISK0.40": {
    "adds_trades": true,
    "forward_sum_not_worse": true,
    "forward_rdd_not_worse": true,
    "hist_portfolio_ev_positive": true,
    "fast_lane_hist_positive": true,
    "max_risk_ok": true,
    "pass": true
  },
  "G2_RESPONSE_RECLAIM_RISK0.25": {
    "adds_trades": true,
    "forward_sum_not_worse": false,
    "forward_rdd_not_worse": false,
    "hist_portfolio_ev_positive": true,
    "fast_lane_hist_positive": true,
    "max_risk_ok": true,
    "pass": false
  },
  "G2_RESPONSE_RECLAIM_RISK0.40": {
    "adds_trades": true,
    "forward_sum_not_worse": false,
    "forward_rdd_not_worse": false,
    "hist_portfolio_ev_positive": true,
    "fast_lane_hist_positive": true,
    "max_risk_ok": true,
    "pass": false
  },
  "G3_FULL_COMPOSITE_RISK0.25": {
    "adds_trades": true,
    "forward_sum_not_worse": false,
    "forward_rdd_not_worse": false,
    "hist_portfolio_ev_positive": true,
    "fast_lane_hist_positive": true,
    "max_risk_ok": true,
    "pass": false
  },
  "G3_FULL_COMPOSITE_RISK0.40": {
    "adds_trades": true,
    "forward_sum_not_worse": false,
    "forward_rdd_not_worse": false,
    "hist_portfolio_ev_positive": true,
    "fast_lane_hist_positive": true,
    "max_risk_ok": true,
    "pass": false
  }
}

## Limitations
- BTC only; ETH/SOL transfer still required.
- 2026 Mar-Aug is reused forward-shadow, not pristine OOS.
- FAST confirmation uses first raw-price close crossing as LAB039/LAB040 approximation to live timer/quote behavior.
- CORE and FAST are independent lanes; portfolio overlap is allowed and risk concurrency is audited.
- Rejected FAST candidates do not consume pause/day quota; accepted FAST trades do. This is intentional stateful gate-before-entry behavior.