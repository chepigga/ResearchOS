# LAB012 post-run reporting correction v001b

This correction is applied **after** the first complete canonical replay and does not change any research inputs, signal rules, execution logic, economics, or numeric outcomes.

The preregistered verdict `REACCEL_SELECTS_EDGE_BUT_WAITING_TOO_LATE` is defined to apply when the *earlier same-signal digestion entry itself has positive EV* while the actual delayed MICRO_REACCEL entry fails the primary economics gate.

The runner mistakenly checked whether `(MICRO_R - EARLY_R) > 0` instead of whether `EARLY_R > 0`.

Correction:
- add `early_entry_ev`, `early_entry_pf`, and `micro_entry_ev` to the same-signal diagnostic;
- use `early_entry_ev > 0` for the preregistered verdict branch;
- update report text accordingly.

No trading/research rule changed.

Patched runner SHA-256: `09931377bb6258051e6de76b8bd3b56f92bf3cd06ea8ff2ec54751c72aea993a`.