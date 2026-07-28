# AK47 H1 Post-M3 Matched Control Lab 001

## Scope
- Real M3 baseline trades from `ReportTester-4.xlsx`.
- Each entry immediately following an M3 exit was matched to a non-post-M3 entry of the same direction with similar pre-entry H1 geometry.
- Matching features were available before entry and did not use outcomes.

## Result
- Treated post-M3 entries: 117
- Post-M3 mean: -0.0141R
- Matched non-M3 controls: +0.0655R
- Paired delta: -0.0795R
- Bootstrap 95% CI: [-0.4356R, +0.2802R]
- Post-M3 win rate: 41.0%
- Control win rate: 47.0%

## Monthly paired delta
- 2026-01: +0.471R
- 2026-02: -0.138R
- 2026-03: +0.046R
- 2026-04: -0.142R
- 2026-05: -0.683R
- 2026-06: +0.001R
- 2026-07: -0.539R

## Interpretation
The average post-M3 entry was weaker than a geometrically similar non-M3 entry, but the confidence interval crosses zero. Therefore a universal causal post-M3 penalty is not established.

The weakness is concentrated primarily in May and July, while January shows the opposite effect. This supports a regime-dependent explanation rather than a universal cooldown rule.

## Verdict
- Universal post-M3 lock: not supported.
- H1 bar geometry alone: insufficient.
- Next causal extension: include tick-level approach, repeated level crossings, immediate Bid/Ask acceptance and short-horizon MFE/MAE ordering.
