# XAU_LSAR_FD_EVENT_STUDY_LAB_001 — Core Report

## Scope
Central frozen families: `LS_RH30_B10` and `FD_W5_T1.75`. Full M1 Bid/Ask 2022-06-01—2026-07-23. Selection uses Discovery and WF only.

## Population
- Event records: 141,063
- Discovery: 71,270
- WF: 34,893
- Sealed: 34,900 counts only in the selection report.

## Phase-1 result
No central family passed the preregistered gate.

## Key finding
The dominant result is directional asymmetry:
- reversal after DOWN liquidity sweeps / displacement is positive in Discovery and WF;
- reversal after UP events is negative or unstable;
- neither mechanism beats the matched-event null strongly enough to qualify as an independent edge.

This is consistent with a long-run bullish XAU drift contaminating reversal outcomes. The event itself does not yet add enough information beyond direction/regime.

## Verdict
- `LS_RH30_B10`: NO-GO as a standalone symmetric reversal event.
- `FD_W5_T1.75`: NO-GO as a standalone symmetric failed-displacement event.
- Sealed OOS remains closed for model selection.
- No entry/exit tournament is authorised.

## Next research implication
Before abandoning the broader concept, the only defensible continuation is a preregistered asymmetric-response layer that explicitly measures reclaim quality, second-push failure, and response ratio, then compares it against a direction- and regime-matched random-time null. Threshold tuning of the current core event definitions is prohibited.
