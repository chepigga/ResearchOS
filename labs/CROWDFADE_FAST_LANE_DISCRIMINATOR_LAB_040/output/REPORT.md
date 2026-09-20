# LAB040 — FAST_LANE_DISCRIMINATOR

Population: 1.0 <= |Z| < 2.05, M5 confirm .30 ATR <=3h, sign-flip cancel, market entry, v200 exits.

- Raw historical: N=2403 EV=+0.0218 PF=1.045 Sum=+52.30R DD=44.68 R/DD=1.170
- Raw 2026: N=252 EV=-0.0520 PF=0.897 Sum=-13.09R DD=22.97 R/DD=-0.570

Passing simple causal rules: **6**

## Best cross-period rule
**reclaim_bin in {>=1.00}**
- Discovery 2021-23: N=149 EV=+0.2730 PF=1.583 Sum=+40.68R DD=5.69 R/DD=7.149
- Validation 2024-25: N=94 EV=+0.0902 PF=1.186 Sum=+8.48R DD=8.01 R/DD=1.059
- All 2021-25: N=243 EV=+0.2023 PF=1.426 Sum=+49.16R DD=8.01 R/DD=6.139
- 2026: N=24 EV=+0.2696 PF=1.641 Sum=+6.47R DD=2.14 R/DD=3.024
- Hist bootstrap: {"N": 243, "months": 60, "observed_sumR": 49.15711697112936, "p_sumR_gt_0": 0.9976, "ci95": [13.9969912464424, 84.8820441592706]}
- 2026 bootstrap: {"N": 24, "months": 6, "observed_sumR": 6.470837445798302, "p_sumR_gt_0": 0.9162, "ci95": [-2.45310752585806, 15.649679713106412]}

## Top robust rules
1. reclaim_bin in {>=1.00} | DISC N=149 EV=+0.2730 PF=1.583 Sum=+40.68R DD=5.69 R/DD=7.149 | VAL N=94 EV=+0.0902 PF=1.186 Sum=+8.48R DD=8.01 R/DD=1.059 | 2026 N=24 EV=+0.2696 PF=1.641 Sum=+6.47R DD=2.14 R/DD=3.024
2. reclaim_bin in {0.50-0.75,>=1.00} | DISC N=487 EV=+0.0901 PF=1.189 Sum=+43.87R DD=11.84 R/DD=3.707 | VAL N=354 EV=+0.1127 PF=1.235 Sum=+39.89R DD=13.52 R/DD=2.950 | 2026 N=93 EV=+0.1370 PF=1.300 Sum=+12.74R DD=8.52 R/DD=1.495
3. trend_state in {BOTH_ALIGN} & crowd_bin in {0.50-1.00} | DISC N=115 EV=+0.0757 PF=1.173 Sum=+8.71R DD=16.88 R/DD=0.516 | VAL N=84 EV=+0.2129 PF=1.552 Sum=+17.89R DD=7.20 R/DD=2.484 | 2026 N=21 EV=+0.0845 PF=1.158 Sum=+1.78R DD=5.82 R/DD=0.305
4. trend_state in {ONE_ALIGN} & response_bin in {>=2.50} | DISC N=137 EV=+0.0810 PF=1.179 Sum=+11.10R DD=12.82 R/DD=0.866 | VAL N=79 EV=+0.0564 PF=1.116 Sum=+4.45R DD=5.41 R/DD=0.824 | 2026 N=25 EV=+0.0747 PF=1.162 Sum=+1.87R DD=3.40 R/DD=0.549
5. confirm_bin in {<=15} & trend_state in {ONE_ALIGN} | DISC N=199 EV=+0.2173 PF=1.496 Sum=+43.23R DD=11.95 R/DD=3.616 | VAL N=125 EV=+0.0550 PF=1.117 Sum=+6.87R DD=11.80 R/DD=0.583 | 2026 N=35 EV=+0.1049 PF=1.236 Sum=+3.67R DD=2.95 R/DD=1.245
6. reclaim_bin in {0.50-0.75} | DISC N=338 EV=+0.0095 PF=1.020 Sum=+3.20R DD=21.05 R/DD=0.152 | VAL N=260 EV=+0.1208 PF=1.253 Sum=+31.41R DD=13.75 R/DD=2.285 | 2026 N=69 EV=+0.0909 PF=1.193 Sum=+6.27R DD=9.70 R/DD=0.647

## Limitations
- 2021-2023 discovery, 2024-2025 internal validation, 2026 reused forward-shadow; 2026 is not pristine OOS.
- Rule family is restricted to simple one-feature unions or two-feature ANDs to reduce overfit.
- BTC only; ETH/SOL transfer remains mandatory before production.
- Exit shell is v200 to isolate entry discrimination; final hybrid must rerun full portfolio sequence.
- Confirmation is completed-M5 close approximation, not exact live quote timer behavior.