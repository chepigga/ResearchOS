# AEIF shadow deployment

## v001 topology
Run **two MT5 terminals on the same Windows VPS and Windows user**:

`AMP/CQG GC sensor → FILE_COMMON → target XAU MT5 shadow executor`

`FILE_COMMON` is intentionally used first to remove network-relay uncertainty from the forward experiment.

## AMP terminal
1. Copy/compile `AMP_GC_AEIF_SHADOW_SENSOR_001.mq5`.
2. Attach it to a chart in the AMP terminal.
3. Set `InpGCSymbol` to the active AMP GC contract. Current default: `GCEZ26`.
4. Leave frozen inputs unchanged: 7-day bootstrap, 200 ms polling, common bridge paths.
5. Expected Journal line: `AMP_GC_AEIF_SHADOW_SENSOR_001 started. NO TRADING.`

The sensor bootstraps historical AMP trade ticks only to seed ATR14 and prior-240 causal references. Historical confirmations are not emitted. Forward confirmations are appended to the shared bridge.

## XAU terminal
1. Copy/compile `XAU_AEIF_SHADOW_EXECUTOR_001.mq5`.
2. Attach it to the target broker/FTMO XAU chart.
3. Set `InpXAUSymbol` to the exact broker symbol (`XAUUSD`, suffix variant, etc.).
4. Keep `InpMaxSignalAgeMs=5000`, `InpSessionGapMs=90000`, TP3R, 240m and single-position semantics unchanged during this forward sample.
5. Expected Journal line: `XAU_AEIF_SHADOW_EXECUTOR_001 started. ZERO ORDER FUNCTIONS.`

The XAU EA consumes the complete live tick stream through `CopyTicks(COPY_TICKS_ALL)` so Bid/Ask stop/target touches between timer snapshots are not lost.

## Safety
Both files contain **zero order/position-management API calls**. Keep the terminal's Algo Trading switch OFF as an additional operational safety layer during shadow collection.

## Files to watch
Under `Terminal/Common/Files/AEIF_SHADOW_001/`:

- `sensor_heartbeat.csv` — AMP sensor health.
- `xau_heartbeat.csv` — XAU shadow health.
- `signals.csv` — immutable forward confirmation packets; created after the first signal.
- `sensor_events.csv` — GC CORE / confirm / expiry diagnostics.
- `xau_shadow_events.csv` — OPEN / CLOSE / REJECT outcomes including spread, transport lag, MFE/MAE and R.

## Freeze discipline
Do not change AEIF thresholds, aggressor bridge, confirmation logic, stale gate, SL/TP, hold time or single-position policy inside this forward sample. Any change gets a new LAB/version.

## Different VPS machines
`FILE_COMMON` only shares files between terminals on the same machine. If AMP and XAU terminals are on different VPS machines, use a network bridge version next; do not alter the frozen signal or shadow-execution rules while changing transport.
