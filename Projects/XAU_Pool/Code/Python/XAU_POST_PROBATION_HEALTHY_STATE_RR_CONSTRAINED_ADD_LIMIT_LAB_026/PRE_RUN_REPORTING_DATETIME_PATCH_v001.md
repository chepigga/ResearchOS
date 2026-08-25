# LAB026 pre-run reporting datetime patch

The first canonical execution reached simulation but failed before verdict/report because frozen LAB025 baseline exit-time columns were loaded as strings while LAB025 serial helpers compare timestamps.

No report/verdict or metrics were read before this patch. Research logic is unchanged.

Patch: parse `baseline_exit_time_1p5` and `baseline_exit_time_2p0` as datetimes when loading frozen LAB025 events.

- patched local LAB026 runner SHA-256: `d8ab4fbcf62832c4195e2118cef4f6e97727efc2396e50d05613b36d01db4304`
- R:R threshold / expiry / health selector / fill logic / gates changed: no
