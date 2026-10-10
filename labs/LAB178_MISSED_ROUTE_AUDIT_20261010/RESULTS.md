# LAB178 — MISSED ROUTE STAGE AUDIT

Research-only BTC M5 2021–2026, frozen prior LABs. 2754 retrospective waves; 2334 missed by LAB176.

## Wave-level diagnostics
- Among 947 hindsight pullback waves with no LAB171 routes: 900 had a basic raw LAB171 signal, 140 had RR>=1.5, 84 had RR>=1.5 and freshness, **none** passed final same-side de-overlap. 807/947 had no geometric RR>=1.5 candidate.
- All 712 LAB171-but-not-LAB175 waves had at least one fresh RR>=1.5 LAB171 route. LAB171 and LAB175 use **different initial detectors**, so don't call them blocked by a single gate.
- Of 221 waves lost by LAB176 6h cooldown, 138 recovered by one alternative same-level clustering heuristic.

## Alternative causal near-target grouping
From 7311 LAB175 candidates, group by engine,side,target_type, target within 0.1 ATR, and <=24h since last same-key appearance, retaining first occurrence of cluster. **5473 first-of-cluster** (~80.5/month), vs 3630 (~53.4/month) on LAB176 fixed 6h. Historical wave coverage **536/2754 (19.5%)**, vs LAB176 420/2754 (15.3%). Not proven independent trades; level-price heuristic is not level identity or orderbook liquidity.

## Fast wave anatomy
366 no-qualifying-pullback historical waves: median 1.71h. At first 25% of wave duration, 285/366 had positive direction displacement; median fraction 10.5% of full wave net displacement in positive-net denominator subset. Future endpoints are for audit only, not runtime signal.

## Limits
No Profit Factor, EV, live fills, costs, or Crowd/OI/Profile; don't extrapolate profitability. LAB169 2754 waves != canonical LAB161 2680. Next: single common causal detector; origin-borne level identity; direct impulse events; broker specs before executable EA. Local reproducibility files: LAB178_WAVE_STAGE_AUDIT.csv, LAB178_STAGE_FUNNEL.csv, LAB178_LIQUIDITY_CLUSTERS.csv, LAB178_NO_PULLBACK_IMPULSE_AUDIT.csv, lab178_audit.py, LAB178_REPORT.md.
