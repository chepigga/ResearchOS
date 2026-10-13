# LAB253 — HANDOFF / RECOVERY / BACKLOG (2026-10-13)

## User directive
Start a new conversation branch and CONTINUE actual historical research, rather than demand exact MQL5 parity. The target: take historical BTC M5, original canonical CrowdFade v157 raw engine events, and user-supplied `trendlines.py` and compare unchanged portfolio against three interventions and combined. Do NOT change production v157. User explicitly authorized testing.

## Critical status
**NO LAB253 historical portfolio backtest has run. No new Net R, PF, or drawdown results exist.** Both Python execution endpoints returned `ClientError`. The independent runner was written to GitHub but NEVER executed, and could have bugs. Do not present older LAB151 results as LAB253.

## Files in conversation
- `trendlines.py`, upload ID `file_000000006e5082098e1e2a7a1065aa86`, mounted location reported `/mnt/data/trendlines.py`. Full source accessible in conversation.
- `btc_5m(2).zip`, upload ID `file_00000000cfb081f5bc5cb1c6b2779319`, mount location reported `/mnt/data/btc_5m(2).zip`. Archive received BUT NOT inspected or loaded because runtime error; schema, range, timezone, data integrity UNKNOWN.
- Prior LAB250/LAB251 files were generated in earlier turns, but do not assume their sandbox URLs are present in a fresh conversation/runtime.

## GitHub
Repository: `chepigga/ResearchOS`.
Canonical recovery branch pointer: `baseline/crowdfade-btc-20261009`.
Baseline documentation:
- `backlog/CURRENT_CROWDFade_BTC_BASELINE.md`
- `backlog/CROWDFade_BTC_BASELINE_MANIFEST_20261009.json`
- `backlog/CROWDFade_BTC_BASELINE_RECOVERY_STATE_20261009.md`
Runner files SAVED on repository default branch on 2026-10-13:
- `labs/LAB253_TRENDLINE_PORTFOLIO_20261013/run_lab253.py` (rough M5 replay; untested)
- `labs/LAB253_TRENDLINE_PORTFOLIO_20261013/export_raw_signals.py` (UNTESTED; assumes LAB150 path and `raw_events(7.5)` function exist—MUST verify)
- `labs/LAB253_TRENDLINE_PORTFOLIO_20261013/INSTRUCTIONS.md`
- `labs/LAB253_TRENDLINE_PORTFOLIO_20261013/README.md`
Previous attempt to create a separate GitHub branch returned API 422. Actual lab files were successfully created on default branch. No existing baseline files changed.

## Canonical frozen portfolio
ENGINE_A + B3_HIGH + R48_HIGH + EARLY_EPISODE; priority A > B3 > R48 > EARLY.
Second position only when first position same side and first MTM >= 0R; max 2; 0.25% account risk per position; 0.50% nominal total open stop risk.
Execution SL 1.0 H1 ATR; TP 3R; max hold 48h; stop-first for simultaneous SL+TP intrabar touches; research costs 2.81 bps normal / 7.5 bps stress.
Reference LAB151 (TRAIN/development, NOT clean forward):
normal N344, 7.17/month, EV+0.618R, PF2.04, R/month +4.43, MTM DD3.97%.
stress N341, 7.10/month, EV+0.571R, PF1.91, R/month +4.06, MTM DD4.52%.
For 100k account 0.25% risk, stressed average historical implied ~$1015/month; not guaranteed.
Past LAB151 MTM DD was M5 close-based and FTMO daily loss reset was UTC proxy, not exact CET/CEST.

## User's TrendAssist module
`trendlines.py`: `resample_server_time(m5, rule, server_offset_hours)`, `atr_mt5`, `compute_main(h4)`, `compute_corr(h1,main)`, `cl_break_signals(m5,corr,main)`.
It ports TrendAssist v1.23 H4 structural 2/2 trend, H1 correction fan / false break / rearm, M5 correction line crossing signals. Only tested on synthetic prices; real MT5 v1.23 parity unverified. No EMA-ret e st branch of indicator, and M5 signal cooldown excludes the original shared EMA-ret e st cooldown. Fixed UTC offset resampling doesn't handle broker DST; ATR SMA initialization needs explicit testing. DO NOT claim literal exact MQL parity. User prioritizes rough research over exact parity.

## Lab variants
BASE = untouched canonical execution.
TL_FILTER = veto an original entry if it disagrees with H4 direction.
TL_TRAIL = initial SL from canonical; trail at confirmed H1 line, no widening. The prototype explicitly removes fixed 3R TP in trailing variants in order to explore >3R tails. This changes occupation and all downstream entries; must full raw chronology.
TL_ADD = CL_BREAK as SECOND SAME-SIDE position ONLY while first position MTM>=0R and portfolio open slots<2; risk ceiling 0.50%.
COMBINED = all three.
Stress costs 7.5bps, stop-first, report net R/month, PF, EV, frequency, peak floating/MTM DD, annual and side breakdown, plus 2.81bps sensitivity.
A placebo trend filter compared against TL_FILTER desirable after primary.
Require all models to start with the SAME raw pre-portfolio candidate stream; using LAB151 accepted trades invalidates occupancy replay.

## Mandatory repair tasks BEFORE claiming results
P0: verify uploaded `btc_5m(2).zip` loads, columns, chronology, UTC/server time, interval, OHLC consistency and gaps.
P0: retrieve/export TRUE raw pre-portfolio v157 events; audit LAB150 function/path referenced by `export_raw_signals.py` (this was a guessed API, not verified).
P0: copy user `trendlines.py` to runtime and test its real input operation; check index timezone and DST. Audit `atr_mt5` calculations.
P0: run `run_lab253.py` for smoke and fix bugs. Do not assume first committed version is correct.
P0: replay BASE, reconcile against canonical LAB151 341 trades in 7.5bps stress. Explain any variance rather than silently accepting.
P1: execute all TL variants with full raw events and record event-level gating/exits, including occupancy and margin.
P1: produce plots of price H4/H1 structural line + accepted trades and equity; OOS caveat: data were repeatedly explored before.
P1: report yearly, side, cost sensitivity, matched benchmark, net R/month and prop DD.
P2: only after positive robust evidence consider broker-specific EA. REQUIRE prop/broker specs before generating final EA.

## Known runner issues to inspect
- `run_lab253.py` loading zipped BTC M5 assumes lowercase `time` or `datetime`, and OHLC named open/high/low/close. Actual zip schema unknown.
- `run_lab253.py` uses a guessed `raw_events(7.5)` in LAB150 exporter; verify LAB150 source and derive correct raw events or replace exporter.
- Prototype could include mismatched H1 ATR, interval gaps, timezone and tick-close look-ahead; stress verification strongly advised.
- Prototype models TL_TRAIL with TP removed entirely (non-comparable TP control unless predeclared).
- No actual computational execution happened during these turns.

## New-thread prompt
`Продовжуємо LAB253 за backlog LAB253_HANDOFF_RECOVERY_20261013.md у ResearchOS. Завантажені trendlines.py та btc_5m(2).zip. Спочатку перевір і виправ runner та експорт сирих сигналів v157, відтвори BASE на BTC M5, потім перевір TL_FILTER / TL_TRAIL / TL_ADD / COMBINED. Покажи фактичні історичні Net R, PF, DD, угоди/міс із реального запуску. Не вимагай паритету MT5 і не змінюй v157.`
