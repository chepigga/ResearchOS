# LAB021 pre-run reporting patch v001

The first canonical attempt reached simulation but failed before verdict/report because the reporting helper expected a non-existent `baseline_duration_min_1p5` column.

Research logic is unchanged. The patch only computes baseline median duration from frozen `baseline_exit_time - baseline_entry_time` when a duration column is absent.

- Pre-patch runner SHA-256: `7d4de4232dc0c6a6c1f6af8dccc543537f0c699acc55ff1b2d2f5ad433fe990b`
- Patched runner SHA-256: `3e38dd164f61e36e5e5b30a39b303e50fe585e150f15a804e034a01a79a733f3`
- No probabilities, outcomes, gates, entry/exit rules, features, learner parameters, or thresholds were changed.
