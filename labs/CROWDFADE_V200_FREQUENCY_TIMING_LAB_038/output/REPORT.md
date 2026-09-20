# LAB038 — v200 frequency through timing/occupancy

Frozen: Z2.05, M15 confirm .25ATR, retrace .60, pending TTL20, SL4.5, TP10, sign-flip cancel.

## Baseline
- hist N=1617 (26.9/mo) EV=+0.0845 PF=1.173 Sum=+136.62R DD=18.81 R/DD=7.261 time=596
- 2026 N=172 (28.7/mo) EV=+0.1321 PF=1.276 Sum=+22.72R DD=8.01 R/DD=2.836 time=64

## LAB038A — confirmation TTL
- 60m: hist N=1617 (26.9/mo) EV=+0.0845 PF=1.173 Sum=+136.62R DD=18.81 R/DD=7.261 time=596 | 2026 N=172 (28.7/mo) EV=+0.1321 PF=1.276 Sum=+22.72R DD=8.01 R/DD=2.836 time=64
- 90m: hist N=1627 (27.1/mo) EV=+0.0675 PF=1.136 Sum=+109.88R DD=30.46 R/DD=3.608 time=598 | 2026 N=171 (28.5/mo) EV=+0.1245 PF=1.263 Sum=+21.29R DD=11.19 R/DD=1.902 time=66
- 120m: hist N=1641 (27.4/mo) EV=+0.0465 PF=1.093 Sum=+76.24R DD=45.57 R/DD=1.673 time=603 | 2026 N=173 (28.8/mo) EV=+0.1075 PF=1.227 Sum=+18.59R DD=10.15 R/DD=1.832 time=68
- 180m: hist N=1648 (27.5/mo) EV=+0.0453 PF=1.090 Sum=+74.62R DD=43.16 R/DD=1.729 time=602 | 2026 N=171 (28.5/mo) EV=+0.0884 PF=1.186 Sum=+15.11R DD=9.91 R/DD=1.525 time=67

Selected TTL: **60m**

## LAB038B — max hold
- H24: hist N=1617 (26.9/mo) EV=+0.0845 PF=1.173 Sum=+136.62R DD=18.81 R/DD=7.261 time=596 | 2026 N=172 (28.7/mo) EV=+0.1321 PF=1.276 Sum=+22.72R DD=8.01 R/DD=2.836 time=64
- H18: hist N=1763 (29.4/mo) EV=+0.0518 PF=1.115 Sum=+91.29R DD=28.94 R/DD=3.154 time=815 | 2026 N=189 (31.5/mo) EV=+0.1301 PF=1.299 Sum=+24.60R DD=7.39 R/DD=3.330 time=84
- H12: hist N=1988 (33.1/mo) EV=+0.0580 PF=1.150 Sum=+115.33R DD=23.58 R/DD=4.890 time=1136 | 2026 N=218 (36.3/mo) EV=+0.0667 PF=1.179 Sum=+14.55R DD=11.80 R/DD=1.233 time=129
- H8: hist N=2221 (37.0/mo) EV=+0.0408 PF=1.123 Sum=+90.57R DD=26.25 R/DD=3.450 time=1499 | 2026 N=253 (42.2/mo) EV=+0.0591 PF=1.184 Sum=+14.95R DD=10.98 R/DD=1.361 time=178
- H6: hist N=2354 (39.2/mo) EV=+0.0223 PF=1.076 Sum=+52.53R DD=41.53 R/DD=1.265 time=1770 | 2026 N=271 (45.2/mo) EV=+0.0549 PF=1.195 Sum=+14.88R DD=10.62 R/DD=1.401 time=207

Selected hold: **24h**

## LAB038C — interaction corners
- C60_H24: hist N=1617 (26.9/mo) EV=+0.0845 PF=1.173 Sum=+136.62R DD=18.81 R/DD=7.261 time=596 | 2026 N=172 (28.7/mo) EV=+0.1321 PF=1.276 Sum=+22.72R DD=8.01 R/DD=2.836 time=64
- C180_H24: hist N=1648 (27.5/mo) EV=+0.0453 PF=1.090 Sum=+74.62R DD=43.16 R/DD=1.729 time=602 | 2026 N=171 (28.5/mo) EV=+0.0884 PF=1.186 Sum=+15.11R DD=9.91 R/DD=1.525 time=67
- C60_H12: hist N=1988 (33.1/mo) EV=+0.0580 PF=1.150 Sum=+115.33R DD=23.58 R/DD=4.890 time=1136 | 2026 N=218 (36.3/mo) EV=+0.0667 PF=1.179 Sum=+14.55R DD=11.80 R/DD=1.233 time=129
- C180_H12: hist N=2047 (34.1/mo) EV=+0.0226 PF=1.056 Sum=+46.26R DD=35.17 R/DD=1.316 time=1171 | 2026 N=222 (37.0/mo) EV=+0.0468 PF=1.120 Sum=+10.38R DD=16.64 R/DD=0.624 time=127
- C60_H6: hist N=2354 (39.2/mo) EV=+0.0223 PF=1.076 Sum=+52.53R DD=41.53 R/DD=1.265 time=1770 | 2026 N=271 (45.2/mo) EV=+0.0549 PF=1.195 Sum=+14.88R DD=10.62 R/DD=1.401 time=207
- C180_H6: hist N=2421 (40.4/mo) EV=-0.0005 PF=0.999 Sum=-1.12R DD=61.99 R/DD=-0.018 time=1799 | 2026 N=268 (44.7/mo) EV=+0.0677 PF=1.244 Sum=+18.13R DD=10.78 R/DD=1.682 time=203

## Limitations
- BTC only
- 2026 is reused forward-shadow
- shorter hold can increase frequency by changing occupancy and therefore later signal reachability