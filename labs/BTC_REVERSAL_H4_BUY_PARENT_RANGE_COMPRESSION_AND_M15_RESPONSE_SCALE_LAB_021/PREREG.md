# BTC_REVERSAL_H4_BUY_PARENT_RANGE_COMPRESSION_AND_M15_RESPONSE_SCALE_LAB_021

## Question
Does the recent H4 two-bar BUY edge improve mechanically as H4 parent sweep range compresses, and is that improvement strengthened by larger M15 child response scale and/or deeper VF maturity?

## Frozen lineage
- Start from persisted LAB020 causal BUY opportunity table.
- No signal reconstruction, no rule changes, no calendar gate, no RR/TTL/entry changes.
- BUY-only H4 TWO_BAR_CONFIRM_12H + VF1 real-risk lineage exactly as LAB019/LAB020.
- August 2026 remains reused stress-audit only.

## Primary parent-range test
Fixed bins on `parent_range_pct` (fraction of price):
1. `<1.0%`
2. `1.0–1.5%`
3. `1.5–2.0%`
4. `2.0–3.0%`
5. `>=3.0%`

No post-hoc threshold promotion is allowed.

For each bin report opportunities, real fills, CumR, mean R/fill, PF, DD, positive-fill rate separately for:
- HIST_PRE_RECENT = 2021-01-01..2025-06-30
- 2025_H1
- 2025_H2
- 2026_JAN_JUL
- POOLED_RECENT = 2025-07-01..2026-07-31
- AUG2026_REUSED_AUDIT

## Threshold-free monotonicity
On real BUY fills:
- Spearman correlation between `parent_range_pct` and `real_R` for pooled recent.
- Same for HIST_PRE_RECENT and ALL_PRE_AUG.
- Episode-cluster bootstrap 5000 draws for pooled recent Spearman rho and for mean-R difference between compact `<1.5%` and large `>=1.5%` parents.

Mechanistic support requires smaller parents to be better; expected sign rho < 0.

## M15 response-scale interaction
Use fixed `child_parent_range_ratio` bins:
- LOW `<0.15`
- MID `0.15–0.25`
- HIGH `>=0.25`

Cross with parent class:
- COMPACT `<1.5%`
- LARGE `>=1.5%`

Report opportunities, fills, CumR, meanR, PF, DD in recent and historical windows.

Hypothesis: if parent compression is a real mechanism rather than a calendar proxy, COMPACT+HIGH response should outperform COMPACT+LOW/MID, while LARGE parents should remain weaker even with a high child ratio.

## VF maturity interaction
Among real fills, split by prior virtual fills:
- VF1 = exactly 1 prior virtual fill
- VF2PLUS = >=2 prior virtual fills

Cross with COMPACT/LARGE parent class. Report economics in pooled recent and historical windows.

## Primary gates
1. `recent_compact_cumR_positive`: pooled recent `<1.5%` CumR > 0.
2. `recent_compact_mean_gt_large`: pooled recent meanR compact > large.
3. `recent_spearman_negative`: pooled recent Spearman rho(parent_range, R) < 0.
4. `bootstrap_compact_minus_large_low_gt_0`: episode-bootstrap 95% CI lower bound for compact-minus-large meanR > 0.
5. `bootstrap_spearman_high_lt_0`: episode-bootstrap 95% CI upper bound of recent Spearman rho < 0.
6. `both_recent_windows_compact_positive`: compact CumR > 0 in both 2025_H2 and 2026_JAN_JUL.
7. `response_scale_supportive`: in pooled recent, COMPACT+HIGH meanR > COMPACT+(LOW+MID) meanR with at least 2 fills in each compared group.
8. `large_not_rescued_by_high_response`: LARGE+HIGH meanR <= COMPACT+HIGH meanR.
9. `vf_maturity_supportive`: within compact recent fills, VF2PLUS meanR >= VF1 meanR, when both groups have >=2 fills.
10. `historical_compact_improves_baseline`: historical compact meanR > historical all-fill meanR.

## Verdict
- `PASS_MECHANISTIC_PARENT_COMPRESSION`: >=8/10 gates including gates 1–6.
- `WATCH_PARENT_COMPRESSION_PARTIAL`: >=6/10, gates 1–3 and 6 pass, but strict bootstrap/interaction support incomplete.
- Else `FAIL_NO_ROBUST_PARENT_COMPRESSION_MECHANISM`.

## Guardrail
This is reused-data mechanism research, not fresh OOS and not a live router. No parent-range cutoff, response-ratio cutoff, or VF split is promoted to trading from LAB021. Any executable router must be separately preregistered and replicated. Live allocation remains 0.