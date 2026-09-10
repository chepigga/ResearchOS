# BTC_LONG_POSITIVE_LINEAGE_RECONCILIATION_AND_FROZEN_V1_LAB_063

## Purpose
Reconcile the already-observed positive BTC BUY/LONG research lineage and freeze one simple, causal, prop-compatible LONG candidate without post-result threshold tuning.

This is **not** a new alpha search. Candidate families are limited to previously tested BUY lineages already present in ResearchOS.

## Reconciled lineage universe
1. **Recent H4 two-bar reversal BUY (LAB019–021)**
   - Strong in 2025H2–2026 but historically unstable; pre-recent windows include material negative EV and August reused audit is negative.
   - Calendar/regime cutoffs are not allowed because LAB020 did not establish a robust causal onset and LAB021 did not establish a robust compression mechanism.
   - Therefore this family cannot become LONG v1 in LAB063.
2. **v283 exact-timing BUY**
   - Exact v283 timing depends on timer/tick-driven broker state and was not proven to be the source of Tier-A edge.
   - U02C4 same-state random null indicates most Tier-A BUY edge is carried by the market-clock state, not by the v283 timestamp.
   - Therefore v283 is not mandatory for LONG v1.
3. **B3 BUY state**
   - U02C5 state-only periodic tests deteriorate in 2026 and are phase-sensitive.
   - Therefore B3 is rejected for LONG v1.
4. **Tier-A BUY state**
   - U02C4 supports state-level edge.
   - U02C5 shows deterministic periodic Tier-A entries positive across 2024/2025/2026 and robust to clock phase; 8h was the previously identified preferred cadence.
   - This is the only family eligible for LONG v1 translation in LAB063.

## Frozen LONG v1 candidate (fixed before this LAB outcome)
Name: `BTC_LONG_V1_TIER_A_8H_TP15`

### State clock
- Source price clock: existing frozen BTC M5/M1 release data.
- H4 bars are resampled from M5.
- H4 Supertrend: ATR(10), multiplier 3.0, same implementation as U02C5.
- Causal convention: at H4 bar-open `t`, use the **previous completed H4 raw state** (`BAR_OPEN + lag1`).
- `TIER_A_BUY` iff `st_age > 58` AND `st_dir == -1`.
- A Tier-A episode starts on the first causal H4 row entering this state and ends when the state changes or a >4h01m data gap breaks continuity.

### Entry clock
- Primary cadence: every **8 hours from causal Tier-A episode onset** while the state remains active.
- Entry: next available M1 open after `signal_time + 1 minute`, identical timing convention to U02C5.
- No v283, FVG, funding, calendar cutoff, score, news, or extra price filter.

### Exit translation required by current prop rules
The strongest U02C5 state-clock lineage used no TP, which is not deployable under the current project rule requiring TP >= 1.5 x SL. Therefore LAB063 freezes the following translation **before its result is inspected**:
- ATR source: latest completed H1 ATR14, Wilder convention inherited from U02C5/U02C2.
- SL distance: `1.5 * H1_ATR14`.
- TP distance: `1.5R` (therefore TP = 2.25 * H1 ATR14 from entry).
- Maximum horizon: 48 hours; if neither SL nor TP has hit, close at the next M1 open at/after 48h.
- If both SL and TP are touched inside the same M1 bar, score **SL first** (conservative ambiguity rule).

This TP translation is a **new frozen execution candidate**, not an already-proven result. Historical/reused results in this LAB can reject it but cannot promote it to fresh OOS.

### Costs
Report three views without choosing among them after outcomes:
- legacy lineage proxy: `$27.5 per BTC round-turn`;
- 5 bps round-turn stress proxy;
- 10 bps round-turn stress proxy.

Primary economic gates use **5 bps**; 10 bps is a mandatory stress gate.

### Prop risk accounting
- Max initial risk budget per Tier-A episode: **0.50%**.
- With 8h cadence and 48h horizon, max planned slots = 6.
- Nominal risk per slot = `0.50% / 6 = 0.083333%` of equity.
- This keeps aggregate planned initial-risk budget <=0.50% per Tier-A episode before considering exits.
- No live allocation is authorized by this LAB.

## Robustness diagnostic fixed before outcomes
One non-promoting clock-phase diagnostic:
- same exact candidate but entries at `episode onset + 4h`, then every 8h while the state remains active.
- No other offsets/cadences may be searched in LAB063.

## Evaluation windows
- `REUSED_2024_2026`: all available frozen release data from 2024-01-01 through the release tail. This is reused development/replication history, **not fresh OOS**.
- Year splits: 2024, 2025, 2026.
- No post-hoc calendar filtering.

## Required metrics
For primary and +4h phase diagnostic:
- Tier-A episodes
- candidate entries / completed trades
- trades/week
- EV_R and PF under legacy, 5bps, 10bps costs
- CumR
- win rate
- max drawdown in R
- additive realized DD under 0.083333% slot risk
- peak concurrent positions
- per-year N, EV5, PF5, CumR5
- TP / SL / TIME distribution

## Reused-history acceptance gates for the frozen translation
All must pass for verdict `FROZEN_LONG_V1_CANDIDATE_READY_FOR_FRESH_OOS`:
1. primary completed trades >= 100;
2. primary EV5 > 0;
3. primary PF5 >= 1.30;
4. primary EV10 > 0;
5. primary PF10 >= 1.10;
6. primary 2024, 2025, and 2026 each have positive EV5 where N>=5;
7. primary realized additive DD at slot risk <=4.0%;
8. peak concurrent positions <=6;
9. +4h phase diagnostic EV5 > 0 and PF5 >=1.10;
10. no tuning / exclusions after outcomes.

If any core economics gate fails, verdict is `REJECT_TP15_TRANSLATION_DO_NOT_FREEZE_LONG_V1`.
If reused gates pass, the rule is frozen as a **candidate only** and still requires fresh sequential OOS plus FTMO/broker-native parity before live use.

## Guardrails
- Existing historical findings may be summarized but not reinterpreted as fresh OOS.
- No optimization of age=58, ST multiplier, cadence, SL, TP, horizon, or costs in LAB063.
- No result from LAB063 may be used to silently alter the candidate and rerun it under the same LAB number.
- Frozen SHORT v1 is untouched.
- Live allocation remains 0.