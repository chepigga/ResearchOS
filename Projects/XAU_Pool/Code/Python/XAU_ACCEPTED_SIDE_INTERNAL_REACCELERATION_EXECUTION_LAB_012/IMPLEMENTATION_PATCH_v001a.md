# LAB012 implementation patch v001a

Frozen before canonical rerun; no outcome tables were read from the failed run.

Reporting-only fix:
- changed pandas expression from `groupby('week').diff.mean()` to `groupby('week')['diff'].mean()` in the same-signal timing bootstrap.

No signal, bias, digestion, reacceleration, entry, SL/TP, cost, serial-lifecycle, or gate logic changed.

- patched runner SHA-256: `685ed8d2df96d4b8d93ca68cd1eb7895c31ee6c7f4100df8f663571f77b9ee2b`
- syntax compile: PASS
- holdout remains sealed