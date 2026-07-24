# FXArena P4c Causal Exit v001

## Verdict

**FAIL_P4C_DEPLOY_GATES__DEPLOY_EXIT_P0**

## Gate 0 controls

- P4b archived replay: **PASS**, N=3535, exit mismatches 0, total +2256.511802R, gross DD 12.436807R.
- TB generator: **PASS 3535/3535**, mismatches 0.

## Frozen P4c law

- Start every trade with TP2 and MICRO30 SL.
- At `entry+30m`, if `tb_flag=true` and the position is still open, expand TP2->TP3.
- If TP2 completed before activation, the trade stays closed; no re-entry.
- non-TB remains TP2 + BE@60 + TO120.
- Archived generator snapshot remains `decision_3bar_time+35m` under M5 `label=right, closed=left`, exactly as preregistered.

## Price of archived lookahead — MONTHLY

- Pre-30m TP2 completions with `tb_flag=true`: **193**.
- Policy divergences: **193**.
- P4b total: **+2256.511802R**.
- P4c total: **+2110.802995R**.
- Delta P4c-P4b: **-145.708807R**; EV delta -0.041219R/signal.
- Gross DD: P4b 12.436807R -> P4c 12.436807R; delta +0.000000R.

| Year | affected N | P4b | P4c | delta |
|---|---:|---:|---:|---:|
| 2023 | 29 | +370.731R | +342.923R | -27.807R |
| 2024 | 47 | +681.219R | +646.928R | -34.291R |
| 2025 | 70 | +744.649R | +695.825R | -48.824R |
| 2026 | 47 | +459.913R | +425.127R | -34.786R |

## TRAILING deploy court

| Metric | P0 | P4c |
|---|---:|---:|
| N | 3515 | 3515 |
| Total | +1889.613320R | +2127.402776R |
| EV | +0.537586R | +0.605235R |
| Gross MaxDD | 14.415969R | 10.618161R |
| Negative months | 0 | 1 |
| Worst month | +1.266512R | -2.040203R |
| All years positive | True | True |

| Gate | PASS |
|---|---|
| PC1 | True |
| PC2 | True |
| PC3 | True |
| PC4 | True |
| PC5 | False |

PC4: paired moving-block, block 20, 5000 iterations, shared indices, seed `2026072406`. `P(total P4c>P0)`=100.00%; diagnostic `P(DD P4c>P0+0.5)`=1.02%.

## PC5 exact cost inheritance

Because P4c exit structure differs from archived P4b, the spread leg was recalculated on the raw M1 spread path rather than inherited blindly. Central stress: spread x1.5, commission 9 points, and 0.05R slip on 1070 changed BE exits.

- Stressed total: **+1903.209668R** versus PC1 threshold +2078.574652R.
- Stressed gross DD: **10.819815R** versus PC2 threshold 14.915969R.
- Spread-stress exit-time changes versus base P4c: **195**.
- PC5: **FAIL**.

## PC5 cost decomposition

| Variant | Total R | Delta vs base | Gross DD | PC1 | PC2 |
|---|---:|---:|---:|---|---|
| BASE | +2127.403R | +0.000R | 10.618R | PASS | PASS |
| COMMISSION_9_ONLY | +2002.190R | -125.212R | 10.618R | FAIL | PASS |
| COMMISSION_9_PLUS_BE_SLIP_0.05 | +1948.690R | -178.712R | 10.768R | FAIL | PASS |
| SPREAD_X1.5_ONLY | +2081.922R | -45.481R | 10.670R | PASS | PASS |
| CENTRAL_PC5_SPREAD_X1.5_COMM9_SLIP0.05 | +1903.210R | -224.193R | 10.820R | FAIL | PASS |

- Base P4c headroom above PC1 is only **+48.828R**.
- Raising commission from 6 to 9 points costs **125.212R** and fails PC1 before BE-slip or spread stress.
- Approximate commission headroom is **1.17 additional points** above the frozen 6-point baseline, assuming unchanged exits.
- Therefore PC5 failure is primarily commission sensitivity; spread x1.5 alone still passes PC1-PC2.

## Promotion

- `trades_P4c_TRAILING_PINNED.csv.gz`: **NOT CREATED**.
- `trades_P4c_MONTHLY.csv.gz`: created as research fixture.
- ContPrimary untouched; no feature/threshold/TP/BE tuning; no re-entry.
