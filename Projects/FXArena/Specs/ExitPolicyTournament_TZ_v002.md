# Exit Policy Tournament v002

- **Project:** FXArena
- **Date:** 2026-07-23
- **Version:** v002
- **Status:** PREREGISTERED / FROZEN BEFORE RUN
- **Supersedes:** `ExitPolicyTournament_TZ_v001` (v001 was not run; delete or ignore if found)
- **Run discipline:** one run, no tuning, no silent overrides
- **Pinned source:** ResearchOS GitHub Release `v.1.1` only
- **Forward isolation:** ContPrimary v1.20 demo-forward must not be touched

## 0. Research question and priors

### Research question

Which exit policy on the PINNED GEO* entries maximizes total R without worsening the drawdown profile, and do ML regression heads justify their complexity versus simple global rules?

### Documented priors — not evidence

- **P-A:** edge is concentrated in the first hour (`v009b`); fixed TO60 is closed by GS7 because of a heavy DD tail.
- **P-B:** TB filters separate tail episodes (`TB v002`); winner's curse has not been removed.
- **P-C:** clustered errors in predictive exits during regime weeks are a known path to the same DD tail; simple mechanical policies such as break-even and partial exit do not have model-error risk.

### Honest framing

The statement “global exit changes do not work” is not proven. GEO* itself is a global exit change that passed the gates. Only TO60 has been shown to have a heavy tail. Therefore this is a tournament, not a prior commitment to adaptive exits.

## 1. Paired tournament design — one variable only: exit

### Fixed entries

Exactly 3,535 PINNED GEO* trades from:

`trades_GEOstar_MICRO30_TP2_TO120_PINNED.csv.gz`

The following remain frozen:

- entry selection;
- selection model;
- risk layer;
- MICRO30 stop;
- trade ordering and chronology.

### Regression heads for P1–P3

- `h_mfe`: predicted `MFE_r` over 120 minutes;
- `h_mae`: predicted `MAE_r` before MFE;
- `h_tmfe`: predicted minutes to MFE.

Training protocol:

- walk-forward ridge regression;
- 42 windows;
- train boundary: episode horizon end must be earlier than the first D3 of the test month;
- train on the complete universe with checksum count `291659`, not on the selected 3,535 trades;
- targets built in one M1 pass and cached;
- OOS Spearman and R² are diagnostics only, not acceptance gates (F3).

### Exit policies

All constants below are frozen. Tuning is prohibited.

#### P0 — baseline

`TP2.0 / TO120`, identical to PINNED GEO*.

Pinned control metrics:

- Total = `+1848.87R`
- MaxDD = `14.416R`
- N = `3535`

#### Adaptive / ML

- **P1 adaptive TP:** `tp_i = clip(0.8 * h_mfe_i, 1.0, 3.0)`, `TO120`.
- **P2 adaptive timeout:** `to_i = clip(1.5 * h_tmfe_i, 45, 120)`, `TP2.0`.
- **P3 combined adaptive:** P1 + P2.

#### Rule-based prior-B

- **P4 TB flag:** causal in-trade flag using first 30 minutes only: `EFFICIENCY_5`, `BB_EXP`, `RANGE_EXP`.
- Flagged trades: `TP3.0 / TO120`.
- No flag: P0.

#### Simple global policies

- **P5 time-based break-even:** at minute 60 move stop to entry, never worse than BE; otherwise P0.
- **P6 partial:** close 50% at `+1.0R`, remaining 50% runs to `TP2.0 / TO120`; all metrics in units of full initial risk.
- **P7 combined simple:** P5 + P6. No variants.

### Execution engine

- reference implementation: M1 loop replay;
- final reported numbers must come only from the loop replay;
- for P5/P6/P7 intrabar ordering is conservative: SL/BE before TP in the same M1 bar;
- use the same stop-first principle as TB v002.

## 2. Pre-registered gates

Baseline for every comparison is PINNED GEO*.

A candidate must pass all applicable gates.

### RH1 — economic improvement

`Total R >= 1848.87 * 1.03 = 1904.3361R`

### RH2 — drawdown ceiling

`MaxDD <= 14.916R`

### RH3 — calendar stability

- negative months `<= 1 / 42`;
- worst month `>= -3R`;
- all years `> 0R`.

### RH4 — GS5 reverse chronology

- degradation `<= 20%`;
- P1–P3: retrain reverse-chronology heads;
- P4–P7: reverse chronology of economics only.

### RH5 — GS6 permutation-200

- P1–P4: shuffle per-episode parameters within month;
- P5–P7: N/A and must be explicitly reported as such.

### RH6 — block bootstrap

Minimum `5,000` paired block-bootstrap iterations.

Both conditions must hold:

1. `P(DD_candidate > DD_GEO* + 0.5R) < 0.05`
2. `P(Total_candidate > Total_GEO*) >= 0.95`

## 3. Frozen verdict rule

Among policies that pass every applicable gate, choose the one with the largest Total R.

### Occam rule

If a simple policy (P5–P7) and a complex policy (P1–P4) both pass and their Total R differs by no more than 3 percentage points, the simple policy wins because it is cheaper to implement in the EA, has no ML degradation risk and does not depend on head quality.

Adaptive heads must beat the best simple policy that passed the gates. Beating only GEO* is insufficient to justify complexity.

### F8 terminal verdict

If no candidate passes all gates:

> Exit improvement on GEO* entries cannot be separated from the drawdown tail.

Then:

- close the exit-policy question;
- retain GEO* unchanged;
- report exactly where each candidate failed: head quality, policy economics or tail stability.

## 4. Discipline and controls

1. Run P0 control first.
2. P0 must match PINNED GEO* signal-by-signal against the fixture.
3. Any mismatch means STOP and debug.
4. Overrides are prohibited.
5. Run P1–P7 exactly once after control passes.
6. Any new constant or policy requires a new specification.
7. Existing falsifications remain active: F1–F7 and TP2/60-closed.
8. `TP > 3.0` and `TO > 120` are out of scope and prohibited.

## 5. Required inputs

- ResearchOS `v.1.1 COMPLETE.zip`;
- `wf_toolkit`;
- M1 data from `tradingticks`;
- complete universe matching checksum count `291659`;
- pinned GEO* trades fixture with N=3535.

## 6. Required artifacts

- regression-head weights by WF window;
- cached M1 targets;
- P0 control diff;
- trade-level outputs for P1–P7;
- monthly and yearly summaries;
- GS5 outputs;
- GS6 permutation-200 outputs for P1–P4;
- paired block-bootstrap CSV with at least 5,000 iterations;
- diagnostics for heads: OOS Spearman and R²;
- final report;
- release `v1.2` package;
- `MANIFEST_SHA256` is mandatory.

## 7. Required report verdict table

For P0–P7 report:

- N;
- Total R;
- EV;
- MaxDD;
- negative months;
- worst month;
- annual totals;
- RH1–RH6 individually;
- complexity class: SIMPLE or COMPLEX;
- formal verdict;
- practical verdict;
- failure location if rejected.

## 8. Governance

- This specification is frozen before the first run.
- GitHub is the source of truth.
- No result becomes canonical until committed with artifacts, hashes, report and register update.
- After completion update `STATUS.md`, `BACKLOG.md`, `RESEARCH_REGISTER.md`, and create Release `v1.2` if the artifact package is complete.
