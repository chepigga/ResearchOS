# CrowdFade three-bot risk-guard fix — 2026-09-26

Affected forward candidates:
- CF191g broker-normalized v197 -> fixed candidate v198
- CF191s broker-normalized v197 -> fixed candidate v198
- CF200 broker-normalized v205 -> fixed candidate v206

## Observed failure
Runtime emitted impossible ~50% daily/total drawdown stops although the account had no such drawdown.

## Root cause
The DD guard restored `EQPEAK`, `DAYEQ`, `HALTDAY`, and `HALTALL` from persistent MT5 terminal Global Variables. The old namespace was keyed by bot/account/magic but did not include broker server or a risk-state schema/version. A stale anchor could therefore survive upgrades/state changes and be compared with current equity. Example: stale peak near 200k vs current equity near 100k produces a false ~50% DD.

## Patch applied to all three bots
1. Risk state moved to a new `RISK2` namespace.
2. Namespace includes broker server + account login + magic + bot family.
3. Legacy risk anchors and halt flags are not imported into RISK2.
4. Cooldown/order/position state remains in the existing bot namespace; only DD state is isolated.
5. `InpResetRiskState` now resets the RISK2 DD keys.
6. Startup diagnostics print equity, balance, dayStart, eqPeak, haltDay, haltAll, and risk namespace.
7. Stop diagnostics now print the actual equity and anchor used in the calculation.
8. Daily DD remains `(dayStartEquity-currentEquity)/dayStartEquity`.
9. Total DD remains high-water equity DD `(equityPeak-currentEquity)/equityPeak`.

## Important safety decision
No automatic adjustment from `ACCOUNT_BALANCE` changes was added because normal realized trading P/L changes balance and must not be mistaken for deposits/withdrawals. The patch fixes contamination by namespacing rather than weakening the DD guard.

## Expected first-run behavior
On first launch of the fixed build, with no RISK2 state, `dayStart == current equity` and `eqPeak == current equity`; both halt flags are false. Subsequent restarts on the same broker server/login/magic restore only the new valid RISK2 state.

## Files produced in the working conversation
- `CrowdFadeMulti_CF191g_RISK_GUARD_FIXED_v198.mq5`
- `CrowdFadeMulti_CF191s_RISK_GUARD_FIXED_v198.mq5`
- `CrowdFadeMulti_CF200_RISK_GUARD_FIXED_v206.mq5`

Compile in MetaEditor before deployment; this environment does not provide the MT5 compiler.