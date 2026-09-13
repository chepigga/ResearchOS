# UNIVERSAL_CONTEXT_FROZEN_HEADS_UNSEEN_MARKET_REPLICATION_LAB_005 — PREREG

Status: **FROZEN BEFORE UNSEEN OUTCOMES**

## Question
Do the two most interesting frozen LAB004 lineages replicate without any retuning on markets never used in LAB001–004?

Primary frozen candidates:
1. **EXPANSION_BULL** continuation head.
2. **COMPRESSION_BEAR** rare first-passage head.

All other LAB004 heads are reported as secondary diagnostics only and cannot rescue a failed primary verdict.

## Unseen market universe
None of these symbols appeared in LAB001–004:
- USDJPY — Yahoo Finance ticker `USDJPY=X`
- GBPUSD — Yahoo Finance ticker `GBPUSD=X`
- AUDUSD — Yahoo Finance ticker `AUDUSD=X`
- USDCAD — Yahoo Finance ticker `CAD=X`

## Frozen data source / window
Public Yahoo Finance chart API, **1h** bars, fixed requested window:
- start: `2024-09-15T00:00:00Z`
- end: `2026-09-01T00:00:00Z`

Each series is resampled to H4 using the same epoch-aligned OHLC aggregation used by prior Universal Context LABs. Only closed H4 bars are used. The exact raw JSON bytes, row counts, first/last timestamps, and SHA256 digest are persisted by the runner for audit.

If Yahoo returns fewer than 500 ready H4 bars for any required market, verdict=`DATA_BLOCKED`.

## Frozen engine lineage
- Geometry: import LAB002 `add_engine()` unchanged.
- Forward outcomes: LAB002 `add_forward()` unchanged.
- Side-specific scores/signals and first-passage logic: import LAB004 `add_heads()` and `add_outcomes()` unchanged.

No weight, threshold, lookback, geometry state, horizon, ATR target, or conflict rule may change in LAB005.

## Primary candidate A — EXPANSION_BULL
Exact LAB004 frozen signal:
- eligible state: `regime == EXPANSION`
- score and threshold exactly as LAB004
- signal: `exp_bull_signal == True`
- outcome: `bull_signed8 = close_ret_8h_atr`

### H1 — unseen Expansion BULL replication
PASS only if all are true:
- at least **3 of 4** unseen markets have N>=50 and mean `bull_signed8 > 0`;
- no unseen market with N>=50 has mean `< -0.05 ATR`;
- pooled N>=250;
- deterministic market×week cluster-bootstrap 95% CI lower bound >0.

This is the main universal-portability gate.

## Primary candidate B — COMPRESSION_BEAR
Exact LAB004 frozen signal:
- eligible state: `regime == COMPRESSION`
- score/threshold exactly LAB004
- signal: `comp_bear_signal == True`
- first unique ±1.0 ATR passage within next 6 H4 bars (24h)
- same-bar double hit = AMBIGUOUS/excluded; neither hit = NONE/excluded.

### H2 — unseen Compression BEAR replication
Performance PASS only if:
- at least **3 of 4** markets have >=10 uniquely resolved signals;
- accuracy >50% in at least **3 of 4** eligible markets;
- no eligible market accuracy <45%;
- pooled resolved N>=60;
- pooled cluster-bootstrap 95% CI lower bound >50%.

If pooled resolved N<60 or fewer than 3 markets have >=10 resolved signals, classify this head as **UNDERPOWERED**, not performance-failed.

## H3 — frozen-head coverage sanity
For every unseen market:
- Expansion BULL signal coverage among EXPANSION bars: **5%–70%**.
- Compression BEAR signal coverage among COMPRESSION bars: **0.5%–15%**.
- LAB004 conflict logic remains unchanged; no hidden override allowed.

PASS only if all four markets satisfy both ranges.

## Statistical protocol
- deterministic 5,000-draw cluster bootstrap by `market × calendar-week`
- seed `2026091305`
- no multiple-testing selection because primary candidate heads and directions were frozen before unseen outcomes.

## Secondary diagnostics — cannot rescue primary gates
Apply all other frozen LAB004 heads unchanged:
- EXPANSION_BEAR
- RETRACEMENT_BULL
- RETRACEMENT_BEAR
- COMPRESSION_BULL

Report by-market N, mean signed ATR / first-passage accuracy, coverage, and side asymmetry. Also report Expansion BULL by calendar year and pooled yearly means.

## Frozen verdicts
- `FROZEN_HEADS_UNSEEN_REPLICATION_SUPPORTED`: H1 PASS, H2 PASS, H3 PASS.
- `EXPANSION_BULL_REPLICATED_COMPRESSION_BEAR_UNDERPOWERED`: H1 PASS, H3 PASS, and H2 is UNDERPOWERED.
- `EXPANSION_BULL_REPLICATED_COMPRESSION_BEAR_FAILED`: H1 PASS, H3 PASS, H2 has adequate power but performance FAILS.
- `UNSEEN_REPLICATION_NOT_SUPPORTED`: H1 FAIL or H3 FAIL.
- `DATA_BLOCKED`: any required unseen market cannot be loaded or has <500 ready H4 bars.

## Interpretation boundary
This LAB is fresh **market OOS**, not broker-execution OOS. Yahoo FX bars are used only to test state/head semantics. Even a PASS does not establish executable entry timing, SL/TP profitability, spread/commission/slippage economics, or FTMO parity.

## Anti-curve-fit boundary
After this prereg commit, no market may be removed or replaced because of results; no threshold, score weight, date window, horizon, ATR target, coverage range, or pass/fail rule may change. Technical source/parser/runtime fixes are allowed only if formulas and market universe remain unchanged and must be disclosed.