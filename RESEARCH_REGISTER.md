# Research Register

Реєстр містить лише перевірені факти та посилання на збережені артефакти. Неперевірені числові результати не вносяться.

| Project | Laboratory | Version | Date | Status | Universe | Primary result | Verdict | Canonical configuration | Supersedes | Next step | Links |
|---|---|---|---|---|---|---|---|---|---|---|---|
| FXArena | Exit Policy Tournament | v002 | 2026-07-23 | COMPLETED / FROZEN | 3535 pinned GEO* episodes | P0 exact replay; P4 best economy at +2134.36R, EV +0.6038R, 0 negative months | FORMAL FAIL — NO P1-P7 WINNER | Frozen P0-P7 specification; P0 GEO* fixture | ExitPolicyTournament_TZ_v001 is ignored | Run one-candidate P4b confirmation | [Release](Projects/FXArena/Releases/v1.2/ExitPolicyTournament_v002/RELEASE_NOTES.md) |
| FXArena | P4 TB Deep Dive / P4b Research | v001 | 2026-07-23 | RESEARCH / FROZEN CANDIDATE | Same 3535 episodes; TB 1274, non-TB 2261 | P4b +2256.51R, EV +0.6383R, MaxDD 13.284R, PF 4.297, 0/42 negative months | EXPLORATORY GO FOR CONFIRMATION; NO-GO FOR EA | TB -> frozen P4; non-TB -> frozen P5 | No live/canonical strategy | Exact RH1-RH6 v003 + untouched replication | [Report](Projects/FXArena/Releases/v1.2/ExitPolicyTournament_v002/FXArena_P4b_Research_v001_Report.md) |
| FXArena | Research checkpoint import | v1.2 | 2026-07-23 | COMPLETED | 26 supplied artifacts | SHA256 manifest and governed classification | HISTORICAL IMPORT COMPLETE | C2 retained as live baseline per source reports | Pending import state | Verify external release assets | [Status](Projects/FXArena/STATUS.md) |
| FXArena | GeoSweep | v009 | 2026-07-22 | COMPLETED / FROZEN | Source report states 291,659 EURUSD M5 touch episodes; canonical GEO* trade universe 3,544 | GEO* selected as `MICRO30 / TP2.0R / timeout120m` | RESEARCH CANONICAL GEO* | MICRO30, TP 2.0R, timeout 120 min | Earlier geometry grids | Independent control reproduction | Import manifest |
| FXArena | TimeoutSweep | v009b | 2026-07-22 | COMPLETED_WITH_CONTROL_OVERRIDE | Frozen GEO* grid | Shorter timeouts tested; source report records user-approved control discrepancy | HISTORICAL RESULT / REPRODUCTION REQUIRED | Gates unchanged in source report | v009 timeout assumption | Independent reproduction | Import manifest |
| FXArena | TrendBirthExecution | v002 | 2026-07-22 | RESEARCH | Full GEO* universe of 3,544 episodes per source report | Universe blocker from v001 closed | CANDIDATE | Uses canonical GeoSweep trade source | v001 subset analysis | Reproduce execution result | Import manifest |
| FXArena | MarketGeometry | v001 | 2026-07-22 | RESEARCH | 2,939 frozen episodes in source report | Causal 15m/30m geometry tested; 60m excluded | CANDIDATE / LEAKAGE AUDIT PASS WITH EXCLUSION | 30m primary score selection | — | Validate on full GEO* universe | Import manifest |
| FXArena | OS Prototype | v001 | 2026-07-22 | RESEARCH | Monthly walk-forward OOS subset | Source report states PASS_NO_LEAKAGE | PROTOTYPE / NOT LIVE BASELINE | C2 unchanged | — | Economic and full-universe validation | Import manifest |
| FXArena | BattleOutcome RiskFirst | v002 | 2026-07-22 | RESEARCH | Tick-covered candidate subset | Threshold and cost replay tables supplied | CANDIDATE | Reversal execution with structural risk unit | — | Verify large candidate/trade assets | Import manifest |

## Integrity notes

- Exit Policy Tournament v002 P0 replay matched all 3535 exits; no policy P1-P7 passed every frozen gate.
- P4b is post-selection research and is not represented as a formal tournament PASS.
- Exact source archive hashes are recorded in `Projects/FXArena/Releases/v1.2/ExitPolicyTournament_v002/SOURCE_ARTIFACTS_SHA256.csv`.
- `FXArena_TrendBirthExecution_v001_report.md` is a verified empty file.
- `weights_schedule_C2.pkl` and `weights_schedule_C2.1.pkl` are byte-identical.
