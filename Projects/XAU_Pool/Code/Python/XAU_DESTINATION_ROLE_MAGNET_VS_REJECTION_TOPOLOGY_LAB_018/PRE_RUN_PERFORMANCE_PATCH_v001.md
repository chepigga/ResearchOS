# LAB018 pre-run performance patch v001

The first canonical replay did not reach model outcomes within the execution window. No partial LAB018 metrics were inspected.

Patch scope is performance-only:
- cache each session start index once;
- when estimating current-session destination age, search only inside the current session slice instead of scanning the full 1.45M-row M1 array for every event.

No destination definition, topology feature, role label, model, threshold, gate, entry, SL, TP, target, split, or holdout rule changed.

Patched runner SHA-256: `c719123272d06ccb884527f26701811ecba98e681c562dff0856a38bcd06ecbd`

Patch semantics:
```diff
+ session_starts = {session: first_index}
...
- scan all dataframe rows for current-session extreme occurrence
+ scan only rows session_start:decision_index for the same occurrence
```
