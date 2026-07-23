# Research Register

Реєстр містить лише перевірені факти та посилання на збережені артефакти. Неперевірені числові результати не вносяться.

| Project | Laboratory | Version | Date | Status | Universe | Primary result | Verdict | Canonical configuration | Supersedes | Next step | Links |
|---|---|---|---|---|---|---|---|---|---|---|---|
| FXArena | Research checkpoint import | v1.2 | 2026-07-23 | COMPLETED | 26 supplied artifacts | SHA256 manifest and governed classification | HISTORICAL IMPORT COMPLETE | C2 retained as live baseline per source reports | Pending import state | Verify Release v1.0 external assets | [Status](Projects/FXArena/STATUS.md) |
| FXArena | GeoSweep | v009 | 2026-07-22 | COMPLETED / FROZEN | Source report states 291,659 EURUSD M5 touch episodes; canonical GEO* trade universe 3,544 | GEO* selected as `MICRO30 / TP2.0R / timeout120m` | RESEARCH CANONICAL GEO* | MICRO30, TP 2.0R, timeout 120 min | Earlier geometry grids | Reproduce exact control from release assets | Import manifest |
| FXArena | TimeoutSweep | v009b | 2026-07-22 | COMPLETED_WITH_CONTROL_OVERRIDE | Frozen GEO* grid | Shorter timeouts tested; source report records user-approved control discrepancy | HISTORICAL RESULT / REPRODUCTION REQUIRED | Gates unchanged in source report | v009 timeout assumption | Independent reproduction | Import manifest |
| FXArena | TrendBirthExecution | v002 | 2026-07-22 | RESEARCH | Full GEO* universe of 3,544 episodes per source report | Universe blocker from v001 closed | CANDIDATE | Uses canonical GeoSweep trade source | v001 subset analysis | Reproduce execution result | Import manifest |
| FXArena | MarketGeometry | v001 | 2026-07-22 | RESEARCH | 2,939 frozen episodes in source report | Causal 15m/30m geometry tested; 60m excluded | CANDIDATE / LEAKAGE AUDIT PASS WITH EXCLUSION | 30m primary score selection | — | Validate on full GEO* universe | Import manifest |
| FXArena | OS Prototype | v001 | 2026-07-22 | RESEARCH | Monthly walk-forward OOS subset | Source report states PASS_NO_LEAKAGE | PROTOTYPE / NOT LIVE BASELINE | C2 unchanged | — | Economic and full-universe validation | Import manifest |
| FXArena | BattleOutcome RiskFirst | v002 | 2026-07-22 | RESEARCH | Tick-covered candidate subset | Threshold and cost replay tables supplied | CANDIDATE | Reversal execution with structural risk unit | — | Verify large candidate/trade assets | Import manifest |

## Integrity notes

- `FXArena_TrendBirthExecution_v001_report.md` is a verified empty file.
- `weights_schedule_C2.pkl` and `weights_schedule_C2.1.pkl` are byte-identical.
- Large CSV and binary artifacts are referenced through the checkpoint and GitHub Release `v1.0`; they are not reconstructed from chat history.
