# FXArena Project State — 2026-07-24

## Deployable canonical system

- **CONT selector:** GEO*-TRAILING q0.96 / trailing 90 days.
- **Canonical N:** 3515 historical trades.
- **Entry:** E0 market at D3+60 seconds.
- **Exit:** P0 TP2 / timeout 120 minutes.
- **Live reference:** `trades_GEOstar_TRAILING_PINNED.csv.gz` inside Closure v001.1.
- **ContPrimary:** unchanged.
- **REV:** not admitted.

## Confirmed/closed research fronts

### Closure v001.1
- MONTHLY research baseline: N=3535, +1848.874807R, gross DD 14.415969R.
- TRAILING live baseline: N=3515, +1889.613320R on archived 6pt basis, gross DD 14.415969R.
- Permanent baseline separation established.

### Entry Lab v001 — F10
- Market at D3+60s retained.
- Alternative entry timing/limit/retracement candidates failed.
- Entry front closed without genuinely new causal information.

### Session Lab v001 — F9
- No session veto justified.
- Hour-level filtering prohibited on current evidence.

### Selection & Sizing v001
- Fixed 0.7/1.0/1.3 sizing failed SA2/SA5.
- Current fixed sizing policy closed.

### P4b / Flag Replay / P4c / PC5-r
- TB generator reproduced 3535/3535 and all 622 trailing-only flags resolved.
- Archived P4b has retrospective flag lookahead.
- Causal P4c is economically strong but final measured fact-cost advantage was 1.0954x, below frozen 1.10x.
- PC5-r is final: P4c excluded from forward A/B and deployment.
- Third PC5 trial prohibited.

### REV Confirmation v001 — F11
- Strong exploratory REV result used episode-final `max_penetration_atr`, unavailable at D3.
- 23,467 episodes were shallow at D3 but deepened later and were retrospectively excluded.
- True causal 2023 control: N=2109, EV -0.287R, PF 0.657, 12/12 negative months.
- True causal 2024–2026H1: N=5830, EV -0.271R, PF 0.677, 29/30 negative months.
- Shallow-acceptance REV funnel closed; no magic 777003 module.

## Current next action

Run the August/live forward benchmark with ContPrimary + GEO*-TRAILING + P0 only. Preserve exact execution provenance, commission, spread and M1/tick data. New research must introduce genuinely new causal information and a new preregistered specification.

## Do not do

- Do not use GEO*-MONTHLY as a live benchmark.
- Do not deploy P4b or P4c.
- Do not reopen PC5 on these data.
- Do not implement the falsified REV shallow-acceptance funnel.
- Do not use final-episode penetration as a D3 feature.
- Do not tune session filters or entry timing on the same sample.
