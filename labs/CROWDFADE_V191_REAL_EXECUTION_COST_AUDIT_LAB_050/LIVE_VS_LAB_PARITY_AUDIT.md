# V191 LIVE vs LAB PARITY AUDIT

Status: **DONE — MATERIAL NON-PARITY FOUND**

Audited live source:
- `CrowdFadeMulti_v191f_BROKER_ROBUST_EPISODE_GATE.mq5`
- latest Library build dated 2026-09-22.

Reference research shell:
- LAB046 frozen dual toxic-state gate
- LAB047 control management
- LAB048/LAB049 trail-arm research
- LAB050 same-live-signal counterfactual

## Executive verdict

The current V191 live code is **not a faithful implementation of the LAB046–049 strategy**.

The largest divergences are structural, not broker slippage:

1. Confirmation is evaluated only once per new broker M5 bar, despite a 1-second timer.
2. Live confirmation/SL/BE/trail geometry uses broker CFD price/ATR, while research used Binance reference price/ATR.
3. The current live build does not implement the LAB046 RAPID_REPEAT_30 and HIGH_VOL vetoes.
4. Current v191f default ExitZ is OFF (0.00), while the LAB047–049 control/counterfactual shell uses ExitZ 0.75.
5. Current v191f adds same-side-Z, |Z|>=0.75 and response-ratio gates that are not part of LAB046.
6. The order comment CF191 timestamp is not frozen at signal-arm time; it uses the then-current Binance source timestamp at order-send time.
7. Live stop/risk geometry is based on ATR at confirmation/entry, while LAB047–049 uses the signal ATR snapshot.
8. The latest v191f universe is BTC+SOL only; the attached broker reports include ETH and therefore represent earlier/mixed V191 lineage, not a pure v191f sample.

Therefore the prior broker-history comparison is useful as an execution/path diagnostic, but should not be interpreted as exact same-original-signal causal parity until signal IDs and live decision telemetry are fixed.

---

## Rule-by-rule parity matrix

| Rule | LAB046–049 | Current v191f LIVE | Parity | Severity |
|---|---|---|---|---|
| Z source | Binance global L/S ratio | Binance global L/S ratio | close | LOW |
| Z window | 72 x M5 = 6h | 6h / 5m = 72 points | yes | LOW |
| Z trigger | abs(Z)>=1.0 | abs(Z)>=1.0 | yes | LOW |
| Decision clock | causal completed M5 signal + raw path confirmation | TryEnter only once per new broker M5 bar | NO | CRITICAL |
| Confirmation threshold | 0.30 ATR against crowd | 0.30 ATR | nominal yes | — |
| Confirmation path | raw second/1m closes | broker bid/ask sampled only at M5 decision points | NO | CRITICAL |
| Signal ATR | frozen at signal | stored, but order stop uses current ATR | NO | HIGH |
| Freshness | <=45m from signal | <=45m from local confirmation arm | partial | HIGH |
| Pre-confirm adverse | <=0.75 ATR on path | v191f gate exists, but sampled only each M5 decision | partial | HIGH |
| Confirm Z consistency | v191d: reject only opposite ExitZ contradiction | same-sign + abs(Z)>=0.75 + optional ExitZ contradiction | NO | HIGH |
| Response-ratio gate | none | >=0.50 | EXTRA RULE | HIGH |
| RAPID_REPEAT_30 veto | required | absent | NO | CRITICAL |
| HIGH_VOL veto | required | absent | NO | CRITICAL |
| Pause | 1 ATR | 1 ATR | nominal | MEDIUM |
| Pause ATR anchor | signal ATR in replay state | entry/current ATR | NO | MEDIUM |
| Max trades/day | 3 | 3 | yes | LOW |
| SL | 1.5 ATR | 1.5 ATR | nominal | — |
| SL ATR anchor | signal ATR | confirmation/current ATR | NO | HIGH |
| BE | arm 0.5 / lock 0.15 | arm 0.5 / lock 0.15 | nominal | MEDIUM |
| Trail control | 2.5 / 0.5 | 2.5 / 0.5 | yes to LAB047 control | LOW |
| Trail balanced research | 3.5 / 0.5 | not current default | NO to LAB050 counterfactual | MEDIUM |
| ExitZ | 0.75 | 0.00 default | NO | CRITICAL |
| Hold | 6h | 6h | yes | LOW |
| Partial TP | off | off | yes | LOW |
| Signal ID | original signal timestamp | current sourceTimeMs at order send | NO | CRITICAL |
| Symbol universe | research sample includes tested symbols per run | current default BTC+SOL | intentional difference | INFO |

---

## Root cause of the ~5 minute live entry lag

`OnTimer()` runs every 1000 ms, but `TryEnter()` immediately returns unless a **new broker M5 bar** has appeared.

So:
- timer frequency is 1 second;
- decision frequency is still ~5 minutes;
- confirmation is not observed continuously.

This directly explains why the broker-history sample showed live entry around 5 minutes after the CF191 timestamp while the research replay commonly confirmed in 2–3 minutes.

This also under-samples:
- max favorable excursion;
- max adverse excursion;
- response ratio.

A move can touch +0.30 ATR, +0.50 ATR BE, or -0.75 ATR adverse and fully retrace between two M5 decision snapshots without the confirmation state machine seeing the path.

---

## Signal timestamp / comment bug

At confirmation arm, live stores:
- confSignalPrice
- confSignalMid
- confAtr
- confZ
- confSignalTime

It does **not** store the Binance `sourceTimeMs` that created the signal.

At order send, the comment is built from:
`g_sym[idx].sourceTimeMs/1000`

By then one or more Binance 5m refreshes may have occurred.

Therefore:
`CF191B/S##########`
is not guaranteed to identify the original signal that armed confirmation.

Required fix:
- add `confSourceTimeMs` to SymState;
- set it exactly when `confActive=true`;
- use `confSourceTimeMs` for comment and all decision logs;
- also log order-send sourceTimeMs separately.

---

## Price/ATR transport mismatch

Research:
- decision/confirm path from Binance reference OHLC;
- ATR from Binance reference M15;
- signal ATR frozen into management geometry.

Live:
- Z from Binance;
- confirmation price from broker CFD bid/ask;
- ATR from broker CFD M15;
- stop based on current broker ATR at confirmation;
- BE/trail inherit that entry ATR.

Therefore two brokers can receive the same Z state but have different:
- confirm times;
- entry prices;
- stop distance;
- effective R;
- BE/trail activation.

This is not merely slippage.

Clean parity choices:

### Option A — strict research parity
Decision engine uses Binance:
- Binance M5/second price for confirm;
- Binance M15 ATR snapshot;
- broker quote used only for actual execution.

### Option B — broker-native strategy
Keep broker price/ATR for decisions, but then re-run all historical/OOS research under broker-native price/ATR data.

Do not compare Binance-LAB results to broker-native live logic as if they were the same strategy.

---

## LAB046 toxic gate mismatch

Frozen supported population requires:
- skip same-side prior extreme <=30m;
- skip HIGH_VOL state.

Current v191f has neither exact rule.

Instead it has:
- same-crowd-side confirm;
- min abs Z 0.75;
- adverse 0.75;
- response ratio >=0.50.

These may be reasonable experiments, but they are not the supported LAB046 population.

Required parity implementation:
1. store previous completed same-sign extreme source timestamp;
2. at signal arm, veto if same-sign extreme gap <=30m;
3. compute causal HIGH_VOL exactly as preregistered:
   - current M15 ATR14 / price;
   - lagged rolling q67 of prior 30-day M5 ATR% distribution;
   - 8640 observations;
   - shift 1;
   - min history 2880;
   - UNKNOWN is not HIGH_VOL.
4. apply both gates at signal state before confirmation.

---

## Exit management mismatch

