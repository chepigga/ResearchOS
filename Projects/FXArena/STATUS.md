# FXArena Status

- **Project:** FXArena
- **Updated:** 2026-07-24
- **Lifecycle status:** ACTIVE_RESEARCH / P4c CAUSAL v001 FAILED PC5
- **Canonical live baseline and deploy exit:** `GEO*-TRAILING` q0.96/90d, N=3515, P0 exits
- **Canonical research baseline:** `GEO*-MONTHLY` top-4%, N=3535
- **ContPrimary:** unchanged
- **DD convention:** gross equity MaxDD is the gate metric; net MaxDD is diagnostic and must be labelled

## P4c Causal Exit v001

- **Gate 0a:** archived P4b replay PASS; 3535 trades, zero exit-time mismatches, +2256.511802R, gross DD 12.436807R
- **Gate 0b:** TB generator PASS 3535/3535, zero mismatches
- **Lookahead price:** 193 TB trades reached TP2 before causal activation; P4b -> P4c costs -145.708807R on MONTHLY
- **P4c MONTHLY:** +2110.802995R; gross DD 12.436807R; zero negative months
- **P4c TRAILING:** +2127.402776R versus P0 +1889.613320R; gross DD 10.618161R versus 14.415969R
- **Calendar:** one negative month, worst -2.040203R; all years positive
- **PC1:** PASS
- **PC2:** PASS
- **PC3:** PASS under preregistered <=1/42, worst >=-3R, all years positive
- **PC4:** PASS; paired moving-block block20/5000/seed2026072406, P(total>P0)=100%, DD-bad diagnostic 1.02%
- **PC5:** FAIL; spread x1.5 + commission 9pt + 0.05R slip gives +1903.209668R, below PC1 threshold +2078.574652R
- **Failure diagnosis:** commission 9 points alone reduces total to +2002.190324R and fails PC1; spread x1.5 alone still passes
- **Verdict:** deploy-exit = P0; P4c remains research-only and `trades_P4c_TRAILING_PINNED` was not created
- **Result checkpoint:** `Releases/v1.2/P4c_Causal_v001/`

## Flag-Replay v001.2

- Full-universe frozen TB flags remain validated: 291659 episodes, 57811 TB
- All 622 trailing-only flags were resolved
- Archived P4b trailing result remains research-only: +2277.306670R, gross DD 10.618161R
- P4b is not deployable because its retrospective TP3 convention is lookahead and P4c failed PC5

## Canonical baselines

- `GEO*-MONTHLY`: N=3535, +1848.874807R, gross DD 14.415969R; research comparisons only
- `GEO*-TRAILING`: N=3515, +1889.613320R, gross DD 14.415969R; live/E-exam/kill comparisons only
- Mixing the two baselines is a registry defect

## Closed fronts

- **Exit improvement:** closed under P4b/P4c frozen policies; deploy remains P0
- **Entry Lab v001:** F10 — `market @ D3+60s` retained
- **Session Lab v001:** F9 — no session edge worth filtering
- **Selection/Sizing Part A:** fixed 0.7/1.0/1.3 sizing failed SA2/SA5

## Next action

Use P0 `GEO*-TRAILING` for the August E-exam and live kill metrics. Do not tune P4c costs, activation time, TP levels or BE time on this sample. Any new exit rule requires a new frozen specification and genuinely new information.
