# XAU_H1_CONTEXT_ALIGNED_MAE_FIRST_PASSAGE_STOP_PATH_LAB_005

Status: PREREGISTERED BEFORE OUTCOME INSPECTION

## Frozen lineage

- Universe: XAU causal pool from LAB003/LAB004, exact frozen parity 263,405 context-eligible events.
- Test subset: `tf == H1`, `context_score > 0.55`, compatibility in {ALIGNED, OPPOSED}.
- Context formula remains frozen: `(Expansion + Pullback - Reversal - Range) / 200`.
- No Context threshold optimization and no TF deletion.
- Current H1 risk unit: `1R_current = 1.5 * ATR14(H1)` measured from the H1 signal close available at event time.
- Native XAU M1 price path only; no future information enters feature selection.

## Primary structural contradiction to explain

LAB004 showed negative realized H1 HIGH alignment premium in frozen trade outcome while common-clock forward directional premium was positive. LAB005 asks whether aligned events are disproportionately stopped first and only later recover in the forecast direction.

## Path construction

For each eligible H1 event, start at `available_event_time` and inspect native M1 OHLC up to 120 elapsed hours. Entry reference is frozen H1 signal close; ATR reference is causal ATR14(H1) from that completed signal bar.

Directional path in current R units:

`path_R = dir * (price - signal_close) / (1.5 * ATR14_H1)`

For intraminute ambiguity where the same M1 bar touches both adverse and favorable barriers, classify the first-passage result as AMBIGUOUS and exclude it from ordering estimators. For executable stop/TP ablations, use conservative STOP-FIRST treatment for same-bar ambiguity.

## Predeclared diagnostics

1. MAE/MFE over 10h, 30h, 120h for ALIGNED vs OPPOSED.
2. Symmetric first passage at `±0.5R`, `±1.0R`, `±1.5R` over 10h/30h/120h.
3. Current-stop late-recovery trap:
   - current stop barrier = `-1.0R_current` (= -1.5 ATR)
   - first favorable comparison barrier = `+1.0R_current`
   - `STOP_FIRST` means adverse barrier is reached before favorable barrier.
   - `STOP_FIRST_RECOVER_PLUS1_120H` means STOP_FIRST occurs and price subsequently reaches `+1.0R_current` by 120h.
   - `STOP_FIRST_RECOVER_ZERO_120H` means STOP_FIRST occurs and price subsequently returns to >= 0R by 120h.
4. Time from first stop hit to recovery-to-zero and recovery-to-+1R when recovery occurs.
5. Stop-width ablation only, not optimization:
   - SL = 1.0 ATR, 1.5 ATR, 2.0 ATR
   - TP fixed at 1.5R_stop for every width to respect minimum R:R 1:1.5
   - horizon fixed at 120h
   - same-bar SL/TP touch is scored as SL first (conservative).

## Primary estimator

`Delta_recovery = P(STOP_FIRST_RECOVER_PLUS1_120H | ALIGNED) - P(... | OPPOSED)`.

Weekly-cluster bootstrap, 5,000 draws. Structural stop-path support requires:

- S1: `Delta_recovery > 0`.
- S2: weekly-cluster bootstrap 95% CI lower bound for `Delta_recovery` > 0.
- S3: aligned 120h terminal directional premium remains > 0 versus opposed (replication of LAB004 direction information).
- S4: realized frozen H1 trade premium remains < 0 (replication of the contradiction being explained).
- S5: `Delta_recovery` positive in at least 3 of 4 eligible years (2023-2026; 2022 may be unavailable from H1 Context warm-up).
- S6: leave-one-year-out `Delta_recovery` positive in at least 3 of 4 runs.

Passing all S1-S6 supports `H1_STOP_PATH_MISMATCH_SUPPORTED_DISCOVERY_ONLY`.

## Secondary interpretation

- A strong positive recovery delta with negative realized trade premium supports path/stop mismatch rather than direction-model failure.
- If wider-stop ablation improves aligned-vs-opposed separation, it is only a mechanistic clue. No stop width is promoted because all widths are inspected on reused history.
- No live filter, sizing change, stop change, or production promotion is authorized from this LAB.
