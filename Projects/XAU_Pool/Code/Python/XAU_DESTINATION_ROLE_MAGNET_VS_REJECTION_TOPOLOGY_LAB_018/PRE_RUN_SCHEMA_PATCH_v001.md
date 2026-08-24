# LAB018 pre-run schema patch v001

The first fit attempt failed before any model was fit or any LAB018 outcome was produced because `nearest_type` appeared twice in the combined model column list: once from the frozen LAB017 room baseline and once from the topology category list.

Patch scope is schema-only:
- topology-only model keeps `nearest_type`;
- combined models include `nearest_type` exactly once by removing duplicate categorical names already present in the LAB017 baseline.

No feature value, destination definition, topology rule, role label, learner, threshold, gate, entry, SL, TP, target, split, or holdout rule changed.

Patched runner SHA-256: `e9708f3f92c883885885fa74b1d5e59887e67dcb2bf1245f8fa04bf5ee788a43`
