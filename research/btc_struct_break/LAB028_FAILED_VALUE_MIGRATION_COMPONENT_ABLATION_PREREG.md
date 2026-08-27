# LAB028 — BTC_FAILED_VALUE_MIGRATION_COMPONENT_ABLATION

Date: 2026-08-27

Objective: decompose the LAB027 failed-value-migration sequence without threshold tuning.

Frozen variants:
A) POC_MIGRATION == OPPOSED (control)
B) OPPOSED + PRIOR_VALUE_ACCEPTANCE (4 consecutive closes outside current value, unchanged from LAB027)
C) OPPOSED + STRUCTURAL_REJECTION (any causal outside-value close followed by completed close back through relevant VA boundary within the frozen 12-bar pre-fill window; unchanged from LAB027)
D) FULL_FAILED_VALUE_MIGRATION = A+B+rejection after accepted run (LAB027 control)

Primary hypothesis: C may preserve the economic effect with materially larger N than D.

Windows due retained M1 coverage: 2024 discovery, 2025 replication, 2026 shadow only.

Primary C gates:
- DISC2024 EV > 0
- REPL2025 EV >= +0.10R
- REPL2025 PF >= 1.30
- REPL2025 N >= 15
- both 2025 half-years non-negative OR weaker half >= -0.05R
- 1.5x cost REPL2025 EV > 0
- overlap current two-engine core <=20% (+/-8 M15 bars)
- portfolio: >=10% trade-count increase, EV >=0.18R, PF >=1.40, DD <=1.35x core, 1.5x cost EV >0

No side selection, no threshold changes, no shortening acceptance window in this LAB.