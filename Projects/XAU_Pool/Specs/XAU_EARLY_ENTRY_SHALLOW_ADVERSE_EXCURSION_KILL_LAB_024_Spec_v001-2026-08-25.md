# XAU_EARLY_ENTRY_SHALLOW_ADVERSE_EXCURSION_KILL_LAB_024 — Spec v001

Date: 2026-08-25
Status: PREREGISTERED / PRE-HOLDOUT

## Question
Does the causal shallow adverse excursion identified by LAB023 become a useful management signal when the frozen early digestion market entry is already live?

## Frozen lineage
- Canonical XAU M1 bid/ask data SHA-256: `db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b`.
- Strong-bias / digestion / early-entry universe is exactly the LAB012/LAB019 lineage.
- Discovery: `break_time < 2024-01-01`.
- Confirmation: `2024-01-01 <= break_time < 2025-07-01`.
- Holdout `>=2025-07-01` remains sealed.
- No new entry selector, context model, or probability model is introduced.

## Frozen baseline
Early digestion market entry:
- next M1 open after digestion close;
- BUY at AskOpen, SELL at BidOpen;
- baseline SL distance `0.50 ATR_touch`;
- TP1.5 distance `0.75 ATR_touch`;
- TP2.0 distance `1.00 ATR_touch`;
- max horizon 60 minutes;
- commission proxy `$0.05` XAU price-equivalent round turn;
- same-bar baseline TP+SL = LOSS.

## Primary management: SHALLOW_AE_KILL_010
Immediately after the frozen market entry, arm one executable protective kill level:
- BUY kill level = `baseline_entry - 0.10 ATR_touch` and is triggered by BidLow touching/crossing it;
- SELL kill level = `baseline_entry + 0.10 ATR_touch` and is triggered by AskHigh touching/crossing it.

Execution:
- kill executes at the frozen kill price when touched;
- if the first post-entry quote opens beyond the kill level, execute at the worse opening quote (BUY exit `min(BidOpen, kill)`, SELL exit `max(AskOpen, kill)`), capped at the frozen baseline SL loss if the gap crosses SL;
- baseline SL remains active and has precedence if already breached beyond the protective threshold;
- because M1 OHLC does not reveal intrabar order, if TP and kill are both touched in the same M1 bar, count KILL first (conservative); if SL and kill are both touched, count SL if the executable opening/barrier geometry implies SL was already crossed, otherwise KILL at its level; no TP credit on ambiguous kill/TP bars.
- if kill is never touched, hold the original baseline position to frozen TP/SL/time-stop.

R reporting:
- 1R remains the frozen baseline risk `0.50 ATR_touch`, so a perfect 0.10 ATR kill is approximately `-0.20R` gross before commission.

## Secondary sensitivity — diagnostics only
Protective adverse-excursion depths:
- `0.05 ATR`, `0.15 ATR`, `0.20 ATR`.
No depth may replace 0.10 ATR as the primary verdict after Confirmation.

## Comparisons
1. Same eligible-universe frozen market-entry baseline.
2. Primary SHALLOW_AE_KILL_010 independent economics.
3. Primary serial economics.
4. Paired management-minus-baseline R on identical trades and weekly-cluster bootstrap.
5. Triggered vs non-triggered cohort: baseline EV, TP rate, managed EV.
6. Eventual baseline TP vs SL damage/savings decomposition.
7. BUY/SELL and Discovery/Confirmation transfer.
8. TP2.0 and +$0.10 cost-stress diagnostics.

## Primary gates
- G0 data/hash/causality PASS; holdout sealed.
- G1 power: Confirmation serial N >= 500 and >= 5 trades/week.
- G2 Confirmation primary serial EV > 0 and PF > 1.
- G3 weekly-cluster primary EV lower 95% CI > 0.
- G4 paired manager-minus-baseline mean > 0 and weekly lower 95% CI > 0.
- G5 Discovery independent EV > 0 and Confirmation independent EV > 0.
- G6 BUY EV > 0 and SELL EV > 0.
- G7 TP2.0 primary EV >= 0.
- G8 +$0.10 stress EV > 0.
- G9 prop proxy: max DD <= 20R and worst day > -16R.
- G10 triggered cohort improves by >= +0.20R versus its own frozen baseline EV.
- G11 non-triggered cohort retains positive frozen/managed edge and is not damaged by the rule.

## Verdict labels
- `SHALLOW_ADVERSE_EXCURSION_KILL_EDGE`
- `SHALLOW_KILL_IMPROVES_BUT_NOT_POSITIVE`
- `SHALLOW_KILL_POSITIVE_BUT_NOT_ROBUST`
- `SHALLOW_KILL_SAVES_LOSERS_BUT_DESTROYS_WINNERS`
- `NO_SHALLOW_ADVERSE_EXCURSION_KILL_EDGE`
- `INVALID_DATA_CAUSALITY`

No threshold rescue, model rescue, holdout opening, EA authorization or live allocation is allowed from this LAB alone.
