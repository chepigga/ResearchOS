# LAB037 — v200 frequency expansion toward v191

Frozen execution: retrace .60 ATR, TTL20, SL4.5, TP10, H24, cancel-sign-flip ON.

## Baseline research candidate
- Hist: N=1617 (26.9/mo) EV=+0.0845 PF=1.173 Sum=+136.62R DD=18.81 R/DD=7.261
- 2026: N=172 (28.7/mo) EV=+0.1321 PF=1.276 Sum=+22.72R DD=8.01 R/DD=2.836

## LAB037A — global Z frontier
- Z2.05: hist N=1617 (26.9/mo) EV=+0.0845 PF=1.173 Sum=+136.62R DD=18.81 R/DD=7.261 | 2026 N=172 (28.7/mo) EV=+0.1321 PF=1.276 Sum=+22.72R DD=8.01 R/DD=2.836
- Z1.75: hist N=1803 (30.1/mo) EV=+0.0234 PF=1.046 Sum=+42.21R DD=35.39 R/DD=1.193 | 2026 N=188 (31.3/mo) EV=+0.0870 PF=1.186 Sum=+16.36R DD=6.10 R/DD=2.682
- Z1.50: hist N=1958 (32.6/mo) EV=+0.0550 PF=1.113 Sum=+107.61R DD=27.06 R/DD=3.977 | 2026 N=199 (33.2/mo) EV=+0.0450 PF=1.095 Sum=+8.96R DD=11.05 R/DD=0.811
- Z1.25: hist N=2040 (34.0/mo) EV=+0.0513 PF=1.106 Sum=+104.57R DD=25.83 R/DD=4.048 | 2026 N=212 (35.3/mo) EV=-0.0236 PF=0.953 Sum=-5.01R DD=17.68 R/DD=-0.283
- Z1.00: hist N=2133 (35.5/mo) EV=+0.0483 PF=1.100 Sum=+103.06R DD=39.92 R/DD=2.582 | 2026 N=224 (37.3/mo) EV=-0.0435 PF=0.917 Sum=-9.75R DD=25.11 R/DD=-0.388

## LAB037B — add mid-Z lane only when H1+H4 aligned with trade
- lane >= 1.75: hist N=1712 (28.5/mo) EV=+0.0664 PF=1.133 Sum=+113.76R DD=21.90 R/DD=5.193 | 2026 N=177 (29.5/mo) EV=+0.0971 PF=1.204 Sum=+17.19R DD=7.35 R/DD=2.338
- lane >= 1.50: hist N=1795 (29.9/mo) EV=+0.0784 PF=1.159 Sum=+140.64R DD=31.50 R/DD=4.465 | 2026 N=186 (31.0/mo) EV=+0.0880 PF=1.184 Sum=+16.36R DD=7.85 R/DD=2.086
- lane >= 1.25: hist N=1846 (30.8/mo) EV=+0.0637 PF=1.128 Sum=+117.65R DD=33.44 R/DD=3.518 | 2026 N=196 (32.7/mo) EV=+0.0474 PF=1.096 Sum=+9.29R DD=10.86 R/DD=0.855
- lane >= 1.00: hist N=1892 (31.5/mo) EV=+0.0843 PF=1.173 Sum=+159.49R DD=25.28 R/DD=6.308 | 2026 N=199 (33.2/mo) EV=+0.0052 PF=1.010 Sum=+1.03R DD=14.70 R/DD=0.070

Selected lane for next step: **2.05**

## LAB037C — M15 confirmation threshold on selected architecture
- confirm 0.25 ATR: hist N=1617 (26.9/mo) EV=+0.0845 PF=1.173 Sum=+136.62R DD=18.81 R/DD=7.261 | 2026 N=172 (28.7/mo) EV=+0.1321 PF=1.276 Sum=+22.72R DD=8.01 R/DD=2.836
- confirm 0.20 ATR: hist N=1630 (27.2/mo) EV=+0.0702 PF=1.143 Sum=+114.44R DD=32.88 R/DD=3.481 | 2026 N=176 (29.3/mo) EV=+0.1821 PF=1.393 Sum=+32.05R DD=8.01 R/DD=3.999
- confirm 0.15 ATR: hist N=1650 (27.5/mo) EV=+0.0613 PF=1.124 Sum=+101.11R DD=30.15 R/DD=3.354 | 2026 N=175 (29.2/mo) EV=+0.2030 PF=1.460 Sum=+35.53R DD=8.01 R/DD=4.433

## Limitations
- BTC only. ETH/SOL transfer must be checked before production.
- 2021-2025 is discovery/in-sample; 2026 Mar-Aug is reused forward-shadow.
- This LAB deliberately keeps retrace 0.60 and TTL20 because LAB033 rejected relaxing them.
- The frequency target is a frontier, not an instruction to maximize trade count.