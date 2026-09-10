# BTC_LONG_V1_POSTFREEZE_FRESH_SEQUENTIAL_AND_BUY_SELL_PORTFOLIO_CONFLICT_AUDIT_LAB_064

## Purpose
Audit the already-frozen BTC LONG v1 sequentially after its LAB063 freeze, and audit interaction/conflicts with the already-frozen BTC SHORT v1 without changing either system.

This LAB is **not an alpha search and not a conflict-router optimization**. No thresholds, clocks, exits, costs, risk sizes, or conflict actions may be altered after outcomes.

## Immutable references

### LONG v1
Frozen candidate from LAB063: `BTC_LONG_V1_TIER_A_8H_TP15`.
Freeze/prereg commit: `ccc855df34918ee320a2e8033115fec02b439475`.
Freeze timestamp: **2026-09-10 14:28:51 UTC**.

Rules remain exactly:
- H4 Supertrend ATR(10) x 3.0 built from BTC M5.
- causal convention: H4 `BAR_OPEN + lag1` (previous completed raw H4 state).
- Tier-A BUY iff `st_age > 58` and `st_dir == -1`.
- deterministic entries every 8h from causal Tier-A episode onset while state is active.
- entry at next M1 open at/after `signal_time + 1 minute`.
- SL = 1.5 x latest completed H1 ATR14.
- TP = 1.5R.
- max horizon = 48h.
- same-M1 SL/TP ambiguity = SL first.
- episode planned initial-risk budget = 0.50%; six possible 8h slots => nominal slot risk = 0.083333333%.
- costs: 5 bps primary, 10 bps stress.

No LONG rule may be modified in LAB064.

### SHORT v1
Frozen SHORT v1 is the unchanged system from `BTC_SHORT_V1_FROZEN_FULL_SYSTEM_POSTFREEZE_REPLICATION_LAB_055` and subsequent parity labs.
For portfolio conflict timing, use the **canonical archived LAB055 execution ledger**, not a rebuilt REST retail-ratio clock.
- only rows with `traded=True` and `side=-1` are SHORT positions.
- position interval is canonical `entry_time` through canonical `exit_time`.
- SHORT risk = 0.25% initial risk per trade.
- SHORT costs/returns use LAB055 frozen `net_r_5bps` and `net_r_10bps` as stored.

No SHORT rule may be modified or reconstructed from the uncertified live REST retail-ratio source.

## Critical window separation
The LONG v1 did not exist as a frozen candidate before 2026-09-10 14:28:51 UTC. Therefore:

### A. `FRESH_POSTFREEZE_LONG`
- starts strictly after **2026-09-10 14:28:51 UTC**;
- ends at the latest fully completed REST price bar available at LAB execution time;
- this is the only window eligible to count toward future LONG promotion.
- a trade is assigned to this window by `signal_time > freeze_timestamp`; outcome is scored only if its frozen exit can be observed with available data. Open/incomplete trades are reported separately and are never scored as losses/wins.

### B. `LOCKED_TRANSFER_CONFLICT`
- starts **2026-08-11 00:00:00 UTC**, the first full UTC day after the frozen LAB063 M1 release tail;
- ends **2026-09-08 23:59:59 UTC**, the canonical LAB055/LAB059 SHORT archive tail available for exact clock comparison;
- this window predates LONG freeze, so it is strictly a transfer/conflict diagnostic and cannot promote LONG v1.

### C. Fresh combined portfolio status
Canonical SHORT events are unavailable after the archive tail because LAB056-059 showed that live REST retail-ratio data cannot reproduce the exact frozen 12h event clock. Therefore LAB064 must **not** substitute REST SHORT events in the fresh post-freeze portfolio.
If no canonical SHORT data exists after LONG freeze, fresh combined BUY/SELL conflict closure is `UNAVAILABLE_CANONICAL_SHORT_TAIL`.

## Price-data extension and parity gate
Frozen LAB063 release files remain the historical seed:
- `btc_1m.zip`
- `btc_5m.zip`

For dates beyond the frozen release tail, use Binance USD-M BTCUSDT futures klines from the already-validated public `www.binance.com/fapi/v1/klines` transport.

