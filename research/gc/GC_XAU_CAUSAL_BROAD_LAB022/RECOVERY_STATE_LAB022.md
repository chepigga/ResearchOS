# GC-XAU CAUSAL BROAD — RECOVERY PACKAGE THROUGH LAB022

Status: 2026-09-29
Repository: chepigga/ResearchOS
Branch: gc-amp-feed-audit-001
Canonical path: research/gc/GC_XAU_CAUSAL_BROAD_LAB022/

## Recovery rule
Continue with LAB023 CIRCUIT_BREAKER_ROBUSTNESS. Do not restart discovery from LAB006/LAB015, do not reintroduce the structural entry gate, and do not retune signal/entry/exit while validating the circuit breaker.

## Scope / limitations
All LAB008–LAB022 conclusions below are based on the v034-opened OOS signal universe, not all 111,172 raw Broad sensor emissions. Historical execution uses XAUUSD M1 proxy data, UTC H1 resampling, commission proxy and conservative same-M1 ambiguity. It is research evidence, not production/live proof.

## Canonical upstream data
- GC compact ticks: @GCE_LAB008H_COMPACT.zip
  SHA256 c4e63942156a7aed97b853b2dbaed18429a23134f6924250ae9dc09351489037
  568 CSVs; 17.30GB unpacked/input summary: 174,022,818 rows; 27,025,331 exclusive directional rows.
- Broad registry: GC_XAU_BROAD_LEGS_LONG_HISTORY_CAUSAL_REGISTRY.csv
  SHA256 13cfbacd8bc46d1806ccbb29cfcccdd605630fa91adbbba0417fa4d27966991d
  N=111,172; range 2025-01-02 00:32 UTC to 2026-07-28 23:58 UTC.
  Labels: BASE1 38,347; DOM2 18,641; MIXED 17,657; MIX2 17,084; DOM_CONT 10,576; REV1 7,401; REV2 1,367; REV3P 99.
- XAU M1 proxy: XAUUSD_M1_20220601_20260723_TICK_NATIVE.csv
  SHA256 db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b
- Current executor source: XAU_EXECUTOR_CAUSAL_BROAD_DEMO_v034_ONE_POSITION_TOTAL.mq5
  SHA256 78e480f77af4760ca0a48e8b1ce85810eb0f8e5d3763cfef6d4f95ec76548585

## Frozen signal / confidence
Canonical Broad sensor lineage remains frozen. LAB011: attack2_volume and episode_index are useful signal-quality variables on both sides; impact_deterioration is not a universal confidence score.
LAB012 HIGH definition: prior-only expanding same-side percentiles, min 50 prior observations; confidence = mean(volume percentile, episode-index percentile); HIGH >= 0.75.

## Frozen entry candidate
HIGH -> +0.50 ATR favorable response within 10m -> entry at response level.
Initial SL = 2 ATR = 1R.
ONE POSITION TOTAL.
This family was positive across LAB016's small response grid. +0.50/10m remains a research choice, not production proof.

## Structural target finding
LAB017: do NOT use old structure as an entry gate.
310 response-qualified opportunities: BUY 219, SELL 91.
BUY median raw structure 1.61R; 49.3% <1.5R; 29.7% behind entry.
SELL median 4.91R; 19.8% <1.5R; 8.8% behind entry.
The old gate systematically removed BUY opportunities. Structure can remain an exit variable.

## MFE finding
LAB018, N310:
ALL mean MFE 4.97R / median 3.86R.
BUY mean 5.20R / median 4.21R.
SELL mean 4.41R / median 3.06R.
Hit +2R 72.6%; +3R 58.7%; +4R 48.7%; +5R 40.0%.
Median milestone times: +1R 11m, +2R 26m, +3R 45.5m, +4R 59m, +5R 68.5m.

## Frozen side-specific exit candidate from LAB019/LAB020
BUY: SL2ATR; after +3R move stop to +1R; max hold 120m.
SELL: SL2ATR; raw previous-12-completed-H1 structural target when valid; max hold 120m.

LAB020 SIDE_SPECIFIC:
N 228; PF 2.021; EV +0.682R; Sum +155.481R; MaxDD 15.961R; WR 34.6%; avg hold 44.4m.
BUY: N139 PF2.250 EV+0.828R Sum+115.147R DD10.179R.
SELL: N89 PF1.670 EV+0.453R Sum+40.334R DD14.634R.
Benchmarks:
120m only: N225 PF1.842 EV+0.625R Sum+140.737R DD17.537R.
Raw structure both sides: N253 PF1.664 EV+0.425R Sum+107.542R DD14.897R.

