# LAB021 — OLD_PROTECTED_PIVOT_STRUCTURAL_REGIME_DISCOVERY result

Date: 2026-08-26
Prereg: 7a9e3e0af1b7298d49ec7cc7e97c7c942a565be1
Operational freeze: d352aeffa5b661a917a89a4f79ea714b2dbd35b1
Verdict: NO_NEW_BROAD_BREAK_REGIME__DISJOINT_COMPRESSION_ISLAND_REMAINS_PRIMARY_REPLICATION_SEED

## BREAK_RETEST VAL results
- R0 OLD CORE: N34, EV +0.293R, PF 1.80, MaxDD 4.36R.
- R1 DISJOINT MODERATE age16-21/risk2.5-3.0: N47, EV +0.017R, PF 1.03. Does not transfer from Compression to BREAK.
- R2 NESTED ANCESTOR: N281, EV -0.098R, PF 0.82. Reject.
- R3 TESTED AND HELD: N32, EV -0.438R, PF 0.32. Reject pooled.
- R4 PERSISTENT DISPLACEMENT: N116, EV -0.053R, PF 0.90. Reject.
- R5 ACCEPTED BALANCE AWAY: N45, EV -0.178R, PF 0.72. Reject.

No new pooled BREAK structural regime passes all discovery gates.

## Key falsification
A young latest pivot hiding an older still-unviolated structural ancestor does not recover edge. Therefore the latest-pivot age filter is not merely an implementation artifact.

## Surviving non-core structural seed
The exact LAB020 Compression surface remains the strongest disjoint candidate:
COMPRESSION SELL / pivot age 16–21 / riskATR 2.5–3.0
- DEV N42, EV +0.380R, PF 1.91
- VAL N26, EV +0.328R, PF 2.20
- 1.5x cost VAL EV +0.298R
- 2023 and 2025 positive; 2024 negative
Status: replication seed only.

## Next
Freeze and replicate the disjoint Compression island with exact pooled BUY/SELL blocker state, M1 execution parity, time-slice concentration, cost stress, and portfolio admission versus the two surviving engines.
