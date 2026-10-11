# CrowdFade research recovery & backlog — 2026-10-11

## Core objective and current decision
Build a BTCUSDT USD-M Futures research system that detects **early confirmed aggressive execution flow** (ignition) and distinguishes continuation vs exhaustion vs stall while meaningful **remaining liquidity-to-liquidity R:R >=1.5** is still available. We cannot predict a news catalyst or identify a single dominant actor from trades. L/S, OI, Volume Profile, H1/H4 structure are **context** only after independent flow trigger and price-response validation.

Research ONLY; no prop-ready trading strategy or MT5 EA approved. Before production request updated broker/prop firm, symbol/account, spreads/commission, swap, stop/freeze, leverage, EA permissions, execution latency/slippage, VPS and challenge rules. Risk target 0.25–0.5%/trade; no martingale/grid; TP >=1.5R; DD limits firm-specific.

## Evidence snapshot (reports in previous conversation; some not yet imported into GitHub)
- LAB194 4411 first-entry VA signals, 10bps assumed all-in: price-only net EV -0.198R; 350 hard L/S AGAINST + OI BUILD +0.020R overall, **2024 -0.115R**. Not robust.
- LAB195/196: modifying stops and simple delayed confirmation did not create reliable positive EV; stop>=4ATR about +0.015R paired change. Entries mostly acceptance and correlated.
- LAB197: breakout quality (pre-compression, volume, H4/D1) improves sorting but strongest exploratory subgroup still about -0.031R net; no stable positive EV.
- LAB198: geometric liquidity R:R / L/S / OI / reconstructed VP — high potential did not generalize, especially 2024.
- LAB199: 194077 15m states, 968 crowd episodes, 535/2754 hindsight large waves preceded by matching warning; 24h +2ATR-before-1ATR ~34.8/36.5/31.3% 2021-23/2024/2025-26 versus weak controls ~32.8/33.6/31.9%; cannot promote to signal.
- LAB200A/200B: Binance Futures BTCUSDT aggTrades pilot 2026-08-01 to 2026-08-07, **5,307,865 aggTrades**, 15m native price bins $25, developing POC/VAH/VAL, session VWAP+SD; calendar previous week cannot be complete without pre-start warmup. Real prints-by-price != resting orderbook/stops.
- LAB201 native VP premove seven-day pilot: 672 snapshots, 577 joined; results underpowered, overlapping.
- LAB202 native vs reconstructed M5 candle uniform spread profile: 570 matched timestamps, ~93.7% same inside/above/below VA, ~72.1% exact POC. Matching VA class is NOT predictive evidence; need study motion.
- LAB203 movement-first: 194029 grid states, future +/-3ATR(H1) within12h. The 'large L/S move + OI build + stalled price' state *underperformed* general movement frequency (~35.5/30.9/32.1% vs 38.5/39.5/40.2% across periods); simple crowd accumulation is not a universal launch signal.
- LAB204 *true Binance aggressive flow* 672 15m bars, 79 events, only 24 after 4h cooldown. Ignition +1.5ATR before -1ATR within6h: first Aug1-4 45.0% n40, Aug5-7 28.6% n28; cooldown 46.2% n13 versus 22.2% n9. Labels from 15m **close-based diagnostic**, not executable tick TP-first. 7 days too few; cannot claim predictive edge or trade EV.

## P0 — Acquire full true trade-by-price history
- **LAB205-DATA**: downloader `lab205_binance_history_downloader.py` shared in conversation (not committed yet). Use Binance public USD-M BTCUSDT daily aggTrades archives; resumable by date, validate ZIP CRC, source sha256 when published, manifest of file size/hash/period/rows, dedupe timestamps and trade IDs, audit discontinuities and suspicious outlier volumes. UTC normalization and batch timestamps; verify first/last trade time and aggressive side semantics (`isBuyerMaker`: buyer is maker => aggressive seller).
- Initial 2026-05-01..2026-08-07 plus **seven preceding warmup days** (April 24 onward), then 2026-02-01..2026-08-07 plus warmup Jan25 onward. Date ranges INCLUDE warmup; do not silently treat warmup as actual test. Downloader should never duplicate validated days.
- Data local on Mac and optionally portable derived aggregates with hashes; do NOT commit multi-GB archives to regular GitHub; use Git LFS/external storage + manifest.
- **Done when** >=3 months continuous verified actual prints; target >=6 months spanning distinct volatility/trend regimes, native 1m/5m/15m aggregates, native bin volume, delta & CVD, native session VWAP, completed session/day/week reference levels, explicit warmup.

