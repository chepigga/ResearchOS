# FXArena Status

- **Project:** FXArena
- **Updated:** 2026-07-23
- **Lifecycle status:** ACTIVE / VALIDATED BASELINE
- **Canonical release:** `v.1.1`
- **Canonical model:** C2
- **Canonical geometry:** GEO* = `MICRO30 + TP2.0 + TO120`
- **Pinned baseline metrics:** N=3535; EV=+0.523020R; Total=+1848.87R; MaxDD=14.416R
- **Canonical verdict:** VALIDATED candidate geometry; retained after GEO** validation
- **Candidate GEO**:** `MICRO30 + TP2.0 + TO60`
- **GEO** verdict:** REJECTED AS CANONICAL after GS7 block-bootstrap failure; retained only as documented observational prior
- **GEO** pinned metrics:** N=3698; EV=+0.528467R; Total=+1954.27R; MaxDD=14.998R
- **Validation summary:** GS5 PASS; GS6 PASS; GS7 FAIL; Pillar B PASS; overall Validation A+B FAIL
- **GS7 reason:** P(DD_GEO** > DD_GEO* + 0.5R)=37.88% versus required <5%; P(Total_GEO** > Total_GEO*)=87.78% versus required >=95%
- **Forward state:** ContPrimary C2 remains under forward/exam governance; no silent model or threshold changes
- **Current research direction:** Regression Heads / Adaptive Exit Layer over unchanged GEO* entries
- **Do not repeat:** global timeout grid on the same data; TP2/60 re-optimization on the same sample
- **Primary checkpoint:** GitHub Release `v.1.1`
- **Source-of-truth order:** this file -> `RESEARCH_REGISTER.md` -> laboratory reports/specifications -> release manifest
