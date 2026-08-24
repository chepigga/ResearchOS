# LAB018 pre-run performance patch v002

After v001, feature construction still exceeded the execution window. No LAB018 model outcomes or target metrics were inspected.

Patch scope is performance-only:
- precompute M15/H1 pivot arrays (`confirm_time`, `pivot_time`, `price`);
- replace per-event Pandas dataframe filtering/sorting with the mathematically identical causal prefix lookup using `searchsorted` on `confirm_time`, then the same lookback, positive signed-distance filter, and nearest-distance argmin.

No pivot definition, lookback, destination identity, topology feature, role label, model, threshold, gate, entry, SL, TP, target, split, or holdout rule changed.

Patched runner SHA-256: `79f0e08dee7071b128b8e723e81774d94d10d39269d712b68a9837fc6a15cb80`

Feature-only profiling after patch:
- frozen LAB017 feature build: ~12.6 s for 4,777 events;
- LAB018 topology build: ~9.2 s for 4,777 events.
