# LAB040 — FAST_LANE_DISCRIMINATOR

Population: EXACT LAB039 FAST parity — completed-M5 signal cadence; first raw-price close crossing .30 ATR <=3h; sign-flip cancel; market entry; v200 exits.

- Raw historical: N=2492 EV=+0.0127 PF=1.026 Sum=+31.68R DD=44.27 R/DD=0.716
- Raw 2026: N=266 EV=-0.1028 PF=0.810 Sum=-27.35R DD=29.23 R/DD=-0.936

Passing simple causal rules: **0**

## Top robust rules

## Limitations
- 2021-2023 discovery, 2024-2025 internal validation, 2026 reused forward-shadow; 2026 is not pristine OOS.
- Rule family is restricted to simple one-feature unions or two-feature ANDs to reduce overfit.
- BTC only; ETH/SOL transfer remains mandatory before production.
- Exit shell is v200 to isolate entry discrimination; final hybrid must rerun full portfolio sequence.
- Confirmation uses the same LAB039 first-raw-close crossing approximation to the live timer/quote behavior; it is not exact tick replay.