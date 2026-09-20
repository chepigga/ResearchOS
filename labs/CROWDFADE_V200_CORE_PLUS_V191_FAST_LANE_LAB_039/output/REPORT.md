# LAB039 — V200 CORE + V191 FAST LANE

CORE remains untouched. FAST only handles 1.0 <= |Z| < 2.05.

## Standalone lanes
- Hist CORE: N=1617 (26.9/mo) EV=+0.0845 PF=1.173 Sum=+136.62R DD=18.81 R/DD=7.261
- Hist FAST + v191 exits: N=5396 (89.9/mo) EV=-0.0416 PF=0.877 Sum=-224.37R DD=250.67 R/DD=-0.895
- Hist FAST + v200 exits: N=2492 (41.5/mo) EV=+0.0127 PF=1.026 Sum=+31.68R DD=44.27 R/DD=0.716
- Hist v191-like full reference: N=5405 (90.1/mo) EV=-0.0577 PF=0.831 Sum=-311.98R DD=329.05 R/DD=-0.948
- 2026 CORE: N=172 (28.7/mo) EV=+0.1321 PF=1.276 Sum=+22.72R DD=8.01 R/DD=2.836
- 2026 FAST + v191 exits: N=552 (92.0/mo) EV=-0.0419 PF=0.862 Sum=-23.14R DD=41.27 R/DD=-0.561
- 2026 FAST + v200 exits: N=266 (44.3/mo) EV=-0.1028 PF=0.810 Sum=-27.35R DD=29.23 R/DD=-0.936
- 2026 v191-like full reference: N=552 (92.0/mo) EV=-0.0545 PF=0.817 Sum=-30.11R DD=42.29 R/DD=-0.712

## Combined portfolio
- CORE_PLUS_FAST191_RISK0.50: hist N=7013 (116.9/mo) EV=+0.0035 PF=1.014 Sum=+24.43R DD=50.61 R/DD=0.483 maxRisk=1.50u | 2026 N=724 (120.7/mo) EV=+0.0154 PF=1.067 Sum=+11.15R DD=14.90 R/DD=0.748 maxRisk=1.50u
- CORE_PLUS_FAST191_RISK0.40: hist N=7013 (116.9/mo) EV=+0.0067 PF=1.031 Sum=+46.87R DD=42.52 R/DD=1.102 maxRisk=1.40u | 2026 N=724 (120.7/mo) EV=+0.0186 PF=1.090 Sum=+13.47R DD=13.18 R/DD=1.022 maxRisk=1.40u
- CORE_PLUS_FASTV200_RISK0.50: hist N=4109 (68.5/mo) EV=+0.0371 PF=1.108 Sum=+152.46R DD=30.52 R/DD=4.996 maxRisk=1.50u | 2026 N=438 (73.0/mo) EV=+0.0207 PF=1.059 Sum=+9.05R DD=13.42 R/DD=0.674 maxRisk=1.50u
- CORE_PLUS_FASTV200_RISK0.40: hist N=4109 (68.5/mo) EV=+0.0363 PF=1.116 Sum=+149.29R DD=28.00 R/DD=5.332 maxRisk=1.40u | 2026 N=438 (73.0/mo) EV=+0.0269 PF=1.084 Sum=+11.78R DD=12.14 R/DD=0.971 maxRisk=1.40u

## Limitations
- BTC only; ETH/SOL transfer is required.
- 2021-2025 is discovery/in-sample; 2026 Mar-Aug is reused forward-shadow.
- v191 live confirmation is timer/quote based; replay approximates market confirmation using first raw close crossing 0.30 ATR.
- v191 broker spread, BE/freeze-level execution and slippage are not modeled beyond flat 0.5 bps research cost.
- v191 score-based lot weighting is intentionally omitted; FAST risk is fixed at 0.50x/0.40x for clean lane attribution.
- CORE and FAST are independent concurrent lanes in portfolio mode; same-symbol aggregate exposure is represented by max_concurrent_risk_units.