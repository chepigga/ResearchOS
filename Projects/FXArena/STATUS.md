# FXArena Status

- **Project:** FXArena
- **Updated:** 2026-07-23
- **Lifecycle status:** ACTIVE / VALIDATED BASELINE / PREREGISTERED LAB
- **Canonical release:** `v.1.1`
- **Canonical model:** C2
- **Canonical geometry:** GEO* = `MICRO30 + TP2.0 + TO120`
- **Pinned baseline metrics:** N=3535; EV=+0.523020R; Total=+1848.87R; MaxDD=14.416R
- **Canonical verdict:** GEO* retained after GEO** validation
- **Rejected candidate:** GEO** = `MICRO30 + TP2.0 + TO60`
- **GEO** verdict:** REJECTED AS CANONICAL after GS7 block-bootstrap failure; retained only as documented observational prior
- **Validation summary:** GS5 PASS; GS6 PASS; GS7 FAIL; Pillar B PASS; overall Validation A+B FAIL
- **Forward state:** ContPrimary v1.20 / C2 demo-forward remains isolated and must not be changed by research experiments

## Active laboratory

- **Laboratory:** Exit Policy Tournament v002
- **Status:** PREREGISTERED / FROZEN BEFORE RUN
- **Spec:** [ExitPolicyTournament_TZ_v002.md](Specs/ExitPolicyTournament_TZ_v002.md)
- **Supersedes:** v001, which was never run
- **Design:** paired P0–P7 tournament on the same 3535 pinned GEO* entries; exit is the only changed variable
- **Candidates:** regression heads, TB flag, global BE at 60 minutes, 50% partial at +1R, and BE+partial
- **Control rule:** P0 must match the pinned GEO* fixture signal-by-signal before any candidate run
- **Gates:** RH1–RH6 plus frozen Occam rule
- **Run discipline:** one run, no tuning, no override
- **Target checkpoint:** Release `v1.2` with mandatory `MANIFEST_SHA256`
- **Execution state:** specification committed; actual run awaits verified availability of Release v.1.1 assets, `wf_toolkit`, full-universe fixture and M1 tradingticks data in the active runtime

## Prohibitions

- do not rerun the global timeout grid on the same data;
- do not re-optimize TP2/60 on the same sample;
- do not use TP >3.0 or TO >120 in v002;
- do not touch ContPrimary v1.20 demo-forward.

## Source-of-truth order

1. this file;
2. `RESEARCH_REGISTER.md`;
3. frozen lab specification;
4. completed reports and release manifest.
