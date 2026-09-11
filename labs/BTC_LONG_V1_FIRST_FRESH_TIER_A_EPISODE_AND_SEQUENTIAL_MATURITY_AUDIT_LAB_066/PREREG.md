# BTC_LONG_V1_FIRST_FRESH_TIER_A_EPISODE_AND_SEQUENTIAL_MATURITY_AUDIT_LAB_066

## Purpose
Observe the already-frozen BTC LONG v1 after its LAB063 freeze and determine whether the first true post-freeze Tier-A episode has appeared, how mature the current causal bearish Supertrend episode is relative to the frozen `st_age > 58` threshold, and whether any frozen 8h LONG slots have become executable/completed.

This LAB is a **sequential maturity audit only**. It must not change the LONG v1 state definition, clock, exits, costs, risk, data transport rules, or promotion gates.

## Immutable LONG v1
Reference freeze: LAB063 candidate `BTC_LONG_V1_TIER_A_8H_TP15`.
Freeze timestamp: **2026-09-10 14:28:51 UTC**.

Frozen rules:
- H4 Supertrend ATR(10) x 3.0 from BTC M5.
- Causal convention: H4 BAR_OPEN with one raw H4-bar lag, identical to LAB063-LAB065.
- Tier-A BUY iff `st_dir == -1` and `st_age > 58`.
- Entry slots every 8h from the causal Tier-A episode onset while Tier-A remains active.
- Entry at the next M1 open at/after `signal_time + 1 minute`.
- SL = 1.5 x H1 ATR14.
- TP = 1.5R.
- Time exit = 48h.
- Same-M1 ambiguity = SL first.
- Cost = 5 bps primary, 10 bps stress.
- Episode risk budget = 0.50%; slot risk = 0.50/6 = 0.0833333333%.
- Live allocation remains 0.

## Data transport
Reuse the separately preregistered LAB065 closed-bar bridge.
- Frozen row at open time `t` is parity-eligible iff `t + interval <= max_frozen_open_time`.
- Apply the same structural rule to M1 and M5 before observing parity outcomes.
- REST bars require `close_time <= run_started_utc`.
- Closed-bar parity must remain 100% exact with zero OHLC difference: M1 overlap >=250, M5 overlap >=100.
- No tolerance and no mismatch-specific filtering.
- Merged frozen->REST M1/M5 continuity must have zero interval gaps in the audit span.

## First fresh Tier-A definition
Consider causal clock rows with `time > 2026-09-10 14:28:51 UTC`.

`first_fresh_tier_a_onset` is the earliest such row with `state == TIER_A_BUY` and the immediately prior causal row not `TIER_A_BUY` (or no prior post-freeze row).

If Tier-A has not appeared, report `null`; this is not a failure.

## Maturity state
At the final causal H4 row report:
- `st_dir`, `st_age`, and frozen state.
- If `st_dir == -1`, report `bars_to_tier_a = max(0, 59 - st_age)` because frozen activation requires integer age >58.
- `hours_to_tier_a_at_4h_per_bar = 4 * bars_to_tier_a` is a mechanical maturity distance, **not a forecast** because the Supertrend direction can reset before then.
- Determine the current continuous `st_dir == -1` bearish Supertrend episode onset and its observed duration.
- Never infer future Tier-A activation if the bearish episode ends.

## Sequential slots and trades
- Enumerate every frozen 8h slot from every fresh Tier-A onset.
- Replay only signals `> freeze timestamp` using the immutable execution rules.
- Preserve open trades as OPEN until TP/SL/time exit is actually observed.
- Report first slot time, all fresh slots, completed/open count, outcomes, EV/PF only once defined.

## Gates
Technical validity:
1. Closed M1 overlap >=250 and exact share = 100%, max diff 0.
2. Closed M5 overlap >=100 and exact share = 100%, max diff 0.
3. M1 continuity gap count = 0.
4. M5 continuity gap count = 0.
5. No tuning; frozen LONG unchanged.

Fresh promotion gate remains LAB065:
- Until >=5 completed post-freeze trades: WATCH only.
- Once N>=5: EV5>0, PF5>=1.10, EV10>0, realized additive DD<=4%, peak open LONG initial risk<=0.50%.
- Broker-native parity remains separately required before live allocation.

## Verdict hierarchy
- Technical gate failure -> `INVALID_TRANSPORT_OR_CONTINUITY_DO_NOT_INTERPRET_LONG`.
- Valid transport, no fresh Tier-A yet -> `WATCH_WAITING_FIRST_FRESH_TIER_A_EPISODE`.
- First fresh Tier-A exists but <5 completed fresh trades -> `WATCH_FIRST_FRESH_TIER_A_OBSERVED__SEQUENTIAL_N_LT5`.
- N>=5 and fresh gates fail -> `FAIL_FRESH_LONG_POSTFREEZE`.
- N>=5 and fresh gates pass -> `PASS_FRESH_LONG_POSTFREEZE__BROKER_NATIVE_PARITY_STILL_REQUIRED`.

No PnL-driven alteration is permitted after this preregistration.