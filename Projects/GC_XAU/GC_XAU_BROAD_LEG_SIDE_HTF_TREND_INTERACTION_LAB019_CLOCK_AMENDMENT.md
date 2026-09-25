# GC_XAU LAB019 — CAUSAL CLOCK AMENDMENT

Frozen before interaction outcomes are calculated: 2026-09-25

The compact LAB018 event-clock representation stores the exact XAU entry minute (ceil of the 0/30-second GC signal clock), not the original second.

To make the HTF state provably non-leaking without reconstructing seconds from outcomes, the operational HTF cutoff for LAB019 is frozen as:

HTF_cutoff = entry_minute - 1 millisecond.

Therefore an H1/H4 bar whose close timestamp equals the entry minute is not used; the latest bar with close < entry minute is used.

This is intentionally conservative:
- it can make an exact-boundary signal use one older completed H1/H4 bar;
- it can never use a bar that completed after a :30-second signal;
- no outcome is used to decide this convention.

All other prereg rules are unchanged.
