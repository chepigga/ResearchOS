# LAB019 pre-run performance patch v001

No LAB019 outcome was read before this patch.

The initial frozen runner recomputed full M1 numpy arrays inside `management_trade()` for every event, causing pathological runtime. The patch precomputes the same arrays once in `main()` and passes them as a read-only context to each trade simulation.

Research logic is unchanged:
- same frozen LAB012 universe/entry/MICRO_REACCEL;
- same 5-bar primary HOLD/KILL timer;
- same degradation rule;
- same TP/SL intrabar priority;
- same next-open kill execution;
- same gates and secondary sensitivities.

Patched LAB019 runner SHA-256: `c14e70993e82aa8101a49c2b6989843f65d6d7a2c6d1ac3a8872ea798080aa88`.
