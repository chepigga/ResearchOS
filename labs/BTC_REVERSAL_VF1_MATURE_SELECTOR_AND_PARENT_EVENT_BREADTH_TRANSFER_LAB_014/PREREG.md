# BTC_REVERSAL_VF1_MATURE_SELECTOR_AND_PARENT_EVENT_BREADTH_TRANSFER_LAB_014

## Question
Can the causal `VF1_MATURE` mechanism from LAB013 preserve positive recent economics while materially expanding trade frequency by broadening only the upstream parent-impulse universe and frozen router breadth?

## Frozen execution / maturity
- Exact LAB013 execution geometry: reversal-side `LIMIT_R0.50_T60`, no market fallback.
- SL = 1.0 × parent event M15 high-low range from filled limit.
- TP = 1.5R primary.
- Same-bar SL+TP ambiguity = SL-first.
- Primary cost = 5 bps round-trip notional.
- Episode definition = selected REV opportunities separated by >7 calendar days.
- `VF1_MATURE`: a real opportunity is admitted only when at least one earlier virtual limit in the same 7d episode has actually filled strictly before current event time. Prior virtual trade outcome is NOT required.

## Frozen router model
To avoid refitting the selector after breadth expansion:
1. Build the canonical parent universe with impulse threshold = trailing 30d 97.5th percentile and 4h cooldown.
2. On DEV 2021-2024 only, freeze the exact LAB003/LAB005 CORE logistic CONT/REV models and 24h tail labels.
3. Freeze router-confidence cutoffs from the canonical DEV score distribution:
   - T20 = q80
   - T25 = q75
   - T30 = q70
   - T40 = q60
4. For broader parent universes, DO NOT refit models or recalibrate confidence thresholds. Score broader events with the same frozen models and thresholds.
5. Execute only events routed `REV` and above the requested frozen breadth threshold.

## Parent-event breadth grid
Trailing 30d impulse quantile, causal and shifted before current bar:
- P975 = 97.5th percentile baseline
- P970 = 97.0th
- P960 = 96.0th
- P950 = 95.0th

Cross with router breadth T20/T25/T30/T40.

### Primary cell
`P960_T30` is fixed before outputs.

### Baseline
`P975_T20` = frozen LAB013 lineage.

All other cells are stability audits only. No post-result winner selection is authorized.

## Evaluation windows
Primary reused transfer windows:
- 2025_H2 = 2025-07-01 through 2025-12-31
- 2026_JAN_JUL = 2026-01-01 through 2026-07-31
- pooled recent = both windows, 13 calendar months total

August 2026 is already consumed and may be shown as descriptive audit only; it cannot promote this LAB.

## Metrics
For every grid cell and window report:
- selected REV opportunities
- mature admitted opportunities
- real fills
- fills/month
- mean net R per filled trade
- cumulative net R
- PF
- max closed-equity DD in R
- max consecutive losses
- 7d episode count / positive episodes
- worst episode R
- top episode share of positive R
- leave-one-episode-out worst remaining R
- episode-cluster bootstrap 95% CI of mean R/opportunity

Also report frequency expansion vs baseline VF1.

## Primary promotion gates: P960_T30
1. 2025_H2 mature fills >= 18 (>=3.0/month).
2. 2026_JAN_JUL mature fills >= 21 (>=3.0/month).
3. pooled mature fills >= 39 (>=3.0/month).
4. 2025_H2 mean net R/fill >= +0.30R.
5. 2026_JAN_JUL mean net R/fill >= +0.30R.
6. PF >=1.5 in both recent windows.
7. max DD <=2.5R in both recent windows.
8. cumulative R positive in both recent windows.
9. pooled cumulative R retains >=90% of baseline `P975_T20/VF1` pooled R.
10. pooled cluster-bootstrap CI lower bound >0.
11. pooled leave-one-episode-out worst remaining R >0.
12. plateau support: at least 2 of four adjacent cells (`P970_T30`, `P960_T25`, `P960_T40`, `P950_T30`) have positive EV/fill in both recent windows, PF>1.3 pooled, and >=2.0 mature fills/month pooled.

## Verdict
- `PASS_VF1_BREADTH_FREQUENCY_TRANSFER`: >=10/12 gates AND gates 1,2,3,4,5,6,8,12 pass.
- `WATCH_VF1_BREADTH_QUALITY_BUT_FREQ_SHORT`: both recent windows positive, EV/fill >0, PF>1, pooled fills/month > baseline, but PASS criteria fail mainly on frequency/plateau.
- `FAIL_VF1_BREADTH_DESTROYS_EDGE`: otherwise.

## Scientific restrictions
- No threshold/model/entry/SL/TP tuning after output inspection.
- No year labels, future outcomes, post-impulse state or virtual outcome are used to activate VF1.
- Broader parent events are scored by the canonical frozen router, not a newly trained breadth-specific router.
- This is research only; no EA/live allocation is authorized by LAB014 alone.
