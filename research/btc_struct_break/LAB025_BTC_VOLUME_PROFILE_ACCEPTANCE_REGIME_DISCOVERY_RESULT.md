# LAB025 — BTC_VOLUME_PROFILE_ACCEPTANCE_REGIME_DISCOVERY result

Date: 2026-08-27
Prereg: a29446c48c645d0493bd1e81bba24266f908c652
Coverage addendum: 32bba1150004bf06096052379963d120381c2012
Final verdict: ONE_VOLUME_PROFILE_REPLICATION_SEED_FOUND__POC_MIGRATION_OPPOSED_BREAK_RETEST

## Data
Retained Binance BTCUSDT M1: 2024-01-01 through 2026-08-10, 1,371,240 M1 bars.
2024 discovery/calibration; 2025 temporal replication; 2026 shadow only.

## Volume profile
24h M1 volume-at-price approximation, 48 bins, M1 volume assigned to HLC3 bin, contiguous 70% value area around POC. POC migration compares current 24h profile to a 24h profile ending 6h earlier.

## Final seed
BREAK_RETEST + POC_MIGRATION OPPOSED

Definition: 24h POC migrates by at least 0.5 M15 ATR against the direction of the trade versus lagged profile.

2024: N51, EV +0.146R, PF 1.28.
2025: N37, EV +0.094R, PF 1.21.
2025 H1 EV +0.087R; H2 EV +0.099R.
2025 1.5x costs EV +0.064R.
Overlap with existing old-pivot core ~8.1%.

Side diagnostic:
2024 BUY +0.171R, SELL +0.113R.
2025 BUY -0.067R, SELL +0.192R.
Do not post-hoc select SELL; pooled state is the frozen replication seed.

2026 shadow: N35, EV -0.351R, PF 0.52. This is a serious warning and prevents promotion.

## Rejected technical false-pass
COMPRESSION SELL / ENTRY_LOCATION ABOVE_VAH had DISC2024 EV 2.22e-18R, a floating-point zero. It is treated as zero and fails the preregistered DISC EV >0 gate.

## Interpretation
Volume profile does provide information not captured by the old protected-pivot core. The opposing POC migration state is low-overlap and repeats across 2024 and 2025, but deteriorates sharply in 2026. It is a replication seed only, not confirmed production edge.

Next clean step: freeze BREAK_RETEST + POC_MIGRATION OPPOSED exactly as defined and test execution/portfolio admission without changing the 0.5 ATR migration threshold or selecting a side post hoc.