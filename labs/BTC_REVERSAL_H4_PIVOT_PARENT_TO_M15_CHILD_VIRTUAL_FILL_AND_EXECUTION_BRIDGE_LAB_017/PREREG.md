# BTC_REVERSAL_H4_PIVOT_PARENT_TO_M15_CHILD_VIRTUAL_FILL_AND_EXECUTION_BRIDGE_LAB_017

## Question
Can the frozen orthogonal `H4_7D_PIVOT_SWEEP_RECLAIM` parent population from LAB016 be monetized by moving execution geometry to a causal M15 child signal, while preserving strict non-overlap with the canonical `P975_T25` engine?

## Frozen parent lineage
- Source lineage: LAB016 v2 after timestamp-unit parity fix.
- Parent family: `H4_7D_PIVOT_SWEEP_RECLAIM` only.
- Frozen canonical router cutoff: T25 = 0.31308988842751206.
- Parent must be router side `REV` and pass T25.
- Parent must be outside ±24h of any frozen canonical `P975_T25` selected event.
- Orthogonality is applied at H4-parent time before any M15 child search.
- No parent threshold, 7d pivot definition, router model, cutoff, or overlap window may be changed in this LAB.

## Primary M15 child rule — BREAK_CONFIRM_12H
For each eligible H4 parent, search completed M15 bars strictly after the H4 parent close and no later than 12h after it.

Parent direction semantics are inherited from LAB016:
- high sweep/reclaim: `impulse_dir=+1`; reversal trade is SHORT;
- low sweep/reclaim: `impulse_dir=-1`; reversal trade is LONG.

First qualifying M15 child:
- SHORT case (`impulse_dir=+1`): `M15 close < M15 open` AND `M15 close < previous M15 low`.
- LONG case (`impulse_dir=-1`): `M15 close > M15 open` AND `M15 close > previous M15 high`.

Only the first qualifying completed M15 bar is used. If none appears within 12h, the parent has `NO_CHILD` and creates no virtual order.

## Primary child execution geometry
The H4 bar no longer sets execution distance. The qualifying M15 child sets all execution geometry:
- virtual reversal limit = `child_close + impulse_dir * 0.50 * child_M15_range`;
- child range = `child_high - child_low`;
- limit TTL = 4 M15 bars = 60 minutes after child close;
- no market fallback;
- 1R stop distance = exactly `1.00 * child_M15_range` from filled limit;
- reversal SHORT: SL above entry; TP below entry;
- reversal LONG: SL below entry; TP above entry;
- primary TP = 1.5R;
- same M15 bar touches TP and SL => SL-first;
- if neither touched => time exit at parent H4 event +24h close;
- round-trip cost stress fixed at 5 bps notional, converted to R using stop fraction.

## Causal VF1 maturity
- Build 7d episodes from the ordered M15 child-opportunity stream after strict H4-parent non-overlap.
- A new episode starts when the gap between child opportunities is >7 days.
- Every child creates a shadow/virtual limit whether or not real risk is allowed.
- A current child is `VF1_MATURE` only if a prior child in the same episode had its virtual limit filled strictly before the current child timestamp.
- The outcome of the prior virtual trade is NOT required and is NOT used.
- Real PnL is counted only for `VF1_MATURE` child opportunities.

## Audit-only child rules
These cannot promote the LAB:
1. `COLOR_ONLY_12H`: first M15 bar in reversal direction by candle color only.
2. `TWO_BAR_CONFIRM_12H`: first point where two consecutive completed M15 closes move in the reversal direction; execution geometry comes from the second bar.

All audits keep the same M15 limit/SL/TP/TTL/cost and VF1 logic.

## Evaluation windows
Reused research windows, not fresh holdouts:
- 2025 H2: 2025-07-01 to 2026-01-01 UTC.
- 2026 Jan-Jul: 2026-01-01 to 2026-08-01 UTC.
- pooled recent: 2025-07-01 to 2026-08-01 UTC.
- August 2026: reused audit only.

Historical descriptive audit: 2021, 2022, 2023, 2024, 2025 H1.

## Primary promotion gates — BREAK_CONFIRM_12H
1. Eligible orthogonal H4 parents >=15 in 2025 H2.
2. Eligible orthogonal H4 parents >=15 in 2026 Jan-Jul.
3. Child-found rate >=50% in both recent windows.
4. Real VF1 fills >=4 in 2025 H2.
5. Real VF1 fills >=4 in 2026 Jan-Jul.
6. Mean net R/fill >0 in both recent windows.
7. PF >1.2 in both recent windows.
8. Cumulative R >0 in both recent windows.
9. Pooled frequency >=0.50 real fills/month.
10. Pooled worst leave-one-episode-out remaining R >0.
11. Pooled max closed-equity DD <=4R.
12. Canonical + child union pooled frequency >=2.20 fills/month AND union cumulative R > canonical +12R.

Verdict:
- `PASS_H4_TO_M15_EXECUTION_BRIDGE` = >=10/12 gates AND gates 3,6,7,8,9 all pass.
- `WATCH_H4_TO_M15_BRIDGE` = >=7/12, positive R in both recent windows, PF>1 both, and frequency higher than zero.
- otherwise `FAIL_H4_TO_M15_EXECUTION_BRIDGE`.

## Scientific constraints
- No outcome-known information may select the M15 child.
- No post-child bar may enter the child trigger.
- No threshold retuning after seeing 2025/2026 results.
- Audit variants cannot rescue a failed primary.
- Reused 2025/2026 windows mean even a PASS is research confirmation, not fresh prospective validation.
- No live allocation is authorized by LAB017 alone.