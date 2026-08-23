# XAU_POST_BREAK_BEHAVIORAL_SEQUENCE_AND_ACCEPTANCE_LAB_008 — v001 REPORT

**Verdict:** `NO_POST_BREAK_PREDICTIVE_MAP`  
**Holdout opened:** `false`

## Primary T+15 — VWAP break behavior

- resolved Confirmation N: **11,790**
- SNAPSHOT AUC: **0.5058**
- SEQUENCE AUC: **0.4969**
- MULTISCALE AUC: **0.4980**
- sequence − snapshot: **-0.0089**
- paired weekly 95% CI: **[-0.0178, +0.0007]**
- Discovery OOF SEQUENCE AUC: **0.5063**
- Brier: **0.2508**

## Scale

| Clock | Snapshot AUC | Sequence AUC | Multiscale AUC |
|---|---:|---:|---:|
| T+5 | 0.5027 | 0.5028 | 0.5080 |
| T+15 | 0.5058 | 0.4969 | 0.4980 |
| T+30 | 0.5051 | 0.5012 | 0.4997 |

## Human-readable T+15 storyline states

- CLEAN_ACCEPTANCE: N **4,035**, future continuation **50.56%**
- TESTED_AND_RECLAIMED: N **1,474**, future continuation **48.51%**
- ACCEPTED_BUT_WEAKENING: N **718**, future continuation **47.91%**
- FAILED_BREAK: N **3,204**, future continuation **50.75%**
- CHOP_UNRESOLVED: N **2,359**, future continuation **48.66%**

## Breadth

- direction -1: N 5,996, AUC **0.4930**
- direction +1: N 5,794, AUC **0.5007**
- HIGH: N 4,010, AUC **0.4939**
- LOW: N 3,295, AUC **0.5030**
- MID: N 4,485, AUC **0.4948**

- anchored-mean control T+15 SEQUENCE AUC: **0.4992**

## Frozen gates

- G0_DATA_CAUSALITY: PASS
- G1_POWER: PASS
- G2_SEQUENCE_AUC: FAIL
- G3_SEQUENCE_BEATS_SNAPSHOT: FAIL
- G4_MULTISCALE_INCREMENTAL: FAIL
- G5_SCALE_BUILD: PASS
- G6_CALIBRATION: FAIL
- G7_STATE_ORDERING: FAIL
- G8_DIRECTION_MIRROR: FAIL
- G9_LEVEL_BREADTH: FAIL
- G10_DISCOVERY_CONFIRMATION_TRANSFER: FAIL

## Interpretation

LAB008 tests whether the evolving post-break story adds information beyond the current snapshot. The verdict above is based on OOS Confirmation and the frozen snapshot-vs-sequence comparison. No entry rule or holdout is opened here.

## Post-hoc target/scale diagnostic — does NOT change the frozen verdict

The primary LAB asked a deliberately hard tradability-style question: after observing the post-break story, can we predict another symmetric +0.50 ATR continuation versus -0.50 ATR failure **from the current decision price**? The answer was no.

A separate exploratory diagnostic asks a more human bias question: after T+15, does the market continue to **accept the new side of the broken level** during the next 30 minutes?

| Future level-relative question | Snapshot AUC | Sequence AUC | Multiscale AUC |
|---|---:|---:|---:|
| terminal price still on break side after 30m | 0.7898 | 0.7932 | 0.7927 |
| >=2/3 of next 30 closes stay on break side | 0.8683 | 0.8706 | 0.8704 |
| no deep reclaim below -0.05 ATR in next 30m | 0.8880 | 0.8923 | 0.8923 |

This changes the interpretation, not the preregistered verdict:

- the post-break state is **highly informative for bias / level acceptance persistence**;
- it is **not informative for an additional +0.50 ATR extension from the already-current price**;
- most bias information is already summarized by the current relation to the broken level, because SEQUENCE adds only ~0.002–0.004 AUC over SNAPSHOT on these exploratory targets.

This is close to the human process in the podcast: first decide that the broken level is now being respected as support/resistance and adopt a directional bias; only then wait for a separate setup. LAB008 therefore suggests separating **bias formation** from **entry timing** rather than forcing one post-break process to do both jobs.