Before interpreting REST-extended LONG results, compare REST OHLC against overlapping frozen release rows:
- M1 overlap target >= 1000 rows where available; minimum acceptable >= 250 rows because the frozen M1 tail may constrain overlap.
- M5 overlap target >= 200 rows; minimum acceptable >= 100 rows.
- exact OHLC equality primary requirement = 100%; timestamps must match exactly.
- also report maximum absolute OHLC difference.

If M1 or M5 parity fails exact equality, verdict is `INVALID_PRICE_TRANSPORT_PARITY_DO_NOT_INTERPRET_FRESH_LONG` and no REST-extended LONG PnL is used.

## Sequential LONG scoring
For both windows, run the frozen LONG engine once on merged frozen+REST price history. Do not re-seed state at the window boundary.
Report:
- Tier-A episodes intersecting/evolving through the window;
- scheduled signals;
- completed trades;
- still-open/incomplete signals;
- EV/PF/CumR at 5bps and 10bps for completed trades;
- TP/SL/TIME counts;
- risk-scaled additive realized DD using 0.083333333% slot risk;
- peak concurrent LONG positions and initial risk.

Fresh LONG status gates:
- if completed N < 5: `WATCH_FRESH_LONG_INSUFFICIENT_N` regardless of sign;
- if N >= 5: require EV5 > 0, PF5 >= 1.10, EV10 > 0, additive DD <= 4.0%; otherwise fresh LONG fails.
No calendar or state exclusion is permitted.

## Portfolio conflict audit on `LOCKED_TRANSFER_CONFLICT`
Use frozen LONG trade intervals and canonical frozen SHORT trade intervals exactly as generated/stored.
No action is taken on conflict; both trades remain in the audit ledger.

Predefined metrics:
1. `DIRECT_OVERLAP_PAIR`: a LONG and SHORT position interval overlap for positive time.
2. `ENTRY_AGAINST_OPEN`: a LONG entry occurs while a SHORT is open, or a SHORT entry occurs while one or more LONGs are open.
3. `NEAR_CONFLICT_12H`: opposite-side entries occur within <=12h but their position intervals do not overlap.
4. unique LONG trades involved in direct conflict / all LONG transfer trades.
5. unique SHORT trades involved in direct conflict / all SHORT transfer trades.
6. total direct-overlap duration in hours and max single-pair overlap hours.

Do **not** infer a conflict-resolution rule from winners/losers in this LAB. Conflict PnL may be described only after fixed conflict membership is computed; any router (`LONG wins`, `SHORT wins`, `first signal wins`, netting, abstention) requires a new preregistered LAB.

## Frozen portfolio risk accounting
- LONG initial risk per open slot: 0.083333333%.
- SHORT initial risk per open trade: 0.25%.
- report peak simultaneous LONG count, SHORT count, total positions, gross initial risk, and directional net initial risk.
- report additive realized portfolio return and DD by chronological exits using each branch's frozen risk size and `net_r_5bps`.
- this is additive realized accounting, **not** mark-to-market intratrade equity DD.

Safety gates for the locked-transfer portfolio diagnostic:
- peak gross initial risk <= 1.00%;
- additive realized DD <= 4.00%.
A conflict rate itself is descriptive and is not an alpha fail gate.

## Verdict hierarchy
1. Price transport parity failure => `INVALID_PRICE_TRANSPORT_PARITY_DO_NOT_INTERPRET_FRESH_LONG`.
2. Otherwise if true fresh completed LONG N < 5 => `WATCH_POSTFREEZE_TOO_EARLY__LOCKED_TRANSFER_CONFLICT_AUDIT_COMPLETE` (or same WATCH with conflict audit unavailable if inputs absent).
3. If fresh N >=5 and fresh gates fail => `FAIL_FRESH_LONG_POSTFREEZE`.
4. If fresh N >=5 and fresh gates pass but canonical fresh SHORT unavailable => `PASS_FRESH_LONG__WATCH_COMBINED_PORTFOLIO_CANONICAL_SHORT_UNAVAILABLE`.
5. No LAB064 verdict authorizes live trading; broker-native/FTMO parity remains required.

## Guardrails
- no optimization;
- no new LONG/SHORT filters;
- no post-result calendar slicing;
- no REST SHORT substitution for canonical archive;
- no conflict policy chosen from outcomes;
- frozen LONG v1 unchanged;
- frozen SHORT v1 unchanged;
- live allocation remains 0.