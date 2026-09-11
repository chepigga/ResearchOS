# XAU_CONTEXT_INDICATOR_STATE_VALIDATION_LAB_007 — PREREG

## Objective
Validate whether the frozen causal H4 Context indicator partitions XAUUSD into meaningfully different future market states. This is **not** an alpha/EA/profitability test. No TP/SL, no position sizing, no PF/EV gate.

## Frozen input and Context
- Canonical XAUUSD M1 asset: release `ak47`, `XAUUSD_M1_20220601_20260723_TICK_NATIVE.csv`.
- Required SHA256: `db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b`.
- H4 Context implementation is frozen from `CROSS_MARKET_CAUSAL_CONTEXT_ROUTER_LAB_001` with the already-audited technical parity hotfixes only:
  1. `d.stack` pandas name collision -> `d['stack']`;
  2. readiness mask before 3-bar score smoothing;
  3. no state attached before a valid frozen regime exists.
- Regimes: `EXPANSION`, `PULLBACK`, `REVERSAL`, `RANGE`.
- Context bar timestamp is H4 open; state is usable only at that H4 bar close (`available_time = H4 open + 4h`).
- No threshold, weight, hysteresis, score, or feature tuning is allowed in this lab.

## Primary sampling unit
Primary sample = **state episode onset**: first causally available H4 state in each contiguous run of one regime. This avoids pseudo-replication from repeated adjacent H4 bars and overlapping 24h forward windows.

Secondary diagnostic sample = every eligible H4 state bar. Secondary results cannot override the primary verdict.

## Causal reference and normalization
At each state observation:
- reference price = close of the H4 bar that produced the state (known at `available_time`);
- scale = ATR14(H4) known at that same close;
- future path starts at/after `available_time` only;
- pre-state momentum direction = sign(`close_t - close_{t-3 H4}`), fully known before the forward window;
- Context bias direction = `BULL=+1`, `BEAR=-1`, `NEUTRAL=0`.

## Frozen horizons
Primary horizon: **24h**.
Secondary shape horizons: **4h, 12h, 48h**.

## Forward state metrics
For each observation and horizon H:
1. `abs_close_atr_H = abs(close_H - ref) / ATR14`.
2. `range_atr_H = (future_max_high - future_min_low) / ATR14`.
3. `up_exc_atr_H = (future_max_high - ref) / ATR14`.
4. `down_exc_atr_H = (ref - future_min_low) / ATR14`.
5. `contained_1atr_H = 1` iff neither +1 ATR nor -1 ATR is touched during H.
6. `two_sided_1atr_H = 1` iff both +1 ATR and -1 ATR are touched during H.
7. `momentum_flip_H = 1` iff the H close return is opposite the frozen pre-state 12h momentum direction; observations with zero pre-momentum are excluded from this metric.
8. `bias_follow_H = 1` iff the H close return is in the frozen Context bias direction; NEUTRAL bias observations are excluded.
9. `bias_signed_close_atr_H = bias_dir * (close_H-ref)/ATR14` where bias is non-neutral.

No future state labels are used to define outcomes.

## Episode/transition diagnostics
Using all eligible H4 state bars, report:
- occupancy by state;
- contiguous episode count and episode duration in H4 bars/hours;
- one-step transition matrix and row-normalized probabilities;
- self-transition rate;
- state confidence distribution.
These are descriptive and are not profitability gates.

## Primary semantic hypotheses (24h, episode-onset sample)
The indicator is judged by whether its labels correspond to different future behavior, not by positive trading expectancy.

### H1 — Expansion has more realized movement than Range
`mean(range_atr_24h | EXPANSION) - mean(range_atr_24h | RANGE) > 0`.

### H2 — Expansion has more terminal displacement than Range
`mean(abs_close_atr_24h | EXPANSION) - mean(abs_close_atr_24h | RANGE) > 0`.

### H3 — Range contains price better than Expansion
`P(contained_1atr_24h | RANGE) - P(contained_1atr_24h | EXPANSION) > 0`.

### H4 — Reversal is more likely to flip pre-state momentum than Expansion
`P(momentum_flip_24h | REVERSAL) - P(momentum_flip_24h | EXPANSION) > 0`.

### H5 — Pullback is more likely than Range to resume the existing Context bias
Among non-neutral bias observations:
`P(bias_follow_24h | PULLBACK) - P(bias_follow_24h | RANGE) > 0`.

## Inference
- Primary uncertainty: weekly cluster bootstrap, 5,000 draws, fixed seed `2026091107`.
- Weeks are resampled jointly across states so pairwise contrasts retain common calendar structure.
- A primary semantic gate passes only if its observed difference has the expected sign **and** the 95% weekly-cluster bootstrap lower bound is > 0.

## Time transfer
For full calendar years 2023, 2024, 2025, 2026 YTD, compute the five primary effect signs without re-estimating anything.
- For each hypothesis, `year_sign_support` = number of eligible years with the preregistered positive sign.
- Transfer gate: at least **3 of the 5 hypotheses** must have the expected sign in **>=3/4 eligible years**.
- 2022 is reported but excluded from the transfer gate because it is partial and contains causal warm-up.

## Verdict rules
Let `semantic_passes` be the number of H1–H5 whose weekly-bootstrap CI lower bound is > 0.

- `CONTEXT_STATE_SEMANTICS_SUPPORTED_DISCOVERY_ONLY` if `semantic_passes >= 4` AND the time-transfer gate passes.
- `PARTIAL_CONTEXT_STATE_SEPARATION` if `semantic_passes` is 2–3, or `semantic_passes >=4` but transfer fails.
- `CONTEXT_STATE_SEMANTICS_NOT_SUPPORTED` if `semantic_passes <=1`.

These verdicts validate/destructively test **state description only**. They do not authorize entries, risk modulation, or live trading.

## Anti-overfit rules
- No outcome-driven state redefinition.
- No threshold search.
- No post-result horizon selection; 24h is primary.
- No dropping states because they look weak.
- Secondary 4/12/48h and all-bar results are diagnostics only.
- Any newly discovered useful interaction must be preregistered in a later lab before being treated as a hypothesis.