## Regime audit
Monthly descriptive regime: BULL > +2%, BEAR < -2%, otherwise FLAT.
SIDE_SPECIFIC BULL: N111 PF2.145 EV+0.750R Sum+83.222R.
FLAT: N114 PF1.985 EV+0.661R Sum+75.355R.
BEAR: N3 only, all SELL, negative. Bear robustness is UNKNOWN.

## LAB021 failure-state finding
BAD MAY (2025-05 + 2026-05): N53 PF0.611 EV-0.306R Sum-16.218R.
GOOD JUL (2025-07 + 2026-07): N56 PF3.735 EV+1.553R Sum+86.951R.
Confidence was not weaker in bad months (0.868 vs 0.851).
BAD MAY ATR 2.125 vs GOOD JUL 1.238; MFE 3.588R vs 5.679R; MAE 3.484R vs 2.819R; Hit3 41.5% vs 66.1%.
High ATR alone is not validated as a filter. May-2025 contained an 8-loss cluster.

## LAB022 circuit-breaker discovery
Frozen LAB020 logic unchanged. Tested only risk permission:
2 or 3 consecutive losses -> pause 6/12/24h;
rolling realized -2R/-3R -> pause 6/12/24h;
baseline no breaker.

Most promising discovery candidate: 2 consecutive realized losses -> pause 12h.
N183; blocked45; PF2.176; EV+0.776R; Sum+141.952R; MaxDD12.924R; WR35.5%.
Retained 91.3% of baseline total R while reducing historical MaxDD ~19%.
BAD MAY: baseline -16.218R/DD18.107R -> 2L/12h -9.818R/DD11.706R.
GOOD JUL: baseline +86.951R -> 2L/12h +91.392R.
Worst realized daily DD: baseline 5.099R -> 4.068R.
At 0.25%/R: ~1.27% -> ~1.02%; at 0.50%/R: ~2.55% -> ~2.03%.
This is realized chronology, not floating tick-equity DD.
2L/24h cuts too much profit; 3-loss breakers trigger too late; tested rolling loss breakers did not materially improve baseline.
2L/12h is DISCOVERY-SELECTED, not production-frozen.

## What is established
1. Old adverse-pullback execution was too restrictive for many HIGH signals.
2. Old structural entry gate systematically disadvantaged BUY.
3. HIGH BUY is not intrinsically weaker than SELL in this audited universe.
4. Short favorable price-response confirmation is more promising than deep adverse-first execution.
5. Post-entry MFE is large; exit management materially changes realized edge.
6. BUY and SELL have materially different exit behavior in this sample.
7. Side-specific exit beats the two tested universal benchmarks on PF/EV/SumR in this sample.
8. Losses cluster; a causal 2-loss pause deserves robustness validation.
9. Tightening HIGH or adding a naive absolute ATR cutoff is not supported as the main fix.

## Unknown / not proven
- Exact tick-level broker execution and broker H1 boundaries.
- Stability of +0.50ATR/10m in fresh OOS.
- BUY +3R->lock1 in genuine bearish gold regimes.
- SELL raw structure with more bearish history.
- Generalization of 2L->12h outside this sample.
- True floating daily drawdown under prop rules.
- Whether confidence double-counts episode structure.
- Full raw-Broad-universe replication rather than v034-opened OOS subset.
- Live/demo parity.

## NEXT: LAB023 CIRCUIT_BREAKER_ROBUSTNESS
Freeze 2 consecutive realized losses -> pause 12h. Do NOT search another pause grid.
Audit:
- month x side x regime;
- all 45 blocked trades, winners/losers and R saved/lost;
- trigger-by-trigger chronology;
- dependence on May-2025;
- recovery immediately after pause;
- daily realized DD;
- frozen breaker vs no-breaker.
Keep only if benefit is distributed across multiple periods/episodes and improves tail risk without depending mainly on May-2025.

## Production status
NO production promotion yet.
Strongest research candidate:
HIGH -> +0.50ATR response <=10m -> entry -> SL2ATR -> side-specific exit.
2L->12h is an unconfirmed risk-layer candidate.
