# FXArena Flag-Replay v001.2 — tb_flag regeneration and C1–C4 closure

## Verdict

**STOP_ALARM_P4B_TRANSFER_GATE_FAIL**

- Frozen TB generator control: **PASS 3535/3535**, mismatches **0**.
- Archived P4b replay control: **PASS**, exit-time mismatches **0**, total +2256.511802R.
- Full universe flag artifact: **291659 episodes**, TB true 57811 (19.82%).
- Trailing set: **3515 episodes**, TB true 1244 (35.39%).
- Newly covered trailing-only episodes: **622**, TB true 196.

## Frozen generator law

`tb_flag = EFFICIENCY_5 OR BB_EXPANSION OR RANGE_EXPANSION_15`

- `EFFICIENCY_5`: `abs(close-close_5) > 0.6*sum(abs(delta_close),5)` and directional displacement.
- `BB_EXPANSION`: directional close outside Bollinger(20,2), population standard deviation `ddof=0`.
- `RANGE_EXPANSION_15`: current M5 range `> 1.5*mean_range_20` and directional candle body.
- Exact archived observation convention: M5 `label=right, closed=left`; snapshot labeled `decision_3bar_time + 35 min`.
- No outcome, MFE, exit result, or post-trade value is used by the generator.

## Controls

| Control | N | Result |
|---|---:|---|
| Frozen tb_flag parity | 3535 | PASS, 0 mismatches |
| Archived P4b replay | 3535 | PASS, 0 exit-time mismatches |

## Trailing C1–C4

| Metric | P0 trailing | P4b trailing |
|---|---:|---:|
| N | 3515 | 3515 |
| Total R | +1889.613320 | +2277.306670 |
| EV R | +0.537586 | +0.647882 |
| Gross MaxDD R | 14.415969 | 10.618161 |
| Negative months | 0 | 1 |
| Worst month R | +1.266512 | -2.040203 |
| All years positive | True | True |

| Gate | Requirement | Observed | Result |
|---|---|---:|---|
| C1 | P4b total >= P0 * 1.10 | +2277.306670R vs +2078.574652R | PASS |
| C2 | P4b gross DD <= P0 + 0.5R | 10.618161R vs 14.915969R | PASS |
| C3 | Neg months <= P0; all years >0 | 1 neg; years positive=True | FAIL |
| C4 | P(total P4b > P0) >= 0.95 | 100.00% | PASS |

C4 uses paired moving-block bootstrap, shared indices, block 20, 5000 iterations, seed `2026072405`. Diagnostic `P(DD_P4b > DD_P0+0.5R)` = 0.72%.

## Pin and registry

- `trades_P4b_TRAILING_PINNED.csv.gz`: NOT CREATED.
- Registry status: **NOT_PROMOTED**.
- This pin is the forward A/B and deploy-R2 reference only when all C1–C4 pass.

## Governance

- No feature, threshold, observation window, selector, or exit tuning.
- P4b rules remain archived and unchanged.
- Flag is not inferred from outcome.
- ContPrimary untouched.
- F1–F10 remain active.

## Important deployment boundary

This session reproduces and transfers the **archived P4b policy exactly as frozen**. The separate forensic audit identified that the archived policy applied the 30-minute flag retrospectively from trade inception. That causal-policy concern is not repaired here because P4b rule changes were explicitly prohibited. A live implementation still requires a separately preregistered causal P4c test or an explicit governance decision accepting the archived convention.
