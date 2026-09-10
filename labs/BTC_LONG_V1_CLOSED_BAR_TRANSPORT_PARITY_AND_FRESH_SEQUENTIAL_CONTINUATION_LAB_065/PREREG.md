# BTC_LONG_V1_CLOSED_BAR_TRANSPORT_PARITY_AND_FRESH_SEQUENTIAL_CONTINUATION_LAB_065

## Purpose
Resolve the LAB064 transport-parity invalidation without altering `BTC_LONG_V1_TIER_A_8H_TP15`, then continue the true post-freeze LONG v1 sequential audit.

This LAB is a data-transport / sequential-validation LAB only. It is **not** an alpha search, strategy repair, parameter optimization, or portfolio-router search.

## Immutable LONG v1 reference
Frozen candidate: `BTC_LONG_V1_TIER_A_8H_TP15` from LAB063.
Freeze/prereg commit: `ccc855df34918ee320a2e8033115fec02b439475`.
Freeze timestamp: **2026-09-10 14:28:51 UTC**.

Frozen rules remain unchanged:
- H4 Supertrend ATR(10) x 3.0 built from BTC M5.
- causal state convention: H4 `BAR_OPEN + lag1`.
- `TIER_A_BUY` iff `st_age > 58` and `st_dir == -1`.
- entries every 8h from causal Tier-A episode onset while active.
- entry at next M1 open at/after `signal_time + 1 minute`.
- H1 ATR14 Wilder; SL = 1.5 x H1 ATR14; TP = 1.5R; max horizon = 48h.
- same-M1 SL/TP ambiguity = SL first.
- primary cost = 5 bps RT; stress = 10 bps RT.
- risk = 0.083333% per LONG slot, max planned episode budget 0.50%.
- no live allocation is authorized.

## LAB064 fact motivating this LAB
LAB064 prereg required 100% exact REST-vs-frozen OHLC parity on all overlapping rows. M1 was 3240/3240 exact. M5 was 832/833 exact; the only mismatch was the **terminal frozen M5 row** at 2026-08-10 21:20 UTC. That row had identical open/high but a frozen low/close 18 USD above the later completed REST bar, consistent with the frozen release ending while that last M5 candle was still forming.

LAB064 remains formally INVALID. LAB065 does not retroactively alter LAB064.

## Frozen closed-bar transport rule — fixed before LAB065 outcomes
A frozen price row is eligible for transport parity and for the historical side of the merged sequential clock only when its bar can be proven closed from the frozen dataset structure itself.

For an interval of length `I`:
- frozen row at open time `t` is `PROVABLY_CLOSED` iff `t + I <= max_frozen_open_time`;
- therefore the terminal frozen row, whose closing boundary lies after the last frozen open timestamp, is `UNPROVEN_TERMINAL` and is excluded from frozen transport;
- this rule is applied identically to M1 and M5; it is not conditional on whether a row happens to match REST.

Consequences fixed before outcomes:
1. Parity is scored only on `PROVABLY_CLOSED` frozen rows intersecting completed REST rows.
2. `UNPROVEN_TERMINAL` frozen rows are not used in the extended sequential dataset.
3. At a timestamp removed as `UNPROVEN_TERMINAL`, a completed REST row may supply that timestamp normally.
4. For timestamps with a `PROVABLY_CLOSED` frozen row, frozen remains canonical and wins merge precedence.
5. REST rows are usable only when their exchange `close_time <= run_started_utc`.

This is a transport rule, not a market-state or outcome filter.

## Price transport parity gates
Evaluate OHLC exact equality with no tolerance and no rounding search.

Required:
- closed M1 overlap >= 250 rows;
- closed M1 exact share = 100%;
- closed M5 overlap >= 100 rows;
- closed M5 exact share = 100%;
- no timestamp shift search;
- no price rounding/quantization fitting;
- no exclusions other than the pre-registered structural closed-bar rule above.

If either closed-bar parity gate fails, verdict = `INVALID_CLOSED_BAR_PRICE_TRANSPORT_PARITY_DO_NOT_INTERPRET_FRESH_LONG`.

## Sequential extension
If transport parity passes:
- build one continuous M1/M5 dataset from eligible frozen rows plus completed REST rows;
- use the frozen LONG v1 algorithm unchanged;
- true fresh signals are those with `signal_time > 2026-09-10 14:28:51 UTC`;
- only signals whose required entry minute exists are instantiated;
- completed trades are scored; still-open trades remain OPEN and do not enter EV/PF;
- no calendar or regime exclusion is permitted.

## Fresh LONG metrics
Report:
- elapsed hours/days since freeze;
- fresh signals with entry;
- completed / open;
- TP / SL / TIME counts;
- EV and PF at 5 bps;
- EV and PF at 10 bps;
- CumR at 5 bps;
- additive realized DD at 0.083333% slot risk;
- peak concurrent LONG positions and peak planned open initial risk;
- current causal Tier-A state and, if active, current episode onset / next scheduled signal when derivable.

## Fresh sequential gates
Promotion cannot occur before sufficient post-freeze observations.

- If completed fresh N < 5: `WATCH_POSTFREEZE_TOO_EARLY__CLOSED_BAR_TRANSPORT_CERTIFIED`.
- If N >= 5, require all:
  1. EV5 > 0;
  2. PF5 >= 1.10;
  3. EV10 > 0;
  4. additive realized DD <= 4.0%;
  5. peak planned open LONG initial risk <= 0.50%;
  6. no tuning.
- If N >= 5 and any economic/risk gate fails: `FAIL_FRESH_LONG_POSTFREEZE`.
- If N >= 5 and all gates pass: `PASS_FRESH_LONG_POSTFREEZE__BROKER_NATIVE_PARITY_STILL_REQUIRED`.

No LAB065 result authorizes live trading. FTMO/broker-native execution parity remains separately required.

## Guardrails
- LAB064 result is not rewritten or upgraded.
- LONG v1 parameters, entry clock, exit rules, costs, and sizing remain frozen.
- SHORT v1 is untouched.
- No conflict policy is studied here.
- No post-result transport exception may be added under LAB065.
- Live allocation remains 0.
