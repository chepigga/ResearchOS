# LAB018 — OLD_PROTECTED_PIVOT_M15_EVENT_FAMILY_DISCOVERY result

Date: 2026-08-25
Prereg: e0203beb432a7c86b7a70e4bd4953a1e9306e42f
Operational freeze: e125b52a43a13bdf53929a7f162d1e21a19c9867
Verdict: POOLED_FAMILIES_FAIL__TWO_SIDE_SPECIFIC_REPLICATION_SEEDS_FOUND

## Pooled VAL results
- BREAK_RETEST control: N34, EV +0.293R, PF 1.80.
- COMPRESSION_RELEASE: N136, EV +0.055R, PF 1.11, 2/3 positive VAL years, 3.7% overlap with control. Fails pooled PF gate.
- FAILED_RESPONSE_RELEASE: N156, EV -0.050R, PF 0.90. Reject pooled.
- TWO_LEG_CORRECTION_RELEASE: N120, EV -0.091R, PF 0.83. Reject.

## Directional discovery seeds
### COMPRESSION_RELEASE SELL
- DEV: N63, EV +0.094R, PF 1.16.
- VAL: N60, EV +0.109R, PF 1.24.
- VAL years: 2023 +0.037R; 2024 +0.113R; 2025 +0.177R (3/3 positive).
- 1.5x cost: EV +0.079R, PF 1.17.
- essentially independent of BREAK_RETEST control.

### FAILED_RESPONSE_RELEASE BUY
- DEV: N80, EV +0.147R, PF 1.30.
- VAL: N82, EV +0.106R, PF 1.21.
- VAL years: 2023 +0.453R; 2024 +0.150R; 2025 -0.125R (2/3 positive).
- 1.5x cost: EV +0.076R, PF 1.15.
- 0% +/-8-bar overlap with COMPRESSION SELL in VAL.

These side choices are LAB018 discoveries, therefore replication seeds only, not confirmed selectors.

## Exploratory three-engine diagnostic
One global active position, combining:
1. existing BREAK_RETEST control;
2. COMPRESSION SELL;
3. FAILED_RESPONSE BUY.

DEV: N149, 37.3 trades/year, EV +0.125R, PF 1.24, MaxDD 11.92R.
VAL: N150, 50 trades/year, EV +0.123R, PF 1.27, MaxDD 10.21R.
VAL yearly: 2023 +0.419R; 2024 +0.089R; 2025 -0.034R.

This is diagnostic only because the asymmetric side selection was learned in LAB018.

## Next
Preregister OLD_PROTECTED_PIVOT_ASYMMETRIC_EVENT_REPLICATION_LAB_019 with exactly two frozen candidates:
- COMPRESSION_RELEASE SELL
- FAILED_RESPONSE_RELEASE BUY
No threshold changes.
