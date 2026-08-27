# LAB025 M1 coverage operational addendum

Date: 2026-08-27
Status: FROZEN BEFORE ANY LAB025 PnL CALCULATION

The retained Binance BTCUSDT M1 archive available to this research line covers 2024 onward, so the original DEV<=2022 / VAL 2023-2025 split cannot be evaluated with genuine M1 volume-at-price data.

To avoid substituting M15 volume or fabricating earlier M1 data, LAB025 uses:
- DISCOVERY/CALIBRATION: calendar 2024
- TEMPORAL REPLICATION: calendar 2025
- SHADOW: 2026, excluded from promotion verdict

All volume-profile definitions, 24h/lagged-6h windows, 48 price bins, value-area 70%, LVN/HVN percentiles, POC migration thresholds, and entry/event populations remain exactly as preregistered in commit a29446c48c645d0493bd1e81bba24266f908c652.

Promotion/discovery gates are adapted only for the shorter evaluable history:
1. 2024 EV >0
2. 2025 EV >= +0.08R
3. 2025 PF >=1.15
4. 2025 N >=15
5. positive at 1.5x cost in 2025
6. 2025 H1 and H2 are not both negative; prefer 2/2 positive halves
7. overlap with existing two-engine core <=50% within +/-8 M15 bars

Any passing state remains a replication seed, not confirmed production edge. 2026 remains shadow only.