# LAB160c — GATE RELAXATION × PROFILE INCREMENTAL REPLAY
Frozen before calculation, 2026-10-10. Parent 2fc655be226af63035457d73b82a09893c27f377.

Question: can additional signals admitted by weaker gates improve frequency and returns; does a predeclared profile rule help those additional signals?
Scope: same 2021–2024 development history and exact LAB155/LAB159 execution assumptions. Not new OOS. Cost2.81/7.5bps, risk0.25%, HALF_TP3_LOCK2, two positions only same side with first MTM>=0, LOCK025 stop transfer. Same priorities and entry prices, no execution optimization.

Controls OLD = original506raw; OLD_PROFILE = R48_NOT_b.
R48 relaxations (one at a time, existing 4/6-bar acceptance and 7th-bar entry unchanged):
- R48_RETEST: remove no-retest requirement; retain mean-margin q60 and OI q60.
- R48_OI: remove OI q60; retain no-retest and mean-margin q60.
- R48_BOTH: remove both; retain mean-margin q60.
Every R48 variant is run without profile and with original NOT_b on all R48.

A relaxations keep extension EXT80, H4 phase CONT/REACCEL and SWING3 unchanged:
- A_Z075: add qualifying abs(Z) upward crossing0.75 instead of1; OI70 unchanged.
- A_OI50: original Z crossing1; OI threshold q50 instead ofq70.
- A_Z075_OI50: both changes.
Each is a union with original A raw signals, deduplicated by source/time/side, because a lower crossing threshold is not a nested trigger universe. Hence these are additional-trigger rules, not literal replacement of old crossings. Priority unchanged. Companion PROFILE applies R48_NOT_b and D-only to NEW A events; existing A/B3/EARLY are preserved. D-only on new A is an exploratory hypothesis from LAB158, not validated by LAB159.

No search over thresholds or selection on new results. Publish all14 arms×2costs. Frozen original distribution thresholds are TRAIN-derived and thus development-fitted.
Report same48-month denominator; portfolio N,EV,PF,R/month,MTM DD; annuals; new raw events standalone with identical exits but no add-on transfer; actually accepted new events; baseline retained/displaced and changed outcomes. Difference in portfolio is not simply sum of standalone new signals due to competition and stop transfer.

Baseline gate: reproduce LAB159 stress OLD N300 and OLD_PROFILE N251 and published EV/PF/Rmonth/DD within reported rounding. Also compare original raw keys against reconstructed R48_HIGH, and data entry indices against source times. If mismatch investigate before reporting.
Uncertainty: paired monthly bootstrap portfolio delta, descriptive only; no multiplicity correction. All history already researched. Profile reconstructed M5 uniform volume within high/low, trailing24h40bins. Inherit historical flow timestamp availability/missing-bar handling and OHLC execution conventions; exact lineage replay is not tick-verified live execution. No production change.

Implementation audit before final runs: original506 raw records include40 repeated source/time/side keys. Preserve their original multiplicity in every arm; deduplicate ONLY newly generated additions. Use occurrence-specific event IDs for portfolio attribution. Removing inherited duplicates would change baseline execution and is outside this comparison.

Matched-control amendment: after the initial14-arm run, add6 NEW_ALL controls so the old R48_NOT_b universe is held fixed on both sides of each incremental profile comparison. NEW_ALL preserves every old-profile raw event and admits all corresponding new events. Compare it to the already specified PROFILE arm; no new threshold or shape rule is fitted. This is a necessary decomposition of the original question, not an OOS extension. Publish all20 arms, including adverse outcomes.