## P0 — LAB205 ignition vs exhaustion (no L/S/OI in first baseline)
1. **Freeze event detector before inspecting labels**: from actual aggressive buy/sell prints, construct 1m/5m delta, CVD slope/acceleration, relative volume versus time-of-day baseline, price displacement and flow efficiency. Avoid a blanket fixed daily count; include ALL qualified flow bursts and de-duplicate with deterministic cooldown. Replicate original LAB204 79 events before modifications (parity).
2. Label outcomes only AFTER event timestamp: continuation, reversal/exhaustion, stall on pre-registered forward horizons 15m/30m/1h/3h/6h and ATR-scaled thresholds. Explicit ties/ambiguous/timeout; high-low tick-order where source supports it, or mark uncertainty. Exhaustion means realized opposite movement, not simply no continuation. Labels are NOT candidate features.
3. Candidate inputs at **closed observation time only**: signed delta change and acceleration, CVD impulse and duration, relative trade volume, candle close location/body/wicks, break of already-confirmed local highs/lows or liquidity sweep, VWAP z-score, developing VA and prior fixed VA, trend preceding event (H1/H4), price impact per volume (and absorption). Session UTC/DST correct; compare trend aligned vs countertrend.
4. Compare feature distributions conditional on labels AND compare with matched non-event time/session/regime controls. Event-level and day-block bootstrap; distinct dates, sessions, N effective, CI, false alarms.
5. Train on chronological months, freeze thresholds, then validate future months. No tuning on holdout, no selecting best regime after seeing its realized P/L.
6. Remaining potential: at event-close/next executable price, distance to significance-ranked **known** liquidity levels H1/H4/session/PWH/L; structural invalidation SL and costs. Keep all known levels/obstacles, not only nearest pivot; target admissibility >=1.5R net.
7. **Execution replay**: next feasible tick/open AFTER confirmation; conservative same-bar TP/SL ordering; realistic spread/fees/slippage and latency, exits with actual price path, one trade per independent event, timeouts; report 1.5/2/3R TP, net EV, PF, DD, MFE/MAE, residual R:R, missed wave fraction, signals/month, max loss streak. No assumption that diagnostic close-first = tradable TP-first.
8. **Acceptance threshold**: no universal preselected 70% WR target. Require net positive EV after costs on genuinely unseen months, enough independent trades, stable subperiods, confidence interval and acceptable DD. If no robust improvement, mark hypothesis failed and STOP optimizing on same 79 events.

## P1 — LAB206 crowd incremental ablation
Only AFTER standalone ignition quality passes validation: append timestamp-safe L/S trajectory (with verified Binance publication lag), OI change and funding to identical events. Compare paired model without crowd, and placebo/shuffle controls, by market regime. Determine incremental net EV and preserved signal frequency. Do not use L/S/OI as primary hard gate.

## P1 — LAB207 native structure, liquidity route, phase
On same frozen events, assess real native developing session/day/week POC migrations, HVN/LVN, VWAP ±SD and session volume, level reaction vs breakout, sweep/reclaim, no-lookahead confirmed liquidity ladder. Treat volume-at-price as executed trades, not standing orders. Test continuation/exhaustion separation, entry location and actual route obstacle ranking without imposing irrelevant 'price inside VA' metric.

## P1 — LAB208 portfolio / broker transfer
Walk-forward/Monte Carlo/block bootstrap, sensitivity to spread+fee+slippage, sessions, volatility regimes; realistic BTC CFD conversion if deployed to MT5. Broker/prop rules obtained prior to implementation. No strategy code or risk escalation without validated net profitability and independent QA.

## Data lineage, artifacts & recovery
- Original 7-day pilot and analyses LAB200B–LAB204 were generated and distributed in conversation; may NOT all exist on GitHub. Do not assert their code/data already committed.
- Frozen local filenames referenced: `LAB204_EVENT_ATLAS.csv`, `LAB204_REPLAY_SUMMARY.csv`, `LAB204_REPORT.md`, `LAB204_IGNITION_PILOT.zip`, `lab204_ignition.py`, `LAB200B_BINANCE_NATIVE_VP_20260801_07.zip`, `lab205_binance_history_downloader.py`.
- Historical research branch links: `lab/lab197-breakout-quality-regime-20261011`, `lab/lab198-liquidity-potential-20261011`, `lab/lab199-pre-move-crowd-20261011`; later LAB200–204 were conversation artifacts, not necessarily GitHub commits.
- Required outputs per lab: SPEC preregistered, DATA_MANIFEST hashes/time ranges, detector and label code, full event-level rows, train/OOS cohort definitions, cost scenario model, summary by year/regime/side, audit with failures, RESULTS, and state recovery checkpoint.

## Immediate next action
1. Run downloader on Mac for May 1–Aug7 and confirm daily manifest; extend to February 1–Aug7 with 7d warmup before each validation start.
2. Upload manifest and **representative** raw ZIPs or derived native minute bars in batches (avoid multi-GB single chat upload).
3. Reproduce LAB204 baseline 79 events on original Aug1–7. Then freeze LAB205 event and label specifications before scanning expanded unseen period.
4. Classify continuation/exhaustion/stall and do independent chronological holdout; only then add context and costed execution replay.

## Hard truth
High delta does not prove future follow-through, high OI does not locate stop clusters, high volume is not resting liquidity, predictive class accuracy is not profit. As of 2026-10-11 NO verified profitable trading edge and NO production-validated EA from LAB200–205.
