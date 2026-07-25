# Research Register

Реєстр містить лише перевірені факти та посилання на збережені артефакти. Неперевірені числові результати не вносяться.

## Validated results

| Project | Laboratory | Version | Date | Status | Universe | Primary result | Verdict | Canonical configuration | Supersedes | Next step | Links |
|---|---|---|---|---|---|---|---|---|---|---|---|
| FXArena | GeoSweep / canonical geometry | v009 / Release v.1.1 | 2026-07-23 | VALIDATED | Pinned GEO* trades | N=3535; EV=+0.523020R; Total=+1848.87R; MaxDD=14.416R | Canonical geometry retained | `MICRO30 + TP2.0 + TO120` | prior C2 execution geometry | Exit Policy Tournament v002 over fixed entries | [Status](Projects/FXArena/STATUS.md) |
| FXArena | TimeoutSweep near-miss | v009b | 2026-07-23 | COMPLETED / CANDIDATE | GEO** TP2/60 pinned trades | N=3698; EV=+0.528467R; Total=+1954.27R; MaxDD=14.998R | Promoted to additional validation, not canonical | `MICRO30 + TP2.0 + TO60` | — | Closed after validation | [Status](Projects/FXArena/STATUS.md) |
| FXArena | GEO** Validation A+B | v001 / Release v.1.1 | 2026-07-23 | REJECTED | Paired pinned GEO* and GEO** sets | GS5 PASS; GS6 PASS; GS7 FAIL; Pillar B PASS | GEO** rejected as canonical replacement | GEO* remains canonical | GEO** provisional status | Do not re-optimize TP2/60 on same data | [Status](Projects/FXArena/STATUS.md) |
| Grok XAU | BH_SWEEP OOS validation | BH_OOS_002 v2 | 2026-07-24 | VALIDATED / PASS | XAUUSD M15, frozen OOS 2026-05-01..2026-07-23 | Step 0 N=88 B52/S36 EV=+0.275780R; OOS N=14 EV_net=+0.235714R; Sum=+3.300R; 3/3 positive months | PASS — demo only | AK47_FT v1.56 BH v1.55; EMA20; TP2R; TO96; cost -0.05R | `InpBH_Enable=false` research blocker | One controlled demo forward month at 0.30% risk; live prohibited | [Status](Projects/Grok_XAU/STATUS.md) · [Report](Projects/Grok_XAU/Reports/BH_OOS_002_v002_Report.md) |

## GS7 decision record

GEO** failed the preregistered block-bootstrap gates:

- `P(DD_GEO** > DD_GEO* + 0.5R) = 37.88%`, required `<5%`.
- `P(Total_GEO** > Total_GEO*) = 87.78%`, required `>=95%`.

The result is economically interesting but insufficiently stable to replace GEO*.

## Active research

| Project | Research line | Version | Status | Locked baseline | Objective | Discipline | Link |
|---|---|---|---|---|---|---|---|
| FXArena | Exit Policy Tournament | v002 | PREREGISTERED / FROZEN BEFORE RUN | Release v.1.1; GEO* `MICRO30 + TP2.0 + TO120`; N=3535 | paired tournament of ML, rule-based and simple global exit policies while entries, stop and risk remain frozen | P0 fixture diff first; one P1–P7 run; RH1–RH6; frozen Occam rule; no tuning | [Spec](Projects/FXArena/Specs/ExitPolicyTournament_TZ_v002.md) |
| Grok XAU | BH_SWEEP demo forward | v1.56 / BH v1.55 | READY | OOS PASS N=14, EV_net=+0.235714R | verify signal parity and execution costs for one complete demo month | no tuning; risk 0.30%; full lifecycle logging; live prohibited | [Status](Projects/Grok_XAU/STATUS.md) |
| Grok XAU | FT core deep oracle | FT_DEEP_001 | STEP 0 PASS / TESTER REGIME / FORMAL ORACLE BLOCKED RAW M5 | AK47_FT_EA_156 NYBUY + LONBUY defaults; source SHA256 `838b3e...8311b65` | determine persistent edge versus regime concentration over 2023-01..2026-07 | Step 0: NYBUY 18/17 with 83.33% overlap, LONBUY 7/7 with 100%; direct tester N=135 EV=+1.123733R but early half -0.007685R and late half +1.878012R => frozen-rule REGIME; no always-on scaling; final raw-bar oracle awaits tester-stream M5 export | [Spec](Projects/Grok_XAU/Specs/TZ-FT-DEEP-001.md) · [Tester report](Projects/Grok_XAU/Reports/FT_DEEP_001_Tester42m_2026-07-25.md) |

## Governance note

GitHub Release `v.1.1` is the current FXArena checkpoint. `Projects/FXArena/STATUS.md` is the operational source of truth; this register is the factual ledger.

For Grok XAU, `Projects/Grok_XAU/STATUS.md` is the operational source of truth. BH OOS PASS permits `InpBH_Enable=true` only on demo at the frozen 0.30% risk. FT_DEEP Step 0 is now passed. Direct 42-month tester evidence classifies FT as REGIME and rejects always-on scaling, but the formal raw-bar oracle remains blocked until the Strategy Tester stream export supplies full 2022-06..2026-07 M5 history without terminal-cache truncation.
