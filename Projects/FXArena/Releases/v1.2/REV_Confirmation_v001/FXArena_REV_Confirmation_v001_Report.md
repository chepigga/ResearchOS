# FXArena REV_Confirmation v001

## Verdict

**F11_SHALLOW_ACCEPTANCE_REV_FALSIFIED**

RC1 failed on the clean 2023 control. Per the frozen specification, RC2–RC6 were not executed and the REV EA question is closed for this funnel.

## Blocking question: where was 2023?

**Scenario (a).** The exploratory result was reported on 2024–2026H1 before the supplied `LevelBattleEvents v003` file was generated on 2026-07-21. The supplied engine artifacts now cover 2023-01 onward, so 2023 was treated as the out-of-dataset control. This is a chronology-based provenance inference and is recorded explicitly.

## Provenance

- Generator identity from artifact naming/schema: `FXArena LevelBattleEngine v003 EVENT_STREAM`.
- Event rows: 1,196,467; `ACCEPTANCE_CONFIRMED`: 106,079; coverage 2023-01-02 through 2026-07-17.
- Exact SHA256 values are in `SOURCE_ARTIFACTS_SHA256.csv`.
- The code that reconstructs D3 penetration and replays trades is published as `run_REV_Confirmation_v001.py`.

## Critical causal audit

The exploratory reference aligns with `Rounds.max_penetration_atr`, but that field is the maximum accumulated through the episode end. It is not the value known at D3.

| Population audit, 2024–2026H1 | N |
|---|---:|
| Acceptance events | 78880 |
| True causal `max_penetration_seen@D3 <= 1.0` | 31749 |
| Final-episode `max_penetration_atr <= 1.0` | 8299 |
| Shallow at D3 but deepened beyond 1R later | 23467 |

The final-episode filter excludes 23467 episodes using future post-D3 behavior. This explains why it approximately recreates the strong candidate, while the genuinely causal D3 snapshot does not.

## RC1 — 2023 out-of-dataset control

| Metric | Requirement | Observed | Gate |
|---|---:|---:|---|
| N | >= 300 | 2109 | PASS |
| EV | >= +0.15R | -0.287213R | FAIL |
| PF | >= 1.30 | 0.6570 | FAIL |
| Negative months | <= 2/12 | 12/12 | FAIL |
| First half | > 0 | -280.523R | FAIL |
| Second half | > 0 | -325.209R | FAIL |

Additional metrics:
- Win rate: 30.63%.
- Total: -605.733R.
- Gross MaxDD: 184.000R.
- Net MaxDD: 611.473R.

## 0.75 threshold diagnostic

The non-production 0.75 threshold also fails: N=1738, EV=-0.304R, PF=0.64, negative months=12/12. It does not rescue the mechanism.

## In-sample causal diagnostic, 2024–2026H1

The true D3 snapshot is also negative on the original reference period: N=5830, EV=-0.271R, PF=0.68, total=-1580.0R, negative months=29/30.

## Gate execution

- RC1: **FAIL**.
- RC2 permutation: NOT EXECUTED.
- RC3 bootstrap: NOT EXECUTED.
- RC4 cost stress: NOT EXECUTED.
- RC5 delay realism: NOT EXECUTED.
- RC6 portfolio with CONT: NOT EXECUTED.

## Governance

- F11 is now active: `shallow-acceptance REV` does not survive the causal D3 reconstruction/control year.
- No threshold, delay, stop, target, dedup, or selection tuning was performed after the result.
- The final-episode penetration proxy is prohibited for deployment and future confirmation claims.
- ContPrimary remains untouched.
- No EA code is produced.
