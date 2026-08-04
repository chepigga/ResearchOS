# Lessons Learned

## 2026-08-04 — XAU_Pool / XAU_POOL_SELECTION_LAB_001

- **Observation:** The candidate pool was negative, while the selected top 4% was positive across IS, OOS-1, OOS-2 and CONTROL.
- **Evidence:** Pool excess ranged from −0.0176R to −0.0316R; selected excess ranged from +0.3240R to +0.3643R; 44/44 months were positive.
- **Lesson:** A weak pool can contain a stable tradable subset; evaluate the selector against a direction/timeframe/month-matched baseline rather than requiring each generator to be profitable.
- **Future impact:** Pool projects must preserve both the raw pool baseline and selection lift.

- **Observation:** The effect came mainly from voting structure rather than the identities of individual mechanics.
- **Evidence:** coincidence block 84% of lift; mechanic flags 7%; regime features 2%; removing regime features preserved the full effect.
- **Lesson:** Agreement/conflict topology can be more informative than indicator identity or generic regime labels.
- **Future impact:** Prioritize a preregistered compact coincidence model and treat regime features as optional until independently useful.

- **Observation:** More trend confirmations correlated monotonically with worse excess and larger EMA stretch.
- **Evidence:** excess declined from approximately −0.02R at zero confirming trend mechanisms to −0.52R at six, while EMA stretch rose from 0.57ATR to about 2.4ATR.
- **Lesson:** Broad trend consensus may be a late-entry/FOMO signature rather than confirmation quality.
- **Future impact:** Test anti-FOMO distance controls only in new sealed data; do not tune them on the known sample.

- **Observation:** Importing reports and code alone does not establish independent reproducibility.
- **Evidence:** raw bytes/hash, primary parquet outputs, fitted models, selected trade tables, logs and environment lock are absent; scripts use `/home/claude/`.
- **Lesson:** A reported PASS and a reproducible checkpoint are separate claims.
- **Future impact:** Candidate promotion requires a complete result bundle and portable rerun instructions.
