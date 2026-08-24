# LAB019 pre-run schema patch v001

No LAB019 verdict/report metrics were read before this patch.

The replay failed after trade simulation because one call to `baseline_stats()` passed the literal string `"BASELINE"` in the parent-module argument position. The patch changes only that call to pass the already loaded frozen LAB012 parent module.

Management simulation, universe, entry, HOLD/KILL logic, timers, barriers, costs, targets and gates are unchanged.

Patched LAB019 runner SHA-256: `51ee9d4a30d41e24bea7b4679b7351d523b315c227028ba45933fd1b019d1359`.
