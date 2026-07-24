# FXArena Status

- **Project:** FXArena
- **Updated:** 2026-07-24
- **Lifecycle status:** ACTIVE_RESEARCH / REV CONFIRMATION F11 CLOSED
- **Canonical live baseline and deploy exit:** `GEO*-TRAILING` q0.96/90d, N=3515, P0 exits
- **Canonical research baseline:** `GEO*-MONTHLY` top-4%, N=3535
- **ContPrimary:** unchanged
- **DD convention:** gross equity MaxDD is the gate metric; net MaxDD is diagnostic and must be labelled

## REV_Confirmation v001 — causal shallow-acceptance court

- **2023 provenance scenario:** (a), treated as out-of-dataset control under the documented artifact chronology
- **Event engine:** `FXArena LevelBattleEngine v003 EVENT_STREAM`; 1,196,467 rows, 106,079 `ACCEPTANCE_CONFIRMED`, coverage 2023-01-02 through 2026-07-17
- **Production funnel:** causal `max_penetration_seen@D3 <= 1.0 ATR`, reconstructed only from M1 available before D3
- **RC1 2023:** N=2109; EV -0.287213R; PF 0.6570; total -605.733R
- **RC1 stability:** 12/12 negative months; H1 -280.523R; H2 -325.209R
- **Drawdown:** gross MaxDD 184.000R; net MaxDD 611.473R
- **RC1 gates:** N PASS; EV FAIL; PF FAIL; calendar FAIL; both halves FAIL
- **Verdict:** `F11_SHALLOW_ACCEPTANCE_REV_FALSIFIED`
- **Frozen stop:** RC2-RC6 NOT EXECUTED; no REV EA module
- **Causal audit:** the old strong reference aligned with final-episode `Rounds.max_penetration_atr`; 23,467 episodes were shallow at D3 but deepened beyond 1 ATR later and were excluded using future information
- **Original-period causal diagnostic:** 2024-2026H1 N=5830, EV -0.271R, PF 0.677, 29/30 negative months
- **Result checkpoint:** `Releases/v1.2/REV_Confirmation_v001/`

## PC5-r Resolution v001 — final paired cost court

- **Gate 0:** PASS; exact 3515/3515 pair, P0 and P4c zero exit-time mismatches at 6pt/x1.0
- **Design:** full paired 4x2x2 grid; commission 5/6/7.5/10pt, spread x1/x1.5, P4c BE slip 0/0.05R
- **Frozen BE set:** 1070 actual P4c BE exits; P0 has no BE branch
- **Central cell 7.5pt/x1.5/0.05R:** P0 +1779.792484R; P4c +1965.815894R; ratio 1.1045x; DD 14.436R vs 10.820R
- **PR1:** PASS
- **PR2:** PASS
- **PR4:** PASS; paired block20/5000/seed2026072407, P(total P4c>P0)=99.98%, DD-bad diagnostic 1.50%
- **Extreme diagnostic 10pt/x1.5/0.05R:** advantage still 1.1110x; DD PASS
- **Fact cell 5pt/x1.0/0.05R:** P0 +1931.350808R; P4c +2115.640260R; ratio 1.0954x; DD PASS
- **PR5:** FAIL because factual-cost advantage is +9.54%, below frozen +10% gate
- **Verdict:** `P4C_CLOSED_FINAL__DEPLOY_EXIT_P0`
- **Third PC5 retrial:** permanently prohibited
- **Result checkpoint:** `Releases/v1.2/PC5r_Resolution_v001/`

## P4c Causal Exit v001

- Archived P4b lookahead price: 193 early TP2 trades and +145.708807R retrospective benefit
- Base causal P4c TRAILING: +2127.402776R; gross DD 10.618161R
- PC1-PC4 passed before final paired-cost adjudication
- Superseded for deploy decision by PC5-r final verdict; P4c remains research-only

## Canonical baselines

- `GEO*-MONTHLY`: N=3535, +1848.874807R, gross DD 14.415969R; research comparisons only
- `GEO*-TRAILING`: N=3515, +1889.613320R at 6pt archived basis, gross DD 14.415969R; live/E-exam/kill comparisons only
- Measured 5pt paired fact cell: P0 +1931.350808R
- Mixing MONTHLY and TRAILING baselines is a registry defect

## Closed fronts

- **REV shallow-acceptance funnel:** F11 — causal D3 mechanism falsified; no EA module
- **Exit improvement:** closed permanently under P4b/P4c and PC5-r; deploy exit P0
- **Entry Lab v001:** F10 — `market @ D3+60s` retained
- **Session Lab v001:** F9 — no session edge worth filtering
- **Selection/Sizing Part A:** fixed 0.7/1.0/1.3 sizing failed SA2/SA5

## Next action

Use P0 `GEO*-TRAILING` / ContPrimary for the August E-exam, forward benchmark and live kill metrics. Do not implement the falsified REV funnel, reuse final-episode penetration, reopen PC5, or modify P4c/P0 on these data.
