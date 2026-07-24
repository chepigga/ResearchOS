# FXArena Status

- **Project:** FXArena
- **Updated:** 2026-07-24
- **Lifecycle status:** ACTIVE_RESEARCH / FLAG-REPLAY v001.2 STOP-ALARM C3
- **Canonical live baseline:** `GEO*-TRAILING` q0.96/90d, N=3515
- **Canonical research baseline:** `GEO*-MONTHLY` top-4%, N=3535
- **ContPrimary:** unchanged
- **DD convention:** gross equity MaxDD is the gate metric; net MaxDD is diagnostic and must be labelled

## Flag-Replay v001.2

- **Frozen generator control:** PASS 3535/3535; 1274 archived TB flags reproduced with zero mismatches
- **Archived P4b replay:** PASS; 0 exit-time mismatches; total +2256.511802R
- **Full universe flags:** 291659 episodes; 57811 TB; pinned generator artifact created
- **Trailing coverage:** all 3515 episodes resolved; 1244 TB, including 196 of 622 trailing-only episodes
- **P0 trailing:** +1889.613320R; gross MaxDD 14.415969R; 0 negative months
- **P4b trailing candidate:** +2277.306670R; gross MaxDD 10.618161R; 1 negative month
- **Transfer gates:** C1 PASS; C2 PASS; C3 FAIL; C4 PASS with P(total>P0)=100%
- **C3 failure:** February 2023 = -2.040203R versus P0 +1.266512R
- **Verdict:** STOP-ALARM / NOT_PROMOTED; `trades_P4b_TRAILING_PINNED` not created
- **Result checkpoint:** `Releases/v1.2/FlagReplay_v001_2/`
- **Separate deploy issue:** archived P4b uses the 30-minute flag retrospectively; exact causal P4c requires a new frozen specification

## Closure v001.1 — monthly vs trailing

- **Control A monthly:** PASS signal-by-signal; N=3535, total +1848.874807R, gross MaxDD 14.415969R
- **Control B trailing:** PASS signal-by-signal; N=3515, total +1889.613320R, gross MaxDD 14.415969R
- **Official live pin:** `trades_GEOstar_TRAILING_PINNED.csv.gz`
- **Permanent rule:** research comparisons use MONTHLY only; live/E-exam/kill metrics use TRAILING only; mixing is a defect

## Closed fronts

- **Entry Lab v001:** F10 — `market @ D3+60s` retained; Entry layer closed
- **Session Lab v001:** F9 — no session edge worth filtering
- **Selection/Sizing Part A:** fixed 0.7/1.0/1.3 sizing failed SA2/SA5

## Exit research

- **Monthly P4b:** +2256.51R; gross MaxDD 12.436807R; research-confirmed
- **Trailing P4b:** economically strong, but frozen transfer failed C3 and is not pinned
- **P5 standalone:** FAIL RH7

## Next action

Do not relax C3 or tune the flag in this session. Choose a new preregistered path: (1) adjudicate whether one isolated negative month is an acceptable deploy gate under a new rule, or (2) test a strictly causal P4c that activates TP3 only after the flag is observable. Exact tick/execution replay remains mandatory before EA deployment.