Current v191f:
`InpExitZ=0.00`

LAB047–049 frozen control:
`ExitZ=0.75`

Thus current v191f intentionally removed an exit mechanism that exists in the research control and in the LAB050 3.5 counterfactual.

If the target is exact LAB050 balanced parity:
- ExitZ = 0.75
- SL = 1.5 ATR
- BE = 0.5 / 0.15
- trail = 3.5 / 0.5
- H6
- no fixed TP.

If the target is LAB047 control parity:
- same, but trail = 2.5 / 0.5.

---

## Telemetry/versioning problems

The v191f source still writes:
- `CrowdFade_signals_v191d_consistency_vol_diag.csv`
- `CrowdFade_execution_v191d_consistency_vol_diag.csv`

and source property version is `1.92` although the build identifies itself as v1.91f.

This makes forensic attribution of live trades ambiguous.

Required:
- explicit immutable build ID in every CSV row;
- explicit strategy config hash;
- unique filenames by build;
- log confSourceTimeMs and orderSendSourceTimeMs;
- log signal ATR and entry ATR separately;
- log current Z and original Z;
- log gate results RAPID/HIGH_VOL/fresh/adverse;
- millisecond timestamps.

---

## Recommended repair order

### P0 — fix identity and clock parity first
1. Freeze original signal source timestamp.
2. Remove the M5-bar lock from confirmation monitoring:
   - new signals can remain M5-state based;
   - active confirmation must be evaluated on the 1s timer / incoming broker ticks.
3. Freeze signal ATR and use the chosen research ATR basis consistently.
4. Log exact decision + execution telemetry.

### P1 — restore frozen research population
5. Implement RAPID_REPEAT_30.
6. Implement HIGH_VOL exactly.
7. Freshness measured from original source signal, not local arm time.
8. Remove non-preregistered v191f same-side/minAbsZ/response gates from the strict-parity build, or keep them only in a separate experimental branch.

### P2 — restore management parity
9. ExitZ=0.75.
10. Choose a declared management branch:
   - CONTROL 2.5/0.5; or
   - BALANCED research 3.5/0.5.
11. Preserve SL1.5, BE0.5/0.15, H6, no TP.

### P3 — broker transport
12. Decide whether decision geometry is Binance-native or broker-native.
13. If Binance-native, broker should execute a decision rather than recompute confirmation geometry.
14. If broker-native, new broker-native research is required.

---

## Audit conclusion

The largest current problem is **not broker execution**.

It is that live V191 and the research V191 are different state machines.

The highest-impact mismatch is:
**M5-gated live confirmation + broker-native ATR/price + missing LAB046 toxic gates + ExitZ disabled.**

Before further parameter tuning, build one strict parity version and validate that the same signal stream produces the same:
- arm/skip decision;
- confirmation timestamp;
- ATR snapshot;
- entry;
- management events;
- exit reason

within expected transport/slippage tolerance.


---

## Timestamp-semantics correction after strict implementation

Binance documentation defines the `globalLongShortAccountRatio.timestamp` field as the **end time of the ratio period**.

LAB043/046 price/flow alignment uses:
`searchsorted(flow_time, M5_availability, left) - 1`.

Therefore a flow source point ending at `T` is intentionally used at the next completed price-M5 decision `T+5m`.

Consequences:
- strict live signal decision ID is `flow_source_timestamp + 300s`;
- the corresponding signal price is the Binance M5 close of the bar `[T, T+5m]`;
- the old live order comment used the then-current flow `sourceTimeMs`, not the original armed decision ID, so broker-report `CF191...` timestamps cannot be used as exact original signal timestamps;
- the earlier empirical observation “comment → fill ≈5m” must **not** by itself be interpreted as a 5-minute confirmation delay.

The separate code-level finding remains valid: old v191f checked active confirmation only when a new broker M5 bar appeared. The strict build removes that broker-M5 gate and evaluates an armed confirmation every scheduler pass.
