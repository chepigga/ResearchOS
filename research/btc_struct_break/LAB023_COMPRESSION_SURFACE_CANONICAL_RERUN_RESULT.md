# LAB023 — COMPRESSION SURFACE CANONICAL RERUN result

Date: 2026-08-26
Prereg: 3926d5cba97dea42dfae31bfd98b7c8715510a1f
Queue freeze: 469fde1396bd6ecff6fff209d153e6414c54862d
Verdict: CANONICAL_COMPRESSION_SURFACE_REBUILT_WITH_FULL_PROVENANCE__NO_ROBUST_NEW_CELL

## Provenance
- exact BTC M15 source SHA256 retained in bundle
- 242,700 canonical M15 rows
- 9,298 raw compression releases
- 8,600 direction-deduplicated events
- 2,599 accepted pooled BUY+SELL family trades
- 1,236 accepted SELL trades
- 1,363 accepted BUY trades
- exact SELL cell-to-trade lineage persisted
- lineage SHA256: 669d3eabf97095ab34673fc2efb416ee7a207b21269174ba96ac3933d1700949
- full compute script persisted

## Fresh canonical surface
No cell with >=20 trades in both DEV and VAL has positive DEV and VAL expectancy.

Cells with DEV>0 and VAL>0 are all small:
- age 22–31 / riskATR >5: DEV N18 EV +0.390R; VAL N19 EV +0.040R, only 1/3 positive VAL years.
- age 16–21 / riskATR 2.5–3.0: DEV N16 EV +0.015R; VAL N10 EV +0.430R, 2/3 positive VAL years; 2026 shadow N2 EV -1.06R.
- age 22–31 / riskATR 3.72–5: DEV N15 EV +0.240R; VAL N8 EV +0.303R, 2/3 positive VAL years.

## Old LAB020 island
The old reported island (age 16–21 / riskATR 2.5–3.0) does not reproduce as a broad stable regime under the new explicit canonical queue.
Fresh result:
- DEV N16, EV +0.015R, PF 1.03
- VAL N10, EV +0.430R, PF 2.78
- 1.5x cost VAL EV +0.400R
- 2026 shadow N2, EV -1.060R

This is too small and unstable to promote.

## Conclusion
The full canonical rerun removes the LAB020 provenance ambiguity but does not reveal a robust new compression surface cell with adequate sample size and DEV->VAL stability.

The current strongest compression engine remains the already replicated OLD PROTECTED PIVOT + COMPRESSION RELEASE SELL lineage. Frequency should not be increased by selecting a new age/risk surface cell from LAB023 without a separate frozen replication.
