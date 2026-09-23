# V191 STRICT LAB PARITY — IMPLEMENTATION

Status: **IMPLEMENTED — DEPLOYABLE ONLINE PARITY BUILD**

Source:
`Projects/CrowdFade/CrowdFadeMulti_v191_STRICT_LAB_PARITY.mq5`

Default research lane:
- BTCUSD broker symbol -> BTCUSDT Binance reference
- Z threshold = 1.00
- RAPID_REPEAT_30 veto = ON
- HIGH_VOL q67 veto = ON
- confirm = 0.30 signal ATR
- freshness = 45m
- max adverse = 0.75 signal ATR
- v191d confirm consistency = opposite ExitZ contradiction only
- SL = 1.50 signal ATR
- BE = 0.50 / lock 0.15 signal ATR
- ExitZ = 0.75
- H6
- no fixed TP
- no score weighting
- no partial close
- no chase
- no spread-based signal gate
- max 3 trades / UTC day
- pause = 1.0 frozen signal ATR
- default trail = BALANCED 3.5 / 0.5
- allowed LAB049 trail arms by fail-fast guard: 2.5 / 3.5 / 5.0; gap fixed 0.5.

## Exact LAB046 state inputs

### Crowd state
Binance global L/S account ratio, 5m, Z over 72 observations.

Binance ratio timestamp is the end of its 5m period.
To reproduce LAB strict-left price/flow alignment:
`signal_decision = ratio_source_end + 300 seconds`.

### Signal price / ATR
At signal decision:
- signal price = Binance completed M5 close for the bar opening at ratio source time;
- ATR = latest completed Binance M15 ATR14;
- ATR is frozen for confirm, SL, BE, trailing and 1R geometry.

### RAPID_REPEAT_30
Computed from the full returned completed flow stream:
previous same-sign |Z|>=1 extreme within <=30m -> signal skipped.

### HIGH_VOL
Exact preregistered construction:
- ATR% = completed M15 ATR14 / signal M5 close;
- prior 8640 M5 ATR% observations;
- current excluded;
- q67 with linear interpolation;
- minimum 2880 observations;
- UNKNOWN is not HIGH_VOL.

The EA fetches enough Binance 5m price history to reconstruct this state at each eligible signal.

## Confirmation

An armed confirmation is evaluated every execution scheduler pass (~1s), not only on broker M5 bars.

Reference price = Binance USD-M current last price.

BUY confirms when:
`ref >= signal_close + 0.30 * signal_ATR`.

SELL confirms when:
`ref <= signal_close - 0.30 * signal_ATR`.

Before confirmation:
- max adverse >0.75 ATR cancels;
- age >45m cancels.

At confirmation:
- BUY cancels only if current crowd Z >= +0.75;
- SELL cancels only if current crowd Z <= -0.75.

No v191e/v191f same-sign, minAbsZ or response-ratio gate exists in the strict build.

## Broker execution transport

The strategy decision geometry is Binance-native.

Broker quote is used only to execute the validated decision.

Initial broker SL distance:
`1.5 * frozen Binance signal ATR`.

After market fill, the EA re-anchors the SL to the actual broker fill while preserving the same frozen ATR distance.

Position management triggers use Binance reference excursion.
Broker SL levels are the corresponding ATR-normalized levels mapped around actual broker fill.

This makes GetLeveraged and IC consume the same decision geometry; broker differences remain execution/spread/slippage differences.

## Identity / persistence

- isolated magic = 77191
- isolated Terminal Global prefix = CF191P
- original flow source timestamp is frozen at arm
- LAB decision timestamp is separately frozen
- pending confirmation is persisted across restart
- last processed signal source is persisted
- ATR pause anchor / daily trade count are persisted
- execution and signal CSV filenames are strict-build-specific.

## Fail-fast parity guard

The EA refuses to initialize if critical parameters drift from the frozen LAB family.

Only trail arm may be one of the preregistered LAB049 values:
- 2.5
- 3.5
- 5.0

Everything else is frozen.

## One unavoidable replay-vs-live distinction

LAB046/049 replay examines the future path of one signal before advancing to the next signal index. In rare cases a failed older candidate can cause the offline replay to later select a younger signal at a timestamp that had already passed by the time the older failure became knowable.

That exact behavior is not physically deployable in real time.

The strict EA therefore uses the causal online equivalent:
- one priority confirmation thesis at a time per symbol;
- later signals are not allowed to retroactively create an earlier fill.

With the LAB046 RAPID_REPEAT_30 veto this difference is narrower, but it is not mathematically zero.

## Validation performed

Static source assertions PASS:
- one TryEnter implementation
- one ManagePositions implementation
- one FetchOne implementation
- balanced braces/parentheses/brackets
- RAPID30 present
- HIGH_VOL present
- q67 8640 / min 2880 present
- signal ATR used for initial stop
- ExitZ 0.75 default
- score off
- spread signal gate off
- same-side/noise v191f gates absent
- isolated magic/global namespace
- strict arm/entry/fill telemetry present

MetaEditor compilation is still required before demo deployment because this environment has no MQL5 compiler.
