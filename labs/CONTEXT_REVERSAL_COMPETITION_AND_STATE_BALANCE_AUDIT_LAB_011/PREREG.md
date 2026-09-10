# CONTEXT_REVERSAL_COMPETITION_AND_STATE_BALANCE_AUDIT_LAB_011 — PREREG

Purpose: diagnose why the LAB010 Reversal score activates frequently while Current Context is rarely REVERSAL. This is an indicator-behavior audit only; no PnL/edge optimization and no weight/threshold changes.

Frozen engine: `CONTEXT_INDICATOR_PUBLIC_SPEC_GAP_CLOSURE_AND_NEXT_CONTEXT_LAB_010` exactly as persisted. Dataset: BTCUSDT H1 2020-01..2026-07 -> frozen H4/D1 causal clock.

Primary questions:
1. When smoothed Reversal score is strongest or near-strongest, which competing state defeats it?
2. How much suppression is caused by raw score competition vs 3-bar smoothing vs inertia +5 vs min-hold vs challenger-gap?
3. Does Reversal commonly appear as Next Context shortly before transitions even when it does not become Current Context?
4. Is rarity concentrated in specific volatility regimes or years, or structurally persistent?

Frozen diagnostics:
- Recompute four raw and 3-bar smoothed scores from LAB010 without modifying formulas.
- Rank Reversal among four scores on every warmed bar.
- Buckets: rank1, rank2, rank3/4; score margin to winner; score quantiles.
- Counterfactual state streams, diagnostic only:
  A RAW_WINNER: highest raw score each bar, no smoothing/state machine.
  B SMOOTH_WINNER: highest 3-bar smoothed score, no state machine.
  C SMOOTH_PLUS_INERTIA: +5 current-state bonus, no min-hold/gap.
  D FULL_MACHINE: frozen LAB010.
  The difference in REVERSAL counts between adjacent stages is the suppression attribution.
- For every bar where Reversal is the top smoothed challenger but FULL_MACHINE remains non-Reversal, classify blocker: current-state inertia, minimum-hold, challenger-gap, or other/tie. Classification must follow frozen LAB010 rules only.
- Report dominant winner over Reversal by EXPANSION/PULLBACK/RANGE and score-margin distribution.
- Report by year and volatility state (`LOW <0.80`, `HIGH >1.35`, else NORMAL`).
- Next Context audit: frequency Reversal appears as next_context; transition conversion rate from prior-bar Next=REVERSAL into realized REVERSAL transition; compare with other next_context states.
- Transition adjacency: on bars within 1, 2, 3 H4 bars before any realized transition, report Reversal rank/share.

Primary interpretation gates (diagnostic, not promotion):
- SCORE_COMPETITION_DOMINANT if >=60% of lost Reversal opportunities are already lost at SMOOTH_WINNER stage vs RAW/SMOOTH rank competition.
- STATE_MACHINE_SUPPRESSION_DOMINANT if >=60% of lost Reversal opportunities occur after Reversal is SMOOTH_WINNER but FULL_MACHINE remains non-Reversal.
- MIXED_SUPPRESSION otherwise when both materially contribute.
- REVERSAL_NOT_STRUCTURALLY_RARE if FULL_MACHINE Reversal share >=0.5%; otherwise REVERSAL_STRUCTURALLY_RARE remains true.

Hard integrity gates:
- Frozen LAB010 Current Context must reproduce exactly, zero mismatches.
- No score/state formula changes.
- Causality not re-tuned; use frozen closed-clock engine.

Outputs: summary.json, REPORT.md, stage_counts.csv, blocker_counts.csv, winner_over_reversal.csv, year_balance.csv, volatility_balance.csv, next_context_conversion.csv.
