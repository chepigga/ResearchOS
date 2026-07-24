# FXArena Status

- **Project:** FXArena
- **Updated:** 2026-07-24
- **Lifecycle status:** ACTIVE_RESEARCH / CLOSURE v001.1 PARTIAL PASS
- **Canonical live baseline:** `GEO*-TRAILING` q0.96/90d, N=3515
- **Canonical research baseline:** `GEO*-MONTHLY` top-4%, N=3535
- **ContPrimary:** unchanged
- **DD convention:** gross equity MaxDD is the gate metric; net MaxDD is diagnostic and must be labelled

## Closure v001.1 — monthly vs trailing

- **Control A monthly:** PASS signal-by-signal; N=3535, total +1848.874807R, gross MaxDD 14.415969R
- **Control B trailing:** PASS signal-by-signal; N=3515, total +1889.613320R, gross MaxDD 14.415969R
- **Official live pin:** `trades_GEOstar_TRAILING_PINNED.csv.gz`
- **Set relationship:** intersection 2893; monthly-only 642; trailing-only 622; Jaccard 69.59%
- **Permanent rule:** research comparisons use MONTHLY only; live/E-exam/kill metrics use TRAILING only; mixing is a defect
- **P4b transfer:** STOP before C1-C4 because frozen causal `tb_flag` covers only 2893/3515 trailing episodes
- **Missing P4b flag coverage:** 622 episodes, all trailing-only
- **P4b trailing pin:** NOT CREATED
- **P4b deployment:** blocked pending a new frozen exact P4/TB flag-replay session; no post-hoc flag inference
- **Result checkpoint:** `Releases/v1.2/Closure_v001_1/`

## Entry Lab v001

- **Control:** PASS with exact 3535/3535 signal order; entry/risk exact; 0 exit-time differences
- **Winner:** E0 `market @ D3+60s`, +2256.51R, gross MaxDD 12.436807R
- **Verdict:** F10 — Entry layer CLOSED; E1-E6 all failed EL1/EL2/EL4

## Session & Time-of-Day Lab v001

- **Verdict:** F9 — no session edge worth filtering; keep all four blocks
- **Stage 2:** NOT RUN

## Selection & Sizing Lab v001

- **Part A:** fixed 0.7/1.0/1.3 sizing FAIL SA2/SA5
- **Part B historical diagnosis:** monthly and trailing are different mechanisms, now canonized separately by Closure v001.1
- **Promotion:** none

## Exit research

- **Monthly P4b observed:** +2256.51R; EV +0.6383R; gross MaxDD 12.436807R; 0 negative months
- **Monthly P4b status:** strong research confirmation only
- **Live P4b status:** NOT VALIDATED because trailing-only causal flags are missing
- **P5 standalone:** FAIL RH7

## Next action

Run a new frozen **P4/TB Flag Replay Closure** on the full selector universe to produce causal 30-minute `tb_flag` for all trailing episodes. Only then rerun Closure C1-C4 and create `trades_P4b_TRAILING_PINNED`. Do not reopen entry timing, session filters, q0.96/90d, or fixed sizing weights.