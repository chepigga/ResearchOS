# FXArena Status

- **Project:** FXArena
- **Updated:** 2026-07-24
- **Lifecycle status:** ACTIVE_RESEARCH / ENTRY LAB v001 CLOSED F10
- **Canonical live baseline:** C2 / ContPrimary unchanged
- **Frozen research control:** GEO* `MICRO30 / TP 2.0R / timeout 120 min`
- **Canonical GEO* metrics:** N=3535; Total net=+1848.87R; EV net=+0.523020R; gross MaxDD=14.415969R
- **DD convention:** gross equity MaxDD is the gate metric; net MaxDD is diagnostic and must be labelled

## Entry Lab v001

- **Control:** PASS with exact 3535/3535 signal order; entry/risk exact; 0 exit-time differences
- **P4b E0:** +2256.511802R; EV +0.638334R; gross MaxDD 12.436807R; 0 negative months
- **Tournament:** E1–E6 all FAIL; no arm passed EL1, EL2 or EL4
- **Best failed total:** E3 confirmation at +1847.72R, still -408.79R versus E0 and gross DD 16.699R
- **Pure limits:** E1/E2 fill 34.23%/31.63% and miss 64.05%/66.95% of TB signals
- **TB economics:** 1274 TB signals contribute +1599.24R, 70.9% of E0 total
- **Hybrids:** E4 +1551.17R; E5 +1829.93R; E6 +1648.59R; none passes paired bootstrap
- **EL4 law:** paired moving-block, block 20, 5000 iterations, seed 2026072404; P(total>E0)=0 for every candidate
- **Verdict:** F10 — `market @ D3+60s` remains optimal; Entry layer CLOSED
- **Promotion:** none; no v1.30 entry composition and no candidate tick validation
- **Result checkpoint:** `Releases/v1.2/EntryLab_v001/`

## Session & Time-of-Day Lab v001

- **Control:** PASS; full S1–S4 diagnostic completed on P0/P4b
- **Closest candidate:** S3 NY overlap contributed 42.48% of P4b top-5 DD losses at 25.205% trade share, but failed frozen T1 and 4/4-year T2 stability
- **Stage 2:** NOT RUN
- **Verdict:** F9 — no session edge worth filtering; keep all four blocks

## Selection & Sizing Lab v001

- **Part A:** fixed 0.7/1.0/1.3 sizing FAIL SA2/SA5 despite monotonic p_win economics
- **Part B:** STOP; trailing q0.96/90d did not reproduce historical monthly-top-4% PINNED
- **Promotion:** none; threshold convention remains unresolved

## Exit research

- **P4b observed:** +2256.51R; EV +0.6383R; gross MaxDD 12.436807R; 0 negative months
- **P4b computable gates:** RH1-RH3, RH5 and RH8 PASS
- **P4b unresolved deploy gates:** formal paired RH6 and exact spread-path RH7
- **P4b status:** STRONG CORE CONFIRMATION / FORMAL HOLD; NO-GO for EA
- **P5 standalone:** FAIL RH7

## Next action

Do not reopen entry timing, session filters or fixed sizing weights without genuinely new information. Priority remains exact ExecutionReplay/deploy closure for P4b, resolution of the selection-threshold convention, and then Exit v004 only after tick replay.